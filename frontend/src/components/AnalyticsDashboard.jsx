import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, DollarSign, Clock, Truck, Zap, RefreshCw, Award } from 'lucide-react'
import axios from 'axios'

const API = 'http://localhost:8000'

function KpiCard({ icon: Icon, label, value, sub, color = 'text-[#00d4a0]', trend }) {
  return (
    <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-600">{label}</span>
        <Icon size={13} className={color} />
      </div>
      <p className={`text-2xl font-mono font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-1 text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
          {Math.abs(trend)}% vs last hour
        </div>
      )}
    </div>
  )
}

function DelayChart({ trend }) {
  if (!trend?.length) return null
  const max = Math.max(...trend.map(t => t.delayed + t.on_time), 1)

  return (
    <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl p-3">
      <p className="text-xs text-slate-500 mb-3 flex items-center gap-1.5">
        <TrendingDown size={11} /> 12-Hour Delay Trend
      </p>
      <div className="flex items-end gap-1 h-20">
        {trend.map((t, i) => {
          const total     = t.delayed + t.on_time
          const delayPct  = total > 0 ? t.delayed / total : 0
          const onTimePct = 1 - delayPct
          return (
            <div key={i} className="flex-1 flex flex-col gap-0.5 items-center group relative">
              <div className="w-full flex flex-col justify-end" style={{ height: 64 }}>
                <div className="w-full bg-red-500/40 rounded-t-sm" style={{ height: `${delayPct * 100}%`, minHeight: delayPct > 0 ? 3 : 0 }} />
                <div className="w-full bg-emerald-500/40" style={{ height: `${onTimePct * 100}%`, minHeight: 3 }} />
              </div>
              {i % 3 === 0 && (
                <span className="text-xs text-slate-700 mt-1 whitespace-nowrap" style={{ fontSize: 9 }}>{t.hour}</span>
              )}
            </div>
          )
        })}
      </div>
      <div className="flex gap-3 mt-2">
        <span className="flex items-center gap-1 text-xs text-slate-600"><span className="w-2 h-2 rounded-sm bg-red-500/60" />Delayed</span>
        <span className="flex items-center gap-1 text-xs text-slate-600"><span className="w-2 h-2 rounded-sm bg-emerald-500/60" />On Time</span>
        <span className="flex items-center gap-1 text-xs text-[#00d4a0] ml-auto"><Zap size={10} />Reroutes: {trend.reduce((s, t) => s + t.rerouted, 0)}</span>
      </div>
    </div>
  )
}

function CarrierCard({ carrier }) {
  const gradeColor = { A:'text-emerald-400', B:'text-blue-400', C:'text-amber-400', D:'text-red-400' }
  return (
    <div className="flex items-center gap-3 bg-[#0b0f1a] border border-white/[0.06] rounded-xl px-3 py-2.5">
      <Award size={14} className={gradeColor[carrier.grade] || 'text-slate-400'} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-300 truncate">{carrier.carrier}</p>
        <p className="text-xs text-slate-600">{carrier.shipments} shipment{carrier.shipments !== 1 ? 's' : ''} · {carrier.avg_speed} km/h avg</p>
      </div>
      <div className="text-right">
        <p className={`text-lg font-mono font-bold ${gradeColor[carrier.grade]}`}>{carrier.grade}</p>
        <p className="text-xs text-slate-600">{carrier.score}/100</p>
      </div>
    </div>
  )
}

function CostRow({ item }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
      <span className="text-xs text-slate-400">{item.icon} {item.category}</span>
      <span className="text-xs font-mono text-emerald-400">+₹{item.amount_inr.toLocaleString()}</span>
    </div>
  )
}

export default function AnalyticsDashboard() {
  const [kpis,     setKpis]     = useState(null)
  const [carriers, setCarriers] = useState([])
  const [trend,    setTrend]    = useState([])
  const [savings,  setSavings]  = useState(null)
  const [loading,  setLoading]  = useState(true)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [k, c, t, s] = await Promise.all([
        axios.get(`${API}/analytics/kpis`),
        axios.get(`${API}/analytics/carrier-performance`),
        axios.get(`${API}/analytics/delay-trend`),
        axios.get(`${API}/analytics/cost-savings`),
      ])
      setKpis(k.data)
      setCarriers(c.data.carriers || [])
      setTrend(t.data.trend || [])
      setSavings(s.data)
    } catch (e) { /* backend may be starting */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchAll() }, [])

  if (loading && !kpis) return (
    <div className="flex items-center justify-center h-32">
      <RefreshCw size={18} className="animate-spin text-[#00d4a0]" />
    </div>
  )

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      {/* Refresh */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Analytics</p>
        <button onClick={fetchAll} className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400">
          <RefreshCw size={10} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* KPI grid */}
      {kpis && (
        <div className="grid grid-cols-2 gap-2">
          <KpiCard icon={TrendingUp}  label="On-Time Rate"    value={`${kpis.on_time_rate_pct}%`}          color="text-emerald-400" />
          <KpiCard icon={Zap}         label="Self-Heals"       value={kpis.reroutes_applied}                 color="text-[#00d4a0]" />
          <KpiCard icon={DollarSign}  label="Cost Saved"       value={`₹${(kpis.cost_saved_inr/1000).toFixed(1)}K`} color="text-emerald-400" />
          <KpiCard icon={Clock}       label="Time Saved"       value={`${kpis.time_saved_minutes}m`}         color="text-blue-400" />
          <KpiCard icon={TrendingDown}label="Delay Reduction"  value={`${kpis.delay_reduction_pct}%`}        color="text-[#00d4a0]" />
          <KpiCard icon={Truck}       label="Heal Success"     value={`${kpis.self_heal_success_rate}%`}     color="text-violet-400" />
        </div>
      )}

      {/* Delay trend chart */}
      <DelayChart trend={trend} />

      {/* Cost savings */}
      {savings && (
        <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl p-3">
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1.5">
            <DollarSign size={11} /> Cost Savings Breakdown
          </p>
          {savings.breakdown?.map((item, i) => <CostRow key={i} item={item} />)}
          <div className="flex justify-between mt-2 pt-2 border-t border-white/[0.06]">
            <span className="text-xs font-semibold text-slate-400">Total Saved</span>
            <span className="text-sm font-mono font-bold text-emerald-400">
              ₹{(savings.total_saved_inr || 0).toLocaleString()}
            </span>
          </div>
        </div>
      )}

      {/* Carrier performance */}
      {carriers.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-slate-500 flex items-center gap-1.5">
            <Award size={11} /> Carrier Performance
          </p>
          {carriers.map((c, i) => <CarrierCard key={i} carrier={c} />)}
        </div>
      )}
    </div>
  )
}
