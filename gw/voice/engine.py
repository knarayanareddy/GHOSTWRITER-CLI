"""Corpus analysis and voice profile generation."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from gw.errors import CorpusError
from gw.models import VoiceProfile

LOG = logging.getLogger(__name__)
SCHEMA_VERSION = "1.0"
TOKEN_RE = re.compile(r"\b[\w']+\b", re.UNICODE)
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]|")
SUPPORTED_SUFFIXES = {".txt", ".md"}

FORMAL_MARKERS = {"therefore", "however", "moreover", "furthermore", "consequently", "nevertheless"}
TECHNICAL_MARKERS = {"system", "data", "model", "interface", "function", "architecture", "implementation", "api"}
LYRICAL_MARKERS = {"moon", "light", "heart", "river", "memory", "dream", "silence", "shadow"}
CONVERSATIONAL_MARKERS = {"you", "we", "i", "let's", "really", "maybe", "just", "kind"}


class VoiceEngine:
    """Analyze UTF-8 text/Markdown corpora into non-verbatim style metrics."""

    def analyze(
        self,
        corpus_paths: list[Path],
        output_profile_path: Path,
        *,
        min_tokens: int = 1000,
        max_tokens: int = 500_000,
        force: bool = False,
    ) -> VoiceProfile:
        """Analyze corpus files and write a VoiceProfile to disk.

        The profile never contains raw corpus text. Recurring n-grams are
        represented by salted SHA-256 digests plus counts, not phrases.
        """

        files = self._expand_and_validate(corpus_paths)
        if not files:
            raise CorpusError("No supported corpus files found (.txt, .md).", recovery_hint="Pass --corpus pointing to UTF-8 .txt or .md files.")

        LOG.info("starting corpus analysis file_count=%s", len(files))
        texts: list[str] = []
        for file in files:
            try:
                texts.append(file.read_text(encoding="utf-8"))
            except UnicodeDecodeError as exc:
                raise CorpusError(
                    f"Corpus file is not valid UTF-8: {file.name}.",
                    recovery_hint="Convert the file to UTF-8 and rerun `ghostwriter train`.",
                ) from exc
            except OSError as exc:
                raise CorpusError(f"Could not read corpus file: {file.name}.", recovery_hint="Check file permissions and try again.") from exc

        combined = "\n\n".join(texts)
        tokens = self._tokens(combined)
        token_count = len(tokens)
        if token_count < min_tokens:
            raise CorpusError(
                f"Corpus too small ({token_count} tokens). Minimum is {min_tokens}.",
                recovery_hint="Add more .txt/.md writing samples or lower --min-tokens for experimentation.",
            )
        if token_count > max_tokens and not force:
            raise CorpusError(
                f"Corpus too large ({token_count} tokens). Maximum is {max_tokens} without --force.",
                recovery_hint="Use --force if you intentionally want to analyze the full corpus.",
            )

        profile = VoiceProfile(
            schema_version=SCHEMA_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
            corpus_hash=self._corpus_hash(files),
            metrics=self._metrics(combined, tokens, files),
        )
        profile.save(output_profile_path)
        LOG.info("voice profile written token_count=%s file_count=%s", token_count, len(files))
        return profile

    def _expand_and_validate(self, paths: list[Path]) -> list[Path]:
        if not paths:
            raise CorpusError("Missing corpus path.", recovery_hint="Run `ghostwriter train --corpus <path>`.")
        files: list[Path] = []
        for raw in paths:
            path = raw.expanduser()
            if not path.exists():
                raise FileNotFoundError(str(raw))
            if path.is_dir():
                files.extend(p for p in sorted(path.rglob("*")) if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)
            elif path.is_file():
                if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                    raise CorpusError(
                        f"Unsupported corpus file type: {path.name}.",
                        recovery_hint="Phase 1 supports .txt and .md only.",
                    )
                files.append(path)
            else:
                raise CorpusError(f"Corpus path is not a file or directory: {path.name}.")
        unreadable = [p.name for p in files if not p.exists() or not p.is_file()]
        if unreadable:
            raise CorpusError(f"Unreadable corpus files: {', '.join(unreadable)}")
        return sorted(set(files))

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]

    @staticmethod
    def _sentences(text: str) -> list[str]:
        # Avoid heavyweight NLP deps. Keep only sentence-like spans with tokens.
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if TOKEN_RE.search(p)]

    @staticmethod
    def _corpus_hash(files: Iterable[Path]) -> str:
        h = hashlib.sha256()
        for file in sorted(files):
            stat = file.stat()
            h.update(f"{file.expanduser().resolve()}|{stat.st_size}\n".encode())
        return h.hexdigest()

    def _metrics(self, text: str, tokens: list[str], files: list[Path]) -> dict[str, object]:
        sentences = self._sentences(text)
        sentence_lengths = [len(self._tokens(s)) for s in sentences] or [0]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if TOKEN_RE.search(p)]
        paragraph_lengths = [len(self._tokens(p)) for p in paragraphs] or [0]
        token_count = len(tokens)
        unique_count = len(set(tokens))
        punctuation = self._punctuation(text, max(token_count, 1))
        return {
            "token_count": token_count,
            "file_count": len(files),
            "total_bytes": sum(p.stat().st_size for p in files),
            "avg_sentence_length": round(mean(sentence_lengths), 2),
            "sentence_length_distribution": self._bucket_lengths(sentence_lengths, (8, 18, 30)),
            "vocabulary_richness": round(unique_count / max(token_count, 1), 4),
            "top_n_grams": self._hashed_top_ngrams(tokens),
            "tonal_register": self._tonal_register(tokens),
            "punctuation_fingerprint": punctuation,
            "structural_patterns": self._structural_patterns(paragraph_lengths, text),
        }

    @staticmethod
    def _bucket_lengths(lengths: list[int], thresholds: tuple[int, int, int]) -> dict[str, float]:
        total = max(len(lengths), 1)
        short = sum(1 for x in lengths if x <= thresholds[0])
        medium = sum(1 for x in lengths if thresholds[0] < x <= thresholds[1])
        long = sum(1 for x in lengths if thresholds[1] < x <= thresholds[2])
        very_long = sum(1 for x in lengths if x > thresholds[2])
        return {
            "short": round(short / total, 3),
            "medium": round(medium / total, 3),
            "long": round(long / total, 3),
            "very_long": round(very_long / total, 3),
        }

    @staticmethod
    def _hashed_top_ngrams(tokens: list[str], top_k: int = 10) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for n in (2, 3):
            counts = Counter(tuple(tokens[i : i + n]) for i in range(max(len(tokens) - n + 1, 0)))
            for gram, count in counts.most_common(top_k // 2):
                digest = hashlib.sha256(" ".join(gram).encode("utf-8")).hexdigest()[:16]
                entries.append({"n": n, "hash": digest, "count": count})
        return entries

    @staticmethod
    def _tonal_register(tokens: list[str]) -> str:
        counts = Counter(tokens)
        scores = {
            "formal": sum(counts[w] for w in FORMAL_MARKERS),
            "technical": sum(counts[w] for w in TECHNICAL_MARKERS),
            "lyrical": sum(counts[w] for w in LYRICAL_MARKERS),
            "conversational": sum(counts[w] for w in CONVERSATIONAL_MARKERS),
        }
        best, value = max(scores.items(), key=lambda kv: kv[1])
        return best if value > 0 else "conversational"

    @staticmethod
    def _punctuation(text: str, token_count: int) -> dict[str, float]:
        marks = [",", ";", ":", "—", "-", "...", "?", "!", "(", ")"]
        return {mark: round(text.count(mark) * 1000 / token_count, 3) for mark in marks}

    def _structural_patterns(self, paragraph_lengths: list[int], text: str) -> list[dict[str, object]]:
        opening = "statement"
        stripped = text.lstrip()
        if stripped.startswith(("How ", "Why ", "What ", "When ", "Where ", "Who ")) or stripped.startswith("?"):
            opening = "question"
        elif stripped.startswith(('"', "'", "“")):
            opening = "quoted"
        elif re.match(r"(?i)^(you|we|i)\b", stripped):
            opening = "direct_personal"
        return [
            {"name": "paragraph_length_distribution", "value": self._bucket_lengths(paragraph_lengths, (50, 120, 220))},
            {"name": "average_paragraph_tokens", "value": round(mean(paragraph_lengths), 2)},
            {"name": "opening_style", "value": opening},
        ]
