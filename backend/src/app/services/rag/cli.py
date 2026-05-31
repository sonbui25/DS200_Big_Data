"""CLI test runner: chat tương tác hoặc 1-câu, in luồng ReAct ra terminal.

Chạy:
    python -m src.app.services.rag.cli                       # interactive
    python -m src.app.services.rag.cli "câu hỏi của user"    # 1-câu
"""

import logging
import sys

from langchain_core.messages import HumanMessage

from src.app.services.rag.agent import build_agent


def _format_message(m) -> str:
    """Format 1 message để in luồng ReAct cho dễ đọc."""
    kind = m.__class__.__name__
    if kind == "HumanMessage":
        return f"\n👤 USER: {m.content}"
    if kind == "AIMessage":
        lines = []
        for tc in (m.tool_calls or []):
            lines.append(f"🔧 GỌI TOOL: {tc['name']}({tc['args']})")
        if m.content:
            lines.append(f"💬 LLM: {m.content}")
        return ("\n" + "\n".join(lines)) if lines else ""
    if kind == "ToolMessage":
        content = str(m.content)
        preview = content[:3000] + ("…" if len(content) > 3000 else "")
        return f"\n📥 KẾT QUẢ [{m.name}]:\n{preview}"
    return ""


def _print_turn(messages):
    """In các message của lượt hiện tại (từ HumanMessage cuối cùng trở đi)."""
    human_idxs = [i for i, m in enumerate(messages) if m.__class__.__name__ == "HumanMessage"]
    start = human_idxs[-1] if human_idxs else 0
    for m in messages[start:]:
        text = _format_message(m)
        if text:
            print(text)


def main():
    logging.basicConfig(level=logging.WARNING)
    for _noisy in ("httpx", "httpcore", "openai", "sentence_transformers"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)
    # Hiển thị log INFO của module RAG (vd: comment giả định HyDE)
    logging.getLogger("src.app.services.rag").setLevel(logging.INFO)

    agent = build_agent()
    config = {"configurable": {"thread_id": "cli"}}

    def run(q: str):
        result = agent.invoke({"messages": [HumanMessage(content=q)]}, config=config)
        _print_turn(result["messages"])

    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("Chat tư vấn điện thoại — gõ 'quit' để thoát. Hội thoại CÓ nhớ ngữ cảnh.")
        while True:
            try:
                q = input("\n👤 Bạn: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in ("quit", "exit", "q", ""):
                break
            run(q)


if __name__ == "__main__":
    main()


# /Users/macbook/Documents/DS200/DS200_Big_Data/Ung_venv311/bin/python -m src.app.services.rag.cli
