import { useEffect, useMemo, useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Flex,
  Heading,
  Select,
  Spinner,
  Stack,
  Text,
} from '@chakra-ui/react'
import { useLevelingStore } from '@/stores/levelingStore'
import { useAIModeOptions, useGuildAIMode, useUpdateGuildAIMode } from '@/hooks/useAIModes'

const AIModeCard = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: modes = [], isLoading: loadingModes } = useAIModeOptions()
  const { data: guildMode, isLoading: loadingGuildMode, isFetching } = useGuildAIMode(selectedGuild)
  const updateMutation = useUpdateGuildAIMode(selectedGuild)

  const [draftMode, setDraftMode] = useState<string>('')

  useEffect(() => {
    if (guildMode?.mode) {
      setDraftMode(guildMode.mode)
    }
  }, [guildMode?.mode])

  const selectedModeDetails = useMemo(
    () => modes.find((m) => m.name === draftMode),
    [modes, draftMode]
  )

  const handleSave = () => {
    if (draftMode) {
      updateMutation.mutate(draftMode)
    }
  }

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Heading size="md" mb={2}>
            AI Mode
          </Heading>
          <Text color="gray.400">Select a guild to view and set its AI mode.</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Flex justify="space-between" align="center" mb={4} wrap="wrap" gap={3}>
          <Box>
            <Heading size="md">AI Mode</Heading>
            <Text color="gray.400" fontSize="sm">
              Choose how the bot responds in this guild.
            </Text>
          </Box>
          {(loadingModes || isFetching || loadingGuildMode) && <Spinner size="sm" color="brand.400" />}
        </Flex>

        <Stack spacing={4}>
          <Select
            bg="#1E1E1E"
            value={draftMode}
            onChange={(e) => setDraftMode(e.target.value)}
            isDisabled={loadingModes || modes.length === 0}
            placeholder={loadingModes ? 'Loading modes...' : 'Select a mode'}
          >
            {modes.map((mode) => (
              <option key={mode.name} value={mode.name}>
                {mode.name}
              </option>
            ))}
          </Select>

          {selectedModeDetails && (
            <Box bg="#2A2A2A" borderRadius="md" p={3}>
              <Stack direction="row" spacing={3} align="center" mb={2} wrap="wrap">
                <Badge colorScheme="purple">{(selectedModeDetails.chance * 100).toFixed(1)}% chance</Badge>
                <Badge colorScheme="red">
                  {(selectedModeDetails.insult_weight * 100).toFixed(0)}% insults
                </Badge>
                <Badge colorScheme="green">
                  {(selectedModeDetails.compliment_weight * 100).toFixed(0)}% compliments
                </Badge>
              </Stack>
              <Text fontSize="sm" color="gray.300">
                Adjusts how often and in what tone the bot replies.
              </Text>
            </Box>
          )}

          <Button
            colorScheme="brand"
            onClick={handleSave}
            isDisabled={!draftMode || updateMutation.isPending}
            isLoading={updateMutation.isPending}
            alignSelf="flex-start"
          >
            Save AI Mode
          </Button>
        </Stack>
      </CardBody>
    </Card>
  )
}

export default AIModeCard
