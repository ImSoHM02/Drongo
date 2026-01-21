import {
  Box,
  Card,
  CardBody,
  Heading,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Button,
  VStack,
  HStack,
  Text,
  Badge,
  Spinner,
} from '@chakra-ui/react'
import { useState } from 'react'
import { useBotConfig, useUpdateBotName, useUpdateNickname } from '@/hooks/useBotConfig'

interface BotConfigCardProps {
  guildId: string
}

export function BotConfigCard({ guildId }: BotConfigCardProps) {
  const { data: config, isLoading } = useBotConfig(guildId)
  const updateBotName = useUpdateBotName()
  const updateNickname = useUpdateNickname()

  const [botName, setBotName] = useState('')
  const [nickname, setNickname] = useState('')
  const [prevConfig, setPrevConfig] = useState(config)

  // Adjust state while rendering when config changes (React 19 pattern)
  if (config !== prevConfig) {
    setBotName(config?.bot_name || 'drongo')
    setNickname(config?.current_nickname || '')
    setPrevConfig(config)
  }

  const handleUpdateBotName = () => {
    if (botName && botName.trim()) {
      updateBotName.mutate({
        guildId,
        botName: botName.trim().toLowerCase(),
      })
    }
  }

  const handleUpdateNickname = () => {
    updateNickname.mutate({
      guildId,
      nickname: nickname.trim(),
    })
  }

  const handleResetNickname = () => {
    updateNickname.mutate({
      guildId,
      nickname: '',
    })
    setNickname('')
  }

  if (isLoading) {
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

  if (!config) {
    return null
  }

  const triggerPhrase = `oi ${botName.toLowerCase()}`
  const isBotNameChanged = botName.toLowerCase() !== (config.bot_name || 'drongo')
  const isNicknameChanged = nickname !== (config.current_nickname || '')

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={1}>
          Bot Configuration
        </Heading>
        <Text fontSize="sm" color="gray.400" mb={6}>
          Customize the bot's name and appearance for this server
        </Text>

        <VStack spacing={6} align="stretch">
          {/* Trigger Name Configuration */}
          <FormControl>
            <FormLabel fontSize="sm">
              Trigger Name
              {isBotNameChanged && (
                <Badge ml={2} colorScheme="orange" fontSize="xs">
                  Unsaved
                </Badge>
              )}
            </FormLabel>
            <HStack>
              <Input
                value={botName}
                onChange={(e) => setBotName(e.target.value)}
                placeholder="drongo"
                maxLength={32}
                bg="#2A2A2A"
                border="none"
                _focus={{ bg: "#333", borderColor: "brand.400" }}
              />
              <Button
                colorScheme="brand"
                onClick={handleUpdateBotName}
                isLoading={updateBotName.isPending}
                isDisabled={!isBotNameChanged || !botName.trim()}
                size="md"
                minW="80px"
              >
                Save
              </Button>
            </HStack>
            <FormHelperText color="gray.400" fontSize="sm">
              Trigger phrase: <Text as="span" fontWeight="bold" color="brand.400">{triggerPhrase}</Text>
            </FormHelperText>
          </FormControl>

          {/* Nickname Configuration */}
          <FormControl>
            <FormLabel fontSize="sm">
              Server Nickname
              {isNicknameChanged && (
                <Badge ml={2} colorScheme="orange" fontSize="xs">
                  Unsaved
                </Badge>
              )}
            </FormLabel>
            <VStack spacing={2} align="stretch">
              <HStack>
                <Input
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder={config.guild_name || 'Enter nickname'}
                  maxLength={32}
                  bg="#2A2A2A"
                  border="none"
                  _focus={{ bg: "#333", borderColor: "brand.400" }}
                />
                <Button
                  colorScheme="brand"
                  onClick={handleUpdateNickname}
                  isLoading={updateNickname.isPending}
                  isDisabled={!isNicknameChanged}
                  size="md"
                  minW="80px"
                >
                  Save
                </Button>
              </HStack>
              {config.current_nickname && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleResetNickname}
                  isLoading={updateNickname.isPending}
                  borderColor="gray.600"
                  _hover={{ bg: "#2A2A2A" }}
                >
                  Reset to Default
                </Button>
              )}
            </VStack>
            {config.current_nickname && (
              <Text fontSize="sm" color="gray.400" mt={2}>
                Current: <Text as="span" fontWeight="bold" color="white">{config.current_nickname}</Text>
              </Text>
            )}
          </FormControl>

          {/* Info Box */}
          <Box
            p={4}
            bg="#2A2A2A"
            borderRadius="md"
            borderLeft="4px"
            borderColor="brand.400"
          >
            <Text fontSize="sm" color="gray.300">
              <Text as="span" fontWeight="bold" color="brand.400">Note:</Text> The trigger name affects the phrase
              you use to interact with the AI (e.g., "oi drongo"). The nickname only changes how the bot appears in the
              member list and messages.
            </Text>
          </Box>
        </VStack>
      </CardBody>
    </Card>
  )
}
