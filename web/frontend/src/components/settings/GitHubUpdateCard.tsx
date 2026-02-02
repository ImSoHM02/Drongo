import { useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Collapse,
  Flex,
  Heading,
  HStack,
  Icon,
  IconButton,
  Spinner,
  Stack,
  Text,
  useDisclosure,
  VStack,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
} from '@chakra-ui/react'
import { ChevronDownIcon, ChevronUpIcon, WarningIcon } from '@chakra-ui/icons'
import { useGitHubStatus, useCheckUpdates, useGitHubUpdate } from '@/hooks/useGitHub'
import { UpdateCheckResult } from '@/types'

const GitHubUpdateCard = () => {
  const { data: status, isLoading: loadingStatus } = useGitHubStatus()
  const checkUpdatesMutation = useCheckUpdates()
  const updateMutation = useGitHubUpdate()
  const { isOpen: isLogOpen, onToggle: toggleLog } = useDisclosure()
  const { isOpen: isConfirmOpen, onOpen: openConfirm, onClose: closeConfirm } = useDisclosure()

  const [updateCheckData, setUpdateCheckData] = useState<UpdateCheckResult | null>(null)

  const handleCheckUpdates = async () => {
    const result = await checkUpdatesMutation.mutateAsync()
    setUpdateCheckData(result)
  }

  const handleUpdate = () => {
    closeConfirm()
    updateMutation.mutate()
  }

  return (
    <>
      <Card bg="#1E1E1E">
        <CardBody>
          <Flex justify="space-between" align="center" mb={4} wrap="wrap" gap={3}>
            <Box>
              <Flex align="center" gap={2} mb={1}>
                <Heading size="md">GitHub Updates</Heading>
              </Flex>
              <Text color="gray.400" fontSize="sm">
                Check for updates and manage bot version.
              </Text>
            </Box>
            {(loadingStatus || checkUpdatesMutation.isPending || updateMutation.isPending) && (
              <Spinner size="sm" color="brand.400" />
            )}
          </Flex>

          <Stack spacing={4}>
            {/* Current Version Section */}
            <Box bg="#2A2A2A" borderRadius="md" p={4}>
              <Text fontSize="sm" fontWeight="bold" mb={2} color="gray.300">
                Current Version
              </Text>
              {status ? (
                <VStack align="stretch" spacing={2}>
                  <HStack spacing={3}>
                    <Text fontSize="sm">
                      <Text as="span" color="gray.400">
                        Branch:{' '}
                      </Text>
                      <Text as="span" fontFamily="mono" color="purple.300">
                        {status.current_branch}
                      </Text>
                    </Text>
                  </HStack>
                  <HStack spacing={3}>
                    <Text fontSize="sm" color="gray.400">
                      Commit:
                    </Text>
                    <Badge colorScheme="purple" fontFamily="mono">
                      {status.current_commit_short}
                    </Badge>
                  </HStack>
                  {status.has_uncommitted_changes && (
                    <HStack spacing={2}>
                      <Icon as={WarningIcon} color="yellow.400" boxSize={4} />
                      <Badge colorScheme="yellow">Uncommitted changes</Badge>
                    </HStack>
                  )}
                </VStack>
              ) : (
                <Text fontSize="sm" color="gray.500">
                  Loading version info...
                </Text>
              )}
            </Box>

            {/* Update Check Results */}
            {updateCheckData && (
              <Box bg="#2A2A2A" borderRadius="md" p={4}>
                <Flex justify="space-between" align="center" mb={2}>
                  <Text fontSize="sm" fontWeight="bold" color="gray.300">
                    {updateCheckData.updates_available ? 'Updates Available' : 'Already Up to Date'}
                  </Text>
                  {updateCheckData.updates_available && (
                    <Badge colorScheme="blue">{updateCheckData.commits_behind} commits behind</Badge>
                  )}
                </Flex>

                {updateCheckData.updates_available && updateCheckData.commit_log.length > 0 && (
                  <>
                    <Button
                      size="sm"
                      variant="ghost"
                      rightIcon={isLogOpen ? <ChevronUpIcon /> : <ChevronDownIcon />}
                      onClick={toggleLog}
                      mb={2}
                      color="blue.300"
                    >
                      {isLogOpen ? 'Hide' : 'Show'} Changelog
                    </Button>
                    <Collapse in={isLogOpen} animateOpacity>
                      <VStack align="stretch" spacing={2} pl={2}>
                        {updateCheckData.commit_log.map((commit) => (
                          <Box key={commit.hash} borderLeft="2px solid" borderColor="purple.500" pl={3} py={1}>
                            <HStack spacing={2} mb={1}>
                              <Badge colorScheme="purple" fontFamily="mono" fontSize="xs">
                                {commit.hash}
                              </Badge>
                              <Text fontSize="xs" color="gray.500">
                                by {commit.author}
                              </Text>
                            </HStack>
                            <Text fontSize="sm" color="gray.200">
                              {commit.message}
                            </Text>
                          </Box>
                        ))}
                      </VStack>
                    </Collapse>
                  </>
                )}

                {!updateCheckData.updates_available && (
                  <Text fontSize="sm" color="gray.400">
                    You are on the latest version from origin/main.
                  </Text>
                )}
              </Box>
            )}

            {/* Info Box */}
            <Box bg="#2A2A2A" borderRadius="md" p={3} borderLeft="4px solid" borderColor="blue.400">
              <Text fontSize="sm" color="gray.300">
                <Text as="span" fontWeight="bold" color="blue.300">
                  Two-step process:
                </Text>{' '}
                First check for updates to see what's new, then update and restart when ready.
              </Text>
            </Box>

            {/* Action Buttons */}
            <HStack spacing={3} wrap="wrap">
              <Button
                colorScheme="blue"
                onClick={handleCheckUpdates}
                isDisabled={checkUpdatesMutation.isPending || updateMutation.isPending}
                isLoading={checkUpdatesMutation.isPending}
              >
                Check for Updates
              </Button>
              <Button
                colorScheme="purple"
                onClick={openConfirm}
                isDisabled={
                  !updateCheckData?.updates_available ||
                  checkUpdatesMutation.isPending ||
                  updateMutation.isPending
                }
                isLoading={updateMutation.isPending}
              >
                Update & Restart
              </Button>
            </HStack>
          </Stack>
        </CardBody>
      </Card>

      {/* Confirmation Modal */}
      <Modal isOpen={isConfirmOpen} onClose={closeConfirm} isCentered>
        <ModalOverlay />
        <ModalContent bg="#1E1E1E">
          <ModalHeader>Confirm Update & Restart</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack align="stretch" spacing={3}>
              <Text>
                This will pull the latest changes from <Badge fontFamily="mono">origin/main</Badge> and restart the
                bot.
              </Text>
              {updateCheckData && (
                <Box bg="#2A2A2A" p={3} borderRadius="md">
                  <Text fontSize="sm" mb={1}>
                    Updates to apply:{' '}
                    <Badge colorScheme="blue">{updateCheckData.commits_behind} commits</Badge>
                  </Text>
                  <Text fontSize="sm" color="gray.400">
                    From: <Badge fontFamily="mono">{updateCheckData.current_commit_short}</Badge>
                  </Text>
                  <Text fontSize="sm" color="gray.400">
                    To: <Badge fontFamily="mono">{updateCheckData.latest_commit_short}</Badge>
                  </Text>
                </Box>
              )}
              {status?.has_uncommitted_changes && (
                <Box bg="yellow.900" p={3} borderRadius="md" borderLeft="4px solid" borderColor="yellow.400">
                  <HStack spacing={2} mb={1}>
                    <Icon as={WarningIcon} color="yellow.400" />
                    <Text fontWeight="bold" fontSize="sm">
                      Uncommitted Changes Detected
                    </Text>
                  </HStack>
                  <Text fontSize="sm">
                    You have uncommitted changes. The update will still proceed, but conflicts may occur.
                  </Text>
                </Box>
              )}
              <Text fontSize="sm" color="gray.400">
                The bot will be unavailable for a few seconds during the restart.
              </Text>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={closeConfirm}>
              Cancel
            </Button>
            <Button colorScheme="purple" onClick={handleUpdate}>
              Confirm Update
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  )
}

export default GitHubUpdateCard
