import { SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, Card, CardBody } from '@chakra-ui/react'
import { DashboardStats } from '@/types/stats'
import { formatNumber, formatBytes } from '@/utils/formatters'

interface StatsGridProps {
  stats: DashboardStats
}

const StatsGrid = ({ stats }: StatsGridProps) => {
  const statItems = [
    { label: 'Messages Processed', value: formatNumber(stats.messages_processed), helpText: `${stats.message_rate}/min` },
    { label: 'Commands Executed', value: formatNumber(stats.commands_executed), helpText: `${stats.command_rate}/min` },
    { label: 'Active Users', value: formatNumber(stats.active_users) },
    { label: 'Bot Guilds', value: formatNumber(stats.bot_guilds) },
    { label: 'Memory Usage', value: formatBytes(stats.memory_usage) },
    { label: 'CPU Usage', value: `${stats.cpu_usage.toFixed(1)}%` },
    { label: 'Database Size', value: formatBytes(stats.database_size) },
    { label: 'Uptime', value: stats.uptime },
  ]

  return (
    <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
      {statItems.map((item) => (
        <Card key={item.label} bg="#1E1E1E">
          <CardBody>
            <Stat>
              <StatLabel color="gray.400">{item.label}</StatLabel>
              <StatNumber color="white" fontSize="2xl">
                {item.value}
              </StatNumber>
              {item.helpText && (
                <StatHelpText color="gray.500">{item.helpText}</StatHelpText>
              )}
            </Stat>
          </CardBody>
        </Card>
      ))}
    </SimpleGrid>
  )
}

export default StatsGrid
