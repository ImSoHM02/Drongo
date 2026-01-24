import {
  Card,
  CardBody,
  Heading,
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Input,
  NumberInput,
  NumberInputField,
  Button,
  Text,
} from '@chakra-ui/react'
import { useState } from 'react'
import {
  useAdminAddXp,
  useAdminAddLevels,
  useAdminRemoveLevels,
} from '@/hooks/useLeveling'
import { useLevelingStore } from '@/stores/levelingStore'

const AdminPanel = () => {
  const { selectedGuild } = useLevelingStore()
  const addXp = useAdminAddXp()
  const addLevels = useAdminAddLevels()
  const removeLevels = useAdminRemoveLevels()

  const [adminId, setAdminId] = useState('')
  const [userId, setUserId] = useState('')
  const [xpAmount, setXpAmount] = useState(100)
  const [levelsAmount, setLevelsAmount] = useState(1)

  const disabled = !selectedGuild || !userId || !adminId

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          Admin Actions
        </Heading>

        {!selectedGuild ? (
          <Text color="gray.400">Select a guild to manage leveling.</Text>
        ) : (
          <VStack spacing={5} align="stretch">
            <HStack>
              <FormControl>
                <FormLabel>Admin Discord ID</FormLabel>
                <Input
                  value={adminId}
                  onChange={(e) => setAdminId(e.target.value)}
                  placeholder="Your Discord ID"
                  bg="#2A2A2A"
                />
              </FormControl>
              <FormControl>
                <FormLabel>Target User ID</FormLabel>
                <Input
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="User ID"
                  bg="#2A2A2A"
                />
              </FormControl>
            </HStack>

            <HStack align="flex-end">
              <FormControl maxW="200px">
                <FormLabel>XP Amount</FormLabel>
                <NumberInput value={xpAmount} min={1} onChange={(_, v) => setXpAmount(v || 0)}>
                  <NumberInputField bg="#2A2A2A" />
                </NumberInput>
              </FormControl>
              <Button
                colorScheme="brand"
                onClick={() =>
                  addXp.mutate({
                    guildId: selectedGuild!,
                    userId,
                    xp: xpAmount,
                    adminId,
                  })
                }
                isLoading={addXp.isPending}
                isDisabled={disabled || xpAmount <= 0}
              >
                Add XP
              </Button>
            </HStack>

            <HStack align="flex-end">
              <FormControl maxW="200px">
                <FormLabel>Levels</FormLabel>
                <NumberInput
                  value={levelsAmount}
                  min={1}
                  onChange={(_, v) => setLevelsAmount(v || 0)}
                >
                  <NumberInputField bg="#2A2A2A" />
                </NumberInput>
              </FormControl>
              <Button
                colorScheme="brand"
                onClick={() =>
                  addLevels.mutate({
                    guildId: selectedGuild!,
                    userId,
                    levels: levelsAmount,
                    adminId,
                  })
                }
                isLoading={addLevels.isPending}
                isDisabled={disabled || levelsAmount <= 0}
              >
                Add Levels
              </Button>
              <Button
                colorScheme="red"
                variant="outline"
                onClick={() =>
                  removeLevels.mutate({
                    guildId: selectedGuild!,
                    userId,
                    levels: levelsAmount,
                    adminId,
                  })
                }
                isLoading={removeLevels.isPending}
                isDisabled={disabled || levelsAmount <= 0}
              >
                Remove Levels
              </Button>
            </HStack>
          </VStack>
        )}
      </CardBody>
    </Card>
  )
}

export default AdminPanel
