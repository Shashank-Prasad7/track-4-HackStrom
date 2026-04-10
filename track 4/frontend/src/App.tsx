import { useState } from 'react'
import { Activity, AlertTriangle, Wifi, WifiOff, Loader2 } from 'lucide-react'
import { useAgentSocket } from './hooks/useAgentSocket'
import { MapView } from './components/MapView'
import { LogPanel } from './components/LogPanel'
import type { HeartbeatEvent } from './types'

// ── Scenario config ───────────────────────────────────────────────────────────

const SCENARIOS = [
  {
    id: 'storm_jebel_ali',
    label: 'Storm · Jebel Ali',
    description: 'Port closure 48h · 3 vessels affected',
    color: 'orange',
  },
  {
    id: 'customs_hold_singapore',
    label: 'Customs Hold · Singapore',
    description: 'Documentation hold · factory at risk',
    color: 'blue',
  },
  {
    id: 'carrier_capacity_drop',
    label: 'Carrier Capacity Drop',
    description: 'Maersk –40% Asia-Europe · 5 bookings',
    color: 'purple',
  },
  {
    id: 'cascade_colombo',
    label: 'Cascade · Colombo',
    description: '6h delay → customs window breach',
    color: 'red',
  },
] as const

const SCENARIO_COLORS: Record<string, string> = {
  orange: 'bg-orange-950/50 text-orange-300 border-orange-800 hover:bg-orange-900/60',
  blue:   'bg-blue-950/50   text-blue-300   border-blue-800   hover:bg-blue-900/60',
  purple: 'bg-purple-950/50 text-purple-300 border-purple-800 hover:bg-purple-900/60',
  red:    'bg-red-950/50    text-red-300    border-red-800    hover:bg-red-900/60',
}

const SCENARIO_PORT: Record<string, string> = {
  storm_jebel_ali:        'AEJEA',
  customs_hold_singapore: 'SGSIN',
  cascade_colombo:        'LKCMB',
  carrier_capacity_drop:  '',
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  if (status === 'connected')
    return <span className="flex items-center gap-1.5 text-emerald-400 text-xs"><Wifi size={12} />Live</span>
  if (status === 'reconnecting')
    return <span className="flex items-center gap-1.5 text-amber-400 text-xs"><Loader2 size={12} className="animate-spin" />Reconnecting…</span>
  return <span className="flex items-center gap-1.5 text-gray-500 text-xs"><WifiOff size={12} />Offline</span>
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const { events, vessels, status, isAgentRunning } = useAgentSocket()
  const [highlightedPort, setHighlightedPort] = useState<string | undefined>()

  const latestHeartbeat = [...events].reverse().find(e => e.type === 'heartbeat') as HeartbeatEvent | undefined
  const atRisk = latestHeartbeat?.at_risk_count ?? 0
  const activeVessels = latestHeartbeat?.active_shipments ?? 11

  async function triggerCounterfactual(shipmentId: string, delayHours: number) {
    await fetch('http://localhost:8000/events/counterfactual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shipment_id: shipmentId, delay_hours: delayHours }),
    })
  }

  async function triggerScenario(scenarioId: string) {
    const port = SCENARIO_PORT[scenarioId]
    setHighlightedPort(port || undefined)
    if (port) setTimeout(() => setHighlightedPort(undefined), 30_000)
    await fetch('http://localhost:8000/events/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioId }),
    })
  }

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden select-none">

      {/* Header */}
      <header className="h-11 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-4 shrink-0 z-10">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-emerald-400" />
          <span className="text-sm font-bold tracking-widest text-gray-100 uppercase">
            Supply Chain Control Tower
          </span>
        </div>

        <div className="h-4 w-px bg-gray-700" />

        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span><span className="text-gray-200 font-semibold">{activeVessels}</span> vessels</span>
          {atRisk > 0 ? (
            <span className="flex items-center gap-1 text-amber-400">
              <AlertTriangle size={11} />
              <span className="font-semibold">{atRisk}</span> at risk
            </span>
          ) : (
            <span className="text-emerald-600">All nominal</span>
          )}
          {isAgentRunning && (
            <span className="flex items-center gap-1.5 text-sky-400">
              <Loader2 size={11} className="animate-spin" />
              Agent running
            </span>
          )}
        </div>

        <div className="ml-auto">
          <StatusBadge status={status} />
        </div>
      </header>

      {/* Main panels */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 relative min-w-0">
          <MapView vessels={vessels} highlightedPort={highlightedPort} />
        </div>

        <LogPanel
          events={events}
          activeVessels={activeVessels}
          onCounterfactual={triggerCounterfactual}
        />
      </div>

      {/* Scenario triggers */}
      <div className="h-14 bg-gray-900 border-t border-gray-800 flex items-center gap-2.5 px-4 shrink-0">
        <span className="text-[10px] font-bold text-gray-600 tracking-widest uppercase mr-1">Simulate</span>
        {SCENARIOS.map(s => (
          <button
            key={s.id}
            onClick={() => triggerScenario(s.id)}
            disabled={isAgentRunning}
            title={s.description}
            className={`px-3 py-1.5 rounded border text-[11px] font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed ${SCENARIO_COLORS[s.color]}`}
          >
            {isAgentRunning
              ? <span className="flex items-center gap-1.5"><Loader2 size={10} className="animate-spin" />{s.label}</span>
              : s.label
            }
          </button>
        ))}
      </div>

    </div>
  )
}
