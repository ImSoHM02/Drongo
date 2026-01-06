import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  NumberInput,
  NumberInputField,
} from '@chakra-ui/react'
import { useState, useEffect } from 'react'
import { LevelRange } from '@/types/leveling'

interface RangeModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (range: Omit<LevelRange, 'id'> | LevelRange) => void
  range?: LevelRange
  guildId: string
}

const RangeModal = ({ isOpen, onClose, onSave, range, guildId }: RangeModalProps) => {
  const [formData, setFormData] = useState<Omit<LevelRange, 'id'>>({
    guild_id: guildId,
    range_name: '',
    min_level: 0,
    max_level: 10,
    description: '',
  })

  useEffect(() => {
    if (range) {
      setFormData(range)
    } else {
      setFormData({
        guild_id: guildId,
        range_name: '',
        min_level: 0,
        max_level: 10,
        description: '',
      })
    }
  }, [range, guildId])

  const handleSave = () => {
    if (range) {
      onSave({ ...formData, id: range.id })
    } else {
      onSave(formData)
    }
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent bg="#1E1E1E">
        <ModalHeader>{range ? 'Edit Level Range' : 'Create Level Range'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel>Range Name</FormLabel>
              <Input
                value={formData.range_name}
                onChange={(e) => setFormData({ ...formData, range_name: e.target.value })}
                bg="#2A2A2A"
                placeholder="Beginner"
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Min Level</FormLabel>
              <NumberInput
                value={formData.min_level}
                onChange={(_, val) => setFormData({ ...formData, min_level: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Max Level</FormLabel>
              <NumberInput
                value={formData.max_level}
                onChange={(_, val) => setFormData({ ...formData, max_level: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Description</FormLabel>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                bg="#2A2A2A"
                placeholder="Levels 1-10"
              />
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button colorScheme="brand" onClick={handleSave}>
            Save
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  )
}

export default RangeModal
