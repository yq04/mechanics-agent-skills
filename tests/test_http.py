"""
Unit tests for mechanics_skills.http module.
Uses mocking to test transports, retries, headers, and rate limiting without live network.
"""

import io
import json
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest
from mechanics_skills.errors import HTTPError, RateLimitError
from mechanics_skills.http import HTTPClient, HTTPResponse, RateLimiter


def test_http_response_properties():
    data = {"message": "success", "count": 42}
    raw = json.dumps(data).encode("utf-8")
    resp = HTTPResponse(
        status_code=200,
        headers={"Content-Type": "application/json; charset=utf-8"},
        content=raw,
        url="https://api.example.com/test",
    )
    assert resp.status_code == 200
    assert resp.json() == data
    assert "success" in resp.text
    # Should not raise
    resp.raise_for_status()


def test_http_response_error_status():
    resp_404 = HTTPResponse(
        status_code=404,
        headers={},
        content=b"Not Found",
        url="https://api.example.com/notfound",
    )
    with pytest.raises(HTTPError) as exc_info:
        resp_404.raise_for_status()
    assert exc_info.value.status_code == 404

    resp_429 = HTTPResponse(
        status_code=429,
        headers={"retry-after": "5"},
        content=b"Rate Limit Exceeded",
        url="https://api.example.com/limited",
    )
    with pytest.raises(RateLimitError) as exc_info:
        resp_429.raise_for_status()
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 5.0


def test_rate_limiter():
    limiter = RateLimiter(limits={"example.com": 100.0})
    # Should execute without error
    limiter.wait("example.com")
    assert "example.com" in limiter._last_times


def test_prepare_url():
    client = HTTPClient()
    url = client._prepare_url("https://api.example.com/search", {"q": "crack", "limit": 10})
    assert "q=crack" in url
    assert "limit=10" in url
    assert url.startswith("https://api.example.com/search?")

    # Existing query string
    url2 = client._prepare_url("https://api.example.com/search?sort=desc", {"q": "crack"})
    assert url2.startswith("https://api.example.com/search?sort=desc&")


@patch("urllib.request.urlopen")
def test_http_client_get_json_success(mock_urlopen):
    payload = {"status": "ok", "items": [1, 2, 3]}
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.info.return_value = {"Content-Type": "application/json"}
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = HTTPClient()
    res = client.get_json("https://api.example.com/data")
    assert res == payload
    mock_urlopen.assert_called_once()


@patch("time.sleep")
@patch("urllib.request.urlopen")
def test_http_client_retry_on_429_then_succeed(mock_urlopen, mock_sleep):
    # First call raises 429 HTTPError, second call succeeds
    error_fp = io.BytesIO(b"Rate limited")
    err_429 = urllib.error.HTTPError(
        url="https://api.example.com/data",
        code=429,
        msg="Too Many Requests",
        hdrs={"Retry-After": "2"},
        fp=error_fp,
    )

    success_resp = MagicMock()
    success_resp.status = 200
    success_resp.getcode.return_value = 200
    success_resp.read.return_value = b'{"result": "ok"}'
    success_resp.info.return_value = {"Content-Type": "application/json"}

    mock_urlopen.side_effect = [
        err_429,
        MagicMock(__enter__=MagicMock(return_value=success_resp)),
    ]

    client = HTTPClient(max_retries=2)
    resp = client.get("https://api.example.com/data")
    assert resp.status_code == 200
    assert resp.json() == {"result": "ok"}
    assert mock_sleep.called
    assert mock_urlopen.call_count == 2


@patch("time.sleep")
@patch("urllib.request.urlopen")
def test_http_client_no_retry_on_404(mock_urlopen, mock_sleep):
    error_fp = io.BytesIO(b"Not Found")
    err_404 = urllib.error.HTTPError(
        url="https://api.example.com/notfound",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=error_fp,
    )
    mock_urlopen.side_effect = err_404

    client = HTTPClient(max_retries=3)
    resp = client.get("https://api.example.com/notfound")
    assert resp.status_code == 404
    # Should not retry 404
    assert mock_urlopen.call_count == 1
    assert not mock_sleep.called

