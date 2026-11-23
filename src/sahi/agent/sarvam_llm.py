"""Sarvam 105B Chat Completions API adapter with structured tool calling."""

import os
import json
import time
import logging
from typing import Optional, List, Dict, Any
import httpx

from sahi.agent.models import TransferProposal, SarvamChatResponse
from sahi.agent.exceptions import (
    SarvamAPIError, SarvamAuthenticationError, SarvamRateLimitError,
    SarvamServerError, SarvamTimeoutError, InvalidToolCallError
)
from sahi.infra.cache import ContentAddressedCache

logger = logging.getLogger(__name__)

# Single documented tool definition: propose_transfer
PROPOSE_TRANSFER_TOOL = {
    "type": "function",
    "function": {
        "name": "propose_transfer",
        "description": "Propose a simulated monetary transfer for SahiGuard safety review. This tool NEVER executes transfers directly.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount_inr": {
                    "type": "integer",
                    "description": "Proposed transfer amount in exact integer Indian Rupees."
                },
                "payee": {
                    "type": "string",
                    "description": "Target recipient name, mobile number, or UPI VPA."
                },
                "extracted_context": {
                    "type": "string",
                    "description": "Spoken phrases or context used to deduce the transfer details."
                }
            },
            "required": ["amount_inr", "payee"]
        }
    }
}

class SarvamLLMAdapter:
    """
    Adapter for Sarvam 105B Chat Completions with function calling.
    Endpoint: POST https://api.sarvam.ai/v2/chat/completions
    """

    DEFAULT_BASE_URL = "https://api.sarvam.ai"
    MODEL_NAME = "sarvam-105b"

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

    def extract_transfer_proposal(
        self,
        transcript_text: str,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> SarvamChatResponse:
        """
        Sends transcript to Sarvam 105B to extract a structured transfer proposal.
        """
        if not transcript_text:
            raise ValueError("Transcript text cannot be empty.")

        default_system_prompt = (
            "You are a helpful Indic banking voice assistant. "
            "Analyze the user's spoken instruction and call the propose_transfer function "
            "with the exact amount in integer INR and payee. If the amount is ambiguous or unspecified, "
            "do not invent numbers."
        )

        messages = [
            {"role": "system", "content": system_prompt or default_system_prompt},
            {"role": "user", "content": transcript_text}
        ]

        # 1. Check local cache
        cache_params = {
            "messages": messages,
            "tool": "propose_transfer"
        }
        cache_key = self.cache.compute_key(
            provider="sarvam",
            model=self.MODEL_NAME,
            action="chat_completions",
            payload_data=transcript_text,
            extra_params=cache_params
        )

        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for Sarvam 105B (key={cache_key[:8]})")
                return self._parse_chat_response(cached_data, cached=True, latency_ms=0.0)

        # 2. Prepare API Call
        if not self.api_key:
            raise SarvamAuthenticationError(
                "SARVAM_API_KEY is not set. Real API requests require a valid subscription key."
            )

        url = f"{self.base_url}/v2/chat/completions"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.MODEL_NAME,
            "messages": messages,
            "tools": [PROPOSE_TRANSFER_TOOL],
            "tool_choice": "auto"
        }

        client = self._get_client()
        start_time = time.perf_counter()
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = client.post(url, headers=headers, json=payload)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if resp.status_code == 200:
                    resp_json = resp.json()
                    # Cache successful response
                    if use_cache:
                        self.cache.set(cache_key, resp_json)

                    return self._parse_chat_response(resp_json, cached=False, latency_ms=round(latency_ms, 2))

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
                last_error = SarvamTimeoutError(f"Request to Sarvam 105B timed out: {exc}")
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
        raise SarvamAPIError("Failed to extract transfer proposal from Sarvam 105B.")

    def _parse_chat_response(
        self,
        resp_json: Dict[str, Any],
        cached: bool = False,
        latency_ms: Optional[float] = None
    ) -> SarvamChatResponse:
        """Parses OpenAI-compatible chat completion JSON and validates propose_transfer tool calls."""
        choices = resp_json.get("choices", [])
        if not choices:
            raise SarvamAPIError("No choices returned in Sarvam chat completion response.")

        choice = choices[0]
        message = choice.get("message", {})
        message_content = message.get("content")
        tool_calls = message.get("tool_calls", [])

        usage = resp_json.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")

        proposal: Optional[TransferProposal] = None
        tool_call_id: Optional[str] = None

        if tool_calls:
            tc = tool_calls[0]
            tool_call_id = tc.get("id")
            fn = tc.get("function", {})
            fn_name = fn.get("name")

            if fn_name != "propose_transfer":
                raise InvalidToolCallError(f"Unexpected tool call function: '{fn_name}'. Expected 'propose_transfer'.")

            args_raw = fn.get("arguments", "{}")
            if isinstance(args_raw, str):
                try:
                    args_dict = json.loads(args_raw)
                except json.JSONDecodeError as err:
                    raise InvalidToolCallError(f"Malformed JSON in tool call arguments: {err}")
            elif isinstance(args_raw, dict):
                args_dict = args_raw
            else:
                raise InvalidToolCallError(f"Unexpected arguments format: {type(args_raw)}")

            # Validate amount and payee
            amount = args_dict.get("amount_inr")
            if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
                raise InvalidToolCallError(f"Invalid transfer amount '{amount}'. Must be an integer > 0.")

            payee = args_dict.get("payee")
            if not payee or not isinstance(payee, str) or not payee.strip():
                raise InvalidToolCallError(f"Invalid payee '{payee}'. Must be a non-empty string.")

            proposal = TransferProposal(
                amount_inr=int(amount),
                payee=payee.strip(),
                extracted_context=args_dict.get("extracted_context"),
                raw_arguments=args_dict
            )

        return SarvamChatResponse(
            proposal=proposal,
            message_content=message_content,
            tool_call_id=tool_call_id,
            cached=cached,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            raw_response=resp_json
        )
