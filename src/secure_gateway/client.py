"""A trusted host boundary: the provider receives only the masked payload."""

from __future__ import annotations

from typing import Callable
import uuid

from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import MaskMode, SurrogateStrategy, UnmaskResult
from secure_gateway.session import SessionVault


class LocalPrivacyClient:
    """Keep this object and the restored response outside the provider/model context."""

    def __init__(self, max_sessions: int = 1000, mapping_limit: int = 100_000,
                 max_input_bytes: int = 16 * 1024 * 1024) -> None:
        self.vault = SessionVault(max_sessions=max_sessions, mapping_limit=mapping_limit)
        self.engine = MaskingEngine(max_input_bytes=max_input_bytes)

    def request(
        self,
        text: str,
        provider: Callable[[str], str],
        mode: MaskMode = MaskMode.CONTENT_WORDS,
        strategy: SurrogateStrategy = SurrogateStrategy.BRACKET,
        sensitive_terms: set[str] | None = None,
        language: str = "auto",
        normalize_particles: bool = False,
        mask_numbers: bool = False,
    ) -> UnmaskResult:
        session = self.vault.create(f"sess_{uuid.uuid4().hex}", mode, strategy)
        try:
            with session.pin():
                return self._request(session, text, provider, mode, strategy,
                                     sensitive_terms, language, normalize_particles, mask_numbers)
        finally:
            self.vault.clear_session(session.session_id)

    def _request(self, session, text, provider, mode, strategy,
                 sensitive_terms, language, normalize_particles, mask_numbers):
        masked = self.engine.mask_text(
            text, session.session_id, session.generator,
            session.forward_store, session.reverse_store, mode=mode,
            sensitive_terms=sensitive_terms, language=language, mask_numbers=mask_numbers,
        )
        response = provider(masked.masked_text)
        return self.engine.unmask(
            response, session.session_id, session.reverse_store, strategy,
            normalize_particles=normalize_particles, strict=True,
        )

    def close(self) -> None:
        self.vault.close()

    def __enter__(self) -> LocalPrivacyClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
