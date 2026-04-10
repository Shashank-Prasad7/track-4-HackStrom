import { useState, useEffect, useRef, useCallback } from 'react'
import type { AgentEvent, VesselState } from '../types'

export type SocketStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

export interface UseAgentSocketReturn {
  events: AgentEvent[]
  vessels: Record<string, VesselState>
  status: SocketStatus
  isAgentRunning: boolean
  clearEvents: () => void
}

const WS_URL = 'ws://localhost:8000/ws'
const MAX_RETRIES = 5
const MAX_EVENTS = 500

export function useAgentSocket(): UseAgentSocketReturn {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [vessels, setVessels] = useState<Record<string, VesselState>>({})
  const [status, setStatus] = useState<SocketStatus>('connecting')
  const [isAgentRunning, setIsAgentRunning] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus(retriesRef.current > 0 ? 'reconnecting' : 'connecting')
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setStatus('connected')
    }

    ws.onmessage = (e: MessageEvent) => {
      try {
        const event = JSON.parse(e.data as string) as AgentEvent

        // Track agent running state
        if (event.type === 'system') {
          if (event.status === 'agent_start') setIsAgentRunning(true)
          if (event.status === 'agent_end' || event.status === 'fallback_activated') {
            setIsAgentRunning(false)
          }
        }

        // Update vessel map from heartbeat (heartbeat carries fleet summary)
        // Full vessel positions come from simulator — update on every event that has position data
        if (event.type === 'observation' && event.data?.position) {
          setVessels(prev => ({
            ...prev,
            [event.shipment_id]: {
              shipment_id: event.shipment_id,
              vessel_name: event.vessel_name,
              position: event.data.position,
              next_port: event.data.next_port,
              current_port: event.data.current_port,
              cargo_type: event.data.cargo_type,
              risk_level: event.severity === 'critical' ? 'critical'
                : event.severity === 'warning' ? 'warning' : 'nominal',
              eta_original: event.data.eta_original,
            },
          }))
        }

        setEvents(prev => {
          const next = [...prev, event]
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next
        })
      } catch {
        // malformed message — ignore
      }
    }

    ws.onclose = () => {
      setStatus('disconnected')
      wsRef.current = null
      if (retriesRef.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 16000)
        retriesRef.current++
        setStatus('reconnecting')
        retryTimerRef.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      retryTimerRef.current && clearTimeout(retryTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const clearEvents = useCallback(() => setEvents([]), [])

  return { events, vessels, status, isAgentRunning, clearEvents }
}
