"""Pure Python and NumPy utilities for WAV audio reading, writing, and validation."""

import io
import wave
import numpy as np
from typing import Tuple

def read_wav_bytes(data: bytes) -> Tuple[np.ndarray, int, int]:
    """
    Reads WAV audio bytes.
    Returns: (samples: np.ndarray in float32 [-1.0, 1.0], sample_rate: int, channels: int)
    """
    if len(data) < 44:
        raise ValueError(f"Invalid WAV payload: too short ({len(data)} bytes).")

    with io.BytesIO(data) as bio:
        with wave.open(bio, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            frames = wf.readframes(n_frames)

    if sample_width == 1:
        # 8-bit unsigned
        raw = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        samples = (raw - 128.0) / 128.0
    elif sample_width == 2:
        # 16-bit signed
        raw = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        samples = raw / 32768.0
    elif sample_width == 4:
        # 32-bit float or int
        raw = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
        samples = raw / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sample_width} bytes")

    if channels > 1:
        samples = samples.reshape(-1, channels)

    return samples, sample_rate, channels

def write_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    """
    Encodes a 1D or 2D NumPy array (float32 in [-1.0, 1.0] or int16) into 16-bit PCM WAV bytes.
    """
    if samples.dtype != np.int16:
        # Clip to prevent overflow distortion
        clipped = np.clip(samples, -1.0, 1.0)
        pcm_data = (clipped * 32767.0).astype(np.int16)
    else:
        pcm_data = samples

    channels = 1 if pcm_data.ndim == 1 else pcm_data.shape[1]

    with io.BytesIO() as bio:
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data.tobytes())
        return bio.getvalue()

def generate_synthetic_tone(
    duration_s: float = 1.0,
    sample_rate: int = 16000,
    frequency_hz: float = 440.0
) -> bytes:
    """Generates a clean synthetic sine wave WAV for test fixtures."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    samples = 0.5 * np.sin(2 * np.pi * frequency_hz * t)
    return write_wav_bytes(samples, sample_rate)
