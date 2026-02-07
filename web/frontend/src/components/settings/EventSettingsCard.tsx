import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardBody,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Select,
  Spinner,
  Text,
} from '@chakra-ui/react'
import { useLevelingStore } from '@/stores/levelingStore'
import { useChannels } from '@/hooks/useChatHistory'
import { useEventSettings, useUpdateEventSettings } from '@/hooks/useEvents'

const EventSettingsCard = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: settings, isLoading } = useEventSettings(selectedGuild)
  const { data: channels = [], isLoading: channelsLoading } = useChannels(selectedGuild)
  const updateSettings = useUpdateEventSettings(selectedGuild)

  const [channelId, setChannelId] = useState<string | null>(null)

  useEffect(() => {
    if (settings) {
      setChannelId(settings.channel_id)
    }
  }, [settings])

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Heading size="md" mb={2}>
            Event Reminders
          </Heading>
          <Text color="gray.400">Select a guild to configure event reminders.</Text>
        </CardBody>
      </Card>
    )
  }

  const handleSave = () => {
    updateSettings.mutate({ channel_id: channelId || null })
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Flex justify="space-between" align="center" mb={4} wrap="wrap" gap={3}>
          <Box>
            <Heading size="md">Event Reminders</Heading>
            <Text color="gray.400" fontSize="sm">
              Choose the channel where event reminders are posted 1 hour before an event starts.
            </Text>
          </Box>
          <HStack spacing={3}>
            {(isLoading || channelsLoading) && <Spinner size="sm" color="brand.400" />}
            <Button
              colorScheme="brand"
              onClick={handleSave}
              isLoading={updateSettings.isPending}
              isDisabled={isLoading || channelsLoading}
            >
              Save
            </Button>
          </HStack>
        </Flex>

        <FormControl>
          <FormLabel>Reminder Channel</FormLabel>
          <Select
            placeholder="Use system channel (default)"
            value={channelId ?? ''}
            onChange={(e) => setChannelId(e.target.value || null)}
            bg="#2A2A2A"
            borderColor="whiteAlpha.200"
          >
            {channels.map((ch) => (
              <option key={ch.id} value={ch.id}>
                #{ch.name}
              </option>
            ))}
          </Select>
        </FormControl>
      </CardBody>
    </Card>
  )
}

export default EventSettingsCard
