import {
  Card,
  CardBody,
  Heading,
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Input,
  Button,
  Box,
  Text,
  Progress,
  Spinner,
} from '@chakra-ui/react'
import { useState } from 'react'
import { useUserLookup } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { calculateLevelProgress } from '@/utils/calculations'
import { formatNumber } from '@/utils/formatters'

const UserLookup = () => {
  const { selectedGuild } = useLevelingStore()
  const [userId, setUserId] = useState('')
  const userLookup = useUserLookup()

  const handleLookup = () => {
    if (!selectedGuild || !userId) return
    userLookup.mutate({ guildId: selectedGuild, userId })
  }

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to lookup users</Text>
        </CardBody>
      </Card>
    )
  }

  const userData = userLookup.data

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          User Lookup
        </Heading>

        <VStack spacing={4} align="stretch">
          <HStack>
            <FormControl>
              <FormLabel>Discord User ID</FormLabel>
              <Input
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="Enter user ID"
                bg="#2A2A2A"
              />
            </FormControl>
            <Button
              colorScheme="brand"
              onClick={handleLookup}
              isLoading={userLookup.isPending}
              mt={8}
            >
              Lookup
            </Button>
          </HStack>

          {userLookup.isPending && (
            <Box textAlign="center" py={4}>
              <Spinner color="brand.400" />
            </Box>
          )}

          {userData && (
            <Box p={4} bg="#2A2A2A" borderRadius="md">
              <VStack align="stretch" spacing={3}>
                <HStack justify="space-between">
                  <Text fontWeight="bold">User:</Text>
                  <Text>{userData.user_name || 'Unknown'}</Text>
                </HStack>

                <HStack justify="space-between">
                  <Text fontWeight="bold">Level:</Text>
                  <Text color="brand.400" fontSize="xl" fontWeight="bold">
                    {userData.current_level}
                  </Text>
                </HStack>

                <HStack justify="space-between">
                  <Text fontWeight="bold">Total XP:</Text>
                  <Text>{formatNumber(userData.total_xp)}</Text>
                </HStack>

                <HStack justify="space-between">
                  <Text fontWeight="bold">Current XP:</Text>
                  <Text>{formatNumber(userData.current_xp)}</Text>
                </HStack>

                <Box>
                  <Text fontWeight="bold" mb={2}>
                    Progress to Next Level:
                  </Text>
                  <Progress
                    value={calculateLevelProgress(userData.current_level, userData.total_xp)}
                    size="sm"
                    colorScheme="brand"
                    borderRadius="full"
                  />
                  <Text fontSize="sm" color="gray.400" mt={1}>
                    {calculateLevelProgress(userData.current_level, userData.total_xp)}%
                  </Text>
                </Box>

                <HStack justify="space-between">
                  <Text fontWeight="bold">Messages Sent:</Text>
                  <Text>{formatNumber(userData.messages_sent)}</Text>
                </HStack>

                {userData.rank_title && (
                  <HStack justify="space-between">
                    <Text fontWeight="bold">Rank:</Text>
                    <Text color="brand.400">{userData.rank_title}</Text>
                  </HStack>
                )}

                {userData.range_name && (
                  <HStack justify="space-between">
                    <Text fontWeight="bold">Level Range:</Text>
                    <Text>{userData.range_name}</Text>
                  </HStack>
                )}
              </VStack>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  )
}

export default UserLookup
