import { HashRouter, Routes, Route } from 'react-router-dom'
import { ChakraProvider } from '@chakra-ui/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import theme from './theme'
import DashboardLayout from './components/layout/DashboardLayout'
import MainView from './components/MainView'
import LogsView from './components/LogsView'
import CommandsView from './components/commands/CommandsView'
import StatsView from './components/stats/StatsView'
import LevelingDashboard from './components/leveling/LevelingDashboard'
import ChatHistoryView from './components/chat/ChatHistoryView'
import SettingsView from './components/SettingsView'
import UpdatesView from './components/UpdatesView'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <HashRouter>
          <Routes>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<MainView />} />
              <Route path="logs" element={<LogsView />} />
              <Route path="commands" element={<CommandsView />} />
              <Route path="stats" element={<StatsView />} />
              <Route path="leveling" element={<LevelingDashboard />} />
              <Route path="chat-history" element={<ChatHistoryView />} />
              <Route path="settings" element={<SettingsView />} />
              <Route path="updates" element={<UpdatesView />} />
            </Route>
          </Routes>
        </HashRouter>
      </QueryClientProvider>
    </ChakraProvider>
  )
}

export default App
