"""Data models for audio generation, degradation conditions, and dataset clips."""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class AudioCondition(str, Enum):
    CLEAN = "CLEAN"
    TELEPHONY = "TELEPHONY"
    TELEPHONY_NOISE = "TELEPHONY_NOISE"

class TTSRequest(BaseModel):
    text: str = Field(..., description="Text prompt to synthesize")
    target_language_code: str = Field(..., description="e.g. 'hi-IN', 'te-IN', 'en-IN'")
    speaker: str = Field("meera", description="Speaker persona voice name")
    model: str = Field("bulbul:v4-flash", description="TTS model identifier")
    provider: str = Field("sarvam", description="TTS provider name")
    extra_params: Dict[str, Any] = Field(default_factory=dict)

class TTSResponse(BaseModel):
    audio_bytes: bytes = Field(..., description="Decoded binary audio payload")
    audio_format: str = Field("wav", description="Audio container format (wav)")
    sample_rate: int = Field(22050, description="Audio sample rate in Hz")
    duration_seconds: float = Field(..., description="Duration of synthesized audio")
    cached: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DegradationConfig(BaseModel):
    target_sample_rate: int = Field(8000, description="Telephony sample rate (8000 Hz)")
    bandpass_low_hz: float = Field(300.0, description="Lower cutoff frequency in Hz")
    bandpass_high_hz: float = Field(3400.0, description="Upper cutoff frequency in Hz")
    apply_mulaw: bool = Field(True, description="Apply G.711 μ-law quantization simulation")
    noise_snr_db: Optional[float] = Field(10.0, description="Target SNR in dB for noise condition")
    noise_seed: int = Field(42, description="Deterministic random seed for noise reproducibility")

class AudioClipRecord(BaseModel):
    clip_id: str
    utterance_id: str
    condition: AudioCondition
    sha256_hash: str
    sample_rate: int
    duration_seconds: float
    snr_db: Optional[float] = None
    provider: str
    model: str
    relative_filepath: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
