"""Deterministic Audio Degradation Engine for Telephony and Noise simulation."""

import io
import math
import numpy as np
import scipy.signal
from typing import Tuple, Optional

try:
    import audioop
except ImportError:
    audioop = None

from sahi.audio.models import AudioCondition, DegradationConfig
from sahi.audio.wav_utils import read_wav_bytes, write_wav_bytes

class AudioDegradationEngine:
    """
    Transforms audio into controlled conditions:
    1. CLEAN: Untouched source audio
    2. TELEPHONY: Mono, 8000 Hz, 300-3400 Hz bandpass, G.711 μ-law companding
    3. TELEPHONY_NOISE: Telephony condition with controlled 10 dB SNR Gaussian noise
    """

    def __init__(self, config: Optional[DegradationConfig] = None):
        self.config = config or DegradationConfig()

    def process(
        self,
        audio_bytes: bytes,
        condition: AudioCondition
    ) -> Tuple[bytes, float, Optional[float]]:
        """
        Processes WAV audio into specified condition.
        Returns: (processed_wav_bytes, duration_seconds, measured_snr_db)
        """
        samples, sr, channels = read_wav_bytes(audio_bytes)

        # 1. Condition: CLEAN (preserve original signal)
        if condition == AudioCondition.CLEAN:
            duration = len(samples) / float(sr)
            return audio_bytes, round(duration, 3), None

        # 2. Telephony pre-processing (Mono conversion)
        if samples.ndim > 1:
            samples = np.mean(samples, axis=1)

        # 3. Resample to target telephony rate (8000 Hz)
        target_sr = self.config.target_sample_rate
        if sr != target_sr:
            target_length = int(round(len(samples) * float(target_sr) / sr))
            samples = scipy.signal.resample(samples, target_length).astype(np.float32)
            sr = target_sr

        # 4. Band-pass filtering (300 Hz - 3400 Hz)
        low_cut = self.config.bandpass_low_hz
        high_cut = self.config.bandpass_high_hz
        # Ensure cutoff is within Nyquist boundary
        nyquist = sr / 2.0
        if high_cut >= nyquist:
            high_cut = nyquist - 50.0

        sos = scipy.signal.butter(
            N=4,
            Wn=[low_cut, high_cut],
            btype="bandpass",
            fs=sr,
            output="sos"
        )
        filtered_samples = scipy.signal.sosfilt(sos, samples).astype(np.float32)

        # 5. G.711 μ-law companding simulation
        if self.config.apply_mulaw:
            telephony_samples = self._apply_mulaw(filtered_samples)
        else:
            telephony_samples = filtered_samples

        measured_snr: Optional[float] = None

        # 6. Condition: TELEPHONY_NOISE (Inject controlled 10 dB SNR noise)
        if condition == AudioCondition.TELEPHONY_NOISE:
            target_snr = self.config.noise_snr_db if self.config.noise_snr_db is not None else 10.0
            telephony_samples, measured_snr = self._inject_controlled_noise(
                telephony_samples,
                target_snr_db=target_snr,
                seed=self.config.noise_seed
            )

        duration = len(telephony_samples) / float(sr)
        out_wav_bytes = write_wav_bytes(telephony_samples, sr)
        return out_wav_bytes, round(duration, 3), measured_snr

    def _apply_mulaw(self, samples: np.ndarray) -> np.ndarray:
        """
        Applies ITU-T G.711 μ-law 8-bit companding encode/decode cycle.
        """
        clipped = np.clip(samples, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype(np.int16)

        if audioop is not None:
            raw_pcm = pcm16.tobytes()
            # Encode 16-bit linear PCM to 8-bit μ-law
            ulaw_bytes = audioop.lin2ulaw(raw_pcm, 2)
            # Decode 8-bit μ-law back to 16-bit linear PCM
            decoded_pcm = audioop.ulaw2lin(ulaw_bytes, 2)
            out_pcm16 = np.frombuffer(decoded_pcm, dtype=np.int16).astype(np.float32)
            return out_pcm16 / 32768.0
        else:
            # Mathematical G.711 μ-law fallback: y = sgn(x) * ln(1 + μ|x|) / ln(1 + μ)
            mu = 255.0
            sign = np.sign(clipped)
            abs_x = np.abs(clipped)
            companded = sign * (np.log(1.0 + mu * abs_x) / np.log(1.0 + mu))
            # 8-bit quantization (-128 to 127)
            quantized = np.round(companded * 127.0) / 127.0
            # Inverse expansion: |x| = ( (1 + μ)^|y| - 1 ) / μ
            expanded = sign * ((np.power(1.0 + mu, np.abs(quantized)) - 1.0) / mu)
            return expanded.astype(np.float32)

    def _inject_controlled_noise(
        self,
        samples: np.ndarray,
        target_snr_db: float,
        seed: int
    ) -> Tuple[np.ndarray, float]:
        """
        Injects Gaussian white noise calibrated to exact target SNR in dB.
        Formula: SNR = 10 * log10( P_signal / P_noise )
        """
        sig_power = float(np.mean(samples ** 2))
        if sig_power <= 1e-12:
            return samples, 0.0

        # P_noise = P_signal / 10^(target_snr / 10)
        noise_power = sig_power / (10.0 ** (target_snr_db / 10.0))
        noise_std = math.sqrt(noise_power)

        rng = np.random.RandomState(seed)
        noise = rng.normal(loc=0.0, scale=noise_std, size=len(samples)).astype(np.float32)

        noisy_samples = samples + noise
        actual_noise_power = float(np.mean(noise ** 2))
        actual_snr_db = 10.0 * math.log10(sig_power / actual_noise_power)

        # Clip output to prevent distortion outside [-1.0, 1.0]
        clipped_noisy = np.clip(noisy_samples, -1.0, 1.0)
        return clipped_noisy, round(actual_snr_db, 2)
