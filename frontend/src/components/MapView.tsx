import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip, useMap } from 'react-leaflet'
import type { VesselState } from '../types'

// ── Constants ─────────────────────────────────────────────────────────────────

const PORTS = [
  { code: 'AEJEA', name: 'Jebel Ali',  lat: 25.01, lng: 55.06 },
  { code: 'SGSIN', name: 'Singapore',  lat: 1.27,  lng: 103.82 },
  { code: 'LKCMB', name: 'Colombo',    lat: 6.93,  lng: 79.84 },
  { code: 'OMSLL', name: 'Salalah',    lat: 17.02, lng: 54.09 },
]

const RISK_COLOR: Record<string, string> = {
  nominal:  '#10b981',  // emerald-500
  warning:  '#f59e0b',  // amber-500
  critical: '#ef4444',  // red-500
}

const CARGO_ICON: Record<string, string> = {
  perishable:          '🌸',
  pharmaceuticals:     '💊',
  consumer_electronics:'📦',
  automotive_parts:    '⚙️',
  industrial_machinery:'🏗️',
  bulk_grain:          '🌾',
  bulk_chemicals:      '🧪',
  textiles:            '🧵',
  consumer_goods:      '📦',
}

// ── Fit bounds helper (fires once vessels load) ───────────────────────────────

function FitBoundsOnLoad({ vessels }: { vessels: Record<string, VesselState> }) {
  const map = useMap()
  const fitted = useRef(false)

  useEffect(() => {
    if (fitted.current) return
    const points = Object.values(vessels)
    if (points.length === 0) return
    const lats = points.map(v => v.position.lat)
    const lngs = points.map(v => v.position.lng)
    map.fitBounds(
      [[Math.min(...lats) - 2, Math.min(...lngs) - 2],
       [Math.max(...lats) + 2, Math.max(...lngs) + 2]],
      { padding: [24, 24] }
    )
    fitted.current = true
  }, [vessels, map])

  return null
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface MapViewProps {
  vessels: Record<string, VesselState>
  highlightedPort?: string
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MapView({ vessels, highlightedPort }: MapViewProps) {
  const vesselList = Object.values(vessels)

  return (
    <MapContainer
      center={[15, 68]}
      zoom={4}
      className="h-full w-full"
      zoomControl
      attributionControl
    >
      {/* CartoDB dark tiles — cache on first load, work offline after */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        subdomains="abcd"
        maxZoom={19}
      />

      <FitBoundsOnLoad vessels={vessels} />

      {/* ── Route polylines (vessel → next port) ── */}
      {vesselList.map(vessel => {
        const port = PORTS.find(p => p.code === vessel.next_port)
        if (!port) return null
        const color = RISK_COLOR[vessel.risk_level] ?? RISK_COLOR.nominal
        const isAt  = vessel.risk_level !== 'nominal'
        return (
          <Polyline
            key={`route-${vessel.shipment_id}`}
            positions={[
              [vessel.position.lat, vessel.position.lng],
              [port.lat, port.lng],
            ]}
            pathOptions={{
              color,
              weight:    isAt ? 1.5 : 1,
              opacity:   isAt ? 0.28 : 0.13,
              dashArray: '5 10',
              className: isAt ? `route-line-${vessel.risk_level}` : '',
            }}
          />
        )
      })}

      {/* ── Port markers ── */}
      {PORTS.map(port => {
        const isHot = highlightedPort === port.code
        return (
          <CircleMarker
            key={port.code}
            center={[port.lat, port.lng]}
            radius={isHot ? 14 : 7}
            pathOptions={{
              color:       isHot ? '#ef4444' : '#6b7280',
              fillColor:   isHot ? '#ef444430' : '#1f2937',
              fillOpacity: 1,
              weight:      isHot ? 2.5 : 1.5,
            }}
          >
            <Tooltip permanent direction="top" offset={[0, -10]}>
              <span style={{ fontWeight: 600, fontSize: 11 }}>{port.name}</span>
            </Tooltip>
          </CircleMarker>
        )
      })}

      {/* ── Port hot ring (animated outer ring when scenario fires) ── */}
      {PORTS.filter(p => p.code === highlightedPort).map(port => (
        <CircleMarker
          key={`${port.code}-ring`}
          center={[port.lat, port.lng]}
          radius={24}
          pathOptions={{
            color:       '#ef4444',
            fillColor:   'transparent',
            fillOpacity: 0,
            weight:      1.5,
            className:   'port-hot-ring',
          }}
        />
      ))}

      {/* ── Vessel markers ── */}
      {vesselList.map(vessel => {
        const color  = RISK_COLOR[vessel.risk_level] ?? RISK_COLOR.nominal
        const radius = vessel.risk_level === 'critical' ? 10 : vessel.risk_level === 'warning' ? 8 : 6
        const icon   = CARGO_ICON[vessel.cargo_type] ?? '🚢'

        return (
          <CircleMarker
            key={vessel.shipment_id}
            center={[vessel.position.lat, vessel.position.lng]}
            radius={radius}
            pathOptions={{
              color,
              fillColor:   color,
              fillOpacity: vessel.risk_level === 'nominal' ? 0.75 : 0.9,
              weight:      vessel.risk_level !== 'nominal' ? 2.5 : 1.5,
              className:   vessel.risk_level === 'critical' ? 'vessel-critical'
                         : vessel.risk_level === 'warning'  ? 'vessel-warning' : '',
            }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              <div style={{ minWidth: 140 }}>
                <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 2 }}>
                  {icon} {vessel.vessel_name}
                </div>
                <div style={{ fontSize: 11, color: '#a8dadc' }}>
                  {vessel.cargo_type.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: 11, color: '#d4eef0' }}>
                  → {vessel.next_port}
                  {vessel.risk_level !== 'nominal' && (
                    <span style={{ color, fontWeight: 600, marginLeft: 6 }}>
                      ● {vessel.risk_level}
                    </span>
                  )}
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
