import { useEffect, useState } from 'react'
import {
  Badge,
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
  Textarea,
} from '@chakra-ui/react'
import { useLevelingStore } from '@/stores/levelingStore'
import { useChannels } from '@/hooks/useChatHistory'
import { useBirthdaySettings, useUpdateBirthdaySettings } from '@/hooks/useBirthdays'

const BirthdaySettingsCard = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: settings, isLoading } = useBirthdaySettings(selectedGuild)
  const { data: channels = [], isLoading: channelsLoading } = useChannels(selectedGuild)
  const updateSettings = useUpdateBirthdaySettings(selectedGuild)

  const [channelId, setChannelId] = useState<string | null>(null)
  const [template, setTemplate] = useState<string>('Happy birthday, {user}! 🎂')

  useEffect(() => {
    if (settings) {
      setChannelId(settings.channel_id)
      setTemplate(settings.message_template || 'Happy birthday, {user}! 🎂')
    }
  }, [settings])

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Heading size="md" mb={2}>
            Birthday Announcements
          </Heading>
          <Text color="gray.400">Select a guild to configure birthday messages.</Text>
        </CardBody>
      </Card>
    )
  }

  const handleSave = () => {
    updateSettings.mutate({
      channel_id: channelId || null,
      message_template: template,
    })
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Flex justify="space-between" align="center" mb={4} wrap="wrap" gap={3}>
          <Box>
            <Heading size="md">Birthday Announcements</Heading>
            <Text color="gray.400" fontSize="sm">
              Choose the channel and message template used for birthday posts.
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

        <FormControl mb={4}>
          <FormLabel>Announcement Channel</FormLabel>
          <Select
            placeholder="Default (system or first sendable channel)"
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

        <FormControl>
          <FormLabel>
            Message Template <Badge ml={2}>Placeholders: {'{user}'}, {'{username}'}, {'{mention}'}</Badge>
          </FormLabel>
          <Textarea
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            bg="#2A2A2A"
            borderColor="whiteAlpha.200"
            minH="120px"
          />
        </FormControl>
      </CardBody>
    </Card>
  )
}

export default BirthdaySettingsCard
