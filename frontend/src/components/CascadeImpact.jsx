import { AlertTriangle, Package, Warehouse, Clock, DollarSign, TrendingDown, ChevronRight } from 'lucide-react'

const RISK_STYLE = {
  CRITICAL: { bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-400',    bar: 'bg-red-500' },
  HIGH:     { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', bar: 'bg-orange-500' },
  MEDIUM:   { bg: 'bg-amber-500/10',  border: 'border-amber-500/30',  text: 'text-amber-400',  bar: 'bg-amber-500' },
  LOW:      { bg: 'bg-emerald-500/10',border: 'border-emerald-500/30',text: 'text-emerald-400',bar: 'bg-emerald-500' },
}

function MetricCard({ icon: Icon, label, value, sub, color = 'text-slate-300' }) {
  return (
    <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl p-3 flex items-center gap-3">
      <Icon size={16} className={color} />
      <div>
        <p className="text-xs text-slate-600">{label}</p>
        <p className={`text-lg font-mono font-semibold ${color}`}>{value}</p>
        {sub && <p className="text-xs text-slate-600">{sub}</p>}
      </div>
    </div>
  )
}

export default function CascadeImpact({ result }) {
  if (!result) return (
    <div className="flex items-center justify-center h-32 text-slate-600 text-sm">
      Run a simulation to see cascading impact
    </div>
  )

  const impact = result.impact || {}
  const risk   = impact.sla_risk || 'LOW'
  const style  = RISK_STYLE[risk] || RISK_STYLE.LOW
  const eventLabel = result.event?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className={`rounded-xl px-4 py-3 border flex items-center justify-between ${style.bg} ${style.border}`}>
        <div>
          <p className={`text-sm font-bold ${style.text}`}>{eventLabel} · {result.location}</p>
          <p className="text-xs text-slate-500 mt-0.5">{result.duration_hours}h · Severity {result.severity}×</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-600">SLA Risk</p>
          <p className={`text-xl font-mono font-bold ${style.text}`}>{risk}</p>
        </div>
      </div>

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard icon={Package}     label="Affected Shipments" value={impact.total_affected_count ?? 0}    color={style.text} />
        <MetricCard icon={Warehouse}   label="Impacted Hubs"      value={impact.total_warehouse_count ?? 0}   color="text-violet-400" />
        <MetricCard icon={Clock}       label="Avg Delay"          value={`${impact.avg_delay_hours ?? 0}h`}   color="text-amber-400" />
        <MetricCard icon={DollarSign}  label="Cost Impact"
          value={`₹${((impact.total_cost_impact_inr || 0) / 100000).toFixed(1)}L`}
          color="text-red-400" />
      </div>

      {/* Cascade chain */}
      {impact.dependency_chain?.length > 0 && (
        <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl p-3">
          <p className="text-xs text-slate-500 mb-2 flex items-center gap-1.5">
            <TrendingDown size={11} /> Cascade Propagation
          </p>
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-xs font-semibold text-[#00d4a0] bg-[#00d4a0]/10 px-2 py-1 rounded-lg">
              {result.location}
            </span>
            {impact.dependency_chain.slice(0, 6).map((city, i) => (
              <span key={i} className="flex items-center gap-1">
                <ChevronRight size={10} className="text-slate-700" />
                <span className="text-xs text-slate-400 bg-white/[0.04] px-2 py-1 rounded-lg">{city}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Affected shipments list */}
      {impact.affected_shipments?.length > 0 && (
        <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl overflow-hidden">
          <p className="text-xs text-slate-500 px-3 py-2 border-b border-white/[0.04] flex items-center gap-1.5">
            <Package size={11} /> Affected Shipments
          </p>
          <div className="divide-y divide-white/[0.04]">
            {impact.affected_shipments.map((s, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2">
                <div>
                  <span className="text-xs font-mono text-[#00d4a0]">{s.shipment_id}</span>
                  <span className="text-xs text-slate-600 ml-2">{s.cargo}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-amber-400">+{s.delay_hours}h</span>
                  {s.sla_breach && (
                    <span className="text-xs bg-red-500/10 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded-full">
                      SLA ⚠
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ETA changes */}
      {result.eta_changes?.length > 0 && (
        <div className="bg-[#0b0f1a] border border-white/[0.06] rounded-xl p-3">
          <p className="text-xs text-slate-500 mb-2">ETA Changes</p>
          {result.eta_changes.map((e, i) => {
            const orig = new Date(e.original_eta)
            const newE = new Date(e.new_eta)
            const fmt  = d => d.toLocaleString('en-IN', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit', hour12:true })
            return (
              <div key={i} className="flex justify-between items-center py-1.5 border-b border-white/[0.04] last:border-0">
                <span className="text-xs font-mono text-[#00d4a0]">{e.shipment_id}</span>
                <div className="text-right">
                  <p className="text-xs text-slate-500 line-through">{fmt(orig)}</p>
                  <p className="text-xs text-amber-400">{fmt(newE)}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
