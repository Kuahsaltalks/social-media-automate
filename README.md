# Social Media Automation Engine (Gemini 3.8 / Flash)

An automated social media engine that turns your raw, dictated thoughts, streams of consciousness, or research notes into high-converting, platform-tailored content across **5 major platforms**—with **strict, non-negotiable character limit enforcement** (never exceeding by even 1 character).

---

## ⚡ Key Features

1. **Strict Character Limit Enforcement**:
   - **X (Twitter - Free Tier)**: Hard ceiling $\le 280$ characters.
   - **Meta Threads**: Hard ceiling $\le 500$ characters.
   - **LinkedIn**: Hard ceiling $\le 3,000$ characters (5-beat storytelling format, real-life relatable friction, tension, and clear payoff).
   - **Carousel Slide Deck**: 5 to 7 slides, strictly $\le 220$ characters per slide with visual design prompts.
   - **Substack Newsletter**: Deep-dive newsletter edition with subject line, preview subtitle, core thesis, and 3 key takeaways.
   - **Zero-Overage Validator**: Every post is automatically counted and validated against the ceiling. If the AI exceeds by even 1 character, the strict engine cleans and trims at natural sentence/word boundaries.

2. **Modular Training Architecture (`rules/`, `skills/`, `learnings/`)**:
   - `rules/`: Houses hard platform limits (`platform_limits.json`), hook psychology formulas (`hooks_and_triggers.md`), and narrative requirements (`linkedin_storytelling.md`).
   - `skills/`: Platform-specific prompt recipes for X, Threads, LinkedIn, Carousels, and Substack.
   - `learnings/`: Train the model on your personal voice (`user_voice_profile.md`), what NOT to do (`anti_patterns.md`), and your top-performing posts (`successful_posts.md`).

3. **Future-Ready GitHub Automated Publishing**:
   - Includes `src/publisher_stub.py` and `.github/workflows/social_publish.yml` for automated Git-backed publishing.

---

## 🚀 Quick Start

### 1. Environment Setup
The project uses `uv` for fast package management:

```bash
# Setup environment and install dependencies
uv venv
uv pip install google-genai python-dotenv pydantic rich

# Copy and configure your Gemini API Key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

### 2. Generate Content from Your Dictated Thoughts

#### Option A: Interactive Dictation Mode
Run without arguments, paste your voice transcript or stream of consciousness, and press `Ctrl+D`:
```bash
./run.py
```

#### Option B: Direct Command Line Argument
```bash
./run.py --thought "I've been thinking about why early startups fail to get traction. They spend 6 months polishing code and 0 days talking to real users in the wild."
```

#### Option C: Pass a File with Notes / Dictation
```bash
./run.py --file path/to/my_research.md
```

#### Option D: Specify Custom Gemini Model
```bash
./run.py --model gemini-2.5-flash --thought "..."
```

---

## 📡 Automated Publishing (Buffer & Substack)

### 1. Free Posting to X, LinkedIn, & Threads (via Buffer API)
Buffer's free plan allows up to 3 channels (e.g. X, LinkedIn, Threads) with zero developer app fees.
1. Get your free Personal API key at: [publish.buffer.com/settings/api](https://publish.buffer.com/settings/api)
2. Add it to `.env`:
   ```bash
   BUFFER_API_KEY=your_key_here
   ```
3. Check your connected channels:
   ```bash
   ./run.py --check-buffer
   ```
4. Dispatch any generated batch directly to Buffer:
   ```bash
   ./run.py --post-buffer outputs/20260906_walking_and_writing/
   ```

### 2. Substack Automated Drafts (via Browser Automation)
Substack drafts are automated via Playwright without needing API keys.
1. **One-Time Login**:
   ```bash
   ./run.py --substack-login
   ```
   A browser opens. Log into your Substack account once. Your session will be safely remembered.
2. **Auto-Create Draft**:
   ```bash
   ./run.py --post-substack outputs/20260906_walking_and_writing/
   ```
   The browser will open, populate the Title, Subtitle, and Body, and save the draft ready for your review!


---

## 📁 Project Structure

```
Social media automate/
├── .env.example                     # Environment template (GEMINI_API_KEY, Model choice)
├── pyproject.toml                   # Project dependencies and metadata
├── run.py                           # Convenient 1-line root runner
├── rules/                           # Strict guidelines, limits & safety checks
│   ├── platform_limits.json         # Machine-readable exact platform constraints
│   ├── platform_limits.md           # Documentation of character ceilings
│   ├── hooks_and_triggers.md        # Hook engineering (curiosity gap, emotional, contrarian/ragebait)
│   └── linkedin_storytelling.md     # Narrative frameworks (relatable experience, tension, resolution)
├── skills/                          # Prompt skills for each platform
│   ├── x_crafting.md                # 280-character post crafting skill
│   ├── threads_crafting.md          # 500-character conversational post skill
│   ├── linkedin_storytelling.md     # 3,000-character story post skill
│   ├── carousel_builder.md          # Slide-by-slide hook-to-CTA carousel skill
│   └── substack_essay.md            # Long-form newsletter essay skill
├── learnings/                       # Training memory & feedback loop
│   ├── user_voice_profile.md        # Tone, slang, style preferences, what to follow
│   ├── anti_patterns.md             # What NOT to do (cringe corporate jargon, emoji spam)
│   └── successful_posts.md          # Benchmark high-performing posts
├── src/                             # Core Python engine
│   ├── __init__.py
│   ├── config.py                    # Loader for rules, skills, learnings, and env
│   ├── validator.py                 # Strict character counter & trimmer
│   ├── engine.py                    # Gemini client & prompt orchestrator
│   ├── publisher_stub.py            # Future GitHub Actions publisher
│   └── cli.py                       # Rich terminal interface
├── tests/
│   └── test_validator.py            # Automated tests for strict limit enforcement
├── outputs/                         # Output batches (JSON + Markdown)
└── .github/workflows/
    └── social_publish.yml           # Automated GitHub publishing workflow
```

---

## 🎯 How to Train and Customize the Engine

1. **Change Your Tone / Slang**:
   Edit `learnings/user_voice_profile.md` with words, catchphrases, or stylistic preferences you want the engine to use.
2. **Ban Annoying Phrases or Habits**:
   Add unwanted corporate buzzwords or emoji habits into `learnings/anti_patterns.md`.
3. **Add Winning Posts (Few-Shot Training)**:
   Whenever you have a post that gets great engagement, paste it into `learnings/successful_posts.md`. The engine reads this file on every run to emulate your top performers.
4. **Adjust Platform Limits**:
   Edit `rules/platform_limits.json` if you ever upgrade account tiers or want tighter constraints.

---

## 🧪 Testing the Validator
Run the automated test suite to ensure the strict character counter and boundary trim logic never fail:

```bash
python3 -m unittest tests/test_validator.py
```
