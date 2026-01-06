import {
  Card,
  CardBody,
  Heading,
  VStack,
  Box,
  Text,
  HStack,
  Badge,
  Button,
  Spinner,
} from '@chakra-ui/react'
import { useXPFeed } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { formatRelativeTime } from '@/utils/formatters'

const XPFeed = () => {
  const { selectedGuild, feedPaused, setFeedPaused } = useLevelingStore()
  const { data: feed = [], isLoading } = useXPFeed(selectedGuild)

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to view XP feed</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Live XP Feed</Heading>
          <Button
            size="sm"
            onClick={() => setFeedPaused(!feedPaused)}
            colorScheme={feedPaused ? 'green' : 'gray'}
          >
            {feedPaused ? 'Resume' : 'Pause'}
          </Button>
        </HStack>

        {isLoading ? (
          <Box textAlign="center" py={8}>
            <Spinner size="xl" color="brand.400" />
          </Box>
        ) : feed.length === 0 ? (
          <Text color="gray.400">No recent XP activity</Text>
        ) : (
          <VStack align="stretch" spacing={2} maxH="500px" overflowY="auto">
            {feed.map((entry, idx) => (
              <Box
                key={`${entry.user_id}-${entry.timestamp}-${idx}`}
                p={3}
                bg="#2A2A2A"
                borderRadius="md"
                borderLeft="3px solid"
                borderLeftColor="brand.400"
              >
                <HStack justify="space-between" mb={1}>
                  <Text fontWeight="bold" fontSize="sm">
                    {entry.user_name}
                  </Text>
                  <Badge colorScheme="brand">+{entry.xp_awarded} XP</Badge>
                </HStack>
                <HStack spacing={3} fontSize="xs" color="gray.400">
                  <Text>
                    {entry.word_count} words • {entry.char_count} chars
                  </Text>
                  {entry.daily_cap_applied && (
                    <Badge colorScheme="yellow" fontSize="xs">
                      Daily Cap
                    </Badge>
                  )}
                </HStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  {formatRelativeTime(entry.timestamp)}
                </Text>
              </Box>
            ))}
          </VStack>
        )}
      </CardBody>
    </Card>
  )
}

export default XPFeed
