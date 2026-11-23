"""Unit tests for Sarvam Saaras v4 and Sarvam 105B adapters with mocked HTTP transport."""

import os
import json
import pytest
import httpx
from unittest.mock import Mock, patch

from sahi.agent.saaras import SaarasSTTAdapter
from sahi.agent.sarvam_llm import SarvamLLMAdapter
from sahi.agent.models import TranscriptResponse, TransferProposal
from sahi.agent.exceptions import (
    SarvamAPIError, SarvamAuthenticationError, SarvamRateLimitError,
    SarvamServerError, SarvamTimeoutError, InvalidToolCallError
)
from sahi.infra.cache import ContentAddressedCache
from sahi.pipeline import SahiPipeline
from sahi.bank.database import MockBankDatabase
from sahi.guard.models import GuardAction

# Dummy audio bytes
DUMMY_AUDIO = b"RIFF....WAVEfmt ....data...."

@pytest.fixture
def temp_cache_dir(tmp_path):
    return str(tmp_path / "test_cache")

@pytest.fixture
def cache(temp_cache_dir):
    return ContentAddressedCache(temp_cache_dir)

# 1. Saaras transcribe success
def test_saaras_transcribe_success(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"transcript": "दो हज़ार पाँच सौ रुपये", "language_code": "hi-IN"},
            headers={"x-request-id": "req_stt_001"}
        )
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client)

    resp = adapter.transcribe(DUMMY_AUDIO, mode="transcribe", language_code="hi-IN")
    assert resp.transcript == "दो हज़ार पाँच सौ रुपये"
    assert resp.language_code == "hi-IN"
    assert resp.mode == "transcribe"
    assert resp.cached is False
    assert resp.request_id == "req_stt_001"

# 2. Saaras codemix success
def test_saaras_codemix_success(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"transcript": "do hazar panch sau rupaye transfer karo", "language_code": "hi-IN"}
        )
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client)

    resp = adapter.transcribe(DUMMY_AUDIO, mode="codemix")
    assert resp.transcript == "do hazar panch sau rupaye transfer karo"
    assert resp.mode == "codemix"

def test_saaras_translit_mode_and_invalid_mode(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"transcript": "do hazaar paanch sau rupaye", "language_code": "hi-IN"}
        )
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client)

    # Fifth supported mode: translit (Romanized Indic output)
    resp = adapter.transcribe(DUMMY_AUDIO, mode="translit")
    assert resp.transcript == "do hazaar paanch sau rupaye"
    assert resp.mode == "translit"

    # Invalid mode rejection
    with pytest.raises(ValueError) as exc_info:
        adapter.transcribe(DUMMY_AUDIO, mode="unsupported_mode")
    assert "Unsupported mode" in str(exc_info.value)

# 3. Telugu and Hindi response handling
def test_saaras_telugu_response_handling(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"transcript": "రెండున్నర వేలు పంపించండి", "language_code": "te-IN"}
        )
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client)

    resp = adapter.transcribe(DUMMY_AUDIO, language_code="te-IN")
    assert resp.transcript == "రెండున్నర వేలు పంపించండి"
    assert resp.language_code == "te-IN"

# 4. Authentication failure (401/403)
def test_saaras_auth_failure(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": "Invalid API key"})
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="bad_key", cache=cache, http_client=client, max_retries=0)

    with pytest.raises(SarvamAuthenticationError) as exc_info:
        adapter.transcribe(DUMMY_AUDIO)
    assert exc_info.value.status_code == 401

# 5. Rate limiting (429)
def test_saaras_rate_limiting(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(429, json={"error": "Too Many Requests"})
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client, max_retries=0)

    with pytest.raises(SarvamRateLimitError) as exc_info:
        adapter.transcribe(DUMMY_AUDIO)
    assert exc_info.value.status_code == 429

# 6. Server failure (500)
def test_saaras_server_failure(cache):
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(500, json={"error": "Internal Server Error"})
    )
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client, max_retries=0)

    with pytest.raises(SarvamServerError) as exc_info:
        adapter.transcribe(DUMMY_AUDIO)
    assert exc_info.value.status_code == 500

# 7. Timeout and retry behaviour
def test_saaras_timeout_and_retry(cache):
    attempts = 0
    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise httpx.ReadTimeout("Timeout")
        return httpx.Response(200, json={"transcript": "recovered after timeout"})

    mock_transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client, max_retries=2)

    resp = adapter.transcribe(DUMMY_AUDIO)
    assert resp.transcript == "recovered after timeout"
    assert attempts == 2

# 8. Cache hit and cache miss
def test_cache_hit_and_miss(cache):
    calls = 0
    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"transcript": "cached transcript", "language_code": "hi-IN"})

    mock_transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client)

    # First call -> Miss
    r1 = adapter.transcribe(DUMMY_AUDIO, mode="transcribe")
    assert r1.cached is False
    assert calls == 1

    # Second call -> Hit
    r2 = adapter.transcribe(DUMMY_AUDIO, mode="transcribe")
    assert r2.cached is True
    assert r2.transcript == "cached transcript"
    assert calls == 1  # No additional network call made!

# 9. Cache invalidation when parameters change
def test_cache_different_parameters(cache):
    calls = 0
    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"transcript": f"transcript call {calls}"})

    mock_transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=mock_transport)
    adapter = SaarasSTTAdapter(api_key="test_key", cache=cache, http_client=client)

    # Mode 1
    r1 = adapter.transcribe(DUMMY_AUDIO, mode="transcribe")
    assert r1.cached is False
    assert calls == 1

    # Mode 2 (different mode produces different cache key)
    r2 = adapter.transcribe(DUMMY_AUDIO, mode="codemix")
    assert r2.cached is False
    assert calls == 2

# 10. Sarvam tool-call parsing (propose_transfer)
def test_sarvam_llm_tool_call_parsing(cache):
    response_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_12345",
                            "type": "function",
                            "function": {
                                "name": "propose_transfer",
                                "arguments": json.dumps({
                                    "amount_inr": 2500,
                                    "payee": "ramesh@upi",
                                    "extracted_context": "दो हज़ार पाँच सौ"
                                })
                            }
                        }
                    ]
                }
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 25}
    }

    mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, json=response_payload))
    client = httpx.Client(transport=mock_transport)
    adapter = SarvamLLMAdapter(api_key="test_key", cache=cache, http_client=client)

    chat_resp = adapter.extract_transfer_proposal("दो हज़ार पाँच सौ रुपये रमेश को भेजो")
    assert chat_resp.proposal is not None
    assert chat_resp.proposal.amount_inr == 2500
    assert chat_resp.proposal.payee == "ramesh@upi"
    assert chat_resp.proposal.extracted_context == "दो हज़ार पाँच सौ"
    assert chat_resp.prompt_tokens == 50

# 11. Malformed tool-call arguments
def test_sarvam_llm_malformed_arguments(cache):
    response_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_bad",
                            "type": "function",
                            "function": {
                                "name": "propose_transfer",
                                "arguments": "{malformed_json...}"
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, json=response_payload))
    client = httpx.Client(transport=mock_transport)
    adapter = SarvamLLMAdapter(api_key="test_key", cache=cache, http_client=client, max_retries=0)

    with pytest.raises(InvalidToolCallError) as exc_info:
        adapter.extract_transfer_proposal("test input")
    assert "Malformed JSON" in str(exc_info.value)

# 12. Invalid amount rejection (<= 0)
def test_sarvam_llm_invalid_amount_rejection(cache):
    response_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_neg",
                            "type": "function",
                            "function": {
                                "name": "propose_transfer",
                                "arguments": json.dumps({"amount_inr": -500, "payee": "suresh@upi"})
                            }
                        }
                    ]
                }
            }
        ]
    }
    mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, json=response_payload))
    client = httpx.Client(transport=mock_transport)
    adapter = SarvamLLMAdapter(api_key="test_key", cache=cache, http_client=client, max_retries=0)

    with pytest.raises(InvalidToolCallError) as exc_info:
        adapter.extract_transfer_proposal("test input")
    assert "Must be an integer > 0" in str(exc_info.value)

def test_sarvam_llm_auth_and_rate_limit_errors(cache):
    # 401 Auth Error
    mock_auth = httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "unauthorized"}))
    client_auth = httpx.Client(transport=mock_auth)
    adapter_auth = SarvamLLMAdapter(api_key="bad_key", cache=cache, http_client=client_auth, max_retries=0)
    with pytest.raises(SarvamAuthenticationError):
        adapter_auth.extract_transfer_proposal("test")

    # 429 Rate Limit Error
    mock_429 = httpx.MockTransport(lambda req: httpx.Response(429, json={"error": "rate limit"}))
    client_429 = httpx.Client(transport=mock_429)
    adapter_429 = SarvamLLMAdapter(api_key="key", cache=cache, http_client=client_429, max_retries=0)
    with pytest.raises(SarvamRateLimitError):
        adapter_429.extract_transfer_proposal("test")

    # 500 Server Error
    mock_500 = httpx.MockTransport(lambda req: httpx.Response(500, json={"error": "server error"}))
    client_500 = httpx.Client(transport=mock_500)
    adapter_500 = SarvamLLMAdapter(api_key="key", cache=cache, http_client=client_500, max_retries=0)
    with pytest.raises(SarvamServerError):
        adapter_500.extract_transfer_proposal("test")

    # Timeout Error
    def timeout_handler(req):
        raise httpx.ReadTimeout("Timeout")
    mock_timeout = httpx.MockTransport(timeout_handler)
    client_timeout = httpx.Client(transport=mock_timeout)
    adapter_timeout = SarvamLLMAdapter(api_key="key", cache=cache, http_client=client_timeout, max_retries=0)
    with pytest.raises(SarvamTimeoutError):
        adapter_timeout.extract_transfer_proposal("test")

def test_sarvam_llm_cache_hit(cache):
    calls = 0
    def handler(req):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={
            "choices": [{
                "message": {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "propose_transfer",
                            "arguments": json.dumps({"amount_inr": 1000, "payee": "user@upi"})
                        }
                    }]
                }
            }]
        })

    mock_transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=mock_transport)
    adapter = SarvamLLMAdapter(api_key="test_key", cache=cache, http_client=client)

    r1 = adapter.extract_transfer_proposal("pay 1000 to user")
    assert r1.cached is False
    assert calls == 1

    r2 = adapter.extract_transfer_proposal("pay 1000 to user")
    assert r2.cached is True
    assert r2.proposal.amount_inr == 1000
    assert calls == 1

# 13. Confirmation that the LLM cannot bypass SahiGuard
def test_llm_cannot_bypass_sahiguard(cache, temp_db_path):
    """
    CRITICAL SAFETY TEST:
    Even if the LLM proposes 50,000 INR when audio transcript says 5,000 INR,
    SahiGuard intercepts the power-of-ten mismatch and aborts simulated transfer.
    """
    bank_db = MockBankDatabase(temp_db_path)
    pipeline = SahiPipeline(bank_db=bank_db)

    # Mock Saaras returning 5000 in both modes
    stt_mock = Mock()
    stt_mock.transcribe.side_effect = [
        TranscriptResponse(transcript="send five thousand rupees", mode="transcribe", audio_hash="hash1"),
        TranscriptResponse(transcript="send 5000 rupees", mode="codemix", audio_hash="hash1"),
    ]

    # Mock LLM maliciously or mistakenly proposing 50,000 (10x error)
    llm_mock = Mock()
    llm_mock.extract_transfer_proposal.return_value = Mock(
        proposal=TransferProposal(amount_inr=50000, payee="attacker@upi")
    )

    result = pipeline.process_audio_pipeline(
        audio_bytes=DUMMY_AUDIO,
        saaras_adapter=stt_mock,
        llm_adapter=llm_mock,
        from_account="ACC_USER_001"
    )

    # Must be ESCALATED by SahiGuard
    assert result.status == "ESCALATED"
    assert result.guard_decision.action == GuardAction.ESCALATE
    assert result.guard_decision.discrepancy_factor == 10.0
    assert result.transfer_response is None

    # Verify zero balance deducted from mock bank
    acc = bank_db.get_account("ACC_USER_001")
    assert acc.balance_inr == 100000
    bank_db.close()

# 14. Opt-in Live Integration Test (Skipped by default)
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_SARVAM_TESTS") or not os.getenv("SARVAM_API_KEY"),
    reason="Live Sarvam API tests require RUN_LIVE_SARVAM_TESTS=1 and SARVAM_API_KEY."
)
def test_live_sarvam_integration_opt_in():
    """Explicitly gated live integration test. Will never run without approval & env flags."""
    adapter = SarvamLLMAdapter()
    resp = adapter.extract_transfer_proposal("pay 500 rupees to Ramesh")
    assert resp.proposal is not None
    assert resp.proposal.amount_inr == 500
