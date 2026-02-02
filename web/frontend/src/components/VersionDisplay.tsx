import { HStack, Text, Code, Tooltip, Spinner } from '@chakra-ui/react'
import { useGitHubStatus } from '@/hooks/useGitHub'

interface VersionDisplayProps {
  /** Display format: 'compact' (commit only), 'standard' (version + commit), 'full' (version + commit + branch) */
  format?: 'compact' | 'standard' | 'full'
  /** Version number to display (from version.json) */
  version?: string
}

const VersionDisplay = ({ format = 'standard', version = '0.1.3.2' }: VersionDisplayProps) => {
  const { data: status, isLoading } = useGitHubStatus()

  if (isLoading) {
    return <Spinner size="xs" color="gray.500" />
  }

  if (!status) {
    return null
  }

  const tooltipLabel = `Branch: ${status.current_branch} • Full commit: ${status.current_commit}`

  return (
    <Tooltip label={tooltipLabel} placement="top">
      <HStack fontSize="xs" color="gray.500" spacing={1} cursor="default">
        {format !== 'compact' && <Text>v{version}</Text>}
        {format !== 'compact' && <Text>•</Text>}
        <Code fontSize="xs" colorScheme="purple" px={1.5} py={0.5}>
          {status.current_commit_short}
        </Code>
        {format === 'full' && (
          <>
            <Text>•</Text>
            <Text>{status.current_branch}</Text>
          </>
        )}
      </HStack>
    </Tooltip>
  )
}

export default VersionDisplay
