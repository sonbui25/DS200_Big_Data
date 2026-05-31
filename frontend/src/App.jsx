import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import TypingIndicator from './components/TypingIndicator'

const SESSION_KEY = 'phone_advisor_session_id'

function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

const WELCOME = {
  role: 'assistant',
  content: `Xin chào! Tôi là trợ lý tư vấn điện thoại, được hỗ trợ bởi AI và kho nhận xét thực tế từ người dùng YouTube Việt Nam.

Tôi có thể giúp bạn:
- **Đánh giá** một mẫu điện thoại cụ thể
- **So sánh** camera, pin, hiệu năng giữa các máy
- **Tư vấn** điện thoại phù hợp theo ngân sách và nhu cầu

Bạn muốn hỏi gì?`,
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const sessionId = useRef(getSessionId())

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage() {
    const question = input.trim()
    if (!question || loading) return

    setMessages(prev => [...prev, { role: 'user', content: question }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId.current }),
      })
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Xin lỗi, có lỗi kết nối. Vui lòng thử lại.',
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header className="bg-white border-b border-sky-100 px-6 py-4 flex items-center gap-3 shadow-sm">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-cyan-500 flex items-center justify-center text-lg shadow-sm">
          📱
        </div>
        <div>
          <h1 className="font-semibold text-slate-800 text-base leading-tight">Tư vấn điện thoại</h1>
          <p className="text-xs text-slate-400">Dựa trên nhận xét thực tế từ người dùng YouTube</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse" />
          <span className="text-xs text-slate-400">Đang hoạt động</span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-sky-100 px-6 py-4">
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nhập câu hỏi... (Enter để gửi, Shift+Enter xuống dòng)"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-sky-200 bg-sky-50/50 px-4 py-3 text-sm
                       focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent focus:bg-white
                       placeholder:text-slate-400 leading-relaxed max-h-32 overflow-y-auto transition-colors"
            style={{ minHeight: '46px' }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="w-11 h-11 rounded-xl bg-gradient-to-br from-sky-400 to-cyan-500
                       hover:from-sky-500 hover:to-cyan-600
                       disabled:from-slate-200 disabled:to-slate-200
                       flex items-center justify-center transition-all flex-shrink-0 shadow-sm"
          >
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2 text-center">
          Câu trả lời dựa trên dữ liệu YouTube thực tế — có thể không bao gồm tất cả sản phẩm.
        </p>
      </div>
    </div>
  )
}
