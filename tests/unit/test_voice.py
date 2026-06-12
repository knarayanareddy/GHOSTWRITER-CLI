import json
from pathlib import Path

import pytest
from gw.errors import CorpusError
from gw.voice import VoiceEngine


def test_voice_profile_contains_metrics_not_verbatim_text(tmp_path: Path):
    corpus = tmp_path / "corpus.md"
    secret_phrase = "unique-seed-phrase"
    corpus.write_text(((f"This {secret_phrase} sentence is synthetic and conversational. ") * 80), encoding="utf-8")
    output = tmp_path / "profile.json"

    profile = VoiceEngine().analyze([corpus], output, min_tokens=10)

    raw = output.read_text(encoding="utf-8")
    assert profile.metrics["token_count"] >= 10
    assert secret_phrase not in raw
    assert "corpus_hash" in json.loads(raw)


def test_voice_engine_rejects_small_corpus(tmp_path: Path):
    corpus = tmp_path / "small.txt"
    corpus.write_text("too small", encoding="utf-8")
    with pytest.raises(CorpusError):
        VoiceEngine().analyze([corpus], tmp_path / "profile.json")


def test_voice_engine_rejects_non_utf8(tmp_path: Path):
    corpus = tmp_path / "bad.txt"
    corpus.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(CorpusError):
        VoiceEngine().analyze([corpus], tmp_path / "profile.json", min_tokens=1)
