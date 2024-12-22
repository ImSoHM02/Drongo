import discord
import io
import cairosvg
from typing import Optional

def wrap_text(text: str, max_width: int = 370, indent_x: int = 20) -> str:
    """
    Wrap text to fit within specified width.
    Returns text with SVG tspan elements for line breaks.
    """
    if not text or text == "?":
        return text
        
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        # Approximately calculate if line width exceeds max_width
        # (assumes average character width of 7 pixels)
        if len(' '.join(current_line)) * 7 > max_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Create SVG tspan elements for each line
    wrapped_text = ''
    for i, line in enumerate(lines):
        if i == 0:
            wrapped_text += f'{line}'
        else:
            wrapped_text += f'<tspan x="{indent_x}" dy="20">{line}</tspan>'
    
    return wrapped_text

def calculate_height(feature_desc: str, action_desc: str) -> int:
    """Calculate required SVG height based on content"""
    base_height = 500  # Base height for standard content
    
    # Calculate additional height needed for wrapped text
    feature_lines = len(wrap_text(feature_desc, 50).split('<tspan')) if feature_desc else 0
    action_lines = len(wrap_text(action_desc, 50).split('<tspan')) if action_desc else 0
    
    # Add 20px per line of wrapped text
    additional_height = (feature_lines + action_lines) * 20
    
    return max(600, base_height + additional_height)

def calculate_modifier(score):
    mod = (score - 10) // 2
    return f"+{mod}" if mod >= 0 else str(mod)

def calculate_proficiency_bonus(cr):
    if cr in ["0", "1/8", "1/4", "1/2", "1"]: return "+2"
    cr_num = float(eval(cr)) if "/" in cr else int(cr)
    return f"+{2 + ((cr_num - 1) // 4)}"

def get_xp_for_cr(cr):
    cr_to_xp = {
        "0": "0", "1/8": "25", "1/4": "50", "1/2": "100",
        "1": "200", "2": "450", "3": "700", "4": "1,100",
        "5": "1,800", "6": "2,300", "7": "2,900", "8": "3,900",
        "9": "5,000", "10": "5,900"
    }
    return cr_to_xp.get(str(cr), "0")

async def generate_statblock_image(interaction, name, size, type, alignment, ac,
                                 hp, speed, strength, dexterity, constitution,
                                 intelligence, wisdom, charisma, challenge,
                                 resistances="?", senses="?", languages="?",
                                 feature_name="", feature_desc="", action_name="",
                                 action_desc=""):
    try:
        # Calculate required height
        height = calculate_height(feature_desc, action_desc)
        
        # Read the SVG template
        with open('dnd-statblock.svg', 'r') as f:
            svg_template = f.read()
            
        # Update SVG height
        svg_template = svg_template.replace('height="600"', f'height="{height}"')
        
        # Calculate ability modifiers
        str_mod = calculate_modifier(strength)
        dex_mod = calculate_modifier(dexterity)
        con_mod = calculate_modifier(constitution)
        int_mod = calculate_modifier(intelligence)
        wis_mod = calculate_modifier(wisdom)
        cha_mod = calculate_modifier(charisma)

        # Calculate proficiency bonus
        proficiency_bonus = calculate_proficiency_bonus(challenge)

        # Calculate initiative (based on Dexterity)
        initiative = dex_mod

        # Calculate saving throws (all based on ability scores)
        str_save_mod = str_mod
        dex_save_mod = dex_mod
        con_save_mod = con_mod
        int_save_mod = int_mod
        wis_save_mod = wis_mod
        cha_save_mod = cha_mod

        # Get XP for challenge rating
        xp = get_xp_for_cr(challenge)

        # Wrap only feature and action descriptions
        wrapped_feature_desc = wrap_text(feature_desc, 370) if feature_desc else ""
        wrapped_action_desc = wrap_text(action_desc, 370) if action_desc else ""

        # Replace placeholders with actual data
        replacements = {
            '{{name}}': name,
            '{{size}}': size.capitalize(),
            '{{type}}': type.lower(),
            '{{alignment}}': alignment.lower(),
            '{{ac}}': str(ac),
            '{{initiative}}': initiative,
            '{{hp}}': str(hp),
            '{{speed}}': speed,
            '{{str}}': str(strength),
            '{{dex}}': str(dexterity),
            '{{con}}': str(constitution),
            '{{int}}': str(intelligence),
            '{{wis}}': str(wisdom),
            '{{cha}}': str(charisma),
            '{{strMod}}': str_mod,
            '{{dexMod}}': dex_mod,
            '{{conMod}}': con_mod,
            '{{intMod}}': int_mod,
            '{{wisMod}}': wis_mod,
            '{{chaMod}}': cha_mod,
            '{{strSave}}': str_save_mod,
            '{{dexSave}}': dex_save_mod,
            '{{conSave}}': con_save_mod,
            '{{intSave}}': int_save_mod,
            '{{wisSave}}': wis_save_mod,
            '{{chaSave}}': cha_save_mod,
            '{{damage_resistances}}': resistances,
            '{{senses}}': senses,
            '{{languages}}': languages,
            '{{challenge}}': challenge,
            '{{xp}}': xp,
            '{{proficiencyBonus}}': proficiency_bonus,
            '{{traitName}}': feature_name,
            '{{traitDesc}}': wrapped_feature_desc,
            '{{actionName}}': action_name,
            '{{actionDesc}}': wrapped_action_desc
        }

        for placeholder, value in replacements.items():
            svg_template = svg_template.replace(placeholder, str(value))

        # Convert SVG to PNG
        png_data = cairosvg.svg2png(bytestring=svg_template.encode('utf-8'))

        # Create a Discord file
        file = discord.File(io.BytesIO(png_data), filename='statblock.png')

        # Send the file using followup since we deferred earlier
        await interaction.followup.send(file=file)

    except Exception as e:
        await interaction.followup.send(f"Error generating stat block: {str(e)}")
        raise

def setup(bot):
    async def generate_statblock_command(interaction: discord.Interaction, name: str, size: str,
                                       type: str, alignment: str, ac: int, hp: int, speed: str,
                                       strength: int, dexterity: int, constitution: int,
                                       intelligence: int, wisdom: int, charisma: int,
                                       challenge: str, resistances: Optional[str] = "?",
                                       senses: Optional[str] = "?", languages: Optional[str] = "?",
                                       feature_name: Optional[str] = "",
                                       feature_desc: Optional[str] = "",
                                       action_name: Optional[str] = "",
                                       action_desc: Optional[str] = ""):
        
        # Input validation is handled by Discord's API through register_commands.py
        await interaction.response.defer()
        
        try:
            await generate_statblock_image(
                interaction, name, size, type, alignment, ac, hp, speed,
                strength, dexterity, constitution, intelligence, wisdom,
                charisma, challenge, resistances, senses, languages,
                feature_name, feature_desc, action_name, action_desc
            )
            bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")
            raise

    # Add the command handler to the bot
    bot.tree.add_command(
        discord.app_commands.Command(
            name="generate_statblock",
            description="Generate a D&D-style stat block",
            callback=generate_statblock_command
        )
    )
