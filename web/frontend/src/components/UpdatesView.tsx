import { useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Checkbox,
  Flex,
  Heading,
  HStack,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react'
import { useGitCommits, usePushUpdates } from '@/hooks/useUpdates'

const UpdatesView = () => {
  const { data: commits = [], isLoading } = useGitCommits(50)
  const pushUpdates = usePushUpdates()
  const [selectedCommits, setSelectedCommits] = useState<Set<string>>(new Set())

  const toggleCommit = (hash: string) => {
    setSelectedCommits((prev) => {
      const next = new Set(prev)
      if (next.has(hash)) {
        next.delete(hash)
      } else {
        next.add(hash)
      }
      return next
    })
  }

  const handlePush = () => {
    if (selectedCommits.size === 0) return
    pushUpdates.mutate(Array.from(selectedCommits), {
      onSuccess: () => {
        setSelectedCommits(new Set())
      },
    })
  }

  const handleSelectAll = () => {
    if (selectedCommits.size === commits.length) {
      setSelectedCommits(new Set())
    } else {
      setSelectedCommits(new Set(commits.map((c) => c.hash)))
    }
  }

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={6} wrap="wrap" gap={3}>
        <Heading size="lg">Updates</Heading>
        <HStack spacing={3}>
          <Button variant="outline" onClick={handleSelectAll} size="sm">
            {selectedCommits.size === commits.length ? 'Deselect All' : 'Select All'}
          </Button>
          <Button
            colorScheme="purple"
            onClick={handlePush}
            isDisabled={selectedCommits.size === 0 || pushUpdates.isPending}
            isLoading={pushUpdates.isPending}
          >
            Push {selectedCommits.size > 0 ? `(${selectedCommits.size})` : ''} Update(s)
          </Button>
        </HStack>
      </Flex>

      <Text color="gray.400" mb={4}>
        Select commits to announce as updates to all servers with configured announcement channels.
      </Text>

      {isLoading ? (
        <Flex justify="center" py={8}>
          <Spinner size="lg" color="brand.400" />
        </Flex>
      ) : commits.length === 0 ? (
        <Card bg="#1E1E1E">
          <CardBody>
            <Text color="gray.400">No commits found.</Text>
          </CardBody>
        </Card>
      ) : (
        <Card bg="#1E1E1E">
          <CardBody>
            <VStack align="stretch" spacing={2}>
              {commits.map((commit) => (
                <Box
                  key={commit.hash}
                  p={3}
                  bg={selectedCommits.has(commit.hash) ? '#2A2A4A' : '#2A2A2A'}
                  borderRadius="md"
                  cursor="pointer"
                  onClick={() => toggleCommit(commit.hash)}
                  borderLeft="3px solid"
                  borderColor={selectedCommits.has(commit.hash) ? 'purple.500' : 'transparent'}
                  _hover={{ bg: selectedCommits.has(commit.hash) ? '#2A2A4A' : '#333' }}
                  transition="all 0.15s"
                >
                  <Flex justify="space-between" align="flex-start">
                    <HStack spacing={3} align="flex-start">
                      <Checkbox
                        isChecked={selectedCommits.has(commit.hash)}
                        onChange={() => toggleCommit(commit.hash)}
                        colorScheme="purple"
                        mt={1}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <Box>
                        <HStack spacing={2} mb={1}>
                          <Badge colorScheme="purple" fontFamily="mono">
                            {commit.short_hash}
                          </Badge>
                          <Text fontSize="xs" color="gray.500">
                            by {commit.author}
                          </Text>
                        </HStack>
                        <Text fontSize="sm">{commit.message}</Text>
                      </Box>
                    </HStack>
                    <Text fontSize="xs" color="gray.500" whiteSpace="nowrap" ml={4}>
                      {new Date(commit.date).toLocaleDateString()}
                    </Text>
                  </Flex>
                </Box>
              ))}
            </VStack>
          </CardBody>
        </Card>
      )}
    </Box>
  )
}

export default UpdatesView
