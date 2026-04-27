import { useState, useEffect, useCallback } from 'react'
import { X, Zap, AlertTriangle, Clock, Truck, Info } from 'lucide-react'

const TYPE_CONFIG = {
  reroute_applied:   { icon: Zap,           bg: 'bg-[#00d4a0]/10', border: 'border-[#00d4a0]/30', text: 'text-[#00d4a0]'  },
  delay_detected:    { icon: AlertTriangle,  bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400'  },
  eta_updated:       { icon: Clock,          bg: 'bg-blue-500/10',  border: 'border-blue-500/30',  text: 'text-blue-400'   },
  sla_breach:        { icon: AlertTriangle,  bg: 'bg-red-500/10',   border: 'border-red-500/30',   text: 'text-red-400'    },
  delivery_complete: { icon: Truck,          bg: 'bg-emerald-500/10',border:'border-emerald-500/30',text:'text-emerald-400' },
  speed_drop:        { icon: AlertTriangle,  bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400'  },
  self_heal:         { icon: Zap,            bg: 'bg-[#00d4a0]/10', border: 'border-[#00d4a0]/30', text: 'text-[#00d4a0]'  },
}

function Toast({ toast, onDismiss }) {
  const cfg  = TYPE_CONFIG[toast.type] || { icon: Info, bg: 'bg-slate-800', border: 'border-slate-700', text: 'text-slate-300' }
  const Icon = cfg.icon

  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 5000)
    return () => clearTimeout(t)
  }, [toast.id, onDismiss])

  return (
    <div className={`flex items-start gap-3 px-3 py-2.5 rounded-xl border shadow-2xl backdrop-blur-sm
      ${cfg.bg} ${cfg.border} animate-in slide-in-from-right-4 duration-300 max-w-xs`}>
      <Icon size={13} className={`shrink-0 mt-0.5 ${cfg.text}`} />
      <div className="flex-1 min-w-0">
        <p className={`text-xs font-semibold ${cfg.text}`}>{toast.title}</p>
        <p className="text-xs text-slate-400 mt-0.5 leading-relaxed line-clamp-2">{toast.message}</p>
      </div>
      <button onClick={() => onDismiss(toast.id)} className="text-slate-600 hover:text-slate-400 shrink-0">
        <X size={11} />
      </button>
    </div>
  )
}

export function useToasts() {
  const [toasts, setToasts] = useState([])

  const addToasts = useCallback((alerts) => {
    if (!alerts?.length) return
    // Only show CRITICAL and WARNING toasts, max 3 at once
    const newToasts = alerts
      .filter(a => a.level !== 'INFO' || a.type === 'delivery_complete')
      .slice(0, 2)
      .map(a => ({ ...a, toastId: `${a.id}-${Date.now()}` }))
    setToasts(prev => [...newToasts, ...prev].slice(0, 4))
  }, [])

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.toastId !== id))
  }, [])

  return { toasts, addToasts, dismiss }
}

export default function ToastContainer({ toasts, onDismiss }) {
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
      {toasts.map(t => (
        <Toast key={t.toastId} toast={{ ...t, id: t.toastId }} onDismiss={onDismiss} />
      ))}
    </div>
  )
}
