import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader, Sparkles } from 'lucide-react'
import { phase4Service } from '../services/api'

const SUGGESTED = [
  "What happens if Delhi warehouse shuts down?",
  "Why are shipments delayed today?",
  "What's the cost impact of current disruptions?",
  "What if heavy rain hits Mumbai for 24 hours?",
  "Which shipments are at highest risk?",
]

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-[#00d4a0]/20' : 'bg-violet-500/20'
      }`}>
        {isUser
          ? <User size={13} className="text-[#00d4a0]" />
          : <Bot  size={13} className="text-violet-400" />
        }
      </div>
      <div className={`max-w-[85%] rounded-2xl px-3 py-2.5 text-xs leading-relaxed ${
        isUser
          ? 'bg-[#00d4a0]/10 border border-[#00d4a0]/20 text-slate-200 rounded-tr-sm'
          : 'bg-[#1a2235] border border-white/[0.06] text-slate-300 rounded-tl-sm'
      }`}>
        {msg.content}
        {msg.thinking && (
          <span className="flex items-center gap-1 text-slate-600 mt-1">
            <Loader size={10} className="animate-spin" /> Thinking…
          </span>
        )}
      </div>
    </div>
  )
}

export default function ChatAssistant() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm your AI supply chain assistant. Ask me anything — disruption impacts, delay causes, what-if scenarios, or cost analysis.",
    }
  ])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const question = text || input.trim()
    if (!question || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    // Add thinking placeholder
    setMessages(prev => [...prev, { role: 'assistant', content: '', thinking: true, id: 'thinking' }])

    try {
      const data = await phase4Service.ask(question)
      setMessages(prev => [
        ...prev.filter(m => m.id !== 'thinking'),
        { role: 'assistant', content: data.answer }
      ])
    } catch (e) {
      setMessages(prev => [
        ...prev.filter(m => m.id !== 'thinking'),
        { role: 'assistant', content: 'Sorry, I could not connect to the backend. Please ensure the server is running on port 8000.' }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3 pb-3 border-b border-white/[0.06]">
        <div className="p-1.5 bg-violet-500/10 rounded-lg">
          <Sparkles size={13} className="text-violet-400" />
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-300">AI Assistant</p>
          <p className="text-xs text-slate-600">Powered by Gemma · Ask anything</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-3 mb-3 min-h-0">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Suggested questions */}
      {messages.length <= 1 && (
        <div className="mb-3">
          <p className="text-xs text-slate-600 mb-2">Try asking:</p>
          <div className="flex flex-col gap-1.5">
            {SUGGESTED.slice(0, 3).map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="text-left text-xs text-slate-400 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 hover:bg-white/[0.06] hover:text-slate-300 transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about supply chain disruptions…"
          disabled={loading}
          className="flex-1 bg-[#0b0f1a] border border-white/[0.08] text-xs text-slate-300 placeholder-slate-700 rounded-xl px-3 py-2.5 focus:outline-none focus:border-violet-500/40 disabled:opacity-50"
        />
        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          className="p-2.5 bg-violet-500/10 border border-violet-500/30 text-violet-400 rounded-xl hover:bg-violet-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
