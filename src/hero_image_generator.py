"""
High-Resolution Social Media Hero Hook Image Generator (1080x1350 / 4:5 Portrait).

Creates scroll-stopping visuals for X, Threads, LinkedIn, Instagram, and Substack.
Features:
- Smart context detection: Uses Kaushal's photo for personal advice/reflections,
  or dynamically fetches high-res images for news subjects / public figures.
- Multi-stop cinematic gradient overlays (Black, Deep Blue, or Emerald Dark Green).
- High-contrast, curiosity-inducing typography and headline hooks with highlighted keywords.
"""
import os
import json
import re
import base64
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# User photos directory
USER_IMAGES_DIRS = [
    PROJECT_ROOT / "my_images",
    PROJECT_ROOT / 'Kaushal"s Images ',
    PROJECT_ROOT / "Kaushals Images",
    PROJECT_ROOT / "images"
]

HERO_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1080px;
    height: 1350px;
    background: #000000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  /* Full Bleed Background Subject Image */
  .bg-image {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: {{OBJECT_POSITION}};
    z-index: 1;
    filter: {{IMAGE_FILTER}};
  }

  /* Top Vignette */
  .top-vignette {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 280px;
    background: linear-gradient(to bottom, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0) 100%);
    z-index: 2;
  }

  /* Bottom Gradient Overlay */
  .bottom-gradient {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 65%;
    background: {{GRADIENT_CSS}};
    z-index: 2;
  }

  /* Low Opacity Subtle Watermarks */
  .watermark {
    position: absolute;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 5px;
    text-transform: uppercase;
    color: #ffffff;
    opacity: 0.10;
    user-select: none;
    pointer-events: none;
    z-index: 2;
  }
  .wm-top {
    top: 55px;
    right: 65px;
  }
  .wm-mid {
    top: 48%;
    left: 65px;
    transform: rotate(-25deg);
  }
  .wm-bot {
    bottom: 350px;
    right: 80px;
  }

  /* Content Wrapper */
  .content-container {
    position: relative;
    z-index: 3;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    height: 100%;
    padding: 60px 65px 75px 65px;
  }

  /* Bottom Typography Hook Section */
  .hook-section {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .headline-hook {
    font-size: {{HEADLINE_FONT_SIZE}};
    font-weight: 900;
    line-height: 1.08;
    color: #ffffff;
    text-transform: uppercase;
    letter-spacing: -1.2px;
    text-shadow: 0 6px 30px rgba(0, 0, 0, 0.95), 0 2px 5px rgba(0,0,0,0.8);
  }

  .highlight-word {
    color: {{HIGHLIGHT_COLOR}};
    display: inline;
    text-shadow: 0 0 35px {{HIGHLIGHT_GLOW}};
  }

  .subtext-teaser {
    font-size: 30px;
    font-weight: 600;
    line-height: 1.35;
    color: #f1f5f9;
    text-shadow: 0 3px 15px rgba(0,0,0,0.9);
    max-width: 920px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.22);
  }
</style>
</head>
<body>
  <img class="bg-image" src="{{IMAGE_SRC}}" alt="Background Subject" />
  <div class="top-vignette"></div>
  <div class="bottom-gradient"></div>

  <!-- Subtle Low Opacity Watermarks -->
  <div class="watermark wm-top">{{WATERMARK_TEXT}}</div>
  <div class="watermark wm-mid">{{WATERMARK_TEXT}}</div>
  <div class="watermark wm-bot">{{WATERMARK_TEXT}}</div>

  <div class="content-container">
    <div class="hook-section">
      <h1 class="headline-hook">{{HEADLINE_HTML}}</h1>
      <p class="subtext-teaser">{{SUBTEXT}}</p>
    </div>
  </div>
</body>
</html>
"""

class HeroImageGenerator:
    def __init__(self, watermark_text: str = "@kaushaltalks"):
        self.watermark_text = watermark_text

    def _get_user_photo(self, expression: str = "serious") -> Optional[Path]:
        """Finds the most fitting photo of Kaushal based on requested expression/vibe."""
        all_photos = []
        for d in USER_IMAGES_DIRS:
            if d.exists() and d.is_dir():
                for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG", "*.MPO"]:
                    all_photos.extend(d.glob(ext))

        if not all_photos:
            return None

        exp_lower = expression.lower()
        if "smile" in exp_lower or "happy" in exp_lower or "positive" in exp_lower:
            for p in all_photos:
                if "SMILING" in p.name.upper() and "SUBTLE" not in p.name.upper():
                    return p
        elif "profile" in exp_lower or "side" in exp_lower or "left" in exp_lower:
            for p in all_photos:
                if "PROFILE" in p.name.upper() or "LEFT" in p.name.upper():
                    return p
        elif "subtle" in exp_lower:
            for p in all_photos:
                if "SUBTLE" in p.name.upper():
                    return p
        elif "serious" in exp_lower or "focus" in exp_lower or "intense" in exp_lower:
            for p in all_photos:
                if "SERIOUS" in p.name.upper():
                    return p

        return all_photos[0]

    def _fetch_web_image(self, query: str) -> Optional[str]:
        """Searches and fetches high-res photo for news entities or public figures."""
        try:
            url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query + ' portrait hd')}&form=HDRSC2&first=1"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
                if not murls:
                    murls = re.findall(r'\"murl\":\"(http[^\"]+)\"', html)
                if murls:
                    for murl in murls[:5]:
                        if not any(bad in murl.lower() for bad in ["logo", "icon", "svg", "vector"]):
                            return murl
        except Exception as e:
            print(f"[Warning] Web image search failed for '{query}': {e}")

        try:
            wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&gsrlimit=1&prop=pageimages&pithumbsize=1200&format=json"
            req = urllib.request.Request(wiki_url, headers={"User-Agent": "SocialMediaHeroGen/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                pages = data.get("query", {}).get("pages", {})
                for _, pdata in pages.items():
                    thumb = pdata.get("thumbnail", {}).get("source")
                    if thumb:
                        return thumb
        except Exception:
            pass

        return None

    def generate_hero_image(
        self,
        batch_folder: Path,
        hero_info: Dict[str, Any]
    ) -> Path:
        """
        Renders a 1080x1350 hero hook image and saves to batch_folder / 'hero_image.png'.
        """
        output_path = batch_folder / "hero_image.png"
        batch_folder.mkdir(parents=True, exist_ok=True)

        context_type = hero_info.get("context_type", "personal").lower()
        subject_name = hero_info.get("subject_name", "Kaushal")
        category_tag = hero_info.get("category_tag", "CASE STUDY").upper()
        headline_text = hero_info.get("headline_hook", "THE M LESSON IN SILENCE")
        subtext = hero_info.get("subtext", "The counter-intuitive truth 99% of people miss.")
        gradient_style = hero_info.get("preferred_gradient", "black").lower()
        expression = hero_info.get("user_expression", "serious")

        # Format Headline HTML & Highlights
        highlight_match = re.search(r'[\{\[](.*?)[\}\]]', headline_text)
        if highlight_match:
            raw_highlight = highlight_match.group(1)
            headline_html = headline_text.replace(highlight_match.group(0), f'<span class="highlight-word">{raw_highlight}</span>')
        else:
            words = headline_text.split()
            if len(words) >= 3:
                headline_html = " ".join(words[:-2]) + f' <span class="highlight-word">{" ".join(words[-2:])}</span>'
            else:
                headline_html = headline_text

        # Configure Gradients & Accents
        if "green" in gradient_style or "emerald" in gradient_style:
            gradient_css = "linear-gradient(to top, #021a0f 0%, rgba(2, 26, 15, 0.96) 28%, rgba(4, 45, 26, 0.75) 55%, rgba(4, 45, 26, 0.25) 75%, rgba(0,0,0,0) 100%)"
            badge_bg = "rgba(16, 185, 129, 0.15)"
            badge_border = "rgba(16, 185, 129, 0.4)"
            badge_color = "#34d399"
            accent_color = "#34d399"
            highlight_color = "#4ade80"
            highlight_glow = "rgba(74, 222, 128, 0.4)"
            category_icon = "⚡"
        elif "blue" in gradient_style or "cyan" in gradient_style:
            gradient_css = "linear-gradient(to top, #030a1a 0%, rgba(3, 10, 26, 0.96) 28%, rgba(8, 28, 68, 0.75) 55%, rgba(8, 28, 68, 0.25) 75%, rgba(0,0,0,0) 100%)"
            badge_bg = "rgba(56, 189, 248, 0.15)"
            badge_border = "rgba(56, 189, 248, 0.4)"
            badge_color = "#38bdf8"
            accent_color = "#38bdf8"
            highlight_color = "#38bdf8"
            highlight_glow = "rgba(56, 189, 248, 0.45)"
            category_icon = "🔥"
        else: # Black / Charcoal
            gradient_css = "linear-gradient(to top, #000000 0%, rgba(0, 0, 0, 0.96) 28%, rgba(12, 12, 12, 0.75) 55%, rgba(12, 12, 12, 0.25) 75%, rgba(0,0,0,0) 100%)"
            badge_bg = "rgba(250, 204, 21, 0.15)"
            badge_border = "rgba(250, 204, 21, 0.4)"
            badge_color = "#facc15"
            accent_color = "#facc15"
            highlight_color = "#facc15"
            highlight_glow = "rgba(250, 204, 21, 0.45)"
            category_icon = "📌"

        # Determine Image Source
        image_data_uri = ""
        object_position = "center top"
        image_filter = "contrast(1.05) brightness(0.95)"

        if context_type == "personal" or "kaushal" in subject_name.lower():
            photo_path = self._get_user_photo(expression)
            if photo_path and photo_path.exists():
                try:
                    with open(photo_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/jpeg" if photo_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                    image_data_uri = f"data:{mime};base64,{b64}"
                    object_position = "center 15%"
                except Exception as e:
                    print(f"[Warning] Error loading user image {photo_path}: {e}")

        if not image_data_uri:
            search_query = hero_info.get("image_search_query") or subject_name
            web_url = self._fetch_web_image(search_query)
            if web_url:
                try:
                    req = urllib.request.Request(web_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        img_bytes = resp.read()
                        b64 = base64.b64encode(img_bytes).decode("utf-8")
                        image_data_uri = f"data:image/jpeg;base64,{b64}"
                        object_position = "center 20%"
                except Exception as e:
                    print(f"[Warning] Error downloading web image {web_url}: {e}")

        if not image_data_uri:
            image_data_uri = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1350'><rect width='100%' height='100%' fill='%23080c14'/></svg>"

        clean_headline_len = len(re.sub(r'<[^>]+>', '', headline_text))
        if clean_headline_len > 45:
            font_size = "52px"
        elif clean_headline_len > 30:
            font_size = "62px"
        else:
            font_size = "72px"

        html_content = (
            HERO_HTML_TEMPLATE
            .replace("{{IMAGE_SRC}}", image_data_uri)
            .replace("{{OBJECT_POSITION}}", object_position)
            .replace("{{IMAGE_FILTER}}", image_filter)
            .replace("{{GRADIENT_CSS}}", gradient_css)
            .replace("{{WATERMARK_TEXT}}", self.watermark_text)
            .replace("{{HEADLINE_HTML}}", headline_html)
            .replace("{{HEADLINE_FONT_SIZE}}", font_size)
            .replace("{{HIGHLIGHT_COLOR}}", highlight_color)
            .replace("{{HIGHLIGHT_GLOW}}", highlight_glow)
            .replace("{{ACCENT_COLOR}}", accent_color)
            .replace("{{SUBTEXT}}", subtext)
        )

        print(f"[Info] Rendering 1080x1350 Hero Hook Image ({category_tag})...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
            page.set_content(html_content)
            page.wait_for_timeout(600)
            page.screenshot(path=str(output_path))
            browser.close()

        print(f"[✔ SUCCESS] Hero Hook Image saved to {output_path}")
        return output_path
