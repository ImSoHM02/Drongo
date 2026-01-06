import { Select, FormControl, FormLabel, Spinner, Box } from '@chakra-ui/react'
import { useGuilds } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'

const GuildSelector = () => {
  const { data: guilds = [], isLoading } = useGuilds()
  const { selectedGuild, setSelectedGuild } = useLevelingStore()

  if (isLoading) {
    return <Spinner size="sm" color="brand.400" />
  }

  return (
    <Box maxW="400px">
      <FormControl>
        <FormLabel>Select Guild</FormLabel>
        <Select
          value={selectedGuild || ''}
          onChange={(e) => setSelectedGuild(e.target.value || null)}
          placeholder="Choose a guild"
          bg="#1E1E1E"
        >
          {guilds.map((guild) => (
            <option key={guild.id} value={guild.id}>
              {guild.name} ({guild.user_count} users)
            </option>
          ))}
        </Select>
      </FormControl>
    </Box>
  )
}

export default GuildSelector
