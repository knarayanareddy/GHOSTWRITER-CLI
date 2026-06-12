from gw.models import VoiceProfile
from gw.prompt import PromptBuilder


def profile(metrics):
    return VoiceProfile("1.0", "now", "hash", metrics)


def test_prompt_branch_styles():
    builder = PromptBuilder()
    text = builder.build(profile({"avg_sentence_length": 35, "vocabulary_richness": 0.2, "punctuation_fingerprint": {";": 2, "!": 2, "...": 1}, "structural_patterns": [{"name": "average_paragraph_tokens", "value": 200}]}), "x" * 3000)
    assert "longer, layered" in text
    assert "familiar vocabulary" in text
    assert "semicolons" in text
    assert len(text) < 3000
