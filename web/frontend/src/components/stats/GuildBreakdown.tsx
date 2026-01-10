import {
  Card,
  CardBody,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Text,
  Box,
  HStack,
  Tooltip,
} from '@chakra-ui/react'
import { GuildStats } from '@/types/stats'
import { formatNumber, formatDate } from '@/utils/formatters'

interface GuildBreakdownProps {
  guilds: GuildStats[]
}

const GuildBreakdown = ({ guilds }: GuildBreakdownProps) => {
  if (!guilds || guilds.length === 0) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Heading size="md" mb={4}>
            Guild Breakdown
          </Heading>
          <Text color="gray.400">No guild data available</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          Guild Breakdown
        </Heading>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400">Guild</Th>
                <Th color="gray.400" isNumeric>Messages</Th>
                <Th color="gray.400" isNumeric>Users</Th>
                <Th color="gray.400" isNumeric>Channels</Th>
                <Th color="gray.400" isNumeric>Recent (1h)</Th>
                <Th color="gray.400" isNumeric>DB Size</Th>
                <Th color="gray.400">Last Activity</Th>
                <Th color="gray.400">Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {guilds.map((guild) => (
                <Tr key={guild.guild_id} _hover={{ bg: '#2A2A2A' }}>
                  <Td>
                    <Tooltip label={`ID: ${guild.guild_id}`} placement="top">
                      <Text fontWeight="medium" fontSize="sm" isTruncated maxW="200px">
                        {guild.guild_name}
                      </Text>
                    </Tooltip>
                  </Td>
                  <Td isNumeric>
                    <Text fontSize="sm">{formatNumber(guild.total_messages)}</Text>
                  </Td>
                  <Td isNumeric>
                    <Text fontSize="sm">{formatNumber(guild.unique_users)}</Text>
                  </Td>
                  <Td isNumeric>
                    <Text fontSize="sm">{formatNumber(guild.active_channels)}</Text>
                  </Td>
                  <Td isNumeric>
                    <Badge
                      colorScheme={guild.recent_activity > 0 ? 'green' : 'gray'}
                      fontSize="xs"
                    >
                      {formatNumber(guild.recent_activity)}
                    </Badge>
                  </Td>
                  <Td isNumeric>
                    <Text fontSize="sm">{guild.database_size_mb.toFixed(2)} MB</Text>
                  </Td>
                  <Td>
                    <Text fontSize="xs" color="gray.400">
                      {guild.last_message ? formatDate(guild.last_message) : 'N/A'}
                    </Text>
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      {guild.is_scanning && (
                        <Badge colorScheme="blue" fontSize="xs">
                          Scanning
                        </Badge>
                      )}
                      {!guild.is_scanning && guild.total_messages > 0 && (
                        <Badge colorScheme="green" fontSize="xs">
                          Active
                        </Badge>
                      )}
                      {!guild.is_scanning && guild.total_messages === 0 && (
                        <Badge colorScheme="gray" fontSize="xs">
                          Empty
                        </Badge>
                      )}
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>

        {/* Summary footer */}
        <Box mt={4} pt={4} borderTop="1px solid" borderColor="gray.700">
          <HStack justify="space-between" fontSize="sm" color="gray.400">
            <Text>
              <Text as="span" fontWeight="bold" color="white">
                {guilds.length}
              </Text>{' '}
              total guild{guilds.length !== 1 ? 's' : ''}
            </Text>
            <Text>
              <Text as="span" fontWeight="bold" color="white">
                {formatNumber(guilds.reduce((sum, g) => sum + g.total_messages, 0))}
              </Text>{' '}
              total messages
            </Text>
            <Text>
              <Text as="span" fontWeight="bold" color="white">
                {guilds.reduce((sum, g) => sum + g.database_size_mb, 0).toFixed(2)} MB
              </Text>{' '}
              total size
            </Text>
          </HStack>
        </Box>
      </CardBody>
    </Card>
  )
}

export default GuildBreakdown
