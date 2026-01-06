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
  Badge,
  useDisclosure,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react'
import { EditIcon, DeleteIcon, AddIcon } from '@chakra-ui/icons'
import { useState } from 'react'
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'
import { MessageTemplate } from '@/types/leveling'
import TemplateModal from './modals/TemplateModal'

const TemplateManagement = () => {
  const { selectedGuild } = useLevelingStore()
  const { data: templates = [], isLoading } = useTemplates(selectedGuild)
  const createTemplate = useCreateTemplate()
  const updateTemplate = useUpdateTemplate()
  const deleteTemplate = useDeleteTemplate()
  const { isOpen, onOpen, onClose } = useDisclosure()
  const [editingTemplate, setEditingTemplate] = useState<MessageTemplate | undefined>()

  const handleCreate = () => {
    setEditingTemplate(undefined)
    onOpen()
  }

  const handleEdit = (template: MessageTemplate) => {
    setEditingTemplate(template)
    onOpen()
  }

  const handleSave = (template: Omit<MessageTemplate, 'id'> | MessageTemplate) => {
    if ('id' in template) {
      updateTemplate.mutate(template)
    } else {
      createTemplate.mutate(template)
    }
  }

  const handleDelete = (templateId: number) => {
    if (confirm('Are you sure you want to delete this template?')) {
      deleteTemplate.mutate(templateId)
    }
  }

  const filterTemplatesByType = (type: MessageTemplate['type']) => {
    return templates.filter((t) => t.type === type)
  }

  if (!selectedGuild) {
    return (
      <Card bg="#1E1E1E">
        <CardBody>
          <Text color="gray.400">Select a guild to manage templates</Text>
        </CardBody>
      </Card>
    )
  }

  const TemplateTable = ({ templates }: { templates: MessageTemplate[] }) => {
    if (templates.length === 0) {
      return <Text color="gray.400">No templates configured</Text>
    }

    return (
      <Box overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th color="gray.400">Name</Th>
              <Th color="gray.400">Content</Th>
              <Th color="gray.400">Priority</Th>
              <Th color="gray.400">Status</Th>
              <Th color="gray.400">Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {templates.map((template) => (
              <Tr key={template.id}>
                <Td fontWeight="bold">{template.name}</Td>
                <Td maxW="300px" isTruncated>
                  {template.content}
                </Td>
                <Td>{template.priority}</Td>
                <Td>
                  <Badge colorScheme={template.enabled ? 'green' : 'gray'}>
                    {template.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </Td>
                <Td>
                  <HStack spacing={2}>
                    <IconButton
                      aria-label="Edit template"
                      icon={<EditIcon />}
                      size="sm"
                      onClick={() => handleEdit(template)}
                    />
                    <IconButton
                      aria-label="Delete template"
                      icon={<DeleteIcon />}
                      size="sm"
                      colorScheme="red"
                      onClick={() => handleDelete(template.id)}
                    />
                  </HStack>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    )
  }

  return (
    <>
      <Card bg="#1E1E1E">
        <CardBody>
          <HStack justify="space-between" mb={4}>
            <Heading size="md">Template Management</Heading>
            <Button leftIcon={<AddIcon />} colorScheme="brand" size="sm" onClick={handleCreate}>
              Add Template
            </Button>
          </HStack>

          {isLoading ? (
            <Box textAlign="center" py={8}>
              <Spinner size="xl" color="brand.400" />
            </Box>
          ) : (
            <Tabs colorScheme="brand">
              <TabList>
                <Tab>Default Level Up</Tab>
                <Tab>Rank Promotion</Tab>
                <Tab>Milestones</Tab>
                <Tab>First Level</Tab>
                <Tab>All</Tab>
              </TabList>

              <TabPanels>
                <TabPanel px={0}>
                  <TemplateTable templates={filterTemplatesByType('default_levelup')} />
                </TabPanel>
                <TabPanel px={0}>
                  <TemplateTable templates={filterTemplatesByType('rank_promotion')} />
                </TabPanel>
                <TabPanel px={0}>
                  <TemplateTable
                    templates={[
                      ...filterTemplatesByType('milestone_level'),
                      ...filterTemplatesByType('major_milestone'),
                    ]}
                  />
                </TabPanel>
                <TabPanel px={0}>
                  <TemplateTable templates={filterTemplatesByType('first_level')} />
                </TabPanel>
                <TabPanel px={0}>
                  <TemplateTable templates={templates} />
                </TabPanel>
              </TabPanels>
            </Tabs>
          )}
        </CardBody>
      </Card>

      {selectedGuild && (
        <TemplateModal
          isOpen={isOpen}
          onClose={onClose}
          onSave={handleSave}
          template={editingTemplate}
          guildId={selectedGuild}
        />
      )}
    </>
  )
}

export default TemplateManagement
