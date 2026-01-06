import {
  Box,
  Heading,
  VStack,
  Text,
  Spinner,
  Card,
  CardBody,
  Badge,
  HStack,
  Select,
} from '@chakra-ui/react'
import { useState } from 'react'
import { useStats } from '@/hooks/useStats'
import { formatDate } from '@/utils/formatters'

const LogsView = () => {
  const { stats } = useStats()
  const [filterType, setFilterType] = useState<string>('all')

  if (!stats) {
    return (
      <Box textAlign="center" py={12}>
        <Spinner size="xl" color="brand.400" />
        <Text mt={4} color="gray.400">
          Waiting for logs data...
        </Text>
      </Box>
    )
  }

  const filteredEvents = stats.recent_events?.filter(
    (event) => filterType === 'all' || event.type === filterType
  ) || []

  const getEventColor = (type: string) => {
    switch (type) {
      case 'error':
        return 'red.500'
      case 'command':
        return 'brand.400'
      case 'status':
        return 'blue.500'
      case 'system':
        return 'purple.500'
      default:
        return 'green.500'
    }
  }

  const getEventBadgeScheme = (type: string) => {
    switch (type) {
      case 'error':
        return 'red'
      case 'command':
        return 'orange'
      case 'status':
        return 'blue'
      case 'system':
        return 'purple'
      default:
        return 'green'
    }
  }

  return (
    <Box>
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Event Logs</Heading>
        <Select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          maxW="200px"
          bg="#1E1E1E"
        >
          <option value="all">All Events</option>
          <option value="info">Info</option>
          <option value="command">Commands</option>
          <option value="status">Status</option>
          <option value="system">System</option>
          <option value="error">Errors</option>
        </Select>
      </HStack>

      <Card bg="#1E1E1E">
        <CardBody>
          {filteredEvents.length === 0 ? (
            <Text color="gray.400" textAlign="center" py={8}>
              No events found
            </Text>
          ) : (
            <VStack align="stretch" spacing={3}>
              {filteredEvents.map((event, idx) => (
                <Box
                  key={idx}
                  p={4}
                  bg="#2A2A2A"
                  borderRadius="md"
                  borderLeft="4px solid"
                  borderLeftColor={getEventColor(event.type)}
                  _hover={{ bg: '#3A3A3A' }}
                  transition="background 0.2s"
                >
                  <HStack justify="space-between" mb={2}>
                    <Badge colorScheme={getEventBadgeScheme(event.type)} fontSize="xs">
                      {event.type.toUpperCase()}
                    </Badge>
                    <Text fontSize="xs" color="gray.400">
                      {formatDate(event.timestamp)}
                    </Text>
                  </HStack>
                  <Text fontSize="sm">{event.event}</Text>
                </Box>
              ))}
            </VStack>
          )}
        </CardBody>
      </Card>

      {filteredEvents.length > 0 && (
        <Text mt={4} fontSize="sm" color="gray.400" textAlign="center">
          Showing {filteredEvents.length} event(s)
        </Text>
      )}
    </Box>
  )
}

export default LogsView
