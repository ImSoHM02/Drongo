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
import { useRanges, useCreateRange, useUpdateRange, useDeleteRange } from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { LevelRange } from '@/types/leveling'
import RangeModal from './modals/RangeModal'

const LevelRangeManagement = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: ranges = [], isLoading } = useRanges(selectedGuild)
  const createRange = useCreateRange()
  const updateRange = useUpdateRange()
  const deleteRange = useDeleteRange()
  const { isOpen, onOpen, onClose } = useDisclosure()
  const [editingRange, setEditingRange] = useState<LevelRange | undefined>()

  const handleCreate = () => {
    setEditingRange(undefined)
    onOpen()
  }

  const handleEdit = (range: LevelRange) => {
    setEditingRange(range)
    onOpen()
  }

  const handleSave = (range: Omit<LevelRange, 'id'> | LevelRange) => {
    if ('id' in range) {
      updateRange.mutate(range)
    } else {
      createRange.mutate(range)
    }
  }

  const handleDelete = (rangeId: number) => {
    if (confirm('Are you sure you want to delete this level range?')) {
      deleteRange.mutate(rangeId)
    }
  }

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to manage level ranges</Text>
        </CardBody>
      </Card>
    )
  }

  return (
    <>
      <Card bg="#1E1E1E">
        <CardBody>
          <HStack justify="space-between" mb={4}>
            <Heading size="md">Level Range Management</Heading>
            <Button leftIcon={<AddIcon />} colorScheme="brand" size="sm" onClick={handleCreate}>
              Add Range
            </Button>
          </HStack>

          {isLoading ? (
            <Box textAlign="center" py={8}>
              <Spinner size="xl" color="brand.400" />
            </Box>
          ) : ranges.length === 0 ? (
            <Text color="gray.400">No level ranges configured</Text>
          ) : (
            <Box overflowX="auto">
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th color="gray.400">Name</Th>
                    <Th color="gray.400">Level Range</Th>
                    <Th color="gray.400">Description</Th>
                    <Th color="gray.400">Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {ranges.map((range) => (
                    <Tr key={range.id}>
                      <Td fontWeight="bold">{range.range_name}</Td>
                      <Td>
                        {range.min_level} - {range.max_level}
                      </Td>
                      <Td maxW="300px" isTruncated>
                        {range.description}
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            aria-label="Edit range"
                            icon={<EditIcon />}
                            size="sm"
                            onClick={() => handleEdit(range)}
                          />
                          <IconButton
                            aria-label="Delete range"
                            icon={<DeleteIcon />}
                            size="sm"
                            colorScheme="red"
                            onClick={() => handleDelete(range.id)}
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
        <RangeModal
          isOpen={isOpen}
          onClose={onClose}
          onSave={handleSave}
          range={editingRange}
          guildId={selectedGuild}
        />
      )}
    </>
  )
}

export default LevelRangeManagement
