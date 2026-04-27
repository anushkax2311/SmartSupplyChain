import { useState, useEffect } from 'react'
import { Bell, BellOff, CheckCheck, AlertTriangle, Info, Zap, Truck, Clock, RefreshCw } from 'lucide-react'
import axios from 'axios'

const API = 'http://localhost:8000'

const LEVEL_STYLE = {
  CRITICAL: { bg: 'bg-red-500/10',    border: 'border-red-500/20',    text: 'text-red-400',    dot: 'bg-red-500'    },
  WARNING:  { bg: 'bg-amber-500/10',  border: 'border-amber-500/20',  text: 'text-amber-400',  dot: 'bg-amber-500'  },
  INFO:     { bg: 'bg-blue-500/10',   border: 'border-blue-500/20',   text: 'text-blue-400',   dot: 'bg-blue-400'   },
}

const TYPE_ICON = {
  reroute_applied:   { icon: Zap,           color: 'text-[#00d4a0]' },
  delay_detected:    { icon: AlertTriangle,  color: 'text-amber-400' },
  eta_updated:       { icon: Clock,          color: 'text-blue-400'  },
  sla_breach:        { icon: AlertTriangle,  color: 'text-red-400'   },
  self_heal:         { icon: Zap,            color: 'text-[#00d4a0]' },
  delivery_complete: { icon: Truck,          color: 'text-emerald-400'},
  speed_drop:        { icon: AlertTriangle,  color: 'text-amber-400' },
}

function AlertCard({ alert, onAck }) {
  const style    = LEVEL_STYLE[alert.level] || LEVEL_STYLE.INFO
  const typeInfo = TYPE_ICON[alert.type] || { icon: Info, color: 'text-slate-400' }
  const Icon     = typeInfo.icon

  const fmtTime = (iso) => {
    try { return new Date(iso).toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', hour12:true }) }
    catch { return iso }
  }

  return (
    <div className={`rounded-xl border px-3 py-2.5 transition-all ${style.bg} ${style.border} ${alert.acknowledged ? 'opacity-40' : ''}`}>
      <div className="flex items-start gap-2.5">
        <div className={`mt-0.5 shrink-0 ${typeInfo.color}`}>
          <Icon size={13} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className={`text-xs font-semibold truncate ${style.text}`}>{alert.title}</p>
            <span className="text-xs text-slate-600 whitespace-nowrap shrink-0">{fmtTime(alert.timestamp)}</span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{alert.message}</p>
          <div className="flex items-center gap-2 mt-1.5">
            {alert.shipment_id && (
              <span className="text-xs font-mono text-[#00d4a0] bg-[#00d4a0]/10 px-1.5 py-0.5 rounded">
                {alert.shipment_id}
              </span>
            )}
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${style.text} ${style.bg}`}>
              {alert.level}
            </span>
            {!alert.acknowledged && (
              <button
                onClick={() => onAck(alert.id)}
                className="ml-auto text-xs text-slate-600 hover:text-slate-400 transition-colors"
              >
                ✓ Dismiss
              </button>
            )}
          </div>
        </div>
        {!alert.acknowledged && (
          <span className={`w-2 h-2 rounded-full shrink-0 mt-1 ${style.dot} pulse-dot`} />
        )}
      </div>
    </div>
  )
}

export default function AlertsPanel({ liveAlerts = [] }) {
  const [alerts, setAlerts]       = useState([])
  const [filter, setFilter]       = useState('ALL')
  const [loading, setLoading]     = useState(false)
  const [unacked, setUnacked]     = useState(0)

  const fetchAlerts = async () => {
    setLoading(true)
    try {
      const r = await axios.get(`${API}/alerts?limit=50`)
      setAlerts(r.data.alerts || [])
      setUnacked(r.data.unacked || 0)
    } catch (e) { /* backend may not be ready */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchAlerts() }, [])

  // Merge live alerts from WS into local state
  useEffect(() => {
    if (liveAlerts.length === 0) return
    setAlerts(prev => {
      const existingIds = new Set(prev.map(a => a.id))
      const newOnes = liveAlerts.filter(a => !existingIds.has(a.id))
      return [...newOnes, ...prev].slice(0, 100)
    })
    setUnacked(n => n + liveAlerts.length)
  }, [liveAlerts])

  const handleAck = async (id) => {
    try { await axios.post(`${API}/alerts/${id}/acknowledge`) } catch {}
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a))
    setUnacked(n => Math.max(0, n - 1))
  }

  const handleAckAll = async () => {
    try { await axios.post(`${API}/alerts/acknowledge-all`) } catch {}
    setAlerts(prev => prev.map(a => ({ ...a, acknowledged: true })))
    setUnacked(0)
  }

  const FILTERS = ['ALL', 'CRITICAL', 'WARNING', 'INFO']
  const filtered = filter === 'ALL' ? alerts : alerts.filter(a => a.level === filter)

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Bell size={14} className="text-amber-400" />
            {unacked > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center font-bold">
                {unacked > 9 ? '9+' : unacked}
              </span>
            )}
          </div>
          <span className="text-xs font-semibold text-slate-300">Alert Center</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchAlerts} className="p-1 text-slate-600 hover:text-slate-400">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          </button>
          {unacked > 0 && (
            <button
              onClick={handleAckAll}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <CheckCheck size={11} /> Dismiss all
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-1">
        {FILTERS.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`flex-1 text-xs py-1 rounded-lg font-medium transition-all ${
              filter === f ? 'bg-[#1a2235] text-[#00d4a0]' : 'text-slate-600 hover:text-slate-400'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-2 min-h-0">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-600">
            <BellOff size={24} className="mb-2 opacity-30" />
            <p className="text-sm">No alerts</p>
          </div>
        ) : (
          filtered.map(a => (
            <AlertCard key={a.id} alert={a} onAck={handleAck} />
          ))
        )}
      </div>

      <p className="text-xs text-slate-700 text-right">{filtered.length} alerts · {unacked} unread</p>
    </div>
  )
}
