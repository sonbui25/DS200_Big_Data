import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex items-end gap-3 justify-end message-enter">
        <div className="bg-gradient-to-br from-sky-400 to-cyan-500 text-white rounded-2xl rounded-br-sm px-4 py-3 max-w-[75%] shadow-sm">
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sky-400 to-cyan-500 flex items-center justify-center flex-shrink-0 text-xs text-white font-semibold shadow-sm">
          B
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 message-enter">
      <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center flex-shrink-0 text-base ring-1 ring-sky-200">
        📱
      </div>
      <div className="bg-white border border-sky-100 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[80%] shadow-sm">
        <div className="prose-chat">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
