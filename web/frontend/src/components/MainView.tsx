import { Box, Heading, Text, VStack } from '@chakra-ui/react'
import GitHubUpdateCard from './settings/GitHubUpdateCard'

const MainView = () => {
  return (
    <Box>
      <Heading size="lg" mb={6}>
        Main
      </Heading>
      <VStack spacing={6} align="stretch">
        <Text color="gray.400">
          Welcome to the Drongo dashboard. Use the navigation menu to access different features.
        </Text>
        <GitHubUpdateCard />
      </VStack>
    </Box>
  )
}

export default MainView
