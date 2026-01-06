import { Box, Flex, Text } from '@chakra-ui/react'

interface ConnectionStatusProps {
  isConnected: boolean
}

const ConnectionStatus = ({ isConnected }: ConnectionStatusProps) => {
  return (
    <Box
      position="fixed"
      bottom={4}
      right={4}
      bg={isConnected ? 'green.500' : 'red.500'}
      color="white"
      px={4}
      py={2}
      borderRadius="md"
      boxShadow="lg"
      zIndex={1000}
    >
      <Flex align="center" gap={2}>
        <Box
          w={2}
          h={2}
          borderRadius="full"
          bg="white"
          animation={isConnected ? 'pulse 2s infinite' : 'none'}
        />
        <Text fontSize="sm" fontWeight="medium">
          {isConnected ? 'Connected' : 'Disconnected'}
        </Text>
      </Flex>
    </Box>
  )
}

export default ConnectionStatus
