"""RetrievalLayer — semantic search over the knowledge corpus (RAG).

Design goals:
  * Real embeddings via the existing embedding_service (multilingual MiniLM).
  * Graceful degradation: if the model can't load (no network / offline),
    fall back to a transparent keyword overlap scorer so retrieval still works.
  * Caches embeddings to disk so repeated cold starts are fast.
"""
from __future__ import annotations

import logging
import os
import re
from typing import List, Optional

import numpy as np

from app.intelligence.knowledge_corpus import CORPUS, KnowledgeDoc
from app.intelligence.schemas import Source

logger = logging.getLogger("RetrievalLayer")

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_CACHE_FILE = os.path.join(_CACHE_DIR, "kb_embeddings.npz")

_BN_STOP = set("এবং ও সে তার এর থেকে করে যে হয় না এক এই সেই আছে তা হল".split())
_EN_STOP = set(
    "the a an and or of to in for is are was be with on at by from this that "
    "how what when where which who my your our we you i it as can should do does".split()
)


def _tokenize(text: str) -> set:
    text = text.lower()
    toks = set(re.findall(r"[a-z0-9ঀ-৿]+", text))
    return {t for t in toks if t not in _EN_STOP and t not in _BN_STOP}


class RetrievalLayer:
    def __init__(self, docs: Optional[List[KnowledgeDoc]] = None):
        self.docs = docs or CORPUS
        self._emb: Optional[np.ndarray] = None
        self._model_available = False

    # ------------------------------------------------------------------
    # Embedding (lazy)
    # ------------------------------------------------------------------
    def _ensure_embeddings(self) -> None:
        if self._emb is not None:
            return
        try:
            from app.services.embedding_service import encode_texts

            texts = [f"{d.title}. {d.text} Tags: {' '.join(d.tags or [])}" for d in self.docs]
            cache_key = None
            if os.path.exists(_CACHE_FILE):
                try:
                    data = np.load(_CACHE_FILE, allow_pickle=True)
                    if "texts" in data and list(data["texts"]) == texts:
                        self._emb = np.array(data["emb"])
                        self._model_available = True
                        return
                except Exception:
                    pass

            matrix = np.array(encode_texts(texts), dtype=np.float32)
            # L2-normalize for cosine
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self._emb = matrix / norms
            self._model_available = True

            try:
                os.makedirs(_CACHE_DIR, exist_ok=True)
                np.savez(_CACHE_FILE, emb=self._emb, texts=np.array(texts, dtype=object))
            except Exception as e:
                logger.debug("Could not cache KB embeddings: %s", e)
        except Exception as e:
            logger.warning(
                "Embedding model unavailable; using keyword fallback. (%s)", e
            )
            self._emb = None
            self._model_available = False

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def retrieve(self, query: str, k: int = 4) -> List[Source]:
        self._ensure_embeddings()
        if self._emb is not None:
            return self._semantic_retrieve(query, k)
        return self._keyword_retrieve(query, k)

    def _semantic_retrieve(self, query: str, k: int) -> List[Source]:
        from app.services.embedding_service import encode_text

        q = np.array(encode_text(query), dtype=np.float32)
        n = np.linalg.norm(q)
        if n > 0:
            q = q / n
        sims = self._emb @ q  # cosine already normalized
        idx = np.argsort(-sims)[:k]
        out: List[Source] = []
        for i in idx:
            d = self.docs[i]
            out.append(
                Source(
                    id=d.id,
                    title=d.title,
                    snippet=d.text[:240],
                    url=d.url,
                    score=round(float(sims[i]), 4),
                )
            )
        return out

    def _keyword_retrieve(self, query: str, k: int) -> List[Source]:
        q_tokens = _tokenize(query)
        scored = []
        for d in self.docs:
            doc_tokens = _tokenize(f"{d.title} {d.text} {' '.join(d.tags or [])}")
            if not q_tokens:
                overlap = 0.0
            else:
                overlap = len(q_tokens & doc_tokens) / len(q_tokens)
            scored.append((overlap, d))
        scored.sort(key=lambda x: -x[0])
        out: List[Source] = []
        for score, d in scored[:k]:
            if score <= 0:
                continue
            out.append(
                Source(
                    id=d.id,
                    title=d.title,
                    snippet=d.text[:240],
                    url=d.url,
                    score=round(float(score), 4),
                )
            )
        return out


_layer: Optional[RetrievalLayer] = None


def get_retrieval_layer() -> RetrievalLayer:
    global _layer
    if _layer is None:
        _layer = RetrievalLayer()
    return _layer
