"""Evaluation and stub adapter for AI4Bharat Indic Parler-TTS local engine."""

import logging
from typing import Dict, Any, Optional
from sahi.audio.models import TTSRequest, TTSResponse
from sahi.audio.providers.base import BaseTTSProvider
from sahi.audio.wav_utils import generate_synthetic_tone, read_wav_bytes

logger = logging.getLogger(__name__)

class IndicParlerEvaluator:
    """
    Evaluator verifying technical readiness, licensing, and runtime requirements
    for AI4Bharat Indic Parler-TTS before weight download.
    """

    MODEL_ID = "ai4bharat/indic-parler-tts"
    LICENSE = "Apache-2.0"
    SUPPORTED_LANGUAGES = ["hi", "te", "en", "bn", "ta", "mr", "gu", "kn", "ml", "pa", "or", "as"]
    ESTIMATED_WEIGHT_SIZE_GB = 2.45
    ESTIMATED_MIN_VRAM_GB = 4.0

    @classmethod
    def get_evaluation_report(cls) -> Dict[str, Any]:
        """Provides technical architecture evaluation for Indic Parler-TTS."""
        return {
            "model_name": cls.MODEL_ID,
            "license": cls.LICENSE,
            "open_source": True,
            "commercial_use_allowed": True,
            "supported_languages": cls.SUPPORTED_LANGUAGES,
            "estimated_weight_size_gb": cls.ESTIMATED_WEIGHT_SIZE_GB,
            "recommended_gpu": "NVIDIA GPU with >= 6GB VRAM (e.g. RTX 4060)",
            "runtime_dependencies": ["torch", "transformers", "parler-tts"],
            "download_policy": "Strict manual approval required. Automatic download disabled.",
            "cost_inr": 0.0,
            "readiness": "EVALUATED_AND_STUBBED"
        }

class IndicParlerTTSStub(BaseTTSProvider):
    """
    Local stub for AI4Bharat Indic Parler-TTS.
    Allows running pipeline tests offline without downloading the 2.5GB model weights.
    """

    def __init__(self, enable_mock_synthesis: bool = True):
        self.enable_mock_synthesis = enable_mock_synthesis

    def estimate_cost_inr(self, character_count: int) -> float:
        """Local open-source model has zero external API cost."""
        return 0.0

    def synthesize(self, request: TTSRequest, use_cache: bool = True) -> TTSResponse:
        """
        Synthesizes offline stub audio (or raises error if real weights required).
        """
        if not self.enable_mock_synthesis:
            raise RuntimeError(
                "AI4Bharat Indic Parler-TTS model weights (2.5 GB) are not downloaded. "
                "Download requires explicit user permission."
            )

        # Generates deterministic mock WAV for testing
        duration = max(0.5, round(len(request.text) * 0.08, 2))
        audio_bytes = generate_synthetic_tone(duration_s=duration, sample_rate=16000)
        samples, sr, _ = read_wav_bytes(audio_bytes)

        return TTSResponse(
            audio_bytes=audio_bytes,
            audio_format="wav",
            sample_rate=sr,
            duration_seconds=duration,
            cached=False,
            metadata={
                "provider": "ai4bharat_indic_parler_tts",
                "model": "indic-parler-tts-stub",
                "license": "Apache-2.0"
            }
        )
