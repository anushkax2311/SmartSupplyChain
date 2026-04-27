import { useState, useMemo, useCallback, useEffect } from 'react'
import { useShipmentSocket } from '../hooks/useShipmentSocket'
import ShipmentTable from '../components/ShipmentTable'
import MapView from '../components/MapView'
import StatsBar from '../components/StatsBar'
import PredictionPanel from '../components/PredictionPanel'
import RouteComparison from '../components/RouteComparison'
import DecisionPanel from '../components/DecisionPanel'
import ExplanationPanel from '../components/ExplanationPanel'
import SimulationPanel from '../components/SimulationPanel'
import CascadeImpact from '../components/CascadeImpact'
import ChatAssistant from '../components/ChatAssistant'
import AlertsPanel from '../components/AlertsPanel'
import AnalyticsDashboard from '../components/AnalyticsDashboard'
import ToastNotifications, { useToasts } from '../components/ToastNotifications'
import { routingService } from '../services/api'
import {
  WifiOff, Truck, Brain, Radio, Route, AlertTriangle,
  Zap, FlaskConical, MessageSquare, Activity, Bell, BarChart3
} from 'lucide-react'

function formatTime(date) {
  if (!date) return ''
  return date.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:true })
}

const LEFT_PANELS = [
  { id: 'table',     label: 'Shipments', icon: Truck          },
  { id: 'ai',        label: 'Predict',   icon: Brain          },
  { id: 'routes',    label: 'Routes',    icon: Route          },
  { id: 'decision',  label: 'Decision',  icon: AlertTriangle  },
  { id: 'explain',   label: 'Explain',   icon: Zap            },
  { id: 'simulate',  label: 'Simulate',  icon: FlaskConical   },
  { id: 'impact',    label: 'Impact',    icon: Activity       },
  { id: 'chat',      label: 'AI Chat',   icon: MessageSquare  },
  { id: 'alerts',    label: 'Alerts',    icon: Bell           },
  { id: 'analytics', label: 'Analytics', icon: BarChart3      },
]

const PANEL_COLORS = {
  table:'text-[#00d4a0]', ai:'text-violet-400', routes:'text-blue-400',
  decision:'text-amber-400', explain:'text-violet-400', simulate:'text-[#00d4a0]',
  impact:'text-red-400', chat:'text-violet-400', alerts:'text-amber-400',
  analytics:'text-blue-400',
}

export default function Dashboard() {
  const { shipments, connected, lastUpdated, reconnectCount, liveAlerts } = useShipmentSocket()
  const { toasts, addToasts, dismiss } = useToasts()

  const [selectedId, setSelectedId]   = useState(null)
  const [activePanel, setActivePanel] = useState('table')
  const [optimizeFor, setOptimizeFor] = useState('balanced')

  // Phase 3
  const [routeData, setRouteData]             = useState(null)
  const [routeLoading, setRouteLoading]       = useState(false)
  const [decision, setDecision]               = useState(null)
  const [decisionLoading, setDecisionLoading] = useState(false)
  const [explanation, setExplanation]         = useState(null)
  const [explainLoading, setExplainLoading]   = useState(false)

  // Phase 4
  const [simResult, setSimResult] = useState(null)

  // Phase 5: pipe live alerts → toasts
  useEffect(() => {
    if (liveAlerts?.length > 0) addToasts(liveAlerts)
  }, [liveAlerts, addToasts])

  // Unread alerts badge count
  const unreadCount = useMemo(() =>
    liveAlerts?.filter(a => !a.acknowledged)?.length || 0
  , [liveAlerts])

  const selected = shipments.find(s => s.id === selectedId) || null

  const stats = useMemo(() => ({
    total:      shipments.length,
    in_transit: shipments.filter(s => s.status === 'In Transit').length,
    delayed:    shipments.filter(s => s.status === 'Delayed').length,
    delivered:  shipments.filter(s => s.status === 'Delivered').length,
    high_risk:  shipments.filter(s => s.prediction?.risk_level === 'HIGH').length,
  }), [shipments])

  const handleSelect = useCallback((id) => {
    setSelectedId(id)
    setRouteData(null)
    setDecision(null)
    setExplanation(null)
  }, [])

  const handleComputeRoutes = useCallback(async () => {
    if (!selectedId) return
    setRouteLoading(true)
    try { setRouteData(await routingService.getRoute(selectedId, optimizeFor)) }
    catch (e) { console.error(e) }
    finally { setRouteLoading(false) }
  }, [selectedId, optimizeFor])

  const handleDecision = useCallback(async () => {
    if (!selectedId) return
    setDecisionLoading(true)
    try {
      const data = await routingService.triggerReroute(selectedId, optimizeFor)
      setDecision(data.decision)
      if (data.active_route && data.alternative_route)
        setRouteData(prev => ({ ...prev, route_a: data.active_route, route_b: data.alternative_route }))
    } catch (e) { console.error(e) }
    finally { setDecisionLoading(false) }
  }, [selectedId, optimizeFor])

  const handleExplain = useCallback(async () => {
    if (!selectedId) return
    setExplainLoading(true)
    try { setExplanation(await routingService.explainRoute(selectedId, optimizeFor)) }
    catch (e) { console.error(e) }
    finally { setExplainLoading(false) }
  }, [selectedId, optimizeFor])

  const handleSimResult = (result) => {
    setSimResult(result)
    setActivePanel('impact')
  }

  return (
    <div className="min-h-screen bg-[#0b0f1a] flex flex-col">
      {/* Toast notifications */}
      <ToastNotifications toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <header className="border-b border-white/[0.06] px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-[#00d4a0]/10 rounded-lg">
            <Truck size={18} className="text-[#00d4a0]" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100 tracking-wide">Smart Supply Chain</h1>
            <p className="text-xs text-slate-600">Phase 5 · Self-Healing Control Tower</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Self-heal indicator */}
          <div className="hidden sm:flex items-center gap-1.5 bg-[#00d4a0]/5 border border-[#00d4a0]/15 rounded-lg px-2 py-1">
            <Zap size={11} className="text-[#00d4a0]" />
            <span className="text-xs text-[#00d4a0]">Self-Healing Active</span>
          </div>

          <select
            value={optimizeFor}
            onChange={e => setOptimizeFor(e.target.value)}
            className="bg-[#1a2235] border border-white/[0.08] text-xs text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
          >
            <option value="balanced">⚖ Balanced</option>
            <option value="time">⚡ Speed</option>
            <option value="cost">💰 Cost</option>
          </select>

          {/* Alerts bell */}
          <button
            onClick={() => setActivePanel('alerts')}
            className="relative p-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] transition-colors"
          >
            <Bell size={14} className="text-slate-400" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center font-bold pulse-dot">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          <div className="flex items-center gap-1.5">
            {connected
              ? <><Radio size={12} className="text-[#00d4a0] pulse-dot" /><span className="text-xs text-[#00d4a0]">Live</span></>
              : <><WifiOff size={12} className="text-red-400" /><span className="text-xs text-red-400">Reconnecting ({reconnectCount})</span></>
            }
          </div>
          {lastUpdated && (
            <span className="text-xs text-slate-600 font-mono hidden lg:block">{formatTime(lastUpdated)}</span>
          )}
        </div>
      </header>

      <main className="flex-1 p-4 flex flex-col gap-4 overflow-hidden">
        <StatsBar stats={stats} />

        {!connected && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-2">
            <WifiOff size={14} />
            WebSocket disconnected — ensure backend is running on port 8000.
          </div>
        )}

        {shipments.length === 0 && connected && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Radio size={24} className="text-[#00d4a0] mx-auto mb-3 pulse-dot" />
              <p className="text-slate-500 text-sm">Waiting for first tick…</p>
            </div>
          </div>
        )}

        {shipments.length > 0 && (
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">

            {/* Left panel */}
            <div className="flex flex-col min-h-0 bg-[#111827] rounded-xl border border-white/[0.06] p-4">
              {/* Scrollable tab bar */}
              <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
                {LEFT_PANELS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setActivePanel(id)}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all shrink-0 ${
                      activePanel === id ? `bg-[#1a2235] ${PANEL_COLORS[id]}` : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <Icon size={11} />
                    {label}
                    {id === 'alerts' && unreadCount > 0 && (
                      <span className="bg-red-500 text-white text-xs w-4 h-4 rounded-full flex items-center justify-center font-bold">
                        {unreadCount > 9 ? '9' : unreadCount}
                      </span>
                    )}
                    {id === 'impact' && simResult && <span className="bg-red-500/20 text-red-400 text-xs px-1 rounded-full">!</span>}
                  </button>
                ))}
              </div>

              <div className="flex-1 overflow-y-auto min-h-0">
                {activePanel === 'table'     && <ShipmentTable shipments={shipments} selectedId={selectedId} onSelect={id => { handleSelect(id); setActivePanel('ai') }} />}
                {activePanel === 'ai'        && <PredictionPanel shipment={selected} />}
                {activePanel === 'routes'    && (
                  <div className="flex flex-col gap-3">
                    <button onClick={handleComputeRoutes} disabled={!selectedId || routeLoading || selected?.status === 'Delivered'}
                      className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                        selectedId && selected?.status !== 'Delivered'
                          ? 'bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20'
                          : 'bg-white/[0.03] border border-white/[0.06] text-slate-600 cursor-not-allowed'
                      }`}>
                      <Route size={14} className={routeLoading ? 'animate-spin' : ''} />
                      {routeLoading ? 'Computing…' : selectedId ? `Compute Routes for ${selectedId}` : 'Select a shipment first'}
                    </button>
                    <RouteComparison routeData={routeData} loading={routeLoading} />
                  </div>
                )}
                {activePanel === 'decision'  && <DecisionPanel decision={decision} loading={decisionLoading} shipmentId={selectedId} onTrigger={handleDecision} />}
                {activePanel === 'explain'   && <ExplanationPanel data={explanation} loading={explainLoading} shipmentId={selectedId} onGenerate={handleExplain} />}
                {activePanel === 'simulate'  && <SimulationPanel onResult={handleSimResult} onLoading={() => {}} />}
                {activePanel === 'impact'    && <CascadeImpact result={simResult} />}
                {activePanel === 'chat'      && <ChatAssistant />}
                {activePanel === 'alerts'    && <AlertsPanel liveAlerts={liveAlerts} />}
                {activePanel === 'analytics' && <AnalyticsDashboard />}
              </div>
            </div>

            {/* Right: Map */}
            <div className="flex flex-col min-h-0 bg-[#111827] rounded-xl border border-white/[0.06] p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Map</h2>
                <div className="flex items-center gap-2 flex-wrap text-xs text-slate-600">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-400" />Transit</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" />Med</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400" />High</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400" />Done</span>
                </div>
              </div>
              <div className="flex-1 min-h-[400px]">
                <MapView shipments={shipments} selectedId={selectedId}
                  onSelect={id => { handleSelect(id); setActivePanel('ai') }}
                  routeData={routeData} />
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  )
}
