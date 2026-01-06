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
  Select,
  Textarea,
  NumberInput,
  NumberInputField,
  Switch,
  Text,
  Box,
  Code,
} from '@chakra-ui/react'
import { useState, useEffect } from 'react'
import { MessageTemplate } from '@/types/leveling'

interface TemplateModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (template: Omit<MessageTemplate, 'id'> | MessageTemplate) => void
  template?: MessageTemplate
  guildId: string
}

const TemplateModal = ({ isOpen, onClose, onSave, template, guildId }: TemplateModalProps) => {
  const [formData, setFormData] = useState<Omit<MessageTemplate, 'id'>>({
    guild_id: guildId,
    name: '',
    type: 'default_levelup',
    content: '',
    conditions: '{}',
    priority: 0,
    enabled: true,
  })

  useEffect(() => {
    if (template) {
      setFormData(template)
    } else {
      setFormData({
        guild_id: guildId,
        name: '',
        type: 'default_levelup',
        content: '',
        conditions: '{}',
        priority: 0,
        enabled: true,
      })
    }
  }, [template, guildId])

  const handleSave = () => {
    if (template) {
      onSave({ ...formData, id: template.id })
    } else {
      onSave(formData)
    }
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="#1E1E1E">
        <ModalHeader>{template ? 'Edit Template' : 'Create Template'}</ModalHeader>
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
              <FormLabel>Type</FormLabel>
              <Select
                value={formData.type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    type: e.target.value as MessageTemplate['type'],
                  })
                }
                bg="#2A2A2A"
              >
                <option value="default_levelup">Default Level Up</option>
                <option value="rank_promotion">Rank Promotion</option>
                <option value="milestone_level">Milestone Level</option>
                <option value="first_level">First Level</option>
                <option value="major_milestone">Major Milestone</option>
              </Select>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Content</FormLabel>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                bg="#2A2A2A"
                rows={6}
                placeholder="Congratulations {user}! You reached level {level}!"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Variables: {'{user}'}, {'{level}'}, {'{rank}'}, {'{xp}'}, {'{total_xp}'}
              </Text>
            </FormControl>

            <FormControl>
              <FormLabel>Conditions (JSON)</FormLabel>
              <Textarea
                value={formData.conditions}
                onChange={(e) => setFormData({ ...formData, conditions: e.target.value })}
                bg="#2A2A2A"
                rows={3}
                fontFamily="monospace"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Example: <Code fontSize="xs">{`{"level": 10}`}</Code>
              </Text>
            </FormControl>

            <FormControl>
              <FormLabel>Priority</FormLabel>
              <NumberInput
                value={formData.priority}
                onChange={(_, val) => setFormData({ ...formData, priority: val })}
                min={0}
              >
                <NumberInputField bg="#2A2A2A" />
              </NumberInput>
            </FormControl>

            <FormControl display="flex" alignItems="center">
              <FormLabel mb={0}>Enabled</FormLabel>
              <Switch
                isChecked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                colorScheme="brand"
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

export default TemplateModal
