from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up lúc container khởi động: load model HF + khởi tạo agent
    from src.app.services.rag.retrieval import _get_embedding_model
    from src.app.services.rag.agent import build_agent
    _get_embedding_model()
    build_agent()
    yield


app = FastAPI(title="Phone Advisory RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
