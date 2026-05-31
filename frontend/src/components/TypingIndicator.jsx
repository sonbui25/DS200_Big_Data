export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 message-enter">
      <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center flex-shrink-0 text-base ring-1 ring-sky-200">
        📱
      </div>
      <div className="bg-white border border-sky-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1 h-4">
          <div className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          <div className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
          <div className="typing-dot w-2 h-2 rounded-full bg-slate-400" />
        </div>
      </div>
    </div>
  )
}
