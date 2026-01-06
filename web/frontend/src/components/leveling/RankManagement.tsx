import {
  Card,
  CardBody,
  Heading,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  HStack,
  IconButton,
  Text,
  Box,
  Spinner,
  useDisclosure,
} from '@chakra-ui/react'
import { EditIcon, DeleteIcon, AddIcon } from '@chakra-ui/icons'
import { useState } from 'react'
import { useRanks, useCreateRank, useUpdateRank, useDeleteRank } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { Rank } from '@/types/leveling'
import RankModal from './modals/RankModal'

const RankManagement = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: ranks = [], isLoading } = useRanks(selectedGuild)
  const createRank = useCreateRank()
  const updateRank = useUpdateRank()
  const deleteRank = useDeleteRank()
  const { isOpen, onOpen, onClose } = useDisclosure()
  const [editingRank, setEditingRank] = useState<Rank | undefined>()

  const handleCreate = () => {
    setEditingRank(undefined)
    onOpen()
  }

  const handleEdit = (rank: Rank) => {
    setEditingRank(rank)
    onOpen()
  }

  const handleSave = (rank: Omit<Rank, 'id'> | Rank) => {
    if ('id' in rank) {
      updateRank.mutate(rank)
    } else {
      createRank.mutate(rank)
    }
  }

  const handleDelete = (rankId: number) => {
    if (confirm('Are you sure you want to delete this rank?')) {
      deleteRank.mutate(rankId)
    }
  }

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to manage ranks</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <>
      <Card bg="#1E1E1E">
        <CardBody>
          <HStack justify="space-between" mb={4}>
            <Heading size="md">Rank Management</Heading>
            <Button leftIcon={<AddIcon />} colorScheme="brand" size="sm" onClick={handleCreate}>
              Add Rank
            </Button>
          </HStack>

          {isLoading ? (
            <Box textAlign="center" py={8}>
              <Spinner size="xl" color="brand.400" />
            </Box>
          ) : ranks.length === 0 ? (
            <Text color="gray.400">No ranks configured</Text>
          ) : (
            <Box overflowX="auto">
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th color="gray.400">Name</Th>
                    <Th color="gray.400">Level Range</Th>
                    <Th color="gray.400">Emoji</Th>
                    <Th color="gray.400">Color</Th>
                    <Th color="gray.400">Description</Th>
                    <Th color="gray.400">Users</Th>
                    <Th color="gray.400">Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {ranks.map((rank) => (
                    <Tr key={rank.id}>
                      <Td fontWeight="bold">{rank.name}</Td>
                      <Td>
                        {rank.level_min} - {rank.level_max || '∞'}
                      </Td>
                      <Td fontSize="lg">{rank.emoji}</Td>
                      <Td>
                        <HStack>
                          <Box
                            w={4}
                            h={4}
                            borderRadius="full"
                            bg={rank.color}
                          />
                          <Text fontSize="xs">{rank.color}</Text>
                        </HStack>
                      </Td>
                      <Td maxW="200px" isTruncated>
                        {rank.description}
                      </Td>
                      <Td>{rank.user_count || 0}</Td>
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            aria-label="Edit rank"
                            icon={<EditIcon />}
                            size="sm"
                            onClick={() => handleEdit(rank)}
                          />
                          <IconButton
                            aria-label="Delete rank"
                            icon={<DeleteIcon />}
                            size="sm"
                            colorScheme="red"
                            onClick={() => handleDelete(rank.id)}
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          )}
        </CardBody>
      </Card>

      {selectedGuild && (
        <RankModal
          isOpen={isOpen}
          onClose={onClose}
          onSave={handleSave}
          rank={editingRank}
          guildId={selectedGuild}
        />
      )}
    </>
  )
}

export default RankManagement
