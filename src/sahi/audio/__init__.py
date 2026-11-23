"""Audio package: TTS providers, DSP degradation engine, and dataset manifest pipeline."""

from sahi.audio.models import (
    AudioCondition,
    TTSRequest,
    TTSResponse,
    DegradationConfig,
    AudioClipRecord
)
from sahi.audio.providers.base import BaseTTSProvider
from sahi.audio.providers.sarvam_bulbul import SarvamBulbulProvider
from sahi.audio.providers.indic_parler import IndicParlerEvaluator, IndicParlerTTSStub
from sahi.audio.degradation import AudioDegradationEngine
from sahi.audio.pipeline import AudioDatasetPipeline
from sahi.audio.wav_utils import read_wav_bytes, write_wav_bytes, generate_synthetic_tone

__all__ = [
    "AudioCondition",
    "TTSRequest",
    "TTSResponse",
    "DegradationConfig",
    "AudioClipRecord",
    "BaseTTSProvider",
    "SarvamBulbulProvider",
    "IndicParlerEvaluator",
    "IndicParlerTTSStub",
    "AudioDegradationEngine",
    "AudioDatasetPipeline",
    "read_wav_bytes",
    "write_wav_bytes",
    "generate_synthetic_tone",
]
