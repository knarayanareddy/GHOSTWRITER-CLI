import json

import httpx
import pytest
from gw.errors import OllamaModelError
from gw.llm import ollama
from gw.llm.ollama import OllamaClient


class FakeStreamResponse:
    status_code = 200

    def __init__(self, lines):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def iter_lines(self):
        return iter(self._lines)

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url):
        return httpx.Response(200, json={"models": [{"name": "llama3"}]}, request=httpx.Request("GET", url))

    def post(self, url, json):
        return httpx.Response(200, json={"response": "done"}, request=httpx.Request("POST", url))


def test_ollama_stream_generate(monkeypatch):
    lines = [json.dumps({"response": "hel"}), json.dumps({"response": "lo"}), json.dumps({"done": True})]
    monkeypatch.setattr(ollama.httpx, "stream", lambda *a, **k: FakeStreamResponse(lines))
    assert "".join(OllamaClient().generate("llama3", "prompt")) == "hello"


def test_ollama_stream_model_error(monkeypatch):
    monkeypatch.setattr(ollama.httpx, "stream", lambda *a, **k: FakeStreamResponse([json.dumps({"error": "missing"})]))
    with pytest.raises(OllamaModelError):
        list(OllamaClient().generate("missing", "prompt"))


def test_ollama_nonstream_and_list_models(monkeypatch):
    monkeypatch.setattr(ollama.httpx, "Client", FakeClient)
    client = OllamaClient()
    assert list(client.generate("llama3", "prompt", stream=False)) == ["done"]
    assert client.list_models() == ["llama3"]
