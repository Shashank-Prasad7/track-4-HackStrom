import { Activity, AlertTriangle, Wifi, WifiOff, Loader2 } from 'lucide-react'
import { useAgentSocket } from './hooks/useAgentSocket'
import type { AgentEvent, HeartbeatEvent } from './types'

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

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  if (status === 'connected') {
    return (
      <span className="flex items-center gap-1.5 text-emerald-400 text-xs">
        <Wifi size={12} />
        Live
      </span>
    )
  }
  if (status === 'reconnecting') {
    return (
      <span className="flex items-center gap-1.5 text-amber-400 text-xs">
        <Loader2 size={12} className="animate-spin" />
        Reconnecting…
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1.5 text-gray-500 text-xs">
      <WifiOff size={12} />
      Offline
    </span>
  )
}

// ── Log event renderer (placeholder — full implementation in H4-H6) ────────────

function EventRow({ event }: { event: AgentEvent }) {
  const base = 'text-xs px-3 py-2 rounded border animate-slide-in'

  if (event.type === 'heartbeat') {
    const hb = event as HeartbeatEvent
    return (
      <div className={`${base} border-gray-800 text-gray-500 flex items-center gap-2`}>
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse-slow inline-block" />
        <span>
          {hb.active_shipments} vessels active · {hb.at_risk_count} at risk
          {hb.brewing_risks.length > 0 && (
            <span className="text-amber-400 ml-2">
              ⚠ {hb.brewing_risks[0].vessel_name} — {hb.brewing_risks[0].risk_type}
            </span>
          )}
        </span>
        <span className="ml-auto text-gray-700">{new Date(event.timestamp).toLocaleTimeString()}</span>
      </div>
    )
  }

  if (event.type === 'system') {
    const color = event.status === 'fallback_activated' ? 'text-amber-400 border-amber-900/50 bg-amber-950/20'
      : event.status === 'agent_start' ? 'text-sky-400 border-sky-900/50 bg-sky-950/20'
      : 'text-gray-500 border-gray-800'
    return (
      <div className={`${base} ${color}`}>
        <span className="font-mono">[SYSTEM]</span> {event.message}
      </div>
    )
  }

  if (event.type === 'observation') {
    const color = event.severity === 'critical' ? 'text-red-300 border-red-900/50 bg-red-950/20'
      : event.severity === 'warning' ? 'text-amber-300 border-amber-900/50 bg-amber-950/20'
      : 'text-gray-300 border-gray-800'
    return (
      <div className={`${base} ${color}`}>
        <span className="font-semibold">{event.vessel_name}</span>
        <span className="mx-1.5 text-gray-600">·</span>
        {event.message}
        {event.data.delay_hours != null && (
          <span className="ml-2 font-mono text-amber-400">+{event.data.delay_hours}h</span>
        )}
      </div>
    )
  }

  if (event.type === 'tool_call') {
    return (
      <div className={`${base} border-indigo-900/50 bg-indigo-950/20 text-indigo-300`}>
        <span className="font-mono text-indigo-500">[TOOL]</span>
        <span className="ml-2 font-semibold">{event.tool_name}</span>
        <span className="ml-2 text-indigo-600 font-mono text-[10px]">
          {JSON.stringify(event.arguments).slice(0, 60)}…
        </span>
      </div>
    )
  }

  if (event.type === 'tool_result') {
    return (
      <div className={`${base} border-indigo-900/30 bg-indigo-950/10 text-indigo-400`}>
        <span className="font-mono text-indigo-600">[RESULT]</span>
        <span className="ml-2">{event.tool_name}</span>
        <span className={`ml-2 text-[10px] font-mono ${event.success ? 'text-emerald-600' : 'text-red-500'}`}>
          {event.success ? '✓' : '✗'} {event.duration_ms}ms
        </span>
      </div>
    )
  }

  if (event.type === 'explanation') {
    return (
      <div className={`${base} border-gray-700 bg-gray-900/60 text-gray-300 leading-relaxed`}>
        {event.text}
      </div>
    )
  }

  if (event.type === 'decision') {
    const urgencyColor = event.urgency === 'critical' ? 'bg-red-500'
      : event.urgency === 'high' ? 'bg-orange-500'
      : event.urgency === 'medium' ? 'bg-amber-500'
      : 'bg-emerald-500'
    const confidencePct = Math.round(event.confidence * 100)
    return (
      <div className={`${base} border-emerald-900/50 bg-emerald-950/20 space-y-2`}>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${urgencyColor}`} />
          <span className="font-semibold text-emerald-300">{event.recommended_action}</span>
          <span className="ml-auto text-xs text-gray-500">{event.vessel_name}</span>
        </div>
        {/* Confidence bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${confidencePct >= 80 ? 'bg-emerald-500' : confidencePct >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <span className="text-xs font-mono text-gray-400">{confidencePct}%</span>
        </div>
        {/* Factors */}
        <div className="flex flex-wrap gap-1">
          {event.factors_considered.map(f => (
            <span key={f} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{f}</span>
          ))}
        </div>
        {/* Alternatives placeholder — full DecisionCard in H6-H8 */}
        {event.alternatives.length > 0 && (
          <div className="text-[11px] text-gray-500 pl-1 border-l border-gray-700 space-y-0.5">
            {event.alternatives.map((alt, i) => (
              <div key={i}>
                <span className="text-gray-400">{alt.action}</span>
                <span className="mx-1">·</span>
                <span>{alt.tradeoff}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return null
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const { events, status, isAgentRunning } = useAgentSocket()

  const latestHeartbeat = [...events].reverse().find(e => e.type === 'heartbeat') as HeartbeatEvent | undefined
  const atRisk = latestHeartbeat?.at_risk_count ?? 0
  const activeVessels = latestHeartbeat?.active_shipments ?? 11

  async function triggerScenario(scenarioId: string) {
    await fetch('http://localhost:8000/events/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioId }),
    })
  }

  return (
    <div className="h-screen w-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden select-none">

      {/* ── Header ── */}
      <header className="h-11 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-4 shrink-0 z-10">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-emerald-400" />
          <span className="text-sm font-bold tracking-widest text-gray-100 uppercase">
            Supply Chain Control Tower
          </span>
        </div>

        <div className="h-4 w-px bg-gray-700" />

        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span>
            <span className="text-gray-200 font-semibold">{activeVessels}</span> vessels
          </span>
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

      {/* ── Main panels ── */}
      <div className="flex flex-1 min-h-0">

        {/* Map panel — filled in H2-H4 */}
        <div className="flex-1 bg-gray-900 relative min-w-0">
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-700">
            <Activity size={40} strokeWidth={1} />
            <p className="text-sm">Map loads in H2–H4 milestone</p>
            <p className="text-xs">react-leaflet · 11 vessel markers</p>
          </div>
        </div>

        {/* Log panel */}
        <div className="w-[440px] border-l border-gray-800 bg-gray-950 flex flex-col shrink-0">
          <div className="h-10 border-b border-gray-800 flex items-center px-4 gap-2 shrink-0">
            <span className="text-[11px] font-bold text-gray-500 tracking-widest uppercase">Agent Log</span>
            <span className="ml-auto text-[10px] text-gray-700">{events.length} events</span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {events.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-700">
                <span className="w-2 h-2 rounded-full bg-emerald-800 animate-pulse" />
                <p className="text-xs">Monitoring {activeVessels} vessels · System nominal</p>
                <p className="text-[10px] text-gray-800">Trigger a scenario to begin</p>
              </div>
            ) : (
              events.map(event => <EventRow key={event.id} event={event} />)
            )}
          </div>
        </div>
      </div>

      {/* ── Scenario triggers ── */}
      <div className="h-14 bg-gray-900 border-t border-gray-800 flex items-center gap-2.5 px-4 shrink-0">
        <span className="text-[10px] font-bold text-gray-600 tracking-widest uppercase mr-1">Simulate</span>
        {SCENARIOS.map(s => (
          <button
            key={s.id}
            onClick={() => triggerScenario(s.id)}
            disabled={isAgentRunning}
            className={`
              px-3 py-1.5 rounded border text-[11px] font-semibold transition-all
              disabled:opacity-40 disabled:cursor-not-allowed
              ${SCENARIO_COLORS[s.color]}
            `}
            title={s.description}
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
