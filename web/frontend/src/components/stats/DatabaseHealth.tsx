import { Card, CardBody, Heading, VStack, Box, Text, Progress, HStack, Badge } from '@chakra-ui/react'
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
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" color="gray.400">
                Total Database Size
              </Text>
              <Badge colorScheme="brand" fontSize="xs">
                {health.database_files} Guild{health.database_files !== 1 ? 's' : ''}
              </Badge>
            </HStack>
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
              Guild Databases
            </Text>
            <Text fontSize="lg" fontWeight="bold">
              {health.database_files}
            </Text>
            <Text fontSize="xs" color="gray.500" mt={1}>
              Separate database per guild
            </Text>
          </Box>

          <Box>
            <Text fontSize="sm" color="gray.400" mb={2}>
              Total Tables
            </Text>
            <Text fontSize="lg" fontWeight="bold">
              {health.table_count}
            </Text>
            <Text fontSize="xs" color="gray.500" mt={1}>
              {health.database_files > 0 ? `~${Math.round(health.table_count / health.database_files)} per guild` : '0 per guild'}
            </Text>
          </Box>
        </VStack>
      </CardBody>
    </Card>
  )
}

export default DatabaseHealth
