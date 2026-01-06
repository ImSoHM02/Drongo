import {
  Box,
  Heading,
  Grid,
  GridItem,
  Card,
  CardBody,
  VStack,
  HStack,
  Text,
  Spinner,
  Button,
  Switch,
  FormControl,
  FormLabel,
  Badge,
} from '@chakra-ui/react'
import { useChatGuilds, useChannels, useRecentMessages, useToggleLogging } from '@/hooks/useChatHistory'
import { useChatStore } from '@/stores/chatStore'
import { formatDate } from '@/utils/formatters'

const ChatHistoryView = () => {
  const { data: guilds = [], isLoading: guildsLoading } = useChatGuilds()
  const { selectedGuild, selectedChannel, setSelectedGuild, setSelectedChannel } = useChatStore()
  const { data: channels = [], isLoading: channelsLoading } = useChannels(selectedGuild)
  const { data: messages = [], isLoading: messagesLoading } = useRecentMessages(
    selectedGuild,
    selectedChannel
  )
  const toggleLogging = useToggleLogging()

  const handleToggleLogging = (guildId: string, enabled: boolean) => {
    toggleLogging.mutate({ guildId, enabled })
  }

  return (
    <Box>
      <Heading size="lg" mb={6}>
        Chat History
      </Heading>

      <Grid templateColumns="300px 250px 1fr" gap={4} h="calc(100vh - 200px)">
        {/* Guild List */}
        <GridItem>
          <Card bg="#1E1E1E" h="100%">
            <CardBody>
              <Heading size="sm" mb={4}>
                Guilds
              </Heading>
              {guildsLoading ? (
                <Spinner size="sm" color="brand.400" />
              ) : (
                <VStack align="stretch" spacing={2}>
                  {guilds.map((guild) => (
                    <Box
                      key={guild.id}
                      p={3}
                      bg={selectedGuild === guild.id ? 'brand.400' : '#2A2A2A'}
                      borderRadius="md"
                      cursor="pointer"
                      onClick={() => setSelectedGuild(guild.id)}
                      _hover={{ bg: selectedGuild === guild.id ? 'brand.500' : '#3A3A3A' }}
                    >
                      <Text fontWeight="bold" fontSize="sm">
                        {guild.name}
                      </Text>
                      <HStack justify="space-between" mt={1}>
                        <Text fontSize="xs" color="gray.400">
                          {guild.message_count} messages
                        </Text>
                        <Badge colorScheme={guild.logging_enabled ? 'green' : 'gray'} fontSize="xs">
                          {guild.logging_enabled ? 'On' : 'Off'}
                        </Badge>
                      </HStack>
                      {selectedGuild === guild.id && (
                        <FormControl display="flex" alignItems="center" mt={2}>
                          <FormLabel mb={0} fontSize="xs">
                            Logging
                          </FormLabel>
                          <Switch
                            size="sm"
                            isChecked={guild.logging_enabled}
                            onChange={(e) => handleToggleLogging(guild.id, e.target.checked)}
                            colorScheme="brand"
                          />
                        </FormControl>
                      )}
                    </Box>
                  ))}
                </VStack>
              )}
            </CardBody>
          </Card>
        </GridItem>

        {/* Channel List */}
        <GridItem>
          <Card bg="#1E1E1E" h="100%">
            <CardBody>
              <Heading size="sm" mb={4}>
                Channels
              </Heading>
              {!selectedGuild ? (
                <Text color="gray.400" fontSize="sm">
                  Select a guild
                </Text>
              ) : channelsLoading ? (
                <Spinner size="sm" color="brand.400" />
              ) : (
                <VStack align="stretch" spacing={2}>
                  {channels.map((channel) => (
                    <Box
                      key={channel.id}
                      p={3}
                      bg={selectedChannel === channel.id ? 'brand.400' : '#2A2A2A'}
                      borderRadius="md"
                      cursor="pointer"
                      onClick={() => setSelectedChannel(channel.id)}
                      _hover={{ bg: selectedChannel === channel.id ? 'brand.500' : '#3A3A3A' }}
                    >
                      <Text fontWeight="bold" fontSize="sm">
                        #{channel.name}
                      </Text>
                      <Text fontSize="xs" color="gray.400" mt={1}>
                        {channel.message_count} messages
                      </Text>
                    </Box>
                  ))}
                </VStack>
              )}
            </CardBody>
          </Card>
        </GridItem>

        {/* Messages */}
        <GridItem>
          <Card bg="#1E1E1E" h="100%">
            <CardBody>
              <Heading size="sm" mb={4}>
                Messages
              </Heading>
              {!selectedChannel ? (
                <Text color="gray.400" fontSize="sm">
                  Select a channel
                </Text>
              ) : messagesLoading ? (
                <Box textAlign="center" py={8}>
                  <Spinner size="xl" color="brand.400" />
                </Box>
              ) : messages.length === 0 ? (
                <Text color="gray.400" fontSize="sm">
                  No messages found
                </Text>
              ) : (
                <VStack align="stretch" spacing={3} overflowY="auto" maxH="calc(100vh - 300px)">
                  {messages.map((message) => (
                    <Box
                      key={message.id}
                      p={3}
                      bg="#2A2A2A"
                      borderRadius="md"
                      borderLeft="3px solid"
                      borderLeftColor="brand.400"
                    >
                      <HStack justify="space-between" mb={2}>
                        <Text fontWeight="bold" fontSize="sm">
                          {message.author_name}
                        </Text>
                        <Text fontSize="xs" color="gray.400">
                          {formatDate(message.timestamp)}
                        </Text>
                      </HStack>
                      <Text fontSize="sm">{message.content}</Text>
                      {message.attachments && message.attachments.length > 0 && (
                        <Badge colorScheme="blue" mt={2} fontSize="xs">
                          {message.attachments.length} attachment(s)
                        </Badge>
                      )}
                    </Box>
                  ))}
                </VStack>
              )}
            </CardBody>
          </Card>
        </GridItem>
      </Grid>
    </Box>
  )
}

export default ChatHistoryView
