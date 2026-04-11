import { useState } from 'react'
import { Activity, AlertTriangle, Wifi, WifiOff, Loader2, Clock, AlertOctagon } from 'lucide-react'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'
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
  orange: 'border-orange-800 hover:bg-orange-900/60',
  blue:   'border-blue-800   hover:bg-blue-900/60',
  purple: 'border-purple-800 hover:bg-purple-900/60',
  red:    'border-red-800    hover:bg-red-900/60',
}

const SCENARIO_BG: Record<string, string> = {
  orange: 'bg-orange-950/50 text-orange-300',
  blue:   'bg-blue-950/50   text-blue-300',
  purple: 'bg-purple-950/50 text-purple-300',
  red:    'bg-red-950/50    text-red-300',
}

const SCENARIO_ACTIVE: Record<string, string> = {
  orange: 'bg-orange-900/80 text-orange-200 ring-1 ring-orange-600/60',
  blue:   'bg-blue-900/80   text-blue-200   ring-1 ring-blue-600/60',
  purple: 'bg-purple-900/80 text-purple-200 ring-1 ring-purple-600/60',
  red:    'bg-red-900/80    text-red-200    ring-1 ring-red-600/60',
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
  const { events, vessels, status, isAgentRunning, systemStatus, lastAgentRunAt, clearEvents } = useAgentSocket()
  const [highlightedPort,   setHighlightedPort]   = useState<string | undefined>()
  const [activeScenarioId,  setActiveScenarioId]  = useState<string | undefined>()

  const latestHeartbeat = [...events].reverse().find(e => e.type === 'heartbeat') as HeartbeatEvent | undefined
  const atRisk        = latestHeartbeat?.at_risk_count ?? 0
  const activeVessels = latestHeartbeat?.active_shipments ?? 11

  // Sparkline: last 24 heartbeat at_risk_count values
  const sparkData = events
    .filter(e => e.type === 'heartbeat')
    .slice(-24)
    .map(e => ({ v: (e as HeartbeatEvent).at_risk_count }))

  function handleClear() {
    clearEvents()
    setHighlightedPort(undefined)
    setActiveScenarioId(undefined)
  }

  const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

  async function triggerCounterfactual(shipmentId: string, delayHours: number) {
    await fetch(`${API}/events/counterfactual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shipment_id: shipmentId, delay_hours: delayHours }),
    })
  }

  async function triggerScenario(scenarioId: string) {
    const port = SCENARIO_PORT[scenarioId]
    setHighlightedPort(port || undefined)
    setActiveScenarioId(scenarioId)
    if (port) setTimeout(() => setHighlightedPort(undefined), 30_000)
    await fetch(`${API}/events/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioId }),
    })
  }

  const isFallback = systemStatus === 'fallback'

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden select-none">

      {/* ── Fallback banner ── */}
      {isFallback && (
        <div className="shrink-0 h-7 bg-amber-950/80 border-b border-amber-800/60 flex items-center justify-center gap-2 animate-fade-in">
          <AlertOctagon size={12} className="text-amber-400" />
          <span className="text-[11px] font-semibold text-amber-400 tracking-wider uppercase">
            Fallback Mode Active — Claude API unreachable · Rule-based decisions in effect
          </span>
        </div>
      )}

      {/* ── Header ── */}
      <header className="h-11 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-4 shrink-0 z-10">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-emerald-400" />
          <span className="font-display text-sm font-bold text-gray-100 uppercase">
            Supply Chain Control Tower
          </span>
        </div>

        <div className="h-4 w-px bg-gray-700" />

        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span>
            <span className="proj-number text-gray-200">{activeVessels}</span>
            <span className="proj-label ml-1">vessels</span>
          </span>
          {atRisk > 0 ? (
            <span className="flex items-center gap-1 text-amber-400">
              <AlertTriangle size={11} />
              <span className="proj-number">{atRisk}</span>
              <span className="proj-label ml-0.5">at risk</span>
            </span>
          ) : (
            <span className="text-emerald-600 proj-label">All nominal</span>
          )}
          {isAgentRunning && (
            <span className="flex items-center gap-1.5 proj-label animate-pulse" style={{ color: 'var(--od-teal)' }}>
              <Loader2 size={11} className="animate-spin" />
              Agent running
            </span>
          )}
          {lastAgentRunAt && !isAgentRunning && (
            <span className="flex items-center gap-1 text-gray-600 proj-caption">
              <Clock size={10} />
              {new Date(lastAgentRunAt).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Risk sparkline — live at_risk_count over last 24 heartbeats */}
        {sparkData.length > 2 && (
          <div className="w-28 h-7 ml-2 opacity-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sparkData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={atRisk > 0 ? '#f59e0b' : '#10b981'}
                  fill={atRisk > 0 ? '#f59e0b22' : '#10b98122'}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="ml-auto">
          <StatusBadge status={status} />
        </div>
      </header>

      {/* ── Main panels ── */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 relative min-w-0">
          <MapView vessels={vessels} highlightedPort={highlightedPort} />
        </div>

        <LogPanel
          events={events}
          activeVessels={activeVessels}
          isAgentRunning={isAgentRunning}
          onCounterfactual={triggerCounterfactual}
          onClear={handleClear}
        />
      </div>

      {/* ── Scenario triggers ── */}
      <div className="h-14 bg-gray-900 border-t border-gray-800 flex items-center gap-2.5 px-4 shrink-0">
        <span className="text-[10px] font-bold text-gray-600 tracking-widest uppercase mr-1">Simulate</span>
        {SCENARIOS.map(s => {
          const isActive = activeScenarioId === s.id && isAgentRunning
          const colorClass = isActive
            ? SCENARIO_ACTIVE[s.color]
            : `${SCENARIO_BG[s.color]} ${SCENARIO_COLORS[s.color]}`
          return (
            <button
              key={s.id}
              onClick={() => triggerScenario(s.id)}
              disabled={isAgentRunning}
              title={s.description}
              className={`px-3 py-1.5 rounded border text-[11px] font-semibold transition-all disabled:cursor-not-allowed ${colorClass} ${isAgentRunning && !isActive ? 'opacity-40' : ''}`}
            >
              {isActive
                ? <span className="flex items-center gap-1.5"><Loader2 size={10} className="animate-spin" />{s.label}</span>
                : s.label
              }
            </button>
          )
        })}
      </div>

    </div>
  )
}
