import { Box, VStack, Text, Link as ChakraLink, Divider } from '@chakra-ui/react'
import { Link, useLocation } from 'react-router-dom'

const Sidebar = () => {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true
    if (path !== '/' && location.pathname.startsWith(path)) return true
    return false
  }

  const NavLink = ({ to, children }: { to: string; children: React.ReactNode }) => (
    <ChakraLink
      as={Link}
      to={to}
      display="block"
      px={4}
      py={2}
      borderRadius="md"
      bg={isActive(to) ? 'brand.400' : 'transparent'}
      color={isActive(to) ? 'white' : 'gray.300'}
      _hover={{
        bg: isActive(to) ? 'brand.500' : 'whiteAlpha.100',
        textDecoration: 'none',
      }}
      transition="all 0.2s"
      fontWeight={isActive(to) ? '600' : '400'}
    >
      {children}
    </ChakraLink>
  )

  return (
    <Box
      as="aside"
      w="250px"
      h="100vh"
      bg="#1A1A1A"
      borderRight="1px solid"
      borderColor="whiteAlpha.200"
      position="fixed"
      left={0}
      top={0}
      overflowY="auto"
    >
      <Box p={6}>
        <Text fontSize="2xl" fontWeight="bold" color="brand.400">
          Drongo
        </Text>
      </Box>

      <VStack spacing={1} align="stretch" px={3}>
        <NavLink to="/">Main</NavLink>
        <NavLink to="/logs">Logs</NavLink>

        <Divider my={3} borderColor="whiteAlpha.200" />

        <Text
          px={4}
          py={2}
          fontSize="xs"
          fontWeight="600"
          color="gray.500"
          textTransform="uppercase"
          letterSpacing="wider"
        >
          Config
        </Text>

        <NavLink to="/commands">Commands</NavLink>
        <NavLink to="/stats">Stats</NavLink>
        <NavLink to="/leveling">Leveling</NavLink>
        <NavLink to="/chat-history">Chat History</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </VStack>
    </Box>
  )
}

export default Sidebar
