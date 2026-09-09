# 🤖 MitroAgents — Autonomous Social Media Distribution & Intelligence Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Strands Agents SDK](https://img.shields.io/badge/SDK-Strands%20Agents-purple.svg)](https://github.com/Kuahsaltalks/mitroagents)

**MitroAgents** is an autonomous AI agent pipeline that transforms raw dictated thoughts, streams of consciousness, voice notes, and shared breaking links into high-converting, platform-tailored content across **6 major distribution channels**—with **strict, non-negotiable character limit enforcement** and 1-tap live publishing.

---

## ⚡ Key Capabilities

1. **Autonomous Multi-Platform Distribution**:
   - **X / Twitter**: Hard ceiling $\le 280$ characters, pattern interrupts, and single intelligent quote-tweets.
   - **Meta Threads**: Hard ceiling $\le 500$ characters, authentic conversational tone.
   - **LinkedIn Storytelling**: Hard ceiling $\le 3,000$ characters (5-beat storytelling format: personal friction, stakes, pivot, takeaway).
   - **Carousel Slide Decks**: 5 to 7 slides, strictly $\le 220$ characters per slide with auto-rendered 1080x1350 visual cards & combined PDF.
   - **Substack Notes**: Live automated browser posting via Playwright directly in your running Chrome session.
   - **Substack Newsletter**: Full deep-dive article generation with subject line, subtitle, and markdown body.
   - **Hero Hook Image Generator**: 1080x1350 4:5 image with dynamic bottom gradient, bold typography, subtle watermarks, and face/news subject integration.

2. **Strands Agents SDK Integration (`strands_agent.py`)**:
   - Native integration with the **Strands Agents SDK** using the `@tool` decorator pattern.
   - Autonomous agent reasoning over `format_and_validate_post`, `generate_full_social_package`, `generate_quote_tweet`, and `dispatch_to_channels`.

3. **Telegram Bot Remote Command Center (`./run.py --bot`)**:
   - Dictate thoughts via voice notes while walking or thinking—transcribed directly via Gemini Flash Audio API.
   - Send any breaking link or tweet for an authentic, human-intelligence quote tweet on X.
   - 1-tap interactive inline buttons to publish directly to Buffer or open Substack.

4. **Zero-Overage Validator (`src/validator.py`)**:
   - Non-negotiable limit enforcement. If any model exceeds a platform ceiling, the strict engine cleans and trims at natural sentence/word boundaries.

5. **Modular Training Architecture (`rules/`, `skills/`, `learnings/`)**:
   - `rules/`: Exact platform constraints (`platform_limits.json`), hook psychology formulas (`hooks_and_triggers.md`), and narrative requirements.
   - `skills/`: Platform-specific prompt recipes for X, Threads, LinkedIn, Carousels, and Substack.
   - `learnings/`: Personal voice guidelines (`user_voice_profile.md`), anti-patterns (`anti_patterns.md`), and winning post benchmarks (`successful_posts.md`).

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/Kuahsaltalks/mitroagents.git
cd mitroagents

# Install dependencies using uv
uv venv
uv pip install -e .

# Configure API Keys
cp .env.example .env
```

Edit `.env` and set your credentials:
```env
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
BUFFER_API_KEY=your_buffer_personal_api_key
```

---

## 🤖 Running MitroAgents

### 1. Run the Telegram Bot Daemon
```bash
./run.py --bot
```
Now send voice notes, brain dumps, or tweet links straight from your phone!

### 2. Run the Strands Autonomous Agent
```bash
python strands_agent.py "Why friction and unpolished authenticity beats 4K corporate polish on social media."
```

### 3. Interactive CLI Generation
```bash
./run.py
```

### 4. Single-Thought Generation
```bash
./run.py --thought "I've been thinking about why early startups fail to get traction."
```

### 5. Automated 1-Tap Publishing
```bash
# Publish batch to Buffer (X, Threads, LinkedIn)
./run.py --post-buffer outputs/latest_batch/

# Publish Substack Article in Active Chrome
./run.py --post-substack outputs/latest_batch/
```

---

## 📁 Repository Architecture

```
mitroagents/
├── strands_agent.py                 # Strands Agents SDK autonomous agent
├── pyproject.toml                   # Project dependencies and packaging
├── run.py                           # Root entrypoint CLI runner
├── LICENSE                          # MIT License
├── rules/                           # Strict platform limits & storytelling rules
│   ├── platform_limits.json         # Exact platform constraints
│   ├── platform_limits.md           # Documentation of character ceilings
│   ├── hooks_and_triggers.md        # Hook engineering formulas
│   └── linkedin_storytelling.md     # Narrative frameworks
├── skills/                          # Prompt skills per platform
│   ├── x_crafting.md                # 280-char X crafting skill
│   ├── threads_crafting.md          # 500-char Threads skill
│   ├── linkedin_storytelling.md     # 3,000-char LinkedIn storytelling
│   ├── carousel_builder.md          # Slide-by-slide carousel skill
│   ├── substack_notes.md            # Substack Notes short-form skill
│   └── substack_essay.md            # Long-form newsletter essay skill
├── learnings/                       # Persona memory & voice training
│   ├── user_voice_profile.md        # Tone, voice, zero-contraction rules
│   ├── anti_patterns.md             # What NOT to do
│   └── successful_posts.md          # Benchmark top performers
├── src/                             # Core engine modules
│   ├── engine.py                    # Multi-platform generation & link quote engine
│   ├── validator.py                 # Strict character limit counter & trimmer
│   ├── telegram_bot.py              # Telegram bot remote daemon
│   ├── buffer_publisher.py          # Buffer API publisher (with media uploads)
│   ├── hero_image_generator.py      # 1080x1350 Hero Hook image generator
│   ├── carousel_renderer.py         # 1080x1350 slide cards & PDF compiler
│   ├── substack_poster.py           # Playwright active Chrome browser automation
│   ├── config.py                    # Environment & config loader
│   └── cli.py                       # Rich terminal interface
└── tests/
    └── test_validator.py            # Automated tests for strict limit enforcement
```

---

## 🧪 Testing the Validator
Run the automated test suite to ensure strict character counts and boundary trim logic never fail:

```bash
python3 -m unittest tests/test_validator.py
```

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
