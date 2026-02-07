import { Box, Heading, VStack } from '@chakra-ui/react'
import { useLevelingStore } from '@/stores/levelingStore'
import { BotConfigCard } from './BotConfigCard'
import GuildSelector from './leveling/GuildSelector'
import GuildCommandsCard from './settings/GuildCommandsCard'
import AIModeCard from './settings/AIModeCard'
import BirthdaySettingsCard from './settings/BirthdaySettingsCard'
import UpdateSettingsCard from './settings/UpdateSettingsCard'
import EventSettingsCard from './settings/EventSettingsCard'

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
        <BirthdaySettingsCard />
        <EventSettingsCard />
        <UpdateSettingsCard />
        <AIModeCard />
        <GuildCommandsCard />
      </VStack>
    </Box>
  )
}

export default SettingsView
