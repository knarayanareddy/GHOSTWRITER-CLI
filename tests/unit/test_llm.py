import pytest
from gw.llm import OllamaClient


def test_ollama_rejects_remote_by_default():
    with pytest.raises(ValueError):
        OllamaClient("http://example.com:11434")


def test_ollama_allows_loopback():
    assert OllamaClient("http://127.0.0.1:11434").base_url == "http://127.0.0.1:11434"
