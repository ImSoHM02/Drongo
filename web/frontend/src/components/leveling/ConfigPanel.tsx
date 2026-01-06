import {
  Card,
  CardBody,
  Heading,
  VStack,
  FormControl,
  FormLabel,
  Input,
  Switch,
  Button,
  Text,
  SimpleGrid,
  Spinner,
  Box,
  NumberInput,
  NumberInputField,
} from '@chakra-ui/react'
import { useState, useEffect } from 'react'
import { useConfig, useUpdateConfig } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { LevelingConfig } from '@/types/leveling'

const ConfigPanel = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: config, isLoading } = useConfig(selectedGuild)
  const updateConfig = useUpdateConfig()
  const [formData, setFormData] = useState<LevelingConfig | null>(null)

  useEffect(() => {
    if (config) {
      setFormData(config)
    }
  }, [config])

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to configure leveling</Text>
        </CardBody>
      </Card>
    )
  }

  if (isLoading || !formData) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Box textAlign="center" py={8}>
            <Spinner size="xl" color="brand.400" />
          </Box>
        </CardBody>
      </Card>
    )
  }

  const handleSave = () => {
    updateConfig.mutate(formData)
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          Leveling Configuration
        </Heading>

        <VStack spacing={4} align="stretch">
          <FormControl display="flex" alignItems="center">
            <FormLabel mb={0}>Enable Leveling</FormLabel>
            <Switch
              isChecked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              colorScheme="brand"
            />
          </FormControl>

          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <FormControl>
              <FormLabel fontSize="sm">Base XP</FormLabel>
              <NumberInput
                value={formData.base_xp}
                onChange={(_, val) => setFormData({ ...formData, base_xp: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Max XP</FormLabel>
              <NumberInput
                value={formData.max_xp}
                onChange={(_, val) => setFormData({ ...formData, max_xp: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Word Multiplier</FormLabel>
              <NumberInput
                value={formData.word_multiplier}
                onChange={(_, val) => setFormData({ ...formData, word_multiplier: val })}
                min={0}
                step={0.1}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Char Multiplier</FormLabel>
              <NumberInput
                value={formData.char_multiplier}
                onChange={(_, val) => setFormData({ ...formData, char_multiplier: val })}
                min={0}
                step={0.1}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Min Cooldown (seconds)</FormLabel>
              <NumberInput
                value={formData.min_cooldown_seconds}
                onChange={(_, val) => setFormData({ ...formData, min_cooldown_seconds: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Max Cooldown (seconds)</FormLabel>
              <NumberInput
                value={formData.max_cooldown_seconds}
                onChange={(_, val) => setFormData({ ...formData, max_cooldown_seconds: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Min Message Chars</FormLabel>
              <NumberInput
                value={formData.min_message_chars}
                onChange={(_, val) => setFormData({ ...formData, min_message_chars: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Min Message Words</FormLabel>
              <NumberInput
                value={formData.min_message_words}
                onChange={(_, val) => setFormData({ ...formData, min_message_words: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Daily XP Cap</FormLabel>
              <NumberInput
                value={formData.daily_xp_cap}
                onChange={(_, val) => setFormData({ ...formData, daily_xp_cap: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Announcement Channel ID</FormLabel>
              <Input
                value={formData.announcement_channel_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    announcement_channel_id: e.target.value || null,
                  })
                }
                bg="#2A2A2A"
                placeholder="Channel ID"
              />
            </FormControl>
          </SimpleGrid>

          <FormControl display="flex" alignItems="center">
            <FormLabel mb={0}>Level Up Announcements</FormLabel>
            <Switch
              isChecked={formData.level_up_announcements}
              onChange={(e) =>
                setFormData({ ...formData, level_up_announcements: e.target.checked })
              }
              colorScheme="brand"
            />
          </FormControl>

          <FormControl display="flex" alignItems="center">
            <FormLabel mb={0}>DM Level Notifications</FormLabel>
            <Switch
              isChecked={formData.dm_level_notifications}
              onChange={(e) =>
                setFormData({ ...formData, dm_level_notifications: e.target.checked })
              }
              colorScheme="brand"
            />
          </FormControl>

          <FormControl>
            <FormLabel fontSize="sm">Blacklisted Channels (comma-separated)</FormLabel>
            <Input
              value={formData.blacklisted_channels}
              onChange={(e) =>
                setFormData({ ...formData, blacklisted_channels: e.target.value })
              }
              bg="#2A2A2A"
              placeholder="channel_id1,channel_id2"
            />
          </FormControl>

          <FormControl>
            <FormLabel fontSize="sm">Whitelisted Channels (comma-separated)</FormLabel>
            <Input
              value={formData.whitelisted_channels}
              onChange={(e) =>
                setFormData({ ...formData, whitelisted_channels: e.target.value })
              }
              bg="#2A2A2A"
              placeholder="channel_id1,channel_id2"
            />
          </FormControl>

          <Button
            colorScheme="brand"
            onClick={handleSave}
            isLoading={updateConfig.isPending}
            mt={4}
          >
            Save Configuration
          </Button>
        </VStack>
      </CardBody>
    </Card>
  )
}

export default ConfigPanel
