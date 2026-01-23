import { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardBody,
  Flex,
  Heading,
  HStack,
  SimpleGrid,
  Spinner,
  Stack,
  Switch,
  Text,
  Tooltip,
  Badge,
} from '@chakra-ui/react'
import { useLevelingStore } from '@/stores/levelingStore'
import { useGuildCommands, useUpdateGuildCommands } from '@/hooks/useGuildCommands'

const GuildCommandsCard = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: commands = [], isLoading, isFetching } = useGuildCommands(selectedGuild)
  const updateCommands = useUpdateGuildCommands(selectedGuild)
  const [localStates, setLocalStates] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const nextState: Record<string, boolean> = {}
    commands.forEach((command) => {
      nextState[command.name] = command.enabled
    })
    setLocalStates(nextState)
  }, [commands])

  const hasChanges = useMemo(() => {
    if (!commands.length) return false
    return commands.some((command) => (localStates[command.name] ?? command.enabled) !== command.enabled)
  }, [commands, localStates])

  const handleToggle = (name: string) => {
    setLocalStates((prev) => ({
      ...prev,
      [name]: !(prev[name] ?? true),
    }))
  }

  const handleSave = () => {
    updateCommands.mutate(localStates)
  }

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Heading size="md" mb={2}>
            Per-Guild Commands
          </Heading>
          <Text color="gray.400">Select a guild to configure which commands are available.</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Flex justify="space-between" align="center" mb={4} wrap="wrap" gap={3}>
          <Box>
            <Heading size="md">Per-Guild Commands</Heading>
            <Text color="gray.400" fontSize="sm">
              Toggle which slash commands are available for this server. Saving will resync commands immediately.
            </Text>
          </Box>
          <HStack spacing={3}>
            {isFetching && <Spinner size="sm" color="brand.400" />}
            <Button
              colorScheme="brand"
              onClick={handleSave}
              isDisabled={!hasChanges || updateCommands.isPending || isLoading}
              isLoading={updateCommands.isPending}
            >
              Save & Sync
            </Button>
          </HStack>
        </Flex>

        {isLoading ? (
          <Box textAlign="center" py={6}>
            <Spinner size="lg" color="brand.400" />
          </Box>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} spacing={4}>
            {commands.map((command) => (
              <Card key={command.name} bg="#2A2A2A" borderWidth={1} borderColor="whiteAlpha.200">
                <CardBody>
                  <HStack justify="space-between" mb={2}>
                    <Text fontWeight="bold" color="brand.300">
                      /{command.name}
                    </Text>
                    <Tooltip label={command.enabled ? 'Disable for this guild' : 'Enable for this guild'}>
                      <Switch
                        colorScheme="brand"
                        isChecked={localStates[command.name] ?? command.enabled}
                        onChange={() => handleToggle(command.name)}
                      />
                    </Tooltip>
                  </HStack>
                  <Text color="gray.300" fontSize="sm">
                    {command.description || 'No description provided.'}
                  </Text>
                  {command.subcommands && command.subcommands.length > 0 && (
                    <Stack spacing={1} mt={3} direction="row" flexWrap="wrap">
                      {command.subcommands.map((sub) => (
                        <Badge key={sub} colorScheme="purple" variant="subtle">
                          {sub}
                        </Badge>
                      ))}
                    </Stack>
                  )}
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </CardBody>
    </Card>
  )
}

export default GuildCommandsCard
