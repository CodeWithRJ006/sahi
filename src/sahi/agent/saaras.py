"""Sarvam Saaras v4 Speech-to-Text API adapter with response caching."""

import os
import time
import hashlib
import logging
from typing import Optional, List, Dict, Any, Union
import httpx

from sahi.agent.models import TranscriptResponse
from sahi.agent.exceptions import (
    SarvamAPIError, SarvamAuthenticationError, SarvamRateLimitError,
    SarvamServerError, SarvamTimeoutError
)
from sahi.infra.cache import ContentAddressedCache

logger = logging.getLogger(__name__)

class SaarasSTTAdapter:
    """
    Adapter for Sarvam AI Saaras v4 speech recognition service.
    Endpoint: POST https://api.sarvam.ai/speech-to-text
    """

    DEFAULT_BASE_URL = "https://api.sarvam.ai"
    MODEL_NAME = "saaras:v4"
    SUPPORTED_MODES = ("transcribe", "codemix", "verbatim", "translate", "translit")

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache: Optional[ContentAddressedCache] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        http_client: Optional[httpx.Client] = None
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.base_url = (base_url or os.getenv("SARVAM_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.cache = cache or ContentAddressedCache()
        self.timeout = timeout
        self.max_retries = max_retries
        self._external_client = http_client

    def _get_client(self) -> httpx.Client:
        if self._external_client is not None:
            return self._external_client
        return httpx.Client(timeout=self.timeout)

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        mode: str = "transcribe",
        language_code: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> TranscriptResponse:
        """
        Transcribes speech audio using Saaras v4.

        Args:
            audio_bytes: Raw binary audio (WAV, MP3, etc.)
            filename: Audio filename with appropriate extension
            mode: 'transcribe', 'codemix', 'verbatim', 'translate', etc.
            language_code: Optional ISO code ('hi-IN', 'te-IN', 'en-IN')
            keyterms: Optional vocabulary biasing terms
            use_cache: Whether to query/store in local content-addressed disk cache
        """
        if not audio_bytes:
            raise ValueError("Audio bytes cannot be empty.")

        if mode not in self.SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported mode '{mode}'. Must be one of {self.SUPPORTED_MODES}."
            )

        audio_hash = hashlib.sha256(audio_bytes).hexdigest()

        # 1. Check local disk cache
        cache_params = {
            "mode": mode,
            "language_code": language_code,
            "keyterms": keyterms or []
        }
        cache_key = self.cache.compute_key(
            provider="sarvam",
            model=self.MODEL_NAME,
            action="speech_to_text",
            payload_data=audio_bytes,
            extra_params=cache_params
        )

        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for Saaras STT (audio_hash={audio_hash[:8]})")
                return TranscriptResponse(
                    transcript=cached_data.get("transcript", ""),
                    language_code=cached_data.get("language_code"),
                    mode=mode,
                    audio_hash=audio_hash,
                    cached=True,
                    request_id=cached_data.get("request_id"),
                    latency_ms=0.0,
                    raw_response=cached_data
                )

        # 2. Prepare API call
        if not self.api_key:
            raise SarvamAuthenticationError(
                "SARVAM_API_KEY is not set. Real API requests require a valid subscription key."
            )

        url = f"{self.base_url}/speech-to-text"
        headers = {
            "api-subscription-key": self.api_key,
        }

        form_data: Dict[str, Any] = {
            "model": self.MODEL_NAME,
            "mode": mode,
        }
        if language_code:
            form_data["language_code"] = language_code
        if keyterms:
            form_data["keyterms"] = keyterms

        files = {
            "file": (filename, audio_bytes, "audio/wav")
        }

        client = self._get_client()
        start_time = time.perf_counter()
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = client.post(url, headers=headers, data=form_data, files=files)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if resp.status_code == 200:
                    resp_json = resp.json()
                    transcript = resp_json.get("transcript", "")
                    detected_lang = resp_json.get("language_code", language_code)
                    request_id = resp.headers.get("x-request-id")

                    # Cache successful response
                    if use_cache:
                        self.cache.set(cache_key, resp_json)

                    return TranscriptResponse(
                        transcript=transcript,
                        language_code=detected_lang,
                        mode=mode,
                        audio_hash=audio_hash,
                        cached=False,
                        request_id=request_id,
                        latency_ms=round(latency_ms, 2),
                        raw_response=resp_json
                    )

                elif resp.status_code in (401, 403):
                    raise SarvamAuthenticationError(
                        f"Authentication failed: {resp.text}",
                        status_code=resp.status_code,
                        response_body=resp.text
                    )
                elif resp.status_code == 429:
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (2 ** attempt))
                        continue
                    raise SarvamRateLimitError(
                        f"Rate limit exceeded: {resp.text}",
                        status_code=429,
                        response_body=resp.text
                    )
                elif resp.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (2 ** attempt))
                        continue
                    raise SarvamServerError(
                        f"Sarvam upstream server error ({resp.status_code}): {resp.text}",
                        status_code=resp.status_code,
                        response_body=resp.text
                    )
                else:
                    raise SarvamAPIError(
                        f"Sarvam API request failed ({resp.status_code}): {resp.text}",
                        status_code=resp.status_code,
                        response_body=resp.text
                    )

            except httpx.TimeoutException as exc:
                last_error = SarvamTimeoutError(f"Request to Saaras timed out: {exc}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * (2 ** attempt))
                    continue
                raise last_error
            except (SarvamAPIError, ValueError):
                raise
            except Exception as exc:
                last_error = SarvamAPIError(f"Unexpected connection failure: {exc}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * (2 ** attempt))
                    continue
                raise last_error

        if last_error:
            raise last_error
        raise SarvamAPIError("Failed to transcribe audio.")
