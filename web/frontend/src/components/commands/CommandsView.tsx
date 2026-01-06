import {
  Box,
  Heading,
  VStack,
  HStack,
  Button,
  Card,
  CardBody,
  Text,
  SimpleGrid,
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Spinner,
} from '@chakra-ui/react'
import { useRef, useState } from 'react'
import { useCommands } from '@/hooks/useCommands'

const CommandsView = () => {
  const { commands, isLoading, registerCommands, restartBot, shutdownBot, isRegistering } = useCommands()
  const { isOpen, onOpen, onClose } = useDisclosure()
  const [dialogAction, setDialogAction] = useState<'restart' | 'shutdown' | null>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)

  const handleAction = (action: 'restart' | 'shutdown') => {
    setDialogAction(action)
    onOpen()
  }

  const confirmAction = () => {
    if (dialogAction === 'restart') {
      restartBot()
    } else if (dialogAction === 'shutdown') {
      shutdownBot()
    }
    onClose()
  }

  return (
    <Box>
      <Heading size="lg" mb={6}>
        Commands
      </Heading>

      <VStack spacing={6} align="stretch">
        {/* Bot Control Section */}
        <Card bg="#1E1E1E">
          <CardBody>
            <Heading size="md" mb={4}>
              Bot Control
            </Heading>
            <HStack spacing={4}>
              <Button
                colorScheme="brand"
                onClick={() => handleAction('restart')}
              >
                Restart Bot
              </Button>
              <Button
                colorScheme="brand"
                onClick={() => handleAction('shutdown')}
              >
                Shutdown Bot
              </Button>
              <Button
                colorScheme="brand"
                onClick={() => registerCommands()}
                isLoading={isRegistering}
              >
                Register Commands
              </Button>
            </HStack>
          </CardBody>
        </Card>

        {/* Commands List Section */}
        <Card bg="#1E1E1E">
          <CardBody>
            <Heading size="md" mb={4}>
              Available Commands
            </Heading>
            {isLoading ? (
              <Box textAlign="center" py={8}>
                <Spinner size="xl" color="brand.400" />
              </Box>
            ) : commands.length === 0 ? (
              <Text color="gray.400">No commands found</Text>
            ) : (
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                {commands.map((command) => (
                  <Card key={command.name} bg="#2A2A2A" borderWidth={1} borderColor="whiteAlpha.200">
                    <CardBody>
                      <Text fontWeight="bold" fontSize="lg" color="brand.400" mb={2}>
                        /{command.name}
                      </Text>
                      <Text fontSize="sm" color="gray.300">
                        {command.description}
                      </Text>
                      {command.usage && (
                        <Text fontSize="xs" color="gray.500" mt={2}>
                          Usage: {command.usage}
                        </Text>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>
            )}
          </CardBody>
        </Card>
      </VStack>

      {/* Confirmation Dialog */}
      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent bg="#1E1E1E">
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {dialogAction === 'restart' ? 'Restart Bot' : 'Shutdown Bot'}
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to {dialogAction} the bot?
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onClose}>
                Cancel
              </Button>
              <Button colorScheme="brand" onClick={confirmAction} ml={3}>
                Confirm
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  )
}

export default CommandsView
