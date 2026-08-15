from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from typing import Protocol

import httpx


@dataclass
class EvidenceCandidate:
    concept: str
    evidence_type: str
    summary: str
    original_text: str
    strength: str = "moderate"


class AIProvider(Protocol):
    def extract_evidence(self, text: str, experience_type: str) -> list[EvidenceCandidate]: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


CONCEPTS = {
    "autonomy": ["freedom", "choice", "choices", "control", "independent", "independence", "trapped", "my own"],
    "connection": ["family", "friend", "friends", "together", "people", "understood", "share", "shared"],
    "learning": ["learn", "learning", "study", "solve", "figuring", "difficult", "challenge", "curious"],
    "creation": ["build", "create", "creating", "project", "made", "design", "idea"],
    "recognition": ["praise", "recognized", "recognition", "award", "win", "winning", "status", "admire"],
    "persistence": ["didn't give up", "did not give up", "kept going", "persist", "retry", "again"],
    "security": ["stable", "stability", "secure", "security", "safe", "salary", "money"],
}
NEGATORS = ["not", "didn't", "did not", "without", "less", "doesn't", "does not"]


class LocalProvider:
    """Deterministic, secret-free provider used by tests and local demos.

    It preserves the same provider contract as the hosted AI path so CI never
    depends on external credentials.
    """

    def extract_evidence(self, text: str, experience_type: str) -> list[EvidenceCandidate]:
        lowered = text.lower()
        out: list[EvidenceCandidate] = []
        for concept, keywords in CONCEPTS.items():
            hits = [kw for kw in keywords if kw in lowered]
            if not hits:
                continue
            contradict = any(n in lowered for n in NEGATORS)
            out.append(
                EvidenceCandidate(
                    concept=concept,
                    evidence_type="contradict" if contradict else "support",
                    summary=f"{concept.title()} signal from {experience_type.replace('_', ' ')}",
                    original_text=text[:2000],
                )
            )
        return out

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Small deterministic hashing embedding. It is intentionally simple but
        # supports cosine semantic-ish retrieval without network access.
        dims = 96
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * dims
            tokens = re.findall(r"[a-z0-9']+", text.lower())
            for token in tokens:
                digest = hashlib.sha256(token.encode()).digest()
                idx = int.from_bytes(digest[:4], "big") % dims
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible Chat Completions + Embeddings APIs."""

    def __init__(self) -> None:
        self.base_url = os.getenv("WHOAMI_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.getenv("WHOAMI_AI_API_KEY", "")
        self.llm_model = os.getenv("WHOAMI_LLM_MODEL", "gpt-4.1-mini")
        self.embedding_model = os.getenv("WHOAMI_EMBEDDING_MODEL", "text-embedding-3-small")
        if not self.api_key:
            raise RuntimeError("WHOAMI_AI_API_KEY is required for openai_compatible provider")
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def extract_evidence(self, text: str, experience_type: str) -> list[EvidenceCandidate]:
        system = (
            "You extract cautious self-reflection evidence. Never diagnose personality or happiness. "
            "Return JSON only as an object with key 'evidence'. Each item must contain concept, "
            "evidence_type (support|contradict|contextual), summary, strength (weak|moderate|strong). "
            "Use the user's own meaning where possible. Do not infer from entertainment preferences."
        )
        user = f"Experience type: {experience_type}\nReflection:\n{text}"
        payload = {
            "model": self.llm_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload)
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
        data = json.loads(raw)
        result: list[EvidenceCandidate] = []
        for item in data.get("evidence", [])[:8]:
            concept = str(item.get("concept", "")).strip()[:200]
            etype = str(item.get("evidence_type", "contextual")).lower()
            strength = str(item.get("strength", "moderate")).lower()
            if not concept or etype not in {"support", "contradict", "contextual"}:
                continue
            if strength not in {"weak", "moderate", "strong"}:
                strength = "moderate"
            result.append(
                EvidenceCandidate(
                    concept=concept,
                    evidence_type=etype,
                    summary=str(item.get("summary", concept))[:1000],
                    original_text=text[:2000],
                    strength=strength,
                )
            )
        return result

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.embedding_model, "input": texts}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self.base_url}/embeddings", headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()["data"]
        ordered = sorted(data, key=lambda x: x["index"])
        return [item["embedding"] for item in ordered]


def get_ai_provider() -> AIProvider:
    provider = os.getenv("WHOAMI_AI_PROVIDER", "local").lower().strip()
    if provider in {"openai", "openai_compatible"}:
        return OpenAICompatibleProvider()
    return LocalProvider()
