import {
  Box,
  Heading,
  VStack,
  SimpleGrid,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react'
import GuildSelector from './GuildSelector'
import Leaderboard from './Leaderboard'
import XPFeed from './XPFeed'
import ConfigPanel from './ConfigPanel'
import RankManagement from './RankManagement'
import TemplateManagement from './TemplateManagement'
import LevelRangeManagement from './LevelRangeManagement'
import UserLookup from './UserLookup'
import AdminPanel from './AdminPanel'

const LevelingDashboard = () => {
  return (
    <Box>
      <Heading size="lg" mb={6}>
        Leveling Dashboard
      </Heading>

      <VStack spacing={6} align="stretch">
        <GuildSelector />

        {/* Live Section */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          <Leaderboard />
          <XPFeed />
        </SimpleGrid>

        {/* Management Tabs */}
        <Tabs colorScheme="brand">
          <TabList>
            <Tab>Configuration</Tab>
            <Tab>Ranks</Tab>
            <Tab>Templates</Tab>
            <Tab>Level Ranges</Tab>
            <Tab>User Lookup</Tab>
            <Tab>Admin</Tab>
          </TabList>

          <TabPanels>
            <TabPanel px={0}>
              <ConfigPanel />
            </TabPanel>
            <TabPanel px={0}>
              <RankManagement />
            </TabPanel>
            <TabPanel px={0}>
              <TemplateManagement />
            </TabPanel>
            <TabPanel px={0}>
              <LevelRangeManagement />
            </TabPanel>
            <TabPanel px={0}>
              <UserLookup />
            </TabPanel>
            <TabPanel px={0}>
              <AdminPanel />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  )
}

export default LevelingDashboard
