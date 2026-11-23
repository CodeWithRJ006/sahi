"""Abstract base interface for Text-to-Speech (TTS) providers in SAHI."""

from abc import ABC, abstractmethod
from sahi.audio.models import TTSRequest, TTSResponse

class BaseTTSProvider(ABC):
    """Abstract interface defining uniform synthesis contracts across TTS engines."""

    @abstractmethod
    def synthesize(self, request: TTSRequest, use_cache: bool = True) -> TTSResponse:
        """Synthesizes speech audio from text and returns a validated TTSResponse."""
        pass

    @abstractmethod
    def estimate_cost_inr(self, character_count: int) -> float:
        """Calculates dry-run cost in INR for a given character count."""
        pass
