import { Box, Heading, VStack, Button, useToast } from '@chakra-ui/react'
import api from '@/services/api'

const MainView = () => {
  const toast = useToast()

  const handleRestart = async () => {
    try {
      await api.post('/bot/restart')
      toast({
        title: 'Bot is restarting...',
        status: 'success',
        duration: 3000,
        position: 'top-right',
      })
    } catch (error) {
      toast({
        title: 'Failed to restart bot',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    }
  }

  const handleShutdown = async () => {
    try {
      await api.post('/bot/shutdown')
      toast({
        title: 'Bot is shutting down...',
        status: 'info',
        duration: 3000,
        position: 'top-right',
      })
    } catch (error) {
      toast({
        title: 'Failed to shutdown bot',
        status: 'error',
        duration: 3000,
        position: 'top-right',
      })
    }
  }

  return (
    <Box>
      <Heading size="lg" mb={6}>
        Main
      </Heading>
      <VStack align="stretch" spacing={4} maxW="300px">
        <Button colorScheme="brand" onClick={handleRestart}>
          Restart Bot
        </Button>
        <Button colorScheme="brand" onClick={handleShutdown}>
          Shutdown Bot
        </Button>
      </VStack>
    </Box>
  )
}

export default MainView
