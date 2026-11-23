"""Unit and integration tests for SAHI audio generation, DSP degradation, and dataset pipeline."""

import base64
import pytest
import httpx
import numpy as np

from sahi.audio.models import AudioCondition, TTSRequest, DegradationConfig
from sahi.audio.wav_utils import read_wav_bytes, write_wav_bytes, generate_synthetic_tone
from sahi.audio.degradation import AudioDegradationEngine
from sahi.audio.providers.sarvam_bulbul import SarvamBulbulProvider
from sahi.audio.providers.indic_parler import IndicParlerTTSStub, IndicParlerEvaluator
from sahi.audio.pipeline import AudioDatasetPipeline
from sahi.dataset.pilot import PILOT_DATASET
from sahi.infra.cache import ContentAddressedCache

@pytest.fixture
def clean_wav_bytes():
    # 1.0s tone at 16,000 Hz
    return generate_synthetic_tone(duration_s=1.0, sample_rate=16000, frequency_hz=1000.0)

@pytest.fixture
def cache(tmp_path):
    return ContentAddressedCache(str(tmp_path / "tts_cache"))

# 1. Provider response decoding (base64 -> WAV)
def test_sarvam_bulbul_response_decoding(cache, clean_wav_bytes):
    b64_audio = base64.b64encode(clean_wav_bytes).decode("ascii")
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"audios": [b64_audio]})
    )
    client = httpx.Client(transport=mock_transport)
    provider = SarvamBulbulProvider(api_key="test_key", cache=cache, http_client=client)

    req = TTSRequest(text="पांच हज़ार रुपये", target_language_code="hi-IN")
    resp = provider.synthesize(req)

    assert resp.audio_bytes == clean_wav_bytes
    assert resp.sample_rate == 16000
    assert resp.duration_seconds == 1.0
    assert resp.cached is False

# 2. Cache hit and miss for TTS synthesis
def test_sarvam_bulbul_cache_hit_and_miss(cache, clean_wav_bytes):
    b64_audio = base64.b64encode(clean_wav_bytes).decode("ascii")
    calls = 0
    def handler(req):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"audios": [b64_audio]})

    mock_transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=mock_transport)
    provider = SarvamBulbulProvider(api_key="test_key", cache=cache, http_client=client)

    req = TTSRequest(text="రెండు వేలు", target_language_code="te-IN")

    # First call: miss
    r1 = provider.synthesize(req)
    assert r1.cached is False
    assert calls == 1

    # Second call: hit
    r2 = provider.synthesize(req)
    assert r2.cached is True
    assert r2.audio_bytes == clean_wav_bytes
    assert calls == 1  # No second API request made!

# 3. Telephony conversion (Mono, 8000 Hz, 300-3400 Hz bandpass)
def test_telephony_degradation(clean_wav_bytes):
    engine = AudioDegradationEngine()
    processed_bytes, duration, snr_val = engine.process(clean_wav_bytes, AudioCondition.TELEPHONY)

    samples, sr, channels = read_wav_bytes(processed_bytes)
    assert sr == 8000
    assert channels == 1
    assert abs(duration - 1.0) < 0.05
    assert snr_val is None

# 4. G.711 μ-law roundtrip companding
def test_mulaw_roundtrip(clean_wav_bytes):
    engine = AudioDegradationEngine(DegradationConfig(apply_mulaw=True))
    orig_samples, sr, _ = read_wav_bytes(clean_wav_bytes)
    mulaw_samples = engine._apply_mulaw(orig_samples)

    # μ-law quantization should preserve signal with minimal distortion (< 5% RMS difference)
    rms_diff = np.sqrt(np.mean((orig_samples - mulaw_samples) ** 2))
    assert rms_diff < 0.05

# 5. Deterministic noise injection (seed preservation)
def test_deterministic_noise_reproducibility(clean_wav_bytes):
    engine1 = AudioDegradationEngine(DegradationConfig(noise_seed=42))
    engine2 = AudioDegradationEngine(DegradationConfig(noise_seed=42))
    engine3 = AudioDegradationEngine(DegradationConfig(noise_seed=99))

    out1, _, _ = engine1.process(clean_wav_bytes, AudioCondition.TELEPHONY_NOISE)
    out2, _, _ = engine2.process(clean_wav_bytes, AudioCondition.TELEPHONY_NOISE)
    out3, _, _ = engine3.process(clean_wav_bytes, AudioCondition.TELEPHONY_NOISE)

    assert out1 == out2  # Exactly identical byte stream with same seed
    assert out1 != out3  # Different seed produces different noise

# 6. SNR correctness (within 0.5 dB of target)
def test_snr_accuracy(clean_wav_bytes):
    target_snr = 10.0
    engine = AudioDegradationEngine(DegradationConfig(noise_snr_db=target_snr, noise_seed=123))
    _, _, measured_snr = engine.process(clean_wav_bytes, AudioCondition.TELEPHONY_NOISE)

    assert measured_snr is not None
    # Must be within 0.5 dB of target 10 dB
    assert abs(measured_snr - target_snr) <= 0.5

# 7. Invalid audio rejection (< 44 bytes or corrupt)
def test_invalid_audio_rejection():
    with pytest.raises(ValueError):
        read_wav_bytes(b"too_short")

    with pytest.raises(Exception):
        read_wav_bytes(b"RIFF" + b"\x00" * 50)

# 8. Dry-run cost estimate calculation
def test_cost_estimation():
    provider = SarvamBulbulProvider(api_key="mock")
    # 2,500 characters should cost ₹2.50 at ₹1/1000 characters
    cost = provider.estimate_cost_inr(2500)
    assert cost == 2.50

    pipeline = AudioDatasetPipeline(tts_provider=provider)
    estimate = pipeline.estimate_dataset_cost_inr()
    assert estimate["total_utterances"] == 24
    assert estimate["clips_to_produce"] == 72
    assert estimate["estimated_cost_inr"] > 0.5
    assert estimate["estimated_cost_inr"] < 2.0  # Entire pilot dataset costs ~ ₹0.90 to ₹1.20

# 9. AI4Bharat Indic Parler-TTS evaluation report
def test_indic_parler_evaluation():
    report = IndicParlerEvaluator.get_evaluation_report()
    assert report["license"] == "Apache-2.0"
    assert "hi" in report["supported_languages"]
    assert "te" in report["supported_languages"]
    assert report["cost_inr"] == 0.0

# 10. Audio pipeline manifest generation (72 clips: 24 x 3)
def test_manifest_generation(tmp_path):
    pipeline = AudioDatasetPipeline(output_dir=str(tmp_path / "audio_out"))
    manifest = pipeline.generate_manifest(save_audio_files=True)

    assert len(manifest) == 72
    clean_clips = [c for c in manifest if c.condition == AudioCondition.CLEAN]
    telephony_clips = [c for c in manifest if c.condition == AudioCondition.TELEPHONY]
    noisy_clips = [c for c in manifest if c.condition == AudioCondition.TELEPHONY_NOISE]

    assert len(clean_clips) == 24
    assert len(telephony_clips) == 24
    assert len(noisy_clips) == 24

    # Verify telephony sample rate is strictly 8000 Hz
    for clip in telephony_clips:
        assert clip.sample_rate == 8000
    for clip in noisy_clips:
        assert clip.sample_rate == 8000
        assert clip.snr_db is not None
        assert abs(clip.snr_db - 10.0) <= 0.5
