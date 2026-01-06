import { Card, CardBody, Heading } from '@chakra-ui/react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { MessageActivity } from '@/types/stats'
import { format } from 'date-fns'

interface ActivityChartProps {
  activity: MessageActivity
}

const ActivityChart = ({ activity }: ActivityChartProps) => {
  const chartData = activity.timestamps.map((time, idx) => ({
    time: format(new Date(time), 'HH:mm'),
    messages: activity.message_counts[idx],
  }))

  return (
    <Card bg="#1E1E1E">
      <CardBody>
        <Heading size="md" mb={4}>
          Message Activity
        </Heading>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="time" stroke="#F5F5F5" fontSize={12} />
            <YAxis stroke="#F5F5F5" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1E1E1E',
                border: '1px solid #333',
                borderRadius: '8px',
              }}
            />
            <Line
              type="monotone"
              dataKey="messages"
              stroke="#FF6B35"
              strokeWidth={2}
              dot={{ fill: '#FF6B35', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardBody>
    </Card>
  )
}

export default ActivityChart
