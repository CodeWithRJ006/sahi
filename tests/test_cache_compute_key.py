# Regression test for ContentAddressedCache.compute_key secret filtering

import json
from sahi.infra.cache import ContentAddressedCache


def test_compute_key_filters_secret_params():
    extra = {
        "api_key": "should_not_be_included",
        "token": "also_hidden",
        "normal": "value",
    }
    key = ContentAddressedCache.compute_key(
        provider="test",
        model="model",
        action="action",
        payload_data={"data": 123},
        extra_params=extra,
    )
    # Compute key without the secret params to compare
    expected = ContentAddressedCache.compute_key(
        provider="test",
        model="model",
        action="action",
        payload_data={"data": 123},
        extra_params={"normal": "value"},
    )
    assert key == expected, "Secret params should be filtered out of the cache key"
