from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.routes.chat import router as chat_router

app = FastAPI(title="Phone Advisory RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
