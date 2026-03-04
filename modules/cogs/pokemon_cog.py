import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


GRAPHQL_URL = "https://graphql.pokeapi.co/v1beta2"
ARTWORK_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png"

POKEMON_QUERY_BY_NAME = """
query GetPokemon($name: String!) {
  pokemon(where: {name: {_eq: $name}}, limit: 1) {
    id
    name
    height
    weight
    pokemontypes(order_by: {slot: asc}) {
      type {
        name
        TypeefficaciesByTargetTypeId {
          damage_factor
          type { name }
        }
      }
    }
    pokemonabilities(order_by: {slot: asc}) {
      is_hidden
      ability { name }
    }
    pokemonstats(order_by: {stat_id: asc}) {
      base_stat
      stat { name }
    }
    pokemonspecy {
      pokemonspeciesflavortexts(where: {language_id: {_eq: 9}}, limit: 1, order_by: {version_id: desc}) {
        flavor_text
      }
    }
  }
}
"""

POKEMON_QUERY_BY_ID = """
query GetPokemonById($id: Int!) {
  pokemon(where: {id: {_eq: $id}}, limit: 1) {
    id
    name
    height
    weight
    pokemontypes(order_by: {slot: asc}) {
      type {
        name
        TypeefficaciesByTargetTypeId {
          damage_factor
          type { name }
        }
      }
    }
    pokemonabilities(order_by: {slot: asc}) {
      is_hidden
      ability { name }
    }
    pokemonstats(order_by: {stat_id: asc}) {
      base_stat
      stat { name }
    }
    pokemonspecy {
      pokemonspeciesflavortexts(where: {language_id: {_eq: 9}}, limit: 1, order_by: {version_id: desc}) {
        flavor_text
      }
    }
  }
}
"""

POKEMON_QUERY_FUZZY = """
query GetPokemonFuzzy($pattern: String!) {
  pokemon(where: {name: {_like: $pattern}}, limit: 10, order_by: {id: asc}) {
    id
    name
  }
}
"""

# Maps common user-friendly prefixes to the PokeAPI suffix format
VARIANT_PREFIXES = {
    "alolan": "alola",
    "alola": "alola",
    "galarian": "galar",
    "galar": "galar",
    "hisuian": "hisui",
    "hisui": "hisui",
    "paldean": "paldea",
    "paldea": "paldea",
    "mega": "mega",
    "gmax": "gmax",
    "gigantamax": "gmax",
}

STAT_SHORT_NAMES = {
    "hp": "HP ",
    "attack": "ATK",
    "defense": "DEF",
    "special-attack": "SPA",
    "special-defense": "SPD",
    "speed": "SPE",
}


class PokemonAPI:
    def __init__(self):
        self._cache: Dict[str, Tuple[dict, datetime]] = {}
        self._cache_duration = timedelta(hours=24)

    def _get_cached(self, key: str) -> Optional[dict]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_duration:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict):
        self._cache[key] = (data, datetime.now())

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Convert user-friendly names like 'alolan vulpix' to API format 'vulpix-alola'."""
        name = name.strip().lower().replace(" ", "-")
        parts = name.split("-", 1)
        if len(parts) == 2 and parts[0] in VARIANT_PREFIXES:
            return f"{parts[1]}-{VARIANT_PREFIXES[parts[0]]}"
        return name

    async def _query(self, session: aiohttp.ClientSession, payload: dict) -> Tuple[bool, Optional[dict], str]:
        try:
            async with session.post(GRAPHQL_URL, json=payload) as response:
                if response.status != 200:
                    return False, None, f"PokeAPI returned status {response.status}"
                data = await response.json()
        except aiohttp.ClientError as e:
            return False, None, f"Failed to reach PokeAPI: {e}"

        if "errors" in data:
            return False, None, data["errors"][0].get("message", "GraphQL error")

        return True, data, ""

    async def fuzzy_search(self, session: aiohttp.ClientSession, name: str) -> List[dict]:
        """Search for Pokemon with names containing the input string."""
        pattern = f"%{name.replace('-', '%')}%"
        payload = {"query": POKEMON_QUERY_FUZZY, "variables": {"pattern": pattern}}
        success, data, _ = await self._query(session, payload)
        if not success:
            return []
        return data.get("data", {}).get("pokemon", [])

    async def get_pokemon(self, session: aiohttp.ClientSession, name: str) -> Tuple[bool, Optional[dict], str]:
        raw_input = name.strip().lower()
        name = self._normalize_name(raw_input)
        cached = self._get_cached(name)
        if cached:
            return True, cached, ""

        is_id = name.isdigit()
        query = POKEMON_QUERY_BY_ID if is_id else POKEMON_QUERY_BY_NAME
        variables = {"id": int(name)} if is_id else {"name": name}

        success, data, error = await self._query(session, {"query": query, "variables": variables})
        if not success:
            return False, None, error

        results = data.get("data", {}).get("pokemon", [])

        # If no exact match, try fuzzy search and return suggestions
        if not results:
            suggestions = await self.fuzzy_search(session, raw_input)
            if suggestions:
                names = [f"`{s['name']}`" for s in suggestions]
                return False, None, f"Pokemon '{raw_input}' not found. Did you mean:\n{', '.join(names)}"
            return False, None, f"Pokemon '{raw_input}' not found"

        pokemon = results[0]
        self._set_cache(name, pokemon)
        if is_id:
            self._set_cache(pokemon["name"], pokemon)
        else:
            self._set_cache(str(pokemon["id"]), pokemon)

        return True, pokemon, ""


def _format_stat_bar(value: int, max_val: int = 255, bar_length: int = 15) -> str:
    filled = round(value / max_val * bar_length)
    return "\u2588" * filled + "\u2591" * (bar_length - filled)


def _format_name(name: str) -> str:
    return name.replace("-", " ").title()


def _compute_type_matchups(pokemon_types: list) -> Dict[str, List[str]]:
    """Compute combined type effectiveness multipliers for a Pokemon's types.

    damage_factor from API: 200 = 2x, 100 = 1x, 50 = 0.5x, 0 = immune.
    For dual types, multiply the factors together.
    """
    combined: Dict[str, float] = defaultdict(lambda: 1.0)

    for pt in pokemon_types:
        for efficacy in pt["type"]["TypeefficaciesByTargetTypeId"]:
            attacking_type = efficacy["type"]["name"]
            factor = efficacy["damage_factor"] / 100
            combined[attacking_type] *= factor

    matchups: Dict[str, List[str]] = {
        "4x": [],
        "2x": [],
        "0.5x": [],
        "0.25x": [],
        "0x": [],
    }

    for atk_type, multiplier in sorted(combined.items()):
        if multiplier == 4:
            matchups["4x"].append(atk_type.title())
        elif multiplier == 2:
            matchups["2x"].append(atk_type.title())
        elif multiplier == 0.5:
            matchups["0.5x"].append(atk_type.title())
        elif multiplier == 0.25:
            matchups["0.25x"].append(atk_type.title())
        elif multiplier == 0:
            matchups["0x"].append(atk_type.title())

    return matchups


def _build_embed(pokemon: dict) -> discord.Embed:
    poke_id = pokemon["id"]
    name = _format_name(pokemon["name"])

    # Flavor text
    description = ""
    species = pokemon.get("pokemonspecy")
    if species:
        flavor_entries = species.get("pokemonspeciesflavortexts", [])
        if flavor_entries:
            description = flavor_entries[0]["flavor_text"].replace("\n", " ").replace("\f", " ")

    embed = discord.Embed(
        title=f"#{poke_id:03d} — {name}",
        description=f"*{description}*" if description else None,
        color=discord.Color.blue(),
    )

    embed.set_thumbnail(url=ARTWORK_URL.format(poke_id))

    # Types
    types = [t["type"]["name"].title() for t in pokemon["pokemontypes"]]
    embed.add_field(name="Type", value=" / ".join(types), inline=True)

    # Height & Weight (decimetres -> m, hectograms -> kg)
    height_m = pokemon["height"] / 10
    weight_kg = pokemon["weight"] / 10
    embed.add_field(name="Height", value=f"{height_m:.1f} m", inline=True)
    embed.add_field(name="Weight", value=f"{weight_kg:.1f} kg", inline=True)

    # Stats bar chart
    stats_lines = []
    for s in pokemon["pokemonstats"]:
        stat_name = STAT_SHORT_NAMES.get(s["stat"]["name"], s["stat"]["name"][:3].upper())
        base = s["base_stat"]
        bar = _format_stat_bar(base)
        stats_lines.append(f"`{stat_name} {bar} {base:>3}`")
    embed.add_field(name="Base Stats", value="\n".join(stats_lines), inline=False)

    # Abilities
    abilities = []
    for a in pokemon["pokemonabilities"]:
        ability_name = _format_name(a["ability"]["name"])
        if a["is_hidden"]:
            ability_name += " *(Hidden)*"
        abilities.append(ability_name)
    embed.add_field(name="Abilities", value=", ".join(abilities), inline=False)

    # Type matchups
    matchups = _compute_type_matchups(pokemon["pokemontypes"])

    weak_parts = []
    if matchups["4x"]:
        weak_parts.append(f"**4x:** {', '.join(matchups['4x'])}")
    if matchups["2x"]:
        weak_parts.append(f"**2x:** {', '.join(matchups['2x'])}")
    if weak_parts:
        embed.add_field(name="Weak To", value="\n".join(weak_parts), inline=False)

    resist_parts = []
    if matchups["0.25x"]:
        resist_parts.append(f"**0.25x:** {', '.join(matchups['0.25x'])}")
    if matchups["0.5x"]:
        resist_parts.append(f"**0.5x:** {', '.join(matchups['0.5x'])}")
    if resist_parts:
        embed.add_field(name="Resistant To", value="\n".join(resist_parts), inline=False)

    if matchups["0x"]:
        embed.add_field(name="Immune To", value=", ".join(matchups["0x"]), inline=False)

    return embed


class PokemonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pokemon_api = PokemonAPI()
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @app_commands.command(name="pokemon", description="Look up a Pokemon by name or Pokedex number")
    @app_commands.describe(name="Pokemon name or Pokedex number")
    async def pokemon_lookup(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        success, pokemon, error = await self.pokemon_api.get_pokemon(self.session, name)
        if not success:
            await interaction.followup.send(f"Error: {error}", ephemeral=True)
            return

        embed = _build_embed(pokemon)
        await interaction.followup.send(embed=embed)

        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()


async def setup(bot):
    await bot.add_cog(PokemonCog(bot))
