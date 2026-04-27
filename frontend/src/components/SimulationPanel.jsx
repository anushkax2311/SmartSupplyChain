import { useState, useEffect } from 'react'
import { Play, Zap, AlertTriangle, RefreshCw } from 'lucide-react'
import { phase4Service } from '../services/api'

const SEVERITY_OPTIONS = [
  { value: 0.5, label: 'Mild',     color: 'text-emerald-400' },
  { value: 1.0, label: 'Moderate', color: 'text-amber-400'   },
  { value: 1.5, label: 'Severe',   color: 'text-red-400'     },
]

export default function SimulationPanel({ onResult, onLoading }) {
  const [events, setEvents]       = useState([])
  const [locations, setLocations] = useState([])
  const [form, setForm] = useState({
    event:    'warehouse_shutdown',
    location: 'Delhi',
    duration: 24,
    severity: 1.0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  useEffect(() => {
    phase4Service.getEvents().then(data => {
      setEvents(data.events || [])
      setLocations(data.locations || [])
    }).catch(() => {
      // fallback defaults
      setEvents([
        { value: 'warehouse_shutdown', label: '🏭 Warehouse Shutdown' },
        { value: 'traffic_spike',      label: '🚗 Traffic Spike'      },
        { value: 'weather_event',      label: '🌧️ Weather Event'      },
        { value: 'road_closure',       label: '🚧 Road Closure'        },
        { value: 'port_congestion',    label: '⚓ Port Congestion'     },
      ])
      setLocations(['Delhi','Mumbai','Bangalore','Hyderabad','Chennai','Kolkata','Nagpur','Ahmedabad','Jaipur','Lucknow'])
    })
  }, [])

  const handleRun = async () => {
    setLoading(true)
    setError(null)
    onLoading(true)
    try {
      const result = await phase4Service.simulate(form)
      onResult(result)
    } catch (e) {
      setError('Simulation failed — is the backend running?')
    } finally {
      setLoading(false)
      onLoading(false)
    }
  }

  const sel = 'w-full bg-[#0b0f1a] border border-white/[0.08] text-sm text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-[#00d4a0]/40'

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-amber-500/10 rounded-lg">
          <Zap size={14} className="text-amber-400" />
        </div>
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">What-If Simulator</h3>
      </div>

      {/* Event type */}
      <div>
        <label className="text-xs text-slate-500 mb-1.5 block">Disruption Event</label>
        <select className={sel} value={form.event} onChange={e => setForm(f => ({ ...f, event: e.target.value }))}>
          {events.map(ev => (
            <option key={ev.value} value={ev.value}>{ev.label}</option>
          ))}
        </select>
      </div>

      {/* Location */}
      <div>
        <label className="text-xs text-slate-500 mb-1.5 block">Affected Location</label>
        <select className={sel} value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))}>
          {locations.map(loc => (
            <option key={loc} value={loc}>{loc}</option>
          ))}
        </select>
      </div>

      {/* Duration */}
      <div>
        <label className="text-xs text-slate-500 mb-1.5 block flex justify-between">
          <span>Duration</span>
          <span className="text-[#00d4a0] font-mono">{form.duration}h</span>
        </label>
        <input
          type="range" min={1} max={168} step={1}
          value={form.duration}
          onChange={e => setForm(f => ({ ...f, duration: parseInt(e.target.value) }))}
          className="w-full accent-[#00d4a0] h-1.5"
        />
        <div className="flex justify-between text-xs text-slate-700 mt-1">
          <span>1h</span><span>1 week</span>
        </div>
      </div>

      {/* Severity */}
      <div>
        <label className="text-xs text-slate-500 mb-1.5 block">Severity</label>
        <div className="flex gap-2">
          {SEVERITY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setForm(f => ({ ...f, severity: opt.value }))}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                form.severity === opt.value
                  ? `bg-[#1a2235] ${opt.color} border-current`
                  : 'text-slate-600 border-white/[0.06] hover:text-slate-400'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-xs text-red-400 flex items-center gap-2">
          <AlertTriangle size={12} /> {error}
        </div>
      )}

      {/* Run button */}
      <button
        onClick={handleRun}
        disabled={loading}
        className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-semibold bg-[#00d4a0]/10 border border-[#00d4a0]/30 text-[#00d4a0] hover:bg-[#00d4a0]/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading
          ? <><RefreshCw size={14} className="animate-spin" /> Running Simulation…</>
          : <><Play size={14} /> Run Simulation</>
        }
      </button>
    </div>
  )
}
