import { useEffect, useRef } from 'react'
import { Trash2 } from 'lucide-react'
import type {
  AgentEvent, HeartbeatEvent, ObservationEvent,
  ToolCallEvent, ToolResultEvent, ExplanationEvent,
  DecisionEvent, CounterfactualEvent, SystemEvent,
} from '../types'

// ── Shared timestamp helper ───────────────────────────────────────────────────

function Ts({ timestamp }: { timestamp: string }) {
  return (
    <span className="ml-auto shrink-0 font-mono text-[10px] text-gray-800 tabular-nums pl-2">
      {new Date(timestamp).toLocaleTimeString()}
    </span>
  )
}

// ── Individual event renderers ────────────────────────────────────────────────

function HeartbeatRow({ event }: { event: HeartbeatEvent }) {
  const hot = event.brewing_risks.length > 0
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-600 border-b border-gray-900/60">
      <span className={`w-2 h-2 rounded-full shrink-0 ${hot ? 'bg-amber-500 animate-pulse' : 'bg-emerald-800 animate-pulse'}`} />
      <span className={hot ? 'text-amber-500' : ''}>
        {event.active_shipments} vessels
        {event.at_risk_count > 0 ? ` · ${event.at_risk_count} at risk` : ' · all nominal'}
        {hot && ` · ⚠ ${event.brewing_risks[0].vessel_name}`}
      </span>
      {event.system_status === 'fallback' && (
        <span className="text-amber-600 font-semibold text-[10px]">FALLBACK</span>
      )}
      <Ts timestamp={event.timestamp} />
    </div>
  )
}

function SystemRow({ event }: { event: SystemEvent }) {
  const styles: Record<string, string> = {
    agent_start:        'text-sky-400 border-sky-900/40 bg-sky-950/20',
    agent_end:          'text-gray-500 border-gray-800',
    fallback_activated: 'text-amber-400 border-amber-900/40 bg-amber-950/20',
    reconnected:        'text-emerald-400 border-emerald-900/40',
  }
  return (
    <div className={`px-3 py-1.5 rounded border text-xs animate-slide-in flex items-center gap-2 ${styles[event.status] ?? 'text-gray-500 border-gray-800'}`}>
      <span className="font-mono opacity-60">[SYS]</span>
      <span className="flex-1">{event.message}</span>
      <Ts timestamp={event.timestamp} />
    </div>
  )
}

function ObservationCard({ event }: { event: ObservationEvent }) {
  const styles = {
    critical: 'text-red-300   border-red-900/50   bg-red-950/20',
    warning:  'text-amber-300 border-amber-900/50 bg-amber-950/20',
    info:     'text-gray-300  border-gray-700',
  }
  const icons = { critical: '🔴', warning: '🟡', info: '⚪' }
  return (
    <div className={`px-3 py-2 rounded border text-sm animate-slide-in ${styles[event.severity]}`}>
      <div className="flex items-center gap-1.5 font-semibold">
        <span>{icons[event.severity]}</span>
        <span>{event.vessel_name}</span>
        <span className="text-[10px] font-mono opacity-50 ml-1">{event.shipment_id}</span>
        <Ts timestamp={event.timestamp} />
      </div>
      <div className="mt-1 opacity-80 text-xs leading-relaxed">{event.message}</div>
      {event.data.delay_hours != null && (
        <div className="mt-1 font-mono text-amber-400">
          <span className="proj-number">+{event.data.delay_hours}h</span>
          <span className="proj-label ml-1 text-amber-600">delay</span>
        </div>
      )}
    </div>
  )
}

function ToolCallRow({ event }: { event: ToolCallEvent }) {
  const argStr = JSON.stringify(event.arguments)
  const preview = argStr.length > 72 ? argStr.slice(0, 72) + '…' : argStr
  return (
    <div className="px-3 py-1.5 rounded border border-indigo-900/40 bg-indigo-950/15 text-xs animate-slide-in flex items-center gap-1">
      <span className="text-indigo-500 font-mono">▶ </span>
      <span className="text-indigo-300 font-semibold">{event.tool_name}</span>
      <span className="text-indigo-700 ml-1 font-mono text-[11px] truncate flex-1">{preview}</span>
      <Ts timestamp={event.timestamp} />
    </div>
  )
}

function ToolResultRow({ event }: { event: ToolResultEvent }) {
  return (
    <div className="px-3 py-1 rounded border border-indigo-900/20 bg-indigo-950/8 text-xs animate-slide-in flex items-center gap-2">
      <span className={`font-mono ${event.success ? 'text-emerald-600' : 'text-red-500'}`}>
        {event.success ? '✓' : '✗'}
      </span>
      <span className="text-indigo-600">{event.tool_name}</span>
      <span className="text-gray-700 font-mono">{event.duration_ms}ms</span>
      <Ts timestamp={event.timestamp} />
    </div>
  )
}

function ExplanationBlock({ event }: { event: ExplanationEvent }) {
  return (
    <div className="px-3 py-2.5 rounded border border-gray-700/60 bg-gray-900/50 text-sm text-gray-300 leading-relaxed animate-slide-in">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider">Reasoning</span>
        <Ts timestamp={event.timestamp} />
      </div>
      {event.text}
    </div>
  )
}

function DecisionCard({
  event,
  onCounterfactual,
}: {
  event: DecisionEvent
  onCounterfactual: (id: string, hours: number) => void
}) {
  const pct = Math.round(event.confidence * 100)
  const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'

  const urgencyDot: Record<string, string> = {
    critical: 'bg-red-500',
    high:     'bg-orange-500',
    medium:   'bg-amber-500',
    low:      'bg-emerald-500',
  }

  const actionBadge: Record<string, string> = {
    reroute:       'bg-blue-900/50   text-blue-300   border-blue-800',
    vendor_switch: 'bg-purple-900/50 text-purple-300 border-purple-800',
    expedite:      'bg-orange-900/50 text-orange-300 border-orange-800',
    hold:          'bg-gray-800      text-gray-400   border-gray-700',
    notify:        'bg-teal-900/50   text-teal-300   border-teal-800',
    escalate:      'bg-red-900/50    text-red-300    border-red-800',
  }

  return (
    <div className="px-3 py-3 rounded border border-emerald-900/50 bg-emerald-950/15 space-y-2.5 animate-slide-in">

      {/* Header */}
      <div className="flex items-start gap-2">
        <span className={`mt-1 w-2.5 h-2.5 rounded-full shrink-0 ${urgencyDot[event.urgency] ?? 'bg-gray-500'}`} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-emerald-300 leading-snug">{event.recommended_action}</div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className={`text-[11px] px-1.5 py-px rounded border font-semibold ${actionBadge[event.action_type] ?? 'bg-gray-800 text-gray-400 border-gray-700'}`}>
              {event.action_type.replace('_', ' ')}
            </span>
            <span className="text-[11px] text-gray-500">{event.vessel_name}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-0.5 shrink-0">
          <span className="text-[11px] font-mono text-gray-600">{event.urgency}</span>
          <Ts timestamp={event.timestamp} />
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="proj-number text-gray-300 w-10 text-right">{pct}%</span>
      </div>

      {/* Reasoning */}
      <p className="text-xs text-gray-400 leading-relaxed">{event.reasoning_summary}</p>

      {/* Factors */}
      {event.factors_considered.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {event.factors_considered.map(f => (
            <span key={f} className="text-[11px] px-1.5 py-px rounded bg-gray-800/80 text-gray-500 border border-gray-700/50">
              {f}
            </span>
          ))}
        </div>
      )}

      {/* Alternatives */}
      {event.alternatives.length > 0 && (
        <div className="space-y-1 pl-2 border-l-2 border-gray-800">
          <div className="text-[10px] text-gray-600 font-semibold uppercase tracking-wider">Alternatives</div>
          {event.alternatives.map((alt, i) => (
            <div key={i} className="flex gap-2 text-xs">
              <span className="text-gray-500 font-mono w-8 shrink-0 tabular-nums">{Math.round(alt.confidence * 100)}%</span>
              <div>
                <span className="text-gray-400">{alt.action}</span>
                <span className="text-gray-600 ml-1">— {alt.tradeoff}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Cost estimates */}
      {(event.estimated_cost_usd != null || event.estimated_time_saving_hours != null) && (
        <div className="flex gap-4 proj-label text-gray-500">
          {event.estimated_cost_usd != null && (
            <span>Cost: <span className="proj-number text-gray-200">${event.estimated_cost_usd.toLocaleString()}</span></span>
          )}
          {event.estimated_time_saving_hours != null && (
            <span>Saves: <span className="proj-number text-gray-200">{event.estimated_time_saving_hours}h</span></span>
          )}
        </div>
      )}

      {/* Counterfactual button */}
      <button
        onClick={() => onCounterfactual(event.shipment_id, 48)}
        className="text-xs px-3 py-1.5 rounded border border-red-900/40 text-red-500 hover:bg-red-950/30 hover:text-red-400 transition-colors font-semibold"
      >
        What if we don't act? →
      </button>
    </div>
  )
}

function CounterfactualCard({ event }: { event: CounterfactualEvent }) {
  const p = event.projected_outcomes
  return (
    <div className="px-3 py-2.5 rounded border border-red-900/50 bg-red-950/20 space-y-2 animate-slide-in">
      <div className="flex items-center gap-2">
        <div className="text-xs font-bold text-red-400 uppercase tracking-wider">Cost of Inaction</div>
        <Ts timestamp={event.timestamp} />
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-gray-500">Additional delay</span>
        <span className="proj-number text-red-300">+{p.additional_delay_hours}h</span>
        <span className="text-gray-500">Penalty estimate</span>
        <span className="proj-number text-red-300">${p.estimated_penalty_usd.toLocaleString()}</span>
        <span className="text-gray-500">SLA breaches</span>
        <span className="proj-number text-red-300">{p.sla_breaches}</span>
        <span className="text-gray-500">Cascade vessels</span>
        <span className="proj-number text-red-300">{p.cascade_affected_shipments}</span>
      </div>
      {p.cargo_at_risk.map((c, i) => (
        <div key={i} className="text-[11px] text-red-600">
          ⚠ {c.cargo_type.replace(/_/g, ' ')}: {c.risk.slice(0, 80)}
        </div>
      ))}
    </div>
  )
}

// ── Session divider ───────────────────────────────────────────────────────────

function SessionDivider({ timestamp }: { timestamp: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <div className="flex-1 h-px bg-gray-800" />
      <span className="text-[10px] text-gray-700 font-mono shrink-0 tracking-wider">
        ── {new Date(timestamp).toLocaleTimeString()} ──
      </span>
      <div className="flex-1 h-px bg-gray-800" />
    </div>
  )
}

// ── Log Panel ─────────────────────────────────────────────────────────────────

interface LogPanelProps {
  events:          AgentEvent[]
  activeVessels:   number
  isAgentRunning:  boolean
  onCounterfactual: (shipmentId: string, delayHours: number) => void
  onClear:         () => void
}

export function LogPanel({ events, activeVessels, isAgentRunning, onCounterfactual, onClear }: LogPanelProps) {
  const endRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom whenever new events arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  // Build rendered list, injecting session dividers when session_id changes
  const items: Array<{ key: string; node: React.ReactNode }> = []
  let lastSessionId: string | undefined

  for (const event of events) {
    if (event.type === 'heartbeat') {
      items.push({ key: event.id, node: <HeartbeatRow event={event as HeartbeatEvent} /> })
      continue
    }

    // Session divider on new session
    if (event.session_id && event.session_id !== lastSessionId && event.type === 'system') {
      if (lastSessionId !== undefined) {
        items.push({
          key: `divider-${event.id}`,
          node: <SessionDivider timestamp={event.timestamp} />,
        })
      }
      lastSessionId = event.session_id
    }

    switch (event.type) {
      case 'system':
        items.push({ key: event.id, node: <SystemRow event={event as SystemEvent} /> })
        break
      case 'observation':
        items.push({ key: event.id, node: <ObservationCard event={event as ObservationEvent} /> })
        break
      case 'tool_call':
        items.push({ key: event.id, node: <ToolCallRow event={event as ToolCallEvent} /> })
        break
      case 'tool_result':
        items.push({ key: event.id, node: <ToolResultRow event={event as ToolResultEvent} /> })
        break
      case 'explanation':
        items.push({ key: event.id, node: <ExplanationBlock event={event as ExplanationEvent} /> })
        break
      case 'decision':
        items.push({
          key: event.id,
          node: <DecisionCard event={event as DecisionEvent} onCounterfactual={onCounterfactual} />,
        })
        break
      case 'counterfactual':
        items.push({ key: event.id, node: <CounterfactualCard event={event as CounterfactualEvent} /> })
        break
    }
  }

  // Dynamic border when agent is running
  const panelBorder = isAgentRunning
    ? 'border-l teal-glow'
    : 'border-l border-gray-800'

  return (
    <div className={`w-[460px] bg-gray-950 flex flex-col shrink-0 transition-all duration-500 ${panelBorder}`}>
      {/* Header */}
      <div className="h-10 border-b border-gray-800 flex items-center px-4 gap-2 shrink-0">
        <span className="text-xs font-bold text-gray-500 tracking-widest uppercase">Agent Log</span>
        {isAgentRunning && (
          <span className="flex items-center gap-1 text-[10px] animate-pulse" style={{ color: 'var(--od-teal)' }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--od-teal)' }} />
            Live
          </span>
        )}
        <span className="ml-auto text-[10px] text-gray-700 tabular-nums">{events.length} events</span>
        {events.length > 0 && (
          <button
            onClick={onClear}
            title="Clear log"
            className="ml-2 p-1 rounded text-gray-700 hover:text-gray-400 hover:bg-gray-800 transition-colors"
          >
            <Trash2 size={11} />
          </button>
        )}
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-700 pb-8">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-800 animate-pulse" />
              <span className="text-sm font-semibold text-gray-600">Monitoring {activeVessels} vessels</span>
              <span className="w-2 h-2 rounded-full bg-emerald-800 animate-pulse" />
            </div>
            <p className="text-xs text-gray-700">System nominal · All routes clear</p>
            <p className="text-[11px] text-gray-800 mt-1">Trigger a scenario below to begin</p>
          </div>
        ) : (
          items.map(({ key, node }) => <div key={key}>{node}</div>)
        )}
        <div ref={endRef} />
      </div>
    </div>
  )
}
