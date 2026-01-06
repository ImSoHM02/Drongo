import { Card, CardBody, Heading, VStack, Box, Text, Progress } from '@chakra-ui/react'
import { DatabaseHealth as DatabaseHealthType } from '@/types/stats'

interface DatabaseHealthProps {
  health: DatabaseHealthType
}

const DatabaseHealth = ({ health }: DatabaseHealthProps) => {
  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          Database Health
        </Heading>
        <VStack spacing={4} align="stretch">
          <Box>
            <Text fontSize="sm" color="gray.400" mb={2}>
              Database Size
            </Text>
            <Text fontSize="lg" fontWeight="bold">
              {health.database_size_mb.toFixed(2)} MB
            </Text>
            <Progress
              value={(health.database_size_mb / 1000) * 100}
              max={100}
              colorScheme="brand"
              size="sm"
              mt={2}
              borderRadius="full"
            />
          </Box>

          <Box>
            <Text fontSize="sm" color="gray.400" mb={2}>
              Tables
            </Text>
            <Text fontSize="lg" fontWeight="bold">
              {health.table_count}
            </Text>
          </Box>

          <Box>
            <Text fontSize="sm" color="gray.400" mb={2}>
              Indexes
            </Text>
            <Text fontSize="lg" fontWeight="bold">
              {health.index_count}
            </Text>
          </Box>
        </VStack>
      </CardBody>
    </Card>
  )
}

export default DatabaseHealth
