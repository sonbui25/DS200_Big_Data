from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.app.services.rag.agent import chat

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question không được để trống")
    try:
        answer = chat(question=req.question, session_id=req.session_id)
        return ChatResponse(answer=answer, session_id=req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
