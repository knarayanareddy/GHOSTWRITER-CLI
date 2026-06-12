import httpx
import pytest
from gw.errors import OllamaConnectionError, OllamaModelError, OllamaTimeoutError
from gw.llm import ollama
from gw.llm.ollama import OllamaClient


def test_ollama_connect_error(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no")
    monkeypatch.setattr(ollama.httpx, "stream", boom)
    with pytest.raises(OllamaConnectionError):
        list(OllamaClient().generate("m", "p"))


def test_ollama_timeout_error(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.TimeoutException("slow")
    monkeypatch.setattr(ollama.httpx, "stream", boom)
    with pytest.raises(OllamaTimeoutError):
        list(OllamaClient().generate("m", "p"))


def test_ollama_404_maps_to_model_error():
    response = httpx.Response(404, request=httpx.Request("POST", "http://x"))
    with pytest.raises(OllamaModelError):
        OllamaClient._raise_for_ollama(response)
