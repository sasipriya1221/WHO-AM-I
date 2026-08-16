from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.providers import EvidenceCandidate


@dataclass(frozen=True)
class ProviderCallSnapshot:
    extract_calls: tuple[tuple[str, str], ...]
    embed_calls: tuple[tuple[str, ...], ...]


@dataclass
class RecordingProviderSpy:
    """Deterministic provider double that records every inference boundary call."""

    candidates: list[EvidenceCandidate] = field(
        default_factory=lambda: [
            EvidenceCandidate(
                concept="autonomy",
                evidence_type="support",
                summary="Autonomy signal from a test reflection",
                original_text="replaced with the submitted text",
                strength="moderate",
            )
        ]
    )
    extract_calls: list[tuple[str, str]] = field(default_factory=list)
    embed_calls: list[tuple[str, ...]] = field(default_factory=list)

    def extract_evidence(self, text: str, experience_type: str) -> list[EvidenceCandidate]:
        self.extract_calls.append((text, experience_type))
        return [
            EvidenceCandidate(
                concept=candidate.concept,
                evidence_type=candidate.evidence_type,
                summary=candidate.summary,
                original_text=text,
                strength=candidate.strength,
            )
            for candidate in self.candidates
        ]

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(tuple(texts))
        return [[1.0, float(index % 2), 0.5] for index, _ in enumerate(texts)]

    def snapshot(self) -> ProviderCallSnapshot:
        return ProviderCallSnapshot(
            extract_calls=tuple(self.extract_calls),
            embed_calls=tuple(self.embed_calls),
        )


NO_PROVIDER_CALLS = ProviderCallSnapshot(extract_calls=(), embed_calls=())
