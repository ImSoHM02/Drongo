import { Box, Heading, VStack } from '@chakra-ui/react'
import { useLevelingStore } from '@/stores/levelingStore'
import { BotConfigCard } from './BotConfigCard'
import GuildSelector from './leveling/GuildSelector'

const SettingsView = () => {
  const { selectedGuild } = useLevelingStore()

  return (
    <Box>
      <Heading size="lg" mb={6}>
        Settings
      </Heading>

      <VStack spacing={6} align="stretch">
        <GuildSelector showUserCount={false} />

        {selectedGuild && <BotConfigCard guildId={selectedGuild} />}
      </VStack>
    </Box>
  )
}

export default SettingsView
