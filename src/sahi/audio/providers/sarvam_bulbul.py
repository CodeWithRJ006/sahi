"""Sarvam Bulbul v4 Flash Text-to-Speech provider adapter."""

import os
import base64
import logging
from typing import Optional, Dict, Any
import httpx

from sahi.audio.models import TTSRequest, TTSResponse
from sahi.audio.providers.base import BaseTTSProvider
from sahi.audio.wav_utils import read_wav_bytes
from sahi.infra.cache import ContentAddressedCache
from sahi.agent.exceptions import (
    SarvamAPIError, SarvamAuthenticationError, SarvamRateLimitError,
    SarvamServerError, SarvamTimeoutError
)

logger = logging.getLogger(__name__)

class SarvamBulbulProvider(BaseTTSProvider):
    """
    Adapter for Sarvam Bulbul v4 Flash Text-to-Speech API.
    Endpoint: POST https://api.sarvam.ai/text-to-speech
    """

    DEFAULT_BASE_URL = "https://api.sarvam.ai"
    MODEL_NAME = "bulbul:v4-flash"
    COST_PER_1000_CHARS_INR = 1.0  # ₹1.00 per 1,000 characters

    VALID_LANGUAGE_CODES = {
        "hi-IN", "bn-IN", "kn-IN", "ml-IN", "mr-IN",
        "od-IN", "pa-IN", "ta-IN", "te-IN", "gu-IN", "en-IN"
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache: Optional[ContentAddressedCache] = None,
        timeout: float = 30.0,
        http_client: Optional[httpx.Client] = None
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.base_url = (base_url or os.getenv("SARVAM_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.cache = cache or ContentAddressedCache()
        self.timeout = timeout
        self._external_client = http_client

    def _get_client(self) -> httpx.Client:
        if self._external_client is not None:
            return self._external_client
        return httpx.Client(timeout=self.timeout)

    def estimate_cost_inr(self, character_count: int) -> float:
        """Returns dry-run cost in INR at ₹1.00 per 1,000 characters."""
        return round((character_count / 1000.0) * self.COST_PER_1000_CHARS_INR, 4)

    def synthesize(self, request: TTSRequest, use_cache: bool = True) -> TTSResponse:
        """
        Synthesizes text to speech using Sarvam Bulbul v4 Flash.
        """
        # Validate language code (handle Hinglish safely)
        target_lang = request.target_language_code
        if target_lang not in self.VALID_LANGUAGE_CODES:
            # Map Hinglish / mixed code to Hindi standard hi-IN or en-IN
            if "hinglish" in target_lang.lower():
                target_lang = "hi-IN"
            else:
                raise ValueError(
                    f"Unsupported language code '{target_lang}'. Must be one of {self.VALID_LANGUAGE_CODES}."
                )

        cache_params = {
            "target_language_code": target_lang,
            "speaker": request.speaker,
            "model": self.MODEL_NAME,
        }
        cache_key = self.cache.compute_key(
            provider="sarvam_bulbul",
            model=self.MODEL_NAME,
            action="text_to_speech",
            payload_data=request.text,
            extra_params=cache_params
        )

        # 1. Check local cache
        if use_cache:
            cached_entry = self.cache.get(cache_key)
            if cached_entry and "audio_base64" in cached_entry:
                logger.info(f"Cache hit for Sarvam Bulbul TTS (key={cache_key[:8]})")
                audio_bytes = base64.b64decode(cached_entry["audio_base64"])
                samples, sample_rate, _ = read_wav_bytes(audio_bytes)
                duration = len(samples) / float(sample_rate)
                return TTSResponse(
                    audio_bytes=audio_bytes,
                    audio_format="wav",
                    sample_rate=sample_rate,
                    duration_seconds=round(duration, 3),
                    cached=True,
                    metadata={"cache_key": cache_key, "speaker": request.speaker}
                )

        # 2. Check API key
        if not self.api_key:
            raise SarvamAuthenticationError(
                "SARVAM_API_KEY is not set. Real TTS generation requires a valid subscription key."
            )

        # 3. Perform API request
        url = f"{self.base_url}/text-to-speech"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": [request.text],
            "target_language_code": target_lang,
            "speaker": request.speaker,
            "model": self.MODEL_NAME,
            "enable_preprocessing": True
        }

        client = self._get_client()
        try:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                resp_json = resp.json()
                audios = resp_json.get("audios", [])
                if not audios:
                    raise SarvamAPIError("No audio payload returned in Sarvam TTS response.")

                b64_str = audios[0]
                audio_bytes = base64.b64decode(b64_str)

                # Validate WAV integrity
                samples, sample_rate, _ = read_wav_bytes(audio_bytes)
                duration = len(samples) / float(sample_rate)

                # Cache successful base64 response
                if use_cache:
                    self.cache.set(cache_key, {
                        "audio_base64": b64_str,
                        "sample_rate": sample_rate,
                        "duration_seconds": round(duration, 3),
                        "text": request.text,
                        "speaker": request.speaker,
                        "target_language_code": target_lang
                    })

                return TTSResponse(
                    audio_bytes=audio_bytes,
                    audio_format="wav",
                    sample_rate=sample_rate,
                    duration_seconds=round(duration, 3),
                    cached=False,
                    metadata={"speaker": request.speaker, "target_language_code": target_lang}
                )

            elif resp.status_code in (401, 403):
                raise SarvamAuthenticationError(
                    f"Sarvam TTS authentication failed: {resp.text}",
                    status_code=resp.status_code
                )
            elif resp.status_code == 429:
                raise SarvamRateLimitError(
                    f"Sarvam TTS rate limit reached: {resp.text}",
                    status_code=429
                )
            elif resp.status_code >= 500:
                raise SarvamServerError(
                    f"Sarvam upstream TTS server error: {resp.text}",
                    status_code=resp.status_code
                )
            else:
                raise SarvamAPIError(
                    f"Sarvam TTS request failed ({resp.status_code}): {resp.text}",
                    status_code=resp.status_code
                )
        except httpx.TimeoutException as exc:
            raise SarvamTimeoutError(f"Sarvam TTS request timed out: {exc}")
