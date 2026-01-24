import { Box, Heading, Text } from '@chakra-ui/react'

const MainView = () => {
  return (
    <Box>
      <Heading size="lg" mb={6}>
        Main
      </Heading>
      <Text color="gray.400">
        Welcome to the Drongo dashboard. Use the navigation menu to access different features.
      </Text>
    </Box>
  )
}

export default MainView
