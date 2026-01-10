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
  Text,
  Box,
  HStack,
  Badge,
} from '@chakra-ui/react'
import { SystemDatabase } from '@/types/stats'

interface SystemDatabasesProps {
  databases: SystemDatabase[]
}

const SystemDatabases = ({ databases }: SystemDatabasesProps) => {
  if (!databases || databases.length === 0) {
    return null
  }

  const totalSize = databases.reduce((sum, db) => sum + db.size_mb, 0)

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          System Databases
        </Heading>
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400">Database</Th>
                <Th color="gray.400">File</Th>
                <Th color="gray.400" isNumeric>Size</Th>
                <Th color="gray.400">Type</Th>
              </Tr>
            </Thead>
            <Tbody>
              {databases.map((db) => (
                <Tr key={db.file} _hover={{ bg: '#2A2A2A' }}>
                  <Td>
                    <Text fontWeight="medium" fontSize="sm">
                      {db.name}
                    </Text>
                  </Td>
                  <Td>
                    <Text fontSize="xs" color="gray.400" fontFamily="monospace">
                      {db.file}
                    </Text>
                  </Td>
                  <Td isNumeric>
                    <Text fontSize="sm">{db.size_mb.toFixed(2)} MB</Text>
                  </Td>
                  <Td>
                    <Badge
                      colorScheme={db.file === 'chat_history.db' ? 'yellow' : 'purple'}
                      fontSize="xs"
                    >
                      {db.file === 'chat_history.db' ? 'Legacy' : 'System'}
                    </Badge>
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
                {databases.length}
              </Text>{' '}
              system database{databases.length !== 1 ? 's' : ''}
            </Text>
            <Text>
              <Text as="span" fontWeight="bold" color="white">
                {totalSize.toFixed(2)} MB
              </Text>{' '}
              total size
            </Text>
          </HStack>
        </Box>
      </CardBody>
    </Card>
  )
}

export default SystemDatabases
