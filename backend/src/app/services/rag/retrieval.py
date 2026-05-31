"""Embedding + HyDE retrieval (Gao et al. 2022, arXiv:2212.10496).

Sinh K hypothetical comment bằng LLM, embed cùng query gốc, mean-pool element-wise
(Equation 8 trong paper) → vector dùng để search trong comment_embeddings.
"""

import json
import logging
from functools import lru_cache

import numpy as np

from src.app.config.settings import settings
from src.app.services.rag.db import get_product_name

logger = logging.getLogger(__name__)

# Phải khớp chính xác với embedding_comment.py: cùng model, cùng max_seq_length,
# cùng bước pyvi tokenize — nếu không query vector sẽ lệch không gian với comment vector.
_EMBEDDING_MODEL_NAME = "dangvantuan/vietnamese-embedding"
_MODEL_MAX_TOKENS = 254

# HyDE config: K hypothetical comment, sampling với temperature cao để đa dạng.
_HYDE_K = 5
_HYDE_MODEL = "gpt-4o-mini"
_HYDE_TEMPERATURE = 0.9


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    model.max_seq_length = _MODEL_MAX_TOKENS
    return model


@lru_cache(maxsize=1)
def _get_openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def _generate_hyde_docs(query: str, aspect: str, product_name: str, k: int = _HYDE_K) -> list[str]:
    """Sinh K comment giả định kiểu YouTube Việt Nam về (product_name, aspect, query)."""
    client = _get_openai_client()
    user_msg = (
        f"Đóng vai người dùng YouTube Việt Nam đang bình luận về điện thoại {product_name}. "
        f"Hãy viết {k} comment KHÁC NHAU về khía cạnh '{aspect}', xoay quanh chủ đề: '{query}'. "
        f"Yêu cầu:\n"
        f"- Mỗi comment ngắn (1-2 câu), giọng tự nhiên như comment YouTube thật.\n"
        f"- Đa dạng góc nhìn: có khen, có chê, có trung tính.\n"
        f"- Có thể nhắc tên máy hoặc đặc điểm riêng (chip, màn hình...) nếu phù hợp.\n"
        f"- Tránh trùng nội dung.\n"
        f"Trả về JSON: {{\"comments\": [\"...\", \"...\", ...]}}"
    )
    try:
        resp = client.chat.completions.create(
            model=_HYDE_MODEL,
            messages=[{"role": "user", "content": user_msg}],
            temperature=_HYDE_TEMPERATURE,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        docs = [d for d in data.get("comments", []) if isinstance(d, str) and d.strip()][:k]
        logger.info("HyDE sinh %d comment giả định cho %s, aspect=%r, query=%r:", len(docs), product_name, aspect, query)
        for i, d in enumerate(docs, 1):
            logger.info("  %d. %s", i, d)
        return docs
    except Exception as e:
        logger.warning("HyDE generation lỗi (%s) — fallback dùng query embedding gốc.", e)
        return []


def hyde_embed(query: str, aspect: str, product_id: int) -> list[float]:
    """HyDE retrieval: mean-pool embedding của K hypothetical docs + query gốc (Equation 8)."""
    from pyvi.ViTokenizer import tokenize as vi_tokenize

    model = _get_embedding_model()
    q_processed = vi_tokenize(query).strip() or query
    product_name = get_product_name(product_id)

    hypo_docs = _generate_hyde_docs(query, aspect, product_name)
    if not hypo_docs:
        # Fallback: nếu sinh HyDE lỗi, chỉ dùng embedding của query gốc (giống behavior cũ).
        return model.encode(q_processed, normalize_embeddings=True).tolist()

    # Batch encode K hypothetical + query trong 1 call → ma trận (K+1, 768).
    hypo_processed = [vi_tokenize(d).strip() or d for d in hypo_docs]
    all_vecs = model.encode(hypo_processed + [q_processed], normalize_embeddings=True)

    # Equation 8: trung bình element-wise → 1 vector 768d.
    mean_vec = all_vecs.mean(axis=0)
    # Re-normalize vì trung bình các vector unit-norm không còn unit-norm nữa.
    mean_vec = mean_vec / (np.linalg.norm(mean_vec) + 1e-12)
    return mean_vec.tolist()
