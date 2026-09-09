"""Core content generation engine powered by Gemini and rule enforcement."""
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .config import load_system_knowledge, get_env_config, OUTPUTS_DIR
from .validator import (
    validate_post_length,
    validate_carousel_slides,
    enforce_strict_trim,
    DEFAULT_LIMITS
)

class SocialMediaEngine:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        cfg = get_env_config()
        self.api_key = api_key or cfg["api_key"]
        self.model = model or cfg["model"]
        self.knowledge = load_system_knowledge()
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Could not initialize google.genai Client: {e}")

    def build_system_prompt(self) -> str:
        """Compose the comprehensive prompt injecting rules, skills, and learnings."""
        prompt = f"""You are an elite, multi-platform social media ghostwriter and strategic growth operator.
Your task is to take the user's raw dictated thoughts, unstructured stream of consciousness, or research notes, and transform them into viral, high-engagement content for 5 platforms simultaneously.

### ABSOLUTE HARD CONSTRAINTS (ZERO TOLERANCE FOR OVERAGE):
1. **X (Twitter) Post**:
   - HARD LIMIT: Maximum 280 characters.
   - You MUST ensure len(post) <= 280. Aim for 240-270 characters.
   - Never exceed 280 characters by even 1 single character.

2. **Threads Post**:
   - HARD LIMIT: Maximum 500 characters.
   - Casual, conversational, relatable pattern interrupt.
   - len(post) <= 500 characters.

3. **LinkedIn Post**:
   - HARD LIMIT: Maximum 3,000 characters. Target 1,400 - 2,500 characters.
   - Must adhere to the 5-Beat Narrative Arc:
     * Beat 1 (Lines 1-2): Irresistible hook that forces clicking "...see more".
     * Beat 2: Grounded in a real-life experience, workplace conflict, or raw failure.
     * Beat 3: The pivot / turning point realization.
     * Beat 4: Actionable bulleted lessons / framework.
     * Beat 5: High-resonance closing thought and genuine discussion question.
   - Mobile-first formatting: 1-2 sentence paragraphs with whitespace.

4. **Carousel Content**:
   - 5 to 7 slides total.
   - STRICT LIMIT: Maximum 220 characters of copy per slide!
   - Slide 1 must be a scroll-stopping visual hook.
   - Include clear `visual_direction` for each slide.

5. **Substack Note Post**:
   - HARD LIMIT: Maximum 1,000 characters. Target 400 - 750 characters.
   - Thoughtful, intellectual, reflective micro-essay for Substack Notes feed.
   - len(post) <= 1000 characters.

6. **Substack Newsletter Edition**:
   - High-open Subject Line (< 50 chars).
   - Subtitle preview (< 90 chars).
   - Compelling narrative hook + 3 key analytical takeaways + actionable playbook.

### RULES & HOOK FRAMEWORKS:
{self.knowledge.get("hooks_and_triggers", "")}

### LINKEDIN STORYTELLING GUIDELINES:
{self.knowledge.get("linkedin_storytelling", "")}

### SUBSTACK NOTES SKILL:
{self.knowledge.get("substack_notes_skill", "")}

### HUMAN-WRITTEN WRITING FORMULA (MANDATORY STYLE & AUTHENTICITY RULES):
{self.knowledge.get("human_writing_formula", "")}

### USER VOICE & ANTI-PATTERNS:
{self.knowledge.get("user_voice", "")}
{self.knowledge.get("anti_patterns", "")}

### CRITICAL RULES TO ENFORCE IN EVERY OUTPUT:
1. STRICTLY NO CONTRACTIONS: Always spell out full words (write "do not", "cannot", "will not", "it is", "that is", "you are", "I am", "I have", "we are", "they are", "did not", "would not").
2. HIGH BURSTINESS & SENTENCE VARIATION: Mix 3-word punchy sentences with longer, reflective, human-paced sentences.
3. PERPLEXITY CONTROL: Avoid predictable AI cliches. Use fresh, concrete, grounded words.
4. NATURAL TYPING & IMPERFECTIONS: Subtle organic typing cadence, occasional lowercase for a word or slight natural imperfection, no quotation marks unless necessary.
5. NO BULLET SPAM: Do not force everything into sterile bullet points. Use organic paragraphs and clean line breaks.

### OUTPUT FORMAT:
You MUST respond with a valid JSON object strictly matching this schema:
{{
  "x": {{
    "post": "The exact post text (under 280 characters)",
    "hook_type": "Contrarian / Ragebait / Curiosity / Relatable"
  }},
  "threads": {{
    "post": "The exact threads post text (under 500 characters)",
    "hook_type": "Conversational / Pattern Interrupt"
  }},
  "linkedin": {{
    "post": "The exact LinkedIn story post (under 3000 characters)",
    "hook_type": "Personal Friction / Relatable Story",
    "story_premise": "Brief 1-line description of the real-life experience"
  }},
  "carousel": {{
    "title": "Carousel Title / Topic",
    "slides": [
      {{
        "slide_number": 1,
        "title": "Slide Title",
        "content": "Slide body copy (STRICTLY under 220 chars)",
        "visual_direction": "Visual layout and design cue"
      }}
    ]
  }},
  "substack_note": {{
    "post": "The exact Substack Note text (STRICTLY under 1000 characters)",
    "hook_type": "Reflective / Intellectual Insight"
  }},
  "substack": {{
    "subject_line": "Catchy email subject",
    "subtitle": "Email preview subtitle",
    "opening_hook": "Hook narrative",
    "body_markdown": "Full formatted newsletter markdown with headings and takeaways"
  }},
  "hero_image": {{
    "context_type": "personal OR news_or_entity",
    "subject_name": "Name of person or company (e.g. Kaushal, Vineeta Singh, Sam Altman, SUGAR Cosmetics)",
    "category_tag": "CASE STUDY | HARD TRUTH | AI STRATEGY | FRAMEWORK | FOUNDER LESSON",
    "headline_hook": "Scroll-stopping curiosity headline in 4-8 words with {{highlighted word in braces}}",
    "subtext": "1-line teaser explaining the tension/lesson to make viewers click and read",
    "preferred_gradient": "black | blue | emerald",
    "image_search_query": "Clean web image search query if news_or_entity (e.g. 'Vineeta Singh SUGAR Cosmetics portrait')",
    "user_expression": "serious | smiling | subtle_smile | side_profile"
  }}
}}
"""
        return prompt

    def generate_content(self, dictated_thought: str) -> Dict[str, Any]:
        """Generate content across all platforms and run strict verification."""
        system_prompt = self.build_system_prompt()
        user_message = f"Here is my raw dictated thought and research notes:\n\n\"\"\"\n{dictated_thought}\n\"\"\"\n\nGenerate the complete 6-platform content package following all strict character limits and hook rules. Return ONLY valid JSON."

        raw_response_text = ""
        
        if self.client:
            models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
            # Deduplicate preserving order
            seen = set()
            models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

            for model_name in models_to_try:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=user_message,
                        config={
                            "system_instruction": system_prompt,
                            "temperature": 0.7,
                            "response_mime_type": "application/json"
                        }
                    )
                    raw_response_text = response.text
                    if raw_response_text:
                        print(f"[✔ Live AI Generation] Model '{model_name}' successfully generated content.")
                        break
                except Exception as e:
                    print(f"[Notice] Model '{model_name}' returned: {e}. Trying fallback...")
            
            if not raw_response_text:
                print("[Info] All live models unavailable. Falling back to rule-based generator.")
                raw_response_text = self._mock_generation(dictated_thought)
        else:
            print("[Notice] No GEMINI_API_KEY detected. Running with test generator mode.")
            raw_response_text = self._mock_generation(dictated_thought)

        data = self._parse_json(raw_response_text)
        validated_data = self._validate_and_sanitize(data)
        
        # Save output to outputs directory
        self._save_outputs(dictated_thought, validated_data)
        
        return validated_data

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from response text."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception as e:
            # Fallback regex search for outer brackets
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            raise ValueError(f"Failed to parse model output as JSON: {e}\nRaw output:\n{text}")

    def _validate_and_sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Strictly enforce character limits on all platform posts."""
        report = {}
        
        # 1. Validate X (Twitter)
        x_content = data.get("x", {}).get("post", "")
        x_val = validate_post_length("x", x_content)
        if not x_val["is_valid"]:
            print(f"[Validator Warning] X post exceeded limit by {x_val['overage']} chars ({x_val['length']}/280). Trimming strictly...")
            x_content = enforce_strict_trim(x_content, DEFAULT_LIMITS["x"])
            data["x"]["post"] = x_content
            x_val = validate_post_length("x", x_content)
        data["x"]["validation"] = x_val

        # 2. Validate Threads
        threads_content = data.get("threads", {}).get("post", "")
        t_val = validate_post_length("threads", threads_content)
        if not t_val["is_valid"]:
            print(f"[Validator Warning] Threads post exceeded limit by {t_val['overage']} chars ({t_val['length']}/500). Trimming strictly...")
            threads_content = enforce_strict_trim(threads_content, DEFAULT_LIMITS["threads"])
            data["threads"]["post"] = threads_content
            t_val = validate_post_length("threads", threads_content)
        data["threads"]["validation"] = t_val

        # 3. Validate LinkedIn
        li_content = data.get("linkedin", {}).get("post", "")
        li_val = validate_post_length("linkedin", li_content)
        if not li_val["is_valid"]:
            print(f"[Validator Warning] LinkedIn post exceeded limit by {li_val['overage']} chars ({li_val['length']}/3000). Trimming strictly...")
            li_content = enforce_strict_trim(li_content, DEFAULT_LIMITS["linkedin"])
            data["linkedin"]["post"] = li_content
            li_val = validate_post_length("linkedin", li_content)
        data["linkedin"]["validation"] = li_val

        # 4. Validate Carousel
        slides = data.get("carousel", {}).get("slides", [])
        for slide in slides:
            c = slide.get("content", "")
            if len(c) > DEFAULT_LIMITS["carousel_slide"]:
                slide["content"] = enforce_strict_trim(c, DEFAULT_LIMITS["carousel_slide"])
        data["carousel"]["validation"] = validate_carousel_slides(slides, DEFAULT_LIMITS["carousel_slide"])

        # 5. Validate Substack Note
        sn_content = data.get("substack_note", {}).get("post", "")
        if sn_content:
            sn_val = validate_post_length("substack_note", sn_content)
            if not sn_val["is_valid"]:
                print(f"[Validator Warning] Substack Note exceeded limit by {sn_val['overage']} chars ({sn_val['length']}/1000). Trimming strictly...")
                sn_content = enforce_strict_trim(sn_content, DEFAULT_LIMITS["substack_note"])
                data["substack_note"]["post"] = sn_content
                sn_val = validate_post_length("substack_note", sn_content)
            data["substack_note"]["validation"] = sn_val

        return data

    def fetch_link_context(self, url: str) -> str:
        """Extracts context, title, text or tweet content from a shared URL."""
        import urllib.request
        # Check if X / Twitter link
        tw_match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)', url)
        if tw_match:
            user, tid = tw_match.group(1), tw_match.group(2)
            try:
                fx_url = f"https://api.fxtwitter.com/{user}/status/{tid}"
                req = urllib.request.Request(fx_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    tweet = data.get("tweet", {})
                    author = tweet.get("author", {}).get("name", user)
                    text = tweet.get("text", "")
                    return f"Tweet by {author} (@{user}): \"{text}\""
            except Exception:
                pass

        # General Web Page Scrape
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                title_m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                title = title_m.group(1).strip() if title_m else ""
                desc_m = re.search(r'<meta\s+name=[\"\']description[\"\']\s+content=[\"\'](.*?)[\"\']', html, re.IGNORECASE)
                desc = desc_m.group(1).strip() if desc_m else ""
                return f"Page Title: {title}\nSummary: {desc}"
        except Exception:
            return f"Link URL: {url}"

    def generate_quote_reaction(self, url: str, user_comment: str = "") -> Dict[str, Any]:
        """
        Generates an intelligent, authentic human quote-tweet for X (@kaushaltalks).
        Adapts naturally to the context:
        - If it is alarming AI progress / lab drama: taps into existential reality / pattern recognition.
        - If it is regular tech/business/culture news: delivers a sharp, genuine human thought or counter-intuitive observation.
        """
        link_context = self.fetch_link_context(url)
        
        prompt = """You are Kaushal (@kaushaltalks). You are writing a single Quote Tweet on X reacting to a link or tweet.

### VOICE & INTELLECT:
- Think and write like a real, discerning human who observes patterns and speaks his genuine mind.
- DO NOT sound like an AI summarizing an article or writing generic marketing commentary.
- USER CONTEXT IS TOP PRIORITY: If the user provided any notes, angle, or rough thoughts with the link (e.g., 'we are cooked', 'look at how they hid this', 'this breaks traditional SaaS'), make their intuition the primary angle and refine it into an ultra-sharp quote tweet.
- If no user note is given:
  - For dramatic AI leaps or frontier lab drama, reflect real human existential fear or insider reality ("we are cooked", "no wonder they left", "everyone is looking at the wrong metric").
  - For standard tech, creator economy, or business news, give an authentic, sharp human reaction or contrarian takeaway.
- Speak plainly, directly, and with conviction.

### CRITICAL RULES:
1. STRICTLY NO CONTRACTIONS: Write 'cannot', 'do not', 'will not', 'it is', 'that is', 'you are', 'I have', 'they are'.
2. TWITTER / X QUOTE LENGTH: Must be STRICTLY UNDER 230 characters so when combined with the URL it remains under 280 characters.
3. OUTPUT ONLY A SINGLE QUOTE: Give your single best, sharpest take.

### OUTPUT JSON SCHEMA:
{
  "quote": "Your single sharp quote tweet text (STRICTLY under 230 characters, no contractions)",
  "angle_summary": "1 short sentence explaining the human reasoning or core premise behind this quote"
}
"""
        user_notes_only = user_comment.replace(url, "").strip()
        user_msg = f"URL: {url}\nLink Content Context:\n{link_context}\n\nUser Accompanying Note / Directive: \"{user_notes_only or 'None provided - determine best authentic human angle'}\""
        
        raw_text = ""
        if self.client:
            models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
            for m in models_to_try:
                try:
                    resp = self.client.models.generate_content(
                        model=m,
                        contents=f"{prompt}\n\n{user_msg}",
                        config={"temperature": 0.7, "response_mime_type": "application/json"}
                    )
                    raw_text = resp.text
                    if raw_text:
                        break
                except Exception as e:
                    print(f"[Notice] Model {m} quote generation error: {e}")

        if not raw_text:
            raw_text = json.dumps({
                "quote": "If you are still looking at this as a normal tech update, you are missing the bigger picture. The baseline just shifted completely.",
                "angle_summary": "Sharp pattern interrupt focusing on how fast the underlying baseline is changing."
            })

        data = self._parse_json(raw_text)
        quote_text = data.get("quote", "").strip()
        
        # Ensure strict contraction and length check
        quote_text = enforce_strict_trim(quote_text, 230)
        data["quote"] = quote_text
        data["url"] = url
        data["link_context"] = link_context
        data["full_x_quote"] = f"{quote_text}\n\n{url}"
        return data

    def _save_outputs(self, raw_input: str, data: Dict[str, Any]):
        """Persist generated package to timestamped output folder."""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r'[^a-zA-Z0-9]', '_', raw_input[:30]).strip('_').lower() or "batch"
        folder = OUTPUTS_DIR / f"{timestamp}_{slug}"
        folder.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = folder / "content.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "raw_dictation": raw_input,
                "content": data
            }, f, indent=2, ensure_ascii=False)

        # Save human-readable Markdown
        md_path = folder / "content.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Social Media Content Batch - {now.strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"**Original Dictated Thought:**\n> {raw_input}\n\n---\n\n")
            
            # X
            x_post = data.get("x", {})
            f.write(f"## 1. X (Twitter) Post\n")
            f.write(f"- **Length:** {x_post.get('validation', {}).get('length', len(x_post.get('post', '')))} / 280 characters\n")
            f.write(f"- **Hook Type:** {x_post.get('hook_type', 'N/A')}\n\n")
            f.write(f"```text\n{x_post.get('post', '')}\n```\n\n---\n\n")

            # Threads
            th_post = data.get("threads", {})
            f.write(f"## 2. Meta Threads Post\n")
            f.write(f"- **Length:** {th_post.get('validation', {}).get('length', len(th_post.get('post', '')))} / 500 characters\n")
            f.write(f"- **Hook Type:** {th_post.get('hook_type', 'N/A')}\n\n")
            f.write(f"```text\n{th_post.get('post', '')}\n```\n\n---\n\n")

            # LinkedIn
            li_post = data.get("linkedin", {})
            f.write(f"## 3. LinkedIn Storytelling Post\n")
            f.write(f"- **Length:** {li_post.get('validation', {}).get('length', len(li_post.get('post', '')))} / 3000 characters\n")
            f.write(f"- **Premise:** {li_post.get('story_premise', 'N/A')}\n\n")
            f.write(f"{li_post.get('post', '')}\n\n---\n\n")

            # Carousel
            car = data.get("carousel", {})
            f.write(f"## 4. Carousel Slide Deck: {car.get('title', 'Carousel')}\n\n")
            for s in car.get("slides", []):
                f.write(f"### Slide {s.get('slide_number')}: {s.get('title')}\n")
                f.write(f"**Copy ({len(s.get('content', ''))}/220 chars):**\n{s.get('content')}\n\n")
                f.write(f"*Design Direction:* {s.get('visual_direction')}\n\n")
            f.write("---\n\n")

            # Substack Note
            sub_note = data.get("substack_note", {})
            f.write(f"## 5. Substack Note (Short-form Feed)\n")
            f.write(f"- **Length:** {sub_note.get('validation', {}).get('length', len(sub_note.get('post', '')))} / 1000 characters\n")
            f.write(f"- **Hook Type:** {sub_note.get('hook_type', 'N/A')}\n\n")
            f.write(f"```text\n{sub_note.get('post', '')}\n```\n\n---\n\n")

            # Substack Newsletter
            sub = data.get("substack", {})
            f.write(f"## 6. Substack Newsletter (Full Article)\n")
            f.write(f"**Subject Line:** {sub.get('subject_line')}\n\n")
            f.write(f"**Subtitle:** {sub.get('subtitle')}\n\n")
            f.write(f"{sub.get('body_markdown')}\n")

        data["_saved_to"] = str(folder)

    def _mock_generation(self, raw_input: str) -> str:
        """Demo generator for testing without an API key."""
        return json.dumps({
            "x": {
                "post": "Most creators obsess over production quality. But here is the brutal truth: if your hook fails in the first 2 seconds, your 4K video is completely invisible.\n\nFriction beats polish every single time.\n\nStop tweaking pixels. Start engineering pattern interrupts.",
                "hook_type": "Contrarian / Pattern Interrupt"
            },
            "threads": {
                "post": "A strange realization from my research notes today.\n\nThe posts you spend 4 hours agonizing over usually flop. But that raw observation you typed in 45 seconds while walking to get coffee? Blows up.\n\nPeople on social platforms do not want corporate PR. They want to hear what went wrong in your day and what you learned from the wreckage.\n\nWhen was the last time you posted something unpolished?",
                "hook_type": "Conversational shower thought"
            },
            "linkedin": {
                "post": "Last year, I watched our biggest launch completely flatline.\n\nMonths of preparation. Sleek slides. Flawless demo.\n\nZero customer traction. Nothing.\n\nI was sitting in my car after the debrief, staring at the dashboard, wondering what we missed.\n\nThen an old colleague said something that hit like cold water on a winter morning: You sold them the destination. You never showed them that you understood their storm.\n\nWe had spent months presenting answers to problems our customers had not even admitted they had yet.\n\nHere is what we changed immediately:\n\nStop announcing features. Start documenting real user friction.\nKill corporate jargon. Speak like two tired engineers having coffee at midnight.\nMake the problem vivid before offering a single line of solution.\n\nThe next sprint, our response rate quadrupled.\n\nAuthenticity is not a tactic. It is the only moat left when AI can generate polished answers in seconds.\n\nWhat is one painful mistake that taught you more than your biggest wins?",
                "hook_type": "Personal Friction & Failure",
                "story_premise": "A product launch that failed because it prioritized polish over customer friction"
            },
            "carousel": {
                "title": "Why Polish Kills Reach (And What Works Instead)",
                "slides": [
                    {
                        "slide_number": 1,
                        "title": "The Polish Trap",
                        "content": "Why your high-effort content is getting zero reach (and the 1 mistake you do not know you are making).",
                        "visual_direction": "High-contrast dark background with neon yellow typography"
                    },
                    {
                        "slide_number": 2,
                        "title": "The Hidden Reality",
                        "content": "Algorithms do not favor perfection. Audiences scroll past perfection because it looks like a sponsored ad.",
                        "visual_direction": "Split screen: Corporate glossy stock photo vs Candid phone note"
                    },
                    {
                        "slide_number": 3,
                        "title": "Rule 1: Hook the Friction",
                        "content": "Start where things broke, not where they succeeded. Vulnerability commands attention immediately.",
                        "visual_direction": "Minimal graphic showing a timeline with a highlighted Failure Moment"
                    },
                    {
                        "slide_number": 4,
                        "title": "Rule 2: Give the Playbook",
                        "content": "Do not tease value behind a link. Give the full tactical takeaway right inside the post.",
                        "visual_direction": "3 numbered bullet icons with bold headings"
                    },
                    {
                        "slide_number": 5,
                        "title": "Summary & Action",
                        "content": "Next time you post: cut half of the filler, lead with the real struggle, and respect their time. Save this for your next draft.",
                        "visual_direction": "Clean CTA slide with bookmark or save icon"
                    }
                ]
            },
            "substack_note": {
                "post": "Most writers struggle because they believe they must possess crystal-clear thinking before putting pen to paper.\n\nThat is completely backwards.\n\nYou do not write because you are clear. You write in order to find out what you are actually thinking. Writing is not a recording device; it is a thinking laboratory.\n\nWhenever you feel stuck on a murky decision today, do not sit in silence. Open a blank page and write the first messy sentence.",
                "hook_type": "Reflective / Writing Philosophy"
            },
            "substack": {
                "subject_line": "The anatomy of attention: Why friction beats polish",
                "subtitle": "Notes from the trenches on how real-life storytelling wins in an AI-saturated feed.",
                "opening_hook": "We have entered an era where perfection has zero marginal cost.",
                "body_markdown": "## The Death of Corporate Polish\n\nEvery day, feeds across X, LinkedIn, and Substack are flooded with synthetically smoothed prose. And yet, reader engagement with generic advice has hit an all-time low.\n\n### The Thesis\nWhen perfection is cheap, friction becomes the premium signal.\n\n### 3 Key Insights from Our Research\n1. Hooks must create an emotional pattern interrupt. If line 1 does not break consensus, line 10 will never be read.\n2. Storytelling needs personal stakes. People do not follow companies; they follow humans with scars and hard-won lessons.\n3. Hard boundaries breed creativity. Respecting platform constraints ensures zero wasted words.\n\n### What to Do Next\nAudit your last 3 pieces of content. If they read like a press release, scrap them and rewrite them as a story of friction and resolution."
            },
            "hero_image": {
                "context_type": "personal",
                "subject_name": "Kaushal",
                "category_tag": "HARD TRUTH",
                "headline_hook": "WHY POLISH {KILLS} REACH ON SOCIAL MEDIA",
                "subtext": "The counter-intuitive reason raw friction beats 4K perfection every time.",
                "preferred_gradient": "emerald",
                "user_expression": "serious"
            }
        })

_thought_cache = {}

def generate_post(raw_thought: str, platform: str) -> str:
    """
    Convenience helper to generate a post for a specific target platform.
    Used by Strands Agent SDK tools.
    """
    global _thought_cache
    if raw_thought in _thought_cache:
        data = _thought_cache[raw_thought]
    else:
        engine = SocialMediaEngine()
        data = engine.generate_content(raw_thought)
        _thought_cache[raw_thought] = data

    plat = platform.lower().strip()
    if plat in ["x", "twitter"]:
        return data.get("x", {}).get("post", "")
    elif plat in ["threads", "meta_threads"]:
        return data.get("threads", {}).get("post", "")
    elif plat in ["linkedin", "li"]:
        return data.get("linkedin", {}).get("post", "")
    elif plat in ["substack_note", "note"]:
        return data.get("substack_note", {}).get("post", "")
    elif plat in ["substack", "newsletter"]:
        return data.get("substack", {}).get("body_markdown", "")
    return data.get("x", {}).get("post", "")


