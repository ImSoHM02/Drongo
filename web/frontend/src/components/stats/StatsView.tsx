import { Box, Heading, VStack, Text, Spinner, SimpleGrid } from '@chakra-ui/react'
import { useStats } from '@/hooks/useStats'
import StatsGrid from './StatsGrid'
import ActivityChart from './ActivityChart'
import DatabaseHealth from './DatabaseHealth'

const StatsView = () => {
  const { stats } = useStats()

  if (!stats) {
    return (
      <Box textAlign="center" py={12}>
        <Spinner size="xl" color="brand.400" />
        <Text mt={4} color="gray.400">
          Waiting for stats data...
        </Text>
      </Box>
    )
  }

  // Mock activity data if not available (you may need to fetch this separately)
  const activityData = {
    timestamps: stats.recent_messages?.map(m => m.timestamp) || [],
    message_counts: stats.recent_messages?.map((_, idx) => idx + 1) || [],
  }

  return (
    <Box>
      <Heading size="lg" mb={6}>
        Stats
      </Heading>

      <VStack spacing={6} align="stretch">
        <StatsGrid stats={stats} />

        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          {activityData.timestamps.length > 0 && (
            <ActivityChart activity={activityData} />
          )}
          <DatabaseHealth health={stats.database_health} />
        </SimpleGrid>
      </VStack>
    </Box>
  )
}

export default StatsView
