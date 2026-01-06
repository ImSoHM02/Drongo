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
  Progress,
  Text,
  HStack,
  Select,
  Box,
  Spinner,
} from '@chakra-ui/react'
import { useState } from 'react'
import { useLeaderboard } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { calculateLevelProgress } from '@/utils/calculations'
import { formatNumber } from '@/utils/formatters'

const Leaderboard = () => {
  const { selectedGuild } = useLevelingStore()
  const [limit, setLimit] = useState(10)
  const { data: leaderboard = [], isLoading } = useLeaderboard(selectedGuild, limit)

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to view leaderboard</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Leaderboard</Heading>
          <Select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            maxW="150px"
            size="sm"
            bg="#2A2A2A"
          >
            <option value={10}>Top 10</option>
            <option value={25}>Top 25</option>
            <option value={50}>Top 50</option>
          </Select>
        </HStack>

        {isLoading ? (
          <Box textAlign="center" py={8}>
            <Spinner size="xl" color="brand.400" />
          </Box>
        ) : leaderboard.length === 0 ? (
          <Text color="gray.400">No data available</Text>
        ) : (
          <Box overflowX="auto">
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th color="gray.400">Rank</Th>
                  <Th color="gray.400">User</Th>
                  <Th color="gray.400">Level</Th>
                  <Th color="gray.400">XP</Th>
                  <Th color="gray.400">Progress</Th>
                  <Th color="gray.400">Messages</Th>
                </Tr>
              </Thead>
              <Tbody>
                {leaderboard.map((entry) => {
                  const progress = calculateLevelProgress(entry.current_level, entry.total_xp)
                  return (
                    <Tr key={entry.user_id}>
                      <Td>
                        <Text
                          fontWeight="bold"
                          color={
                            entry.position === 1
                              ? 'yellow.400'
                              : entry.position === 2
                              ? 'gray.300'
                              : entry.position === 3
                              ? 'orange.400'
                              : 'white'
                          }
                        >
                          #{entry.position}
                        </Text>
                      </Td>
                      <Td>
                        <Box>
                          <Text>{entry.user_name}</Text>
                          {entry.rank_title && (
                            <Text fontSize="xs" color="brand.400">
                              {entry.rank_title}
                            </Text>
                          )}
                        </Box>
                      </Td>
                      <Td>
                        <Text fontWeight="bold" color="brand.400">
                          {entry.current_level}
                        </Text>
                      </Td>
                      <Td>{formatNumber(entry.total_xp)}</Td>
                      <Td>
                        <Box minW="100px">
                          <Progress
                            value={progress}
                            size="sm"
                            colorScheme="brand"
                            borderRadius="full"
                          />
                          <Text fontSize="xs" color="gray.400" mt={1}>
                            {progress}%
                          </Text>
                        </Box>
                      </Td>
                      <Td>{formatNumber(entry.messages_sent)}</Td>
                    </Tr>
                  )
                })}
              </Tbody>
            </Table>
          </Box>
        )}
      </CardBody>
    </Card>
  )
}

export default Leaderboard
