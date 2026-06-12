import httpx
from gw.publishers.base import HttpPublisherBase, build_publisher


class Store:
    pass


class Base(HttpPublisherBase):
    platform = "test"


def test_retry_exhausts_transient_and_body_fallback():
    pub = Base(Store(), sleeper=lambda _: None)
    calls = {"n": 0}
    def send():
        calls["n"] += 1
        return httpx.Response(503, text="not-json", request=httpx.Request("POST", "http://x"))
    response, attempts, error = pub._retry_request(type("D", (), {"idempotency_key": "k"})(), send)
    assert attempts == 3
    assert response.status_code == 503
    assert pub._error_from_response(response, error) == "HTTP 503"


def test_retry_timeout_and_http_error():
    pub = Base(Store(), sleeper=lambda _: None)
    response, attempts, error = pub._retry_request(object(), lambda: (_ for _ in ()).throw(httpx.TimeoutException("slow")))
    assert response is None and error == "network timeout"
    response, attempts, error = pub._retry_request(object(), lambda: (_ for _ in ()).throw(httpx.ConnectError("bad")))
    assert response is None and error == "ConnectError"


def test_factory_unknown_platform_raises():
    try:
        build_publisher("unknown", Store())
    except ValueError as exc:
        assert "Unsupported" in str(exc)
