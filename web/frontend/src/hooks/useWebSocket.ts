import { useEffect, useState, useRef } from 'react'
import { wsService } from '@/services/websocket'
import { useToast } from '@chakra-ui/react'

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false)
  const toast = useToast()
  const hasShownConnectedToast = useRef(false)

  useEffect(() => {
    wsService.connect()

    const handleStatsUpdate = () => {
      // Only update connection status and show toast if transitioning from disconnected to connected
      setIsConnected((prev) => {
        if (!prev && !hasShownConnectedToast.current) {
          hasShownConnectedToast.current = true
          toast({
            title: 'Connected',
            status: 'success',
            duration: 2000,
            position: 'top-right',
          })
        }
        return true
      })
    }

    // Monitor connection by listening to stats_update
    wsService.on('stats_update', handleStatsUpdate)

    return () => {
      wsService.off('stats_update', handleStatsUpdate)
      wsService.disconnect()
    }
  }, [toast])

  return { isConnected }
}
