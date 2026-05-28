📝 GHOSTWRITER CLI

Comprehensive Engineering Design Document
Version 1.0 | Local-First AI Voice-Cloning Writing Assistant
TABLE OF CONTENTS

    Project Overview & Vision
    Goals, Non-Goals & Constraints
    System Architecture
    Module Breakdown
        4.1 Voice Analysis Engine
        4.2 Content Generation Engine
        4.3 Prompt Builder & System
        4.4 Publishing Layer
        4.5 Terminal User Interface (TUI)
        4.6 Ephemeral Data Eraser
        4.7 Profile Management
    Data Models & Schemas
    API Specifications (Internal)
    Directory Structure
    Configuration System
    Voice Profile Deep Dive
    Generation Strategy Deep Dive
    Publishing Integrations
    Privacy & Erasure Model
    TUI Implementation Details
    Platform Support Matrix
    Security Model & Threat Boundaries
    Storage & Persistence
    Logging & Observability
    Testing Strategy
    Build, Packaging & Installation
    Performance Targets & Benchmarks
    Error Handling Strategy
    Dependency Registry
    Milestone & Phased Rollout Plan
    Open Questions & Future Work

1. Project Overview & Vision
1.1 What is GhostWriter CLI?

GhostWriter is a local-first, privacy-preserving command-line tool that learns your unique writing voice from your existing content corpus and generates new posts, articles, emails, and threads in that voice using a locally-run LLM (via Ollama). It is designed to:

    Train on your blog posts, articles, or any text corpus
    Extract statistical and stylistic features to build a reusable "voice profile"
    Generate new content from brief prompts using your voice
    Review generated content in an interactive terminal UI before publishing
    Publish to Mastodon, Bluesky, Nostr, or save to file
    Erase all intermediate session data after each run

Key differentiator: GhostWriter is not a cloud service. All processing, model inference, and data storage happen on your local machine. No API keys, no telemetry, no third-party servers.
1.2 The Problem Being Solved

Modern content creation tools suffer from:

    Cloud lock-in: Most AI writing assistants send your content to third-party APIs
    Voice inconsistency: Generic AI outputs don't match your established writing style
    Platform fragmentation: Publishing to multiple platforms requires manual reformatting
    Privacy concerns: Your drafts, ideas, and personal voice are exposed to external services
    Approval gaps: Generated content gets published without human review

GhostWriter addresses all of these by operating entirely on your machine, learning your actual voice, requiring explicit approval, and supporting multi-platform publishing from a single workflow.
1.3 Design Philosophy
Principle	Description
Local-first	All AI inference via local Ollama. No cloud dependencies.
Voice authenticity	Train on real user content; don't mimic "AI voice"
Human-in-the-loop	Every generated piece requires explicit approval
Ephemeral by default	Session data is wiped after every run unless explicitly saved
Multi-platform	Generate once, publish to Mastodon/Bluesky/Nostr/file
CLI-native	Built for terminal power users; no GUI dependencies
Privacy-preserving	Voice profiles store derived features, not full raw text
2. Goals, Non-Goals & Constraints
2.1 Goals (In Scope)

✅ Train voice profiles from local text corpus (.txt, .md, .rst)
✅ Analyze writing style: sentence length, vocabulary richness, tone, themes
✅ Generate content in user's voice via local Ollama LLM
✅ Multi-format support: single post, thread (numbered), article (sections), email
✅ Length control: short/medium/long with word count targets
✅ Refinement pass: Two-stage generation (draft → refine)
✅ Interactive TUI review with approve/regenerate/discard/edit options
✅ Multi-platform publishing: Mastodon, Bluesky, Nostr, local file
✅ Secure credential storage: Encrypted config for platform API keys
✅ Session wiping: Automatic cleanup of temp files, drafts, shell history
✅ Profile versioning: Save and manage multiple voice profiles
✅ Offline-first: Works without internet (except for publishing)
✅ Cross-platform: macOS, Linux, Windows (via WSL or native)
2.2 Non-Goals (Explicitly Out of Scope)

❌ Cloud-based LLM inference (OpenAI, Anthropic, etc.)
❌ Real-time collaborative editing
❌ Built-in spell/grammar checking (delegate to external tools)
❌ Image generation or multimodal content
❌ Social media analytics or engagement tracking
❌ Automatic scheduled posting (user must explicitly trigger)
❌ Web UI or Electron app (CLI/TUI only)
❌ Model fine-tuning (uses prompt engineering, not weight updates)
2.3 Constraints

    Must work with Ollama as the local LLM backend
    Must support Python 3.10+
    Voice profile analysis must complete in < 60 seconds for typical corpus (100 docs)
    Content generation must stream output for user feedback
    Platform publishing must handle rate limits gracefully
    Session wipe must complete in < 5 seconds
    Must not store plaintext passwords/tokens in config files

3. System Architecture
3.1 High-Level Architecture Diagram

text

┌──────────────────────────────────────────────────────────────────┐
│                      USER'S LOCAL MACHINE                        │
│                                                                  │
│  ┌────────────┐          ┌─────────────────────────────────┐    │
│  │  Corpus    │          │     GHOSTWRITER CLI              │    │
│  │  (~/blog)  │─────────▶│                                  │    │
│  └────────────┘          │  ┌───────────────────────────┐   │    │
│                          │  │   Voice Engine            │   │    │
│  ┌────────────┐          │  │   - Corpus Loader         │   │    │
│  │  Profiles  │◀────────▶│  │   - Statistical Analysis  │   │    │
│  │  (~/.gw/)  │          │  │   - LLM Voice Extractor   │   │    │
│  └────────────┘          │  └───────────┬───────────────┘   │    │
│                          │              │                    │    │
│  ┌────────────┐          │  ┌───────────▼───────────────┐   │    │
│  │ Ollama     │◀────────▶│  │   Content Generator       │   │    │
│  │ (LLM)      │          │  │   - Prompt Builder        │   │    │
│  │ :11434     │          │  │   - Ollama Client         │   │    │
│  └────────────┘          │  │   - Content Refiner       │   │    │
│                          │  └───────────┬───────────────┘   │    │
│  ┌────────────┐          │              │                    │    │
│  │  Terminal  │◀────────▶│  ┌───────────▼───────────────┐   │    │
│  │   (TUI)    │          │  │   Review Interface (TUI)  │   │    │
│  └────────────┘          │  │   - Textual App           │   │    │
│                          │  │   - Approve/Regenerate    │   │    │
│                          │  └───────────┬───────────────┘   │    │
│                          │              │                    │    │
│                          │  ┌───────────▼───────────────┐   │    │
│                          │  │   Publisher Multiplexer   │   │    │
│                          │  │   - Mastodon API          │   │    │
│                          │  │   - Bluesky AT Protocol   │   │    │
│                          │  │   - Nostr Client          │   │    │
│                          │  │   - File Writer           │   │    │
│                          │  └───────────┬───────────────┘   │    │
│                          │              │                    │    │
│                          │  ┌───────────▼───────────────┐   │    │
│                          │  │   Ephemeral Eraser        │   │    │
│                          │  │   - Temp Dir Wiper        │   │    │
│                          │  │   - Session History Scrub │   │    │
│                          │  └───────────────────────────┘   │    │
│                          └─────────────────────────────────┘    │
│                                          │                       │
└──────────────────────────────────────────┼───────────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  INTERNET   │
                                    │  (Publish)  │
                                    └─────────────┘

3.2 Data Flow: Train → Write → Publish

text

┌─────────────────────────────────────────────────────────────────┐
│  TRAIN PHASE                                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. User: `ghostwriter train ~/blog/ --profile my-blog`        │
│  2. Corpus Loader: recursively loads *.md, *.txt, *.rst        │
│  3. Statistical Analyzer: computes avg sentence/word length,   │
│     vocab richness, punctuation patterns                        │
│  4. LLM Voice Extractor: sends samples to Ollama to extract    │
│     tone, themes, and system prompt                             │
│  5. VoiceProfile: serialized to ~/.ghostwriter/profiles/        │
│                    my-blog.json                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  WRITE PHASE                                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. User: `ghostwriter write "why local AI matters"            │
│            --profile my-blog --format article --length long`    │
│  2. Profile Loader: loads my-blog.json                          │
│  3. Prompt Builder: constructs system + user prompt from        │
│     profile + brief + format rules                              │
│  4. Ollama Client: streams generation to terminal               │
│  5. Content Refiner: second-pass LLM call to polish output      │
│  6. TUI: presents draft in Textual interface                    │
│  7. User: [Approve] / [Regenerate] / [Edit] / [Discard]        │
│  8a. If Regenerate → loop back to step 4                        │
│  8b. If Approve → proceed to publish                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PUBLISH PHASE                                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Publisher Multiplexer: routes to Mastodon/Bluesky/Nostr    │
│  2. Platform Client: authenticates + posts content              │
│  3. Success/Failure: logged to session                          │
│  4. Eraser: wipes temp files, session dir, shell history refs  │
└─────────────────────────────────────────────────────────────────┘

3.3 Component Ownership Matrix
Component	Language	Responsibilities
CLI Entry	Python + Typer	Argument parsing, command dispatch
Voice Engine	Python	Corpus loading, stats, LLM analysis
Generator	Python	Prompt building, Ollama client, refinement
TUI	Python + Textual	Interactive review UI
Publisher	Python + httpx	Mastodon/Bluesky/Nostr API clients
Eraser	Python	Secure file deletion, history scrubbing
Profile Store	JSON	Persistent voice profiles
Session Store	Temp files	Ephemeral drafts (wiped on exit)
4. Module Breakdown
4.1 Voice Analysis Engine

Purpose: Analyze a corpus of user writing and extract a reusable "voice profile" containing statistical features, stylistic patterns, and an LLM-generated system prompt.
4.1.1 Corpus Loader

Python

# ghostwriter/voice/loader.py

from pathlib import Path
from typing import List

class CorpusLoader:
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".rst", ".markdown"}
    
    def load(self, path: Path) -> List[str]:
        """
        Load all supported text files from a directory or single file.
        
        Args:
            path: File or directory path
            
        Returns:
            List of document strings (one per file)
        """
        if path.is_file():
            return [self._read_file(path)]
        
        docs = []
        for ext in self.SUPPORTED_EXTENSIONS:
            docs.extend(self._read_file(p) for p in path.rglob(f"*{ext}"))
        
        return docs
    
    def _read_file(self, path: Path) -> str:
        """Read file with UTF-8, fallback to latin-1, skip on error."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="latin-1")
            except Exception as e:
                print(f"⚠️  Skipping {path}: {e}")
                return ""

4.1.2 Statistical Analyzer

Python

# ghostwriter/voice/analyzer.py

import re
from typing import List, Dict
from collections import Counter

class StatisticalAnalyzer:
    def analyze(self, docs: List[str]) -> Dict:
        """
        Compute statistical features across corpus.
        
        Returns:
            {
                "avg_sentence_length": float,
                "avg_word_length": float,
                "vocab_richness": float,  # type-token ratio
                "punctuation_style": {...},
                "doc_count": int,
                "total_words": int
            }
        """
        sentences = []
        words = []
        punct_counts = Counter()
        
        for doc in docs:
            doc_sentences = self._split_sentences(doc)
            sentences.extend(doc_sentences)
            
            for sent in doc_sentences:
                words.extend(self._tokenize(sent))
            
            punct_counts.update(self._count_punctuation(doc))
        
        total_words = len(words)
        unique_words = len(set(words))
        
        return {
            "avg_sentence_length": sum(len(self._tokenize(s)) for s in sentences) / len(sentences) if sentences else 0,
            "avg_word_length": sum(len(w) for w in words) / total_words if total_words else 0,
            "vocab_richness": unique_words / total_words if total_words else 0,
            "punctuation_style": {
                "ellipsis_rate": punct_counts["..."] / len(docs),
                "dash_rate": punct_counts["—"] / len(docs),
                "exclamation_rate": punct_counts["!"] / len(docs),
                "question_rate": punct_counts["?"] / len(docs)
            },
            "doc_count": len(docs),
            "total_words": total_words
        }
    
    def _split_sentences(self, text: str) -> List[str]:
        return re.split(r'[.!?]+', text)
    
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-z]+\b', text.lower())
    
    def _count_punctuation(self, text: str) -> Counter:
        return Counter(c for c in text if c in "...—!?")

4.1.3 LLM Voice Extractor

Python

# ghostwriter/voice/llm_extractor.py

from ollama import Client
from typing import List, Dict
import json

class LLMVoiceExtractor:
    def __init__(self, model: str = "mistral"):
        self.client = Client()
        self.model = model
    
    def extract_voice(self, sample_docs: List[str]) -> Dict:
        """
        Use Ollama to analyze writing samples and extract:
        - tone (one word)
        - themes (list of keywords)
        - system_prompt (instruction for mimicking voice)
        
        Args:
            sample_docs: First ~10 docs from corpus (or all if < 10)
        
        Returns:
            {
                "tone": str,
                "themes": List[str],
                "system_prompt": str
            }
        """
        combined_sample = "\n\n---\n\n".join(sample_docs[:10])
        
        prompt = f"""Analyze the following writing samples and extract the author's voice characteristics.

Samples:
{combined_sample[:8000]}  # Truncate to ~8k chars

Return a JSON object with:
- "tone": one-word descriptor (e.g., "analytical", "conversational", "technical")
- "themes": list of 3-5 key themes or topics this author writes about
- "system_prompt": a detailed instruction (2-3 sentences) for an LLM to mimic this author's voice

Return ONLY valid JSON, no markdown formatting."""

        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            format="json"
        )
        
        return json.loads(response["response"])

4.1.4 Voice Profile Model

Python

# ghostwriter/voice/profile.py

from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json

class VoiceProfile(BaseModel):
    """
    Complete voice profile for a user's writing corpus.
    Stored as JSON at ~/.ghostwriter/profiles/<name>.json
    """
    name: str
    
    # Statistical features
    avg_sentence_length: float
    avg_word_length: float
    vocab_richness: float
    punctuation_style: dict
    doc_count: int
    total_words: int
    
    # LLM-extracted features
    tone: str
    themes: List[str]
    system_prompt: str
    
    # Few-shot examples (first 500 chars of up to 5 docs)
    sample_texts: List[str]
    
    # Metadata
    created_at: str
    corpus_path: str
    
    def save(self, name: Optional[str] = None) -> Path:
        """Save profile to ~/.ghostwriter/profiles/<name>.json"""
        profile_dir = Path.home() / ".ghostwriter" / "profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        profile_name = name or self.name
        path = profile_dir / f"{profile_name}.json"
        
        path.write_text(self.model_dump_json(indent=2))
        return path
    
    @classmethod
    def load(cls, name: str) -> "VoiceProfile":
        """Load profile from ~/.ghostwriter/profiles/<name>.json"""
        path = Path.home() / ".ghostwriter" / "profiles" / f"{name}.json"
        return cls.model_validate_json(path.read_text())
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all saved profile names."""
        profile_dir = Path.home() / ".ghostwriter" / "profiles"
        if not profile_dir.exists():
            return []
        return [p.stem for p in profile_dir.glob("*.json")]

4.2 Content Generation Engine

Purpose: Generate new content from a brief using a loaded voice profile, Ollama LLM, and a two-pass refinement strategy.
4.2.1 Prompt Builder

Python

# ghostwriter/generator/prompt_builder.py

from ghostwriter.voice.profile import VoiceProfile
from typing import Dict

class PromptBuilder:
    """
    Constructs system + user prompts from voice profile + content brief.
    """
    
    FORMAT_TEMPLATES = {
        "post": {
            "desc": "Single social media post (max 500 chars)",
            "rules": "- Write as a single cohesive post\n- Maximum 500 characters\n- No section headers"
        },
        "thread": {
            "desc": "Multi-post thread (5-8 numbered posts)",
            "rules": "- Format as: [1/n] ...\n- Each post ≤ 280 chars\n- Number all posts\n- 5-8 posts total"
        },
        "article": {
            "desc": "Long-form article with sections",
            "rules": "- Include ## section headers\n- Add introduction and conclusion\n- Use paragraphs, not bullet points"
        },
        "email": {
            "desc": "Professional email",
            "rules": "- Include 'Subject:' line\n- Formal greeting and sign-off\n- Professional tone"
        }
    }
    
    LENGTH_GUIDANCE = {
        "short": "Keep it brief and punchy (200-400 words)",
        "medium": "Standard length (400-800 words)",
        "long": "Go deep and comprehensive (800-1500 words)"
    }
    
    def build(
        self,
        profile: VoiceProfile,
        brief: str,
        format: str = "post",
        length: str = "medium"
    ) -> Dict[str, str]:
        """
        Build system + user prompts.
        
        Returns:
            {
                "system": str,  # System prompt with voice instructions
                "user": str     # User prompt with brief + format rules
            }
        """
        system_prompt = self._build_system_prompt(profile)
        user_prompt = self._build_user_prompt(profile, brief, format, length)
        
        return {"system": system_prompt, "user": user_prompt}
    
    def _build_system_prompt(self, profile: VoiceProfile) -> str:
        return f"""{profile.system_prompt}

## Style Notes (Match These EXACTLY):
- Average sentence length: {profile.avg_sentence_length:.1f} words
- Tone: {profile.tone}
- Key themes: {', '.join(profile.themes)}
- Vocabulary richness: {profile.vocab_richness:.2f} (type-token ratio)

## Critical Instructions:
- Write EXACTLY as this author would write
- Match their rhythm, vocabulary level, and sentence structure
- Use their characteristic punctuation patterns
- Do NOT use generic AI phrases like "delve into", "in conclusion", "it's worth noting"
- Be authentic to THIS voice, not a generic LLM voice"""
    
    def _build_user_prompt(
        self,
        profile: VoiceProfile,
        brief: str,
        format: str,
        length: str
    ) -> str:
        format_rules = self.FORMAT_TEMPLATES[format]["rules"]
        length_guide = self.LENGTH_GUIDANCE[length]
        
        # Include few-shot examples
        examples = "\n\n".join(
            f"Example {i+1}:\n{text[:500]}"
            for i, text in enumerate(profile.sample_texts[:3])
        )
        
        return f"""Here are authentic examples of this author's writing:

{examples}

---

Now write NEW content on the following topic:
{brief}

Format: {format}
{format_rules}

Length: {length_guide}

Write in the author's voice. Begin now:"""

4.2.2 Ollama Client

Python

# ghostwriter/generator/ollama_client.py

from ollama import Client
from typing import Generator, Dict

class OllamaClient:
    def __init__(self, model: str = "llama3:8b", base_url: str = "http://localhost:11434"):
        self.client = Client(host=base_url)
        self.model = model
    
    def generate(
        self,
        system: str,
        prompt: str,
        stream: bool = True
    ) -> Generator[str, None, None] | str:
        """
        Generate content from Ollama.
        
        Args:
            system: System prompt
            prompt: User prompt
            stream: If True, yield tokens as they arrive
        
        Returns:
            Generator of strings if stream=True, else full response string
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat(
            model=self.model,
            messages=messages,
            stream=stream,
            options={
                "temperature": 0.85,
                "top_p": 0.95,
                "num_predict": 2048
            }
        )
        
        if stream:
            for chunk in response:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        else:
            return response["message"]["content"]

4.2.3 Content Refiner

Python

# ghostwriter/generator/refiner.py

from ghostwriter.generator.ollama_client import OllamaClient
from ghostwriter.voice.profile import VoiceProfile

class ContentRefiner:
    """
    Second-pass refinement to remove AI-isms and improve voice match.
    """
    
    def __init__(self, client: OllamaClient):
        self.client = client
    
    def refine(self, draft: str, profile: VoiceProfile) -> str:
        """
        Polish draft to better match voice profile.
        
        Args:
            draft: Initial generated content
            profile: Target voice profile
        
        Returns:
            Refined content string
        """
        refine_prompt = f"""You are a copy editor specializing in voice matching.

The following draft was written to sound like a specific author with these characteristics:
- Tone: {profile.tone}
- Themes: {', '.join(profile.themes)}
- Avg sentence length: {profile.avg_sentence_length:.1f} words

Draft:
{draft}

Instructions:
1. Remove any generic AI phrases ("delve into", "it's important to note", "in conclusion", etc.)
2. Match the rhythm and sentence structure to the target average
3. Ensure authenticity — make it sound like a real human wrote it
4. Stay true to the original brief and content; only refine the STYLE
5. Return ONLY the refined text, no commentary

Refined version:"""

        system = "You are a professional copy editor focused on voice authenticity."
        
        return self.client.generate(
            system=system,
            prompt=refine_prompt,
            stream=False
        )

4.2.4 Content Generator (Orchestrator)

Python

# ghostwriter/generator/generator.py

from ghostwriter.voice.profile import VoiceProfile
from ghostwriter.generator.prompt_builder import PromptBuilder
from ghostwriter.generator.ollama_client import OllamaClient
from ghostwriter.generator.refiner import ContentRefiner
from typing import Generator

class ContentGenerator:
    def __init__(
        self,
        profile: VoiceProfile,
        model: str = "llama3:8b"
    ):
        self.profile = profile
        self.client = OllamaClient(model=model)
        self.prompt_builder = PromptBuilder()
        self.refiner = ContentRefiner(self.client)
    
    def generate(
        self,
        brief: str,
        format: str = "post",
        length: str = "medium",
        refine: bool = True
    ) -> Generator[str, None, None]:
        """
        Generate content and optionally refine.
        
        Yields tokens during generation for live terminal feedback.
        Final yield is the complete (possibly refined) text.
        """
        prompts = self.prompt_builder.build(
            self.profile,
            brief,
            format,
            length
        )
        
        # Stream initial generation
        draft = ""
        for token in self.client.generate(
            prompts["system"],
            prompts["user"],
            stream=True
        ):
            draft += token
            yield token
        
        if refine:
            print("\n\n⚡ Refining draft...\n")
            refined = self.refiner.refine(draft, self.profile)
            yield f"\n\n--- REFINED VERSION ---\n{refined}"
        else:
            yield draft

4.3 Prompt Builder & System

Covered in section 4.2.1 above (integrated into Content Generation Engine).
4.4 Publishing Layer

Purpose: Publish approved content to Mastodon, Bluesky, Nostr, or save to local file. Handle platform-specific APIs, authentication, and rate limits.
4.4.1 Publisher Interface

Python

# ghostwriter/publisher/base.py

from abc import ABC, abstractmethod
from typing import Dict, Optional

class Publisher(ABC):
    """
    Base publisher interface.
    All platform publishers must implement this.
    """
    
    @abstractmethod
    def publish(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Publish content to platform.
        
        Args:
            content: The text to publish
            metadata: Optional platform-specific metadata
        
        Returns:
            {
                "success": bool,
                "url": str (if applicable),
                "error": str (if failed)
            }
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Check if credentials/config are valid."""
        pass

4.4.2 Mastodon Publisher

Python

# ghostwriter/publisher/mastodon.py

import httpx
from typing import Dict, Optional, List
from pathlib import Path
import json

class MastodonPublisher(Publisher):
    def __init__(self, config_path: Path):
        config = json.loads(config_path.read_text())
        self.instance = config["instance"]
        self.token = config["token"]
        self.visibility = config.get("visibility", "public")
        
        self.client = httpx.Client(
            base_url=f"https://{self.instance}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    def publish(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Publish to Mastodon.
        
        Handles both single posts and threads (detected by [n/m] markers).
        """
        if self._is_thread(content):
            return self._publish_thread(content)
        else:
            return self._publish_single(content)
    
    def _is_thread(self, content: str) -> bool:
        return bool(re.search(r'\[\d+/\d+\]', content))
    
    def _publish_single(self, content: str) -> Dict:
        resp = self.client.post(
            "/api/v1/statuses",
            json={
                "status": content,
                "visibility": self.visibility
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "url": data["url"],
                "id": data["id"]
            }
        else:
            return {
                "success": False,
                "error": resp.text
            }
    
    def _publish_thread(self, content: str) -> Dict:
        """
        Publish thread by splitting on [n/m] markers and chaining replies.
        """
        posts = self._split_thread(content)
        urls = []
        in_reply_to = None
        
        for post_text in posts:
            resp = self.client.post(
                "/api/v1/statuses",
                json={
                    "status": post_text,
                    "visibility": self.visibility,
                    "in_reply_to_id": in_reply_to
                }
            )
            
            if resp.status_code != 200:
                return {"success": False, "error": f"Failed at post {len(urls)+1}: {resp.text}"}
            
            data = resp.json()
            in_reply_to = data["id"]
            urls.append(data["url"])
        
        return {
            "success": True,
            "url": urls[0],  # First post URL
            "thread_urls": urls
        }
    
    def _split_thread(self, content: str) -> List[str]:
        """Split content by [n/m] markers."""
        return re.split(r'\[\d+/\d+\]\s*', content)[1:]  # Skip empty first element
    
    def validate_config(self) -> bool:
        resp = self.client.get("/api/v1/accounts/verify_credentials")
        return resp.status_code == 200

4.4.3 Bluesky Publisher

Python

# ghostwriter/publisher/bluesky.py

import httpx
from typing import Dict, Optional
from pathlib import Path
import json
from datetime import datetime, timezone

class BlueskyPublisher(Publisher):
    BASE_URL = "https://bsky.social"
    
    def __init__(self, config_path: Path):
        config = json.loads(config_path.read_text())
        self.handle = config["handle"]
        self.password = config["password"]  # Use app password, not main password
        
        self.client = httpx.Client(base_url=self.BASE_URL)
        self.session = None
        self._authenticate()
    
    def _authenticate(self):
        """Create session with Bluesky."""
        resp = self.client.post(
            "/xrpc/com.atproto.server.createSession",
            json={
                "identifier": self.handle,
                "password": self.password
            }
        )
        
        if resp.status_code == 200:
            self.session = resp.json()
            self.client.headers["Authorization"] = f"Bearer {self.session['accessJwt']}"
        else:
            raise ValueError(f"Bluesky auth failed: {resp.text}")
    
    def publish(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Publish to Bluesky.
        
        Note: Bluesky has a 300 grapheme limit (not characters).
        This implementation uses naive character truncation; production
        should use proper grapheme counting.
        """
        # Truncate to 300 chars (naive; should be graphemes)
        text = content[:300]
        
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        resp = self.client.post(
            "/xrpc/com.atproto.repo.createRecord",
            json={
                "repo": self.session["did"],
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": now
                }
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            # Construct Bluesky web URL
            rkey = data["uri"].split("/")[-1]
            url = f"https://bsky.app/profile/{self.handle}/post/{rkey}"
            return {"success": True, "url": url, "uri": data["uri"]}
        else:
            return {"success": False, "error": resp.text}
    
    def validate_config(self) -> bool:
        return self.session is not None

4.4.4 File Publisher

Python

# ghostwriter/publisher/file.py

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

class FilePublisher(Publisher):
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def publish(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Save content to timestamped file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ghostwriter_{timestamp}.md"
        path = self.output_dir / filename
        
        path.write_text(content, encoding="utf-8")
        
        return {
            "success": True,
            "path": str(path)
        }
    
    def validate_config(self) -> bool:
        return self.output_dir.exists() and self.output_dir.is_dir()

4.4.5 Publisher Multiplexer

Python

# ghostwriter/publisher/multiplexer.py

from typing import List, Dict
from pathlib import Path
from ghostwriter.publisher.mastodon import MastodonPublisher
from ghostwriter.publisher.bluesky import BlueskyPublisher
from ghostwriter.publisher.file import FilePublisher

class PublisherMultiplexer:
    """
    Route publishing to one or more platforms.
    """
    
    def __init__(self):
        self.publishers = {}
        self._load_publishers()
    
    def _load_publishers(self):
        """Load configured publishers from ~/.ghostwriter/publishers/"""
        pub_dir = Path.home() / ".ghostwriter" / "publishers"
        
        if (pub_dir / "mastodon.json").exists():
            self.publishers["mastodon"] = MastodonPublisher(pub_dir / "mastodon.json")
        
        if (pub_dir / "bluesky.json").exists():
            self.publishers["bluesky"] = BlueskyPublisher(pub_dir / "bluesky.json")
    
    def publish(
        self,
        content: str,
        platforms: List[str],
        save_file: bool = False,
        output_dir: Path = None
    ) -> Dict[str, Dict]:
        """
        Publish to multiple platforms.
        
        Args:
            content: Content to publish
            platforms: List of platform names ("mastodon", "bluesky", etc.)
            save_file: Also save to file
            output_dir: Directory for file output
        
        Returns:
            {
                "mastodon": {"success": True, "url": "..."},
                "bluesky": {"success": False, "error": "..."},
                ...
            }
        """
        results = {}
        
        for platform in platforms:
            if platform not in self.publishers:
                results[platform] = {"success": False, "error": "Not configured"}
                continue
            
            results[platform] = self.publishers[platform].publish(content)
        
        if save_file:
            file_pub = FilePublisher(output_dir or Path.cwd())
            results["file"] = file_pub.publish(content)
        
        return results

4.5 Terminal User Interface (TUI)

Purpose: Interactive review interface using Textual framework. User can approve, regenerate, edit, or discard generated content.
4.5.1 Review Screen

Python

# ghostwriter/tui/review.py

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TextArea, Button, Static
from textual.containers import Container, Horizontal
from textual.binding import Binding

class ReviewApp(App):
    """
    Textual TUI for reviewing generated content.
    """
    
    CSS = """
    #content-area {
        height: 80%;
        border: solid green;
    }
    
    .button-bar {
        height: auto;
        align: center middle;
    }
    
    Button {
        margin: 1 2;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+a", "approve", "Approve & Publish"),
        Binding("ctrl+r", "regenerate", "Regenerate"),
        Binding("ctrl+q", "discard", "Discard"),
        Binding("ctrl+e", "edit", "Edit"),
    ]
    
    def __init__(self, initial_content: str):
        super().__init__()
        self.content = initial_content
        self.result = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield TextArea(
            self.content,
            id="content-area",
            language="markdown"
        )
        yield Horizontal(
            Button("✅ Approve & Publish", id="approve", variant="success"),
            Button("🔄 Regenerate", id="regenerate", variant="primary"),
            Button("✏️  Edit", id="edit"),
            Button("🗑️  Discard", id="discard", variant="error"),
            classes="button-bar"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.action_approve()
        elif event.button.id == "regenerate":
            self.action_regenerate()
        elif event.button.id == "edit":
            self.action_edit()
        elif event.button.id == "discard":
            self.action_discard()
    
    def action_approve(self):
        """User approved content."""
        text_area = self.query_one(TextArea)
        self.result = ("approved", text_area.text)
        self.exit()
    
    def action_regenerate(self):
        """User wants to regenerate."""
        self.result = ("regenerate", None)
        self.exit()
    
    def action_edit(self):
        """Switch TextArea to editable mode."""
        text_area = self.query_one(TextArea)
        text_area.read_only = False
        text_area.focus()
    
    def action_discard(self):
        """User discarded content."""
        self.result = ("discard", None)
        self.exit()

def review_content(content: str) -> tuple[str, str | None]:
    """
    Launch TUI review and return user decision.
    
    Returns:
        ("approved", final_text) | ("regenerate", None) | ("discard", None)
    """
    app = ReviewApp(content)
    app.run()
    return app.result

4.6 Ephemeral Data Eraser

Purpose: Securely wipe session data, temp files, and shell history references after each run.

Python

# ghostwriter/eraser/eraser.py

import os
import shutil
import secrets
from pathlib import Path
from typing import List

class Eraser:
    """
    Wipe ephemeral session data.
    
    Targets:
    - /tmp/ghostwriter_*
    - ~/.ghostwriter/sessions/
    - Shell history lines containing "ghostwriter"
    """
    
    TEMP_PATTERNS = ["/tmp/ghostwriter_*", "/var/tmp/ghostwriter_*"]
    SESSION_DIR = Path.home() / ".ghostwriter" / "sessions"
    SHELL_HISTORY_FILES = [
        Path.home() / ".bash_history",
        Path.home() / ".zsh_history",
        Path.home() / ".history"
    ]
    
    def wipe_session(self):
        """Execute full session wipe."""
        print("🧹 Wiping session data...")
        
        self._wipe_temp_dirs()
        self._wipe_session_dir()
        self._scrub_shell_history()
        self._sync_filesystem()
        
        print("✅ Session data wiped")
    
    def _wipe_temp_dirs(self):
        """Remove temp directories matching patterns."""
        for pattern in self.TEMP_PATTERNS:
            for path in Path("/tmp").glob("ghostwriter_*"):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    self._secure_delete(path)
    
    def _wipe_session_dir(self):
        """Clear session directory."""
        if self.SESSION_DIR.exists():
            for item in self.SESSION_DIR.iterdir():
                if item.is_file():
                    self._secure_delete(item)
    
    def _scrub_shell_history(self):
        """Remove lines containing 'ghostwriter' from shell history files."""
        for hist_file in self.SHELL_HISTORY_FILES:
            if not hist_file.exists():
                continue
            
            lines = hist_file.read_text().splitlines()
            cleaned = [line for line in lines if "ghostwriter" not in line.lower()]
            
            if len(cleaned) < len(lines):
                hist_file.write_text("\n".join(cleaned) + "\n")
    
    def _secure_delete(self, path: Path):
        """
        Overwrite file with random data before deletion.
        
        Note: This is NOT cryptographically secure on SSDs due to
        wear leveling, but it's better than nothing.
        """
        if not path.is_file():
            return
        
        size = path.stat().st_size
        
        # Overwrite 3 times with random data
        for _ in range(3):
            with path.open("wb") as f:
                f.write(secrets.token_bytes(size))
                f.flush()
                os.fsync(f.fileno())
        
        path.unlink()
    
    def _sync_filesystem(self):
        """Force filesystem sync (Unix only)."""
        try:
            os.sync()
        except AttributeError:
            pass  # Not available on Windows

4.7 Profile Management

Purpose: CLI commands to list, inspect, and delete voice profiles.

Python

# ghostwriter/cli/profiles.py

import typer
from rich.console import Console
from rich.table import Table
from ghostwriter.voice.profile import VoiceProfile

app = typer.Typer(name="profiles")
console = Console()

@app.command("list")
def list_profiles():
    """List all saved voice profiles."""
    profiles = VoiceProfile.list_all()
    
    if not profiles:
        console.print("[yellow]No profiles found.[/yellow]")
        console.print("Create one with: [bold]ghostwriter train <corpus_path> --profile <name>[/bold]")
        return
    
    table = Table(title="Voice Profiles")
    table.add_column("Name", style="cyan")
    table.add_column("Docs", justify="right")
    table.add_column("Words", justify="right")
    table.add_column("Tone")
    table.add_column("Created")
    
    for name in profiles:
        profile = VoiceProfile.load(name)
        table.add_row(
            name,
            str(profile.doc_count),
            str(profile.total_words),
            profile.tone,
            profile.created_at[:10]
        )
    
    console.print(table)

@app.command("show")
def show_profile(name: str):
    """Show detailed profile information."""
    try:
        profile = VoiceProfile.load(name)
    except FileNotFoundError:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]{profile.name}[/bold cyan]")
    console.print(f"Created: {profile.created_at}")
    console.print(f"Corpus: {profile.corpus_path}")
    console.print(f"\n📊 [bold]Statistics[/bold]")
    console.print(f"  Documents: {profile.doc_count}")
    console.print(f"  Total words: {profile.total_words}")
    console.print(f"  Avg sentence length: {profile.avg_sentence_length:.1f} words")
    console.print(f"  Avg word length: {profile.avg_word_length:.1f} chars")
    console.print(f"  Vocab richness: {profile.vocab_richness:.2%}")
    console.print(f"\n🎨 [bold]Voice Characteristics[/bold]")
    console.print(f"  Tone: {profile.tone}")
    console.print(f"  Themes: {', '.join(profile.themes)}")
    console.print(f"\n💬 [bold]System Prompt[/bold]")
    console.print(f"  {profile.system_prompt}")

@app.command("delete")
def delete_profile(
    name: str,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """Delete a voice profile."""
    if not confirm:
        proceed = typer.confirm(f"Delete profile '{name}'?")
        if not proceed:
            raise typer.Abort()
    
    path = Path.home() / ".ghostwriter" / "profiles" / f"{name}.json"
    if path.exists():
        path.unlink()
        console.print(f"[green]✓[/green] Deleted profile '{name}'")
    else:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        raise typer.Exit(1)

5. Data Models & Schemas
5.1 Voice Profile Schema

JSON

{
  "name": "my-blog",
  "avg_sentence_length": 18.7,
  "avg_word_length": 4.9,
  "vocab_richness": 0.42,
  "punctuation_style": {
    "ellipsis_rate": 0.3,
    "dash_rate": 1.2,
    "exclamation_rate": 0.1,
    "question_rate": 0.4
  },
  "doc_count": 87,
  "total_words": 45230,
  "tone": "analytical",
  "themes": ["machine learning", "software architecture", "privacy", "local-first"],
  "system_prompt": "You are writing as a technical blogger who explains complex topics clearly without dumbing them down. Your writing is precise, uses concrete examples, and favors clarity over cleverness. You avoid buzzwords and prefer plain technical language.",
  "sample_texts": [
    "The fundamental problem with cloud AI is...",
    "Local-first software means...",
    "..."
  ],
  "created_at": "2024-03-15T10:23:45Z",
  "corpus_path": "/Users/me/blog/posts"
}

5.2 Publisher Config Schema (Mastodon)

JSON

{
  "instance": "mastodon.social",
  "token": "your_access_token_here",
  "visibility": "public"
}

5.3 Publisher Config Schema (Bluesky)

JSON

{
  "handle": "yourhandle.bsky.social",
  "password": "your_app_password_here"
}

6. API Specifications (Internal)

GhostWriter is a CLI tool with no REST API. Internal "APIs" are Python class interfaces.
6.1 Voice Engine Interface

Python

class VoiceAnalyzer:
    def __init__(self, model: str = "mistral")
    def analyze(self, corpus_path: Path) -> VoiceProfile

6.2 Content Generator Interface

Python

class ContentGenerator:
    def __init__(self, profile: VoiceProfile, model: str = "llama3:8b")
    def generate(
        self,
        brief: str,
        format: str = "post",
        length: str = "medium",
        refine: bool = True
    ) -> Generator[str, None, None]

6.3 Publisher Interface

Python

class Publisher(ABC):
    @abstractmethod
    def publish(self, content: str, metadata: Optional[Dict] = None) -> Dict
    @abstractmethod
    def validate_config(self) -> bool

7. Directory Structure

text

ghostwriter/
├── ghostwriter/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py                 # Typer CLI entry point
│   │   ├── train.py                # Train command
│   │   ├── write.py                # Write command
│   │   ├── profiles.py             # Profile management commands
│   │   └── setup.py                # Publisher setup commands
│   │
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── loader.py               # Corpus loader
│   │   ├── analyzer.py             # Statistical analyzer
│   │   ├── llm_extractor.py        # LLM-based voice extraction
│   │   └── profile.py              # VoiceProfile model
│   │
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py       # Prompt construction
│   │   ├── ollama_client.py        # Ollama API client
│   │   ├── refiner.py              # Content refinement
│   │   └── generator.py            # Orchestrator
│   │
│   ├── publisher/
│   │   ├── __init__.py
│   │   ├── base.py                 # Publisher interface
│   │   ├── mastodon.py             # Mastodon publisher
│   │   ├── bluesky.py              # Bluesky publisher
│   │   ├── nostr.py                # Nostr publisher (future)
│   │   ├── file.py                 # File publisher
│   │   └── multiplexer.py          # Multi-platform router
│   │
│   ├── tui/
│   │   ├── __init__.py
│   │   └── review.py               # Textual review interface
│   │
│   ├── eraser/
│   │   ├── __init__.py
│   │   └── eraser.py               # Session data wiper
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py             # Config management
│
├── tests/
│   ├── test_voice/
│   ├── test_generator/
│   ├── test_publisher/
│   └── test_integration/
│
├── pyproject.toml
├── README.md
├── LICENSE
└── Makefile

# Runtime directories (created on first run)
~/.ghostwriter/
├── profiles/                       # Voice profiles (persistent)
│   ├── my-blog.json
│   └── tech-twitter.json
├── publishers/                     # Platform configs (persistent)
│   ├── mastodon.json
│   └── bluesky.json
└── sessions/                       # Ephemeral (wiped after each run)
    └── (temp files during generation)

8. Configuration System
8.1 Global Config File

toml

# ~/.ghostwriter/config.toml

[ollama]
base_url = "http://localhost:11434"
default_model = "llama3:8b"
timeout_seconds = 120

[generation]
default_format = "post"
default_length = "medium"
enable_refinement = true
stream_output = true

[publishing]
default_platforms = ["file"]        # Safe default
confirm_before_publish = true

[privacy]
auto_wipe_sessions = true
wipe_shell_history = true
store_sample_texts = true           # If false, profile won't save examples

[tui]
theme = "monokai"
line_numbers = true

8.2 Config Loader

Python

# ghostwriter/config/settings.py

from pathlib import Path
import toml
from typing import Dict

class Settings:
    DEFAULT_CONFIG = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "llama3:8b",
            "timeout_seconds": 120
        },
        "generation": {
            "default_format": "post",
            "default_length": "medium",
            "enable_refinement": True,
            "stream_output": True
        },
        "publishing": {
            "default_platforms": ["file"],
            "confirm_before_publish": True
        },
        "privacy": {
            "auto_wipe_sessions": True,
            "wipe_shell_history": True,
            "store_sample_texts": True
        },
        "tui": {
            "theme": "monokai",
            "line_numbers": True
        }
    }
    
    def __init__(self):
        self.config_path = Path.home() / ".ghostwriter" / "config.toml"
        self.config = self._load()
    
    def _load(self) -> Dict:
        if not self.config_path.exists():
            self._create_default()
        return toml.load(self.config_path)
    
    def _create_default(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w") as f:
            toml.dump(self.DEFAULT_CONFIG, f)
    
    def get(self, key: str, default=None):
        """Get nested config value by dot notation."""
        keys = key.split(".")
        value = self.config
        for k in keys:
            value = value.get(k, {})
        return value if value != {} else default

9. Voice Profile Deep Dive
9.1 Training Pipeline

text

Corpus Input → Corpus Loader → Statistical Analyzer → LLM Extractor → VoiceProfile

Step 1: Load Corpus

    Recursively find all .txt, .md, .rst files
    Read with UTF-8 (fallback to latin-1)
    Store as list of strings (one per file)

Step 2: Statistical Analysis

    Sentence splitting via regex [.!?]+
    Word tokenization via \b[a-z]+\b
    Compute averages and ratios

Step 3: LLM Voice Extraction

    Send first ~10 docs (truncated to 8k chars) to Ollama
    Request JSON with tone/themes/system_prompt
    Parse and validate response

Step 4: Save Profile

    Serialize as JSON to ~/.ghostwriter/profiles/<name>.json
    Include metadata: corpus path, timestamp

9.2 Privacy Considerations

What is stored in profiles:

    ✅ Statistical features (averages, ratios)
    ✅ LLM-extracted characteristics (tone, themes)
    ✅ System prompt
    ✅ First 500 chars of up to 5 sample docs (configurable)

What is NOT stored:

    ❌ Full corpus text
    ❌ Raw file paths beyond corpus root
    ❌ User's personal information

Risk: Sample texts could contain sensitive info. Users can disable via privacy.store_sample_texts = false in config.
10. Generation Strategy Deep Dive
10.1 Two-Pass Generation

Pass 1: Initial Draft

    Use voice profile's system_prompt
    Include few-shot examples from sample_texts
    Stream tokens to terminal for live feedback
    Temperature: 0.85 (creative but not chaotic)

Pass 2: Refinement (optional, enabled by default)

    Send draft + profile to refiner
    Explicit instruction: remove AI-isms, match rhythm
    Non-streaming (one-shot response)
    Temperature: 0.7 (more conservative)

10.2 Format-Specific Generation Rules
Format	Rules	Example Output
post	Max 500 chars, single cohesive post	Plain text block
thread	5-8 posts, each ≤280 chars, numbered [n/m]	[1/5] ... [2/5] ...
article	Sections with ## headers, intro + conclusion	Markdown with structure
email	Subject: line, greeting, professional tone	Email format
10.3 Length Guidance

    short: 200-400 words
    medium: 400-800 words
    long: 800-1500 words

Injected into prompt as natural language guidance; LLM interprets flexibly.
11. Publishing Integrations
11.1 Mastodon API Integration

Authentication: OAuth2 Bearer token (stored in ~/.ghostwriter/publishers/mastodon.json)

Endpoints Used:

    POST /api/v1/statuses — Create status (post)
        Body: {"status": "...", "visibility": "public"|"unlisted"|"private", "in_reply_to_id": "..." (for threads)}

Thread Handling:

    Split content by [n/m] markers
    Post first with no in_reply_to_id
    Subsequent posts reference previous id

Rate Limits: Mastodon instances vary; default is ~300 posts/5 min. Publisher should respect X-RateLimit-* headers.
11.2 Bluesky (AT Protocol) Integration

Authentication: Session-based (email/password or app password)

Endpoints Used:

    POST /xrpc/com.atproto.server.createSession
        Body: {"identifier": "handle", "password": "..."}
        Returns: {"accessJwt": "...", "refreshJwt": "...", "did": "..."}
    POST /xrpc/com.atproto.repo.createRecord
        Body: {"repo": "<did>", "collection": "app.bsky.feed.post", "record": {...}}

Post Schema:

JSON

{
  "$type": "app.bsky.feed.post",
  "text": "Content here (max 300 graphemes)",
  "createdAt": "2024-03-15T10:30:00Z"
}

Limitations:

    300 grapheme limit (not characters)
    No native threading (yet); multiple posts are independent

11.3 Nostr Integration (Future)

Protocol: Nostr Event Protocol (kind 1 for text notes)

Implementation Plan:

    Use python-nostr library
    Generate ephemeral keypair or load from config
    Publish events to multiple relays
    Store relay URLs in config

12. Privacy & Erasure Model
12.1 What is Ephemeral vs. Persistent
Data Type	Lifetime	Storage Location	Wiped?
Voice profiles	Persistent	~/.ghostwriter/profiles/	No
Publisher configs	Persistent	~/.ghostwriter/publishers/	No
Generation drafts	Ephemeral	~/.ghostwriter/sessions/	Yes
Temp Ollama outputs	Ephemeral	/tmp/ghostwriter_*	Yes
Shell history refs	Ephemeral	~/.bash_history, etc.	Yes
12.2 Secure Deletion Strategy

Method: 3-pass overwrite with random bytes + fsync + unlink

Limitations:

    ⚠️ Not effective on SSDs due to wear leveling, overprovisioning, and FTL remapping
    ✅ Effective on HDDs and in-memory filesystems
    ✅ Better than nothing as a defense-in-depth measure

NIST Guidance: For SSDs, physical destruction or ATA Secure Erase is the only reliable method. Software overwriting provides minimal confidentiality protection.

GhostWriter Approach:

    Overwrite anyway (catches HDD users, limits casual forensics)
    Document limitations clearly
    Recommend full-disk encryption (LUKS/FileVault/BitLocker) as additional layer

12.3 Shell History Scrubbing

Target Files:

    ~/.bash_history
    ~/.zsh_history
    ~/.history

Method:

    Read entire file
    Filter out lines containing "ghostwriter"
    Overwrite original file

Limitations:

    Doesn't catch terminal scrollback buffers
    Doesn't catch tmux/screen buffers
    Doesn't catch in-memory history (until shell exits)

13. TUI Implementation Details
13.1 Textual Framework

Why Textual:

    Modern terminal UI framework (Python)
    Rich widget library (TextArea, Button, Tables)
    CSS-like styling
    Keyboard bindings
    Active development

13.2 Review Workflow

text

Generated Content
      │
      ▼
┌─────────────────┐
│ TextArea        │  (Read-only initially)
│ (Markdown)      │
└────────┬────────┘
         │
    User presses:
         │
    ┌────┼────┬────┬─────┐
    │    │    │    │     │
    ▼    ▼    ▼    ▼     ▼
  Approve Edit Regen Discard
    │    │    │    │
    │    │    │    └─→ Exit with ("discard", None)
    │    │    └──────→ Exit with ("regenerate", None)
    │    └───────────→ Switch TextArea to editable, stay in loop
    └────────────────→ Exit with ("approved", final_text)

13.3 Keyboard Shortcuts
Key	Action
Ctrl+A	Approve & Publish
Ctrl+R	Regenerate
Ctrl+E	Edit (enable editing)
Ctrl+Q	Discard
14. Platform Support Matrix
Platform	Supported	Notes
macOS	✅	Primary development platform
Linux	✅	Debian/Ubuntu/Fedora/Arch tested
Windows	⚠️	Via WSL2 (native Windows support possible but not prioritized)
BSD	🔶	Should work; untested
14.1 Dependencies by Platform
Dependency	macOS	Linux	Windows (WSL2)
Python 3.10+	Homebrew or system	System package manager	WSL apt
Ollama	brew install ollama	Download from ollama.ai	WSL or Windows native
Terminal emulator	iTerm2/Terminal.app	Any modern terminal	Windows Terminal (recommended)
15. Security Model & Threat Boundaries
15.1 Trust Zones

text

┌────────────────────────────────────┐
│  FULLY TRUSTED (user's machine)    │
│  - Python interpreter              │
│  - Ollama service                  │
│  - Local filesystem                │
│  - Voice profiles                  │
│  - Publisher configs               │
└────────────────┬───────────────────┘
                 │
┌────────────────▼───────────────────┐
│  SEMI-TRUSTED (platform APIs)      │
│  - Mastodon instance               │
│  - Bluesky PDS                     │
│  - Nostr relays                    │
└────────────────┬───────────────────┘
                 │
┌────────────────▼───────────────────┐
│  UNTRUSTED (public internet)       │
│  - Network eavesdroppers           │
│  - Malicious relays/servers        │
└────────────────────────────────────┘

15.2 Threat Model
Threat	Mitigation
Credential theft from config files	File permissions 0600, recommend OS keychain integration (future)
Corpus text exposure	Profiles store limited samples; full corpus never transmitted
Session data recovery	3-pass secure deletion + shell history scrubbing
Ollama prompt injection	User controls corpus; trust boundary at user input
Platform API MitM	HTTPS for all API calls
Malicious platform stealing content	User chooses platforms; no automatic publishing
15.3 Credentials Storage

Current (v1.0): JSON files with 0600 permissions

Future (v1.1+):

    macOS: keyring library → macOS Keychain
    Linux: keyring → Secret Service API / KWallet / gnome-keyring
    Windows: keyring → Windows Credential Locker

16. Storage & Persistence
16.1 Storage Breakdown
Data	Format	Location	Size (typical)
Voice profiles	JSON	~/.ghostwriter/profiles/	10-50 KB each
Publisher configs	JSON	~/.ghostwriter/publishers/	1-2 KB each
Global config	TOML	~/.ghostwriter/config.toml	2 KB
Session temp files	Various	~/.ghostwriter/sessions/	50-500 KB (ephemeral)
16.2 No Database

GhostWriter intentionally avoids a database. All persistence is file-based (JSON/TOML).

Rationale:

    Simplicity: No schema migrations, no SQLite dependency
    Transparency: Users can inspect/edit JSON files directly
    Portability: Easy to backup (cp -r ~/.ghostwriter ~/Backup/)

17. Logging & Observability
17.1 Logging Strategy

Python

# ghostwriter/logger.py

import logging
from pathlib import Path

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s"
    ))
    logger.addHandler(console)
    
    # Optional file handler
    log_dir = Path.home() / ".ghostwriter" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "ghostwriter.log")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(file_handler)
    
    return logger

17.2 What is Logged
Event	Level	Example
CLI command invoked	INFO	ghostwriter train ~/blog --profile my-blog
Profile loaded	DEBUG	Loaded profile 'my-blog' with 87 docs
Ollama generation start	INFO	Generating content with llama3:8b...
Content approved	INFO	User approved content for publishing
Publish success	INFO	Published to mastodon: https://...
Publish failure	ERROR	Bluesky publish failed: 401 Unauthorized
Session wipe	INFO	Session data wiped
17.3 Privacy in Logs

What is NOT logged:

    Full generated content text
    User's corpus content
    API credentials
    Shell commands containing secrets

18. Testing Strategy
18.1 Test Pyramid

text

                  ┌──────────┐
                  │   E2E    │  (5%)
                  │  (CLI)   │
                  └────┬─────┘
              ┌────────┴────────┐
              │  Integration    │  (25%)
              │  (Voice+Gen)    │
              └────────┬────────┘
          ┌────────────┴────────────┐
          │      Unit Tests         │  (70%)
          │  (Analyzers, Builders)  │
          └─────────────────────────┘

18.2 Unit Tests

Python

# tests/test_voice/test_analyzer.py

import pytest
from ghostwriter.voice.analyzer import StatisticalAnalyzer

def test_sentence_splitting():
    analyzer = StatisticalAnalyzer()
    text = "This is a sentence. This is another! And a question?"
    sentences = analyzer._split_sentences(text)
    assert len(sentences) == 4  # Including empty trailing

def test_vocab_richness():
    analyzer = StatisticalAnalyzer()
    docs = ["the cat sat on the mat", "the dog ran"]
    stats = analyzer.analyze(docs)
    
    # Total words: 8, unique: 8
    # Richness = 8/8 = 1.0
    assert stats["vocab_richness"] == pytest.approx(0.8, abs=0.1)

18.3 Integration Tests

Python

# tests/test_integration/test_train_and_generate.py

import pytest
from pathlib import Path
from ghostwriter.voice.analyzer import VoiceAnalyzer
from ghostwriter.generator.generator import ContentGenerator

@pytest.fixture
def sample_corpus(tmp_path):
    """Create temporary corpus."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    
    (corpus_dir / "post1.txt").write_text("This is my first post about AI.")
    (corpus_dir / "post2.txt").write_text("Another post discussing local-first software.")
    
    return corpus_dir

def test_full_pipeline(sample_corpus):
    """Train profile and generate content."""
    # Train
    analyzer = VoiceAnalyzer(model="mistral")
    profile = analyzer.analyze(sample_corpus)
    
    assert profile.doc_count == 2
    assert profile.tone is not None
    
    # Generate
    generator = ContentGenerator(profile, model="llama3:8b")
    content = ""
    for token in generator.generate(
        brief="Write about privacy",
        format="post",
        length="short"
    ):
        content += token
    
    assert len(content) > 0
    assert len(content) < 600  # Respects short length + post format

18.4 Mocking Ollama in Tests

Python

# tests/conftest.py

import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_ollama_client(monkeypatch):
    """Mock Ollama client to avoid network calls in tests."""
    mock = Mock()
    mock.generate.return_value = {
        "response": '{"tone": "analytical", "themes": ["AI", "privacy"], "system_prompt": "Test prompt"}'
    }
    mock.chat.return_value = {
        "message": {"content": "Generated test content"}
    }
    
    monkeypatch.setattr("ghostwriter.generator.ollama_client.Client", lambda **kwargs: mock)
    return mock

19. Build, Packaging & Installation
19.1 Pyproject.toml

toml

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ghostwriter-cli"
version = "1.0.0"
description = "Local-first AI writing assistant with voice cloning"
authors = [{name = "Your Name", email = "you@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.10"
dependencies = [
    "typer[all] >=0.9.0",
    "ollama >=0.1.0",
    "textual >=0.50.0",
    "pydantic >=2.0.0",
    "httpx >=0.25.0",
    "rich >=13.0.0",
    "toml >=0.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest >=7.0.0",
    "pytest-cov",
    "black",
    "mypy",
    "ruff"
]

[project.scripts]
ghostwriter = "ghostwriter.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["ghostwriter"]

19.2 Installation Methods

Method 1: pipx (recommended for users)

Bash

pipx install ghostwriter-cli

Method 2: pip

Bash

pip install --user ghostwriter-cli

Method 3: From source

Bash

git clone https://github.com/yourorg/ghostwriter-cli.git
cd ghostwriter-cli
pip install -e .

19.3 First-Time Setup

Bash

# 1. Install Ollama
curl https://ollama.ai/install.sh | sh

# 2. Pull required models
ollama pull llama3:8b
ollama pull mistral

# 3. Start Ollama service
ollama serve  # Or `systemctl start ollama` on Linux

# 4. Install GhostWriter
pipx install ghostwriter-cli

# 5. Create first profile
ghostwriter train ~/my-blog/ --profile blog-voice

# 6. Write something
ghostwriter write "why local AI matters" --profile blog-voice

20. Performance Targets & Benchmarks
Operation	Target	Measurement Method
Corpus loading (100 files)	< 5 seconds	time ghostwriter train ...
Voice analysis (100 docs)	< 60 seconds	End-to-end train command
LLM voice extraction	< 30 seconds	Ollama API call latency
Content generation (post)	< 15 seconds	Time to first complete draft
Content refinement	< 10 seconds	Second-pass LLM call
TUI launch	< 1 second	Textual app initialization
Session wipe	< 5 seconds	Full erasure of temp + history
Profile save/load	< 100ms	JSON serialization
20.1 Ollama Performance Variables
Factor	Impact
Model size	Llama3 70B: ~30s, Mistral 7B: ~5s
Hardware	GPU (M1/M2/NVIDIA): 3-10x faster than CPU
Context length	8k context: 2x slower than 2k
Concurrency	Single-threaded; Ollama handles queue
21. Error Handling Strategy
21.1 Error Categories

Python

# ghostwriter/errors.py

class GhostWriterError(Exception):
    """Base exception for GhostWriter."""
    pass

class CorpusLoadError(GhostWriterError):
    """Failed to load corpus."""
    pass

class ProfileNotFoundError(GhostWriterError):
    """Profile doesn't exist."""
    pass

class OllamaConnectionError(GhostWriterError):
    """Cannot connect to Ollama."""
    pass

class PublishError(GhostWriterError):
    """Publishing failed."""
    pass

21.2 Error Handling Policy

Corpus Loading:

    Skip unreadable files (log warning)
    Continue with remaining files
    Fail if zero files loaded

Voice Analysis:

    If LLM extraction fails → retry once
    If still fails → use fallback defaults (tone="neutral", themes=[])

Generation:

    If Ollama unreachable → clear error message + check instructions
    If generation times out (>120s) → retry with shorter context

Publishing:

    If API call fails → log error, do NOT wipe session
    User can retry manually

Session Wipe:

    Best-effort; never fail the whole command
    Log warnings for any files that couldn't be deleted

22. Dependency Registry
22.1 Python Dependencies

toml

# Core dependencies
typer = ">=0.9.0"              # CLI framework
ollama = ">=0.1.0"             # Ollama Python client
textual = ">=0.50.0"           # TUI framework
pydantic = ">=2.0.0"           # Data validation
httpx = ">=0.25.0"             # HTTP client (for publishers)
rich = ">=13.0.0"              # Terminal formatting
toml = ">=0.10.0"              # Config file parsing

# Dev dependencies
pytest = ">=7.0.0"
pytest-cov
black                          # Code formatter
mypy                           # Type checker
ruff                           # Linter

22.2 External Tools Required
Tool	Version	Required For	Install
Ollama	Latest	LLM inference	curl https://ollama.ai/install.sh | sh
Python	>=3.10	Runtime	System package manager
22.3 Optional Tools

    pipx: Isolated Python app installer (recommended)
    bat: Better cat for viewing profiles (cosmetic)

23. Milestone & Phased Rollout Plan
Phase 1 — Foundation (Weeks 1-4)

Goal: Working train + generate + review workflow

    ✅ Project structure & pyproject.toml
    ✅ Corpus loader (txt/md/rst)
    ✅ Statistical analyzer
    ✅ LLM voice extractor (Ollama integration)
    ✅ VoiceProfile model (Pydantic + JSON save/load)
    ✅ CLI train command
    ✅ Prompt builder (system + user prompts)
    ✅ Ollama client (streaming generation)
    ✅ CLI write command
    ✅ Textual TUI review screen
    ✅ File publisher (save to local file)
    ✅ Unit tests for voice + generator
    ✅ README with quickstart

Deliverable: ghostwriter train + ghostwriter write working end-to-end with file output.
Phase 2 — Publishing (Weeks 5-8)

Goal: Multi-platform publishing

    ✅ Publisher base interface
    ✅ Mastodon publisher (single post + threads)
    ✅ Bluesky publisher (AT Protocol)
    ✅ Publisher multiplexer
    ✅ CLI setup mastodon command
    ✅ CLI setup bluesky command
    ✅ Secure config storage (0600 permissions)
    ✅ Publish confirmation prompt
    ✅ Integration tests for publishers (with mocks)
    ✅ Error handling for API failures

Deliverable: Users can publish to Mastodon and Bluesky from TUI.
Phase 3 — Privacy & Refinement (Weeks 9-12)

Goal: Ephemeral data wiping + content refinement

    ✅ Ephemeral Eraser (temp files + shell history)
    ✅ Secure deletion (3-pass overwrite)
    ✅ Auto-wipe on command completion
    ✅ Content refiner (second-pass LLM)
    ✅ Profile management CLI (ghostwriter profiles list/show/delete)
    ✅ Global config system (TOML)
    ✅ Privacy config options (disable sample storage)
    ✅ Documentation on security model
    ✅ End-to-end tests

Deliverable: Privacy-preserving version with automatic cleanup.
Phase 4 — Polish & Distribution (Weeks 13-16)

Goal: Production-ready release

    ✅ Nostr publisher (basic)
    ✅ Keyring integration for credentials (macOS/Linux)
    ✅ Comprehensive CLI help text
    ✅ Error messages UX review
    ✅ Performance benchmarking
    ✅ Optimize Ollama prompts
    ✅ PyPI packaging
    ✅ Homebrew formula (macOS)
    ✅ AUR package (Arch Linux)
    ✅ Full documentation site (MkDocs)
    ✅ Video quickstart tutorial
    ✅ 80% test coverage target

Deliverable: v1.0 release on PyPI + package managers.
24. Open Questions & Future Work
24.1 Open Technical Questions
Question	Status	Notes
Grapheme counting for Bluesky	Open	Need proper Unicode grapheme library
Ollama model auto-download	Open	Should CLI auto-pull missing models?
Profile versioning	Open	Migrate profiles when voice engine changes?
Multi-user support	Backlog	Separate profiles per OS user account
Voice profile compression	Backlog	Profiles could be smaller with embeddings instead of samples
24.2 Potential Future Features
Feature	Description	Priority
Voice fine-tuning	Actual model fine-tuning (LoRA) instead of prompt engineering	Medium
Image generation	Generate cover images via Stable Diffusion	Low
Scheduled posting	Cron-like scheduled publish	Medium
Analytics dashboard	Track post performance (external API integration)	Low
Nostr NIP-07 support	Browser extension integration for Nostr	Medium
Telegram/Discord publishing	Additional platforms	Low
Voice merging	Combine multiple profiles into hybrid voice	Low
Interactive editing	Real-time collaborative editing in TUI	Low
Spell/grammar checking	Integrate LanguageTool or similar	Medium
24.3 Known Limitations at v1.0

    ⚠️ Bluesky threads: No native threading support; each post is independent
    ⚠️ SSD secure deletion: Not cryptographically secure due to hardware limitations
    ⚠️ Grapheme counting: Naive character counting for Bluesky (should be graphemes)
    ⚠️ Windows native: Requires WSL2; native Windows support is untested
    ⚠️ Ollama required: No cloud LLM fallback option
    ⚠️ No spell check: Users must run external tools
    ⚠️ Single-language: Prompts and CLI are English-only (i18n not implemented)

End of GhostWriter CLI Comprehensive Design Document — v1.0

This document covers the complete architecture, implementation details, and build plan for GhostWriter CLI, a local-first AI writing assistant with voice cloning, multi-platform publishing, and privacy-first ephemeral data handling. All processing happens on the user's machine via Ollama. No cloud dependencies, no telemetry, no third-party AI APIs.
