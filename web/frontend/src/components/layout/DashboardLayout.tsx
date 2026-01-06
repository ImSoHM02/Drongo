import { Box } from '@chakra-ui/react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import ConnectionStatus from './ConnectionStatus'
import { useWebSocket } from '@/hooks/useWebSocket'

const DashboardLayout = () => {
  const { isConnected } = useWebSocket()

  return (
    <Box display="flex" minH="100vh" bg="#121212">
      <Sidebar />
      <Box
        ml="250px"
        flex={1}
        p={8}
        overflowY="auto"
      >
        <Outlet />
      </Box>
      <ConnectionStatus isConnected={isConnected} />
    </Box>
  )
}

export default DashboardLayout
