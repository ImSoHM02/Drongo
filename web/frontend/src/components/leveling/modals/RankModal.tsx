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
import { Rank } from '@/types/leveling'

interface RankModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (rank: Omit<Rank, 'id'> | Rank) => void
  rank?: Rank
  guildId: string
}

const RankModal = ({ isOpen, onClose, onSave, rank, guildId }: RankModalProps) => {
  const [formData, setFormData] = useState<Omit<Rank, 'id'>>({
    guild_id: guildId,
    name: '',
    level_min: 0,
    level_max: null,
    color: '#FF6B35',
    emoji: '',
    discord_role_id: null,
    description: '',
  })

  useEffect(() => {
    if (rank) {
      setFormData(rank)
    } else {
      setFormData({
        guild_id: guildId,
        name: '',
        level_min: 0,
        level_max: null,
        color: '#FF6B35',
        emoji: '',
        discord_role_id: null,
        description: '',
      })
    }
  }, [rank, guildId])

  const handleSave = () => {
    if (rank) {
      onSave({ ...formData, id: rank.id })
    } else {
      onSave(formData)
    }
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent bg="#1E1E1E">
        <ModalHeader>{rank ? 'Edit Rank' : 'Create Rank'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel>Name</FormLabel>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                bg="#2A2A2A"
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Min Level</FormLabel>
              <NumberInput
                value={formData.level_min}
                onChange={(_, val) => setFormData({ ...formData, level_min: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Max Level (optional)</FormLabel>
              <NumberInput
                value={formData.level_max || ''}
                onChange={(_, val) => setFormData({ ...formData, level_max: val || null })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" placeholder="Leave empty for no max" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Color (hex)</FormLabel>
              <Input
                value={formData.color}
                onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                bg="#2A2A2A"
                type="color"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Emoji</FormLabel>
              <Input
                value={formData.emoji}
                onChange={(e) => setFormData({ ...formData, emoji: e.target.value })}
                bg="#2A2A2A"
                placeholder="⭐"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Discord Role ID (optional)</FormLabel>
              <Input
                value={formData.discord_role_id || ''}
                onChange={(e) =>
                  setFormData({ ...formData, discord_role_id: e.target.value || null })
                }
                bg="#2A2A2A"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Description</FormLabel>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                bg="#2A2A2A"
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

export default RankModal
