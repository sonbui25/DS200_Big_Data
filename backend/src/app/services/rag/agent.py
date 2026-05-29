"""
RAG Agent dùng LangChain + Gemini.

Chạy thử:
    python -m src.app.services.rag.agent
    python -m src.app.services.rag.agent "Samsung S24 chụp đêm có tốt không?"
"""

import logging
import sys
from functools import lru_cache

from langchain_core.messages import HumanMessage, trim_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.app.config.settings import settings
from src.app.services.rag._tools import (
    get_all_specs,
    get_comments,
    get_product_specs,
    list_products,
    search_product,
)

logger = logging.getLogger(__name__)

TOOLS = [search_product, get_all_specs, get_product_specs, get_comments, list_products]

# Ngân sách token tối đa đưa vào LLM mỗi lượt. Chỉ cắt cái GỬI cho LLM,
# state lưu trong checkpointer vẫn giữ đầy đủ lịch sử.
MAX_INPUT_TOKENS = 6000

SYSTEM_PROMPT = """Bạn là trợ lý tư vấn điện thoại cho người dùng Việt Nam. Thế mạnh riêng của bạn là
kho comment YouTube thực tế đã phân loại theo khía cạnh — hãy ưu tiên dựa vào trải
nghiệm thực tế này, kết hợp với thông số kỹ thuật chính thức.

- Khi so sánh nhiều máy, luôn đối chiếu trên CÙNG khía cạnh để công bằng.
- Trích dẫn cụ thể từ comment để tăng thuyết phục.
- Nếu chưa rõ user muốn máy nào hoặc tiêu chí gì, hỏi lại để xác nhận.
- Trả lời bằng tiếng Việt, ngắn gọn, có cấu trúc rõ ràng.

Tự chọn và phối hợp các tool dựa trên mô tả của từng tool.
"""


@lru_cache(maxsize=1)
def build_agent():
    """Tạo agent 1 lần rồi tái dùng (lru_cache) — để MemorySaver giữ được lịch sử giữa các lượt."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.llm_api_key,
        temperature=0.1,
    )

    # Chạy trước mỗi lần gọi LLM: cắt bớt lịch sử theo token.
    # Trả về llm_input_messages → chỉ ảnh hưởng input gửi LLM, KHÔNG xóa state đã lưu.
    def pre_model_hook(state):
        trimmed = trim_messages(
            state["messages"],
            max_tokens=MAX_INPUT_TOKENS,
            token_counter=llm,        # đếm token thật bằng tokenizer của model (chuẩn)
            strategy="last",          # ưu tiên giữ phần mới nhất
            start_on="human",         # cửa sổ bắt đầu từ HumanMessage → không cắt lẻ cặp tool-call
        )
        return {"llm_input_messages": trimmed}

    checkpointer = MemorySaver()      # lưu lịch sử trong RAM, phân vùng theo thread_id
    return create_react_agent(
        llm,
        TOOLS,
        prompt=SYSTEM_PROMPT,         # system inject sẵn, không nằm trong state → không bị trim
        pre_model_hook=pre_model_hook,
        checkpointer=checkpointer,
    )


def chat(question: str, thread_id: str = "default") -> str:
    agent = build_agent()
    result = agent.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    question = sys.argv[1] if len(sys.argv) > 1 else "Samsung S24 chụp đêm có tốt không?"
    print(f"\nCâu hỏi: {question}\n{'─' * 50}")
    print(chat(question))
