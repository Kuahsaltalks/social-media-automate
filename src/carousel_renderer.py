"""
High-Resolution Carousel Slide Image & PDF Generator.

Renders 1080x1350 (4:5 portrait) social media slide cards using HTML/CSS & Playwright,
and automatically compiles them into an interactive PDF carousel for LinkedIn/Instagram.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import base64
import img2pdf
from playwright.sync_api import sync_playwright

HTML_SLIDE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1080px;
    height: 1350px;
    background: #070a11;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 75px 80px 70px 80px;
    position: relative;
    overflow: hidden;
  }
  
  /* Modern ambient background glows */
  .glow-top {
    position: absolute;
    top: -200px;
    right: -200px;
    width: 650px;
    height: 650px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.18) 0%, rgba(0,0,0,0) 70%);
    border-radius: 50%;
    z-index: 0;
  }
  
  .glow-bottom {
    position: absolute;
    bottom: -200px;
    left: -200px;
    width: 650px;
    height: 650px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.16) 0%, rgba(0,0,0,0) 70%);
    border-radius: 50%;
    z-index: 0;
  }

  .content-wrapper {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
    justify-content: space-between;
  }

  /* Top Bar */
  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 24px;
  }
  
  .topic-tag {
    font-size: 19px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.12);
    padding: 10px 22px;
    border-radius: 100px;
    border: 1px solid rgba(56, 189, 248, 0.3);
  }

  .slide-counter {
    font-size: 24px;
    font-weight: 800;
    color: #94a3b8;
    letter-spacing: 1.5px;
  }

  /* Visual Illustration Box */
  .visual-container {
    width: 100%;
    height: 540px;
    border-radius: 24px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 20px 45px rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.12);
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0e1422;
    margin: 18px 0;
  }

  .visual-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  /* Text Area */
  .text-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 52px;
    height: 52px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(99, 102, 241, 0.25));
    border: 1px solid rgba(56, 189, 248, 0.4);
    color: #38bdf8;
    font-size: 24px;
    font-weight: 800;
    flex-shrink: 0;
  }

  .slide-title {
    font-size: 48px;
    font-weight: 800;
    line-height: 1.2;
    color: #ffffff;
    letter-spacing: -1px;
  }

  .slide-title.hook-slide {
    font-size: 52px;
    background: linear-gradient(135deg, #ffffff 40%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .card-container {
    background: rgba(255, 255, 255, 0.035);
    border-left: 4px solid #38bdf8;
    border-radius: 0 18px 18px 0;
    padding: 24px 30px;
    backdrop-filter: blur(10px);
  }

  .slide-content {
    font-size: 30px;
    font-weight: 450;
    line-height: 1.48;
    color: #cbd5e1;
  }

  /* Bottom Bar */
  .bottom-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 24px;
  }

  .author-info {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .author-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(135deg, #38bdf8, #818cf8);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    color: #070a11;
    font-size: 22px;
  }

  .author-handle {
    font-size: 24px;
    font-weight: 700;
    color: #f1f5f9;
  }

  .swipe-cta {
    font-size: 24px;
    font-weight: 700;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
</head>
<body>
  <div class="glow-top"></div>
  <div class="glow-bottom"></div>
  <div class="content-wrapper">
    <div class="top-bar">
      <div class="topic-tag">{{TOPIC}}</div>
      <div class="slide-counter">{{SLIDE_NUM}} / {{TOTAL_SLIDES}}</div>
    </div>

    {{VISUAL_CONTAINER_HTML}}

    <div class="text-section">
      <div class="title-row">
        {{STEP_BADGE_HTML}}
        <h1 class="slide-title {{HOOK_CLASS}}">{{TITLE}}</h1>
      </div>
      <div class="card-container">
        <p class="slide-content">{{CONTENT}}</p>
      </div>
    </div>

    <div class="bottom-bar">
      <div class="author-info">
        <div class="author-avatar">{{AUTHOR_AVATAR}}</div>
        <div class="author-handle">{{AUTHOR_HANDLE}}</div>
      </div>
      <div class="swipe-cta">{{CTA_TEXT}}</div>
    </div>
  </div>
</body>
</html>
"""

class CarouselRenderer:
    def __init__(self, author_handle: str = "@aiwithkaushal"):
        self.author_handle = author_handle

    def render_carousel(self, batch_folder: Path) -> Dict[str, Any]:
        """
        Reads content.json from batch_folder, generates illustrated slide PNG images,
        and compiles them into carousel.pdf with @aiwithkaushal branding and community CTA.
        """
        json_file = batch_folder if batch_folder.is_file() else batch_folder / "content.json"
        if not json_file.exists():
            raise FileNotFoundError(f"content.json not found in {batch_folder}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        carousel_data = data.get("content", {}).get("carousel", {})
        topic = carousel_data.get("title", "Framework")
        slides = carousel_data.get("slides", [])
        
        if not slides:
            raise ValueError("No slides found in carousel data.")

        output_dir = json_file.parent / "carousel_images"
        output_dir.mkdir(parents=True, exist_ok=True)

        total_slides = len(slides)
        image_paths = []

        print(f"[Info] Rendering {total_slides} illustrated carousel slides for {self.author_handle} (1080x1350)...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)

            for i, slide in enumerate(slides, start=1):
                slide_num_str = f"{i:02d}"
                total_slides_str = f"{total_slides:02d}"
                title = slide.get("title", f"Point {i}")
                content = slide.get("content", "")

                is_hook = (i == 1)
                is_last = (i == total_slides)
                
                hook_class = "hook-slide" if is_hook else ""
                
                if is_last:
                    cta_text = 'Comment "AI" 🚀'
                    step_badge_html = '<div class="step-badge" style="background: rgba(34, 197, 94, 0.2); border-color: rgba(34, 197, 94, 0.4); color: #4ade80;">🚀</div>'
                else:
                    cta_text = "Swipe ➔"
                    step_badge_html = f'<div class="step-badge">{slide_num_str}</div>' if not is_hook else ""

                # Look for corresponding illustration file: art_1.jpg, art_2.jpg, etc.
                art_file = output_dir / f"art_{i}.jpg"
                if not art_file.exists():
                    art_file = output_dir / f"art_{i}.png"
                
                visual_container_html = ""
                if art_file.exists():
                    with open(art_file, "rb") as f_img:
                        b64_str = base64.b64encode(f_img.read()).decode("utf-8")
                    mime = "image/jpeg" if art_file.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                    visual_container_html = f'''
                    <div class="visual-container">
                        <img class="visual-img" src="data:{mime};base64,{b64_str}" alt="Visual Scene" />
                    </div>
                    '''

                avatar_letter = self.author_handle.replace("@", "")[:1].upper() if self.author_handle else "A"
                formatted_content = content.replace("\n\n", "<br><br>").replace("\n", "<br>")

                html_content = (
                    HTML_SLIDE_TEMPLATE
                    .replace("{{TOPIC}}", topic[:32])
                    .replace("{{SLIDE_NUM}}", slide_num_str)
                    .replace("{{TOTAL_SLIDES}}", total_slides_str)
                    .replace("{{VISUAL_CONTAINER_HTML}}", visual_container_html)
                    .replace("{{STEP_BADGE_HTML}}", step_badge_html)
                    .replace("{{TITLE}}", title)
                    .replace("{{HOOK_CLASS}}", hook_class)
                    .replace("{{CONTENT}}", formatted_content)
                    .replace("{{AUTHOR_AVATAR}}", avatar_letter)
                    .replace("{{AUTHOR_HANDLE}}", self.author_handle)
                    .replace("{{CTA_TEXT}}", cta_text)
                )

                page.set_content(html_content)
                page.wait_for_timeout(400)

                image_filename = f"slide_{i}.png"
                img_path = output_dir / image_filename
                page.screenshot(path=str(img_path))
                image_paths.append(img_path)
                print(f"[✔] Rendered Illustrated Slide {i}/{total_slides} -> {image_filename}")

            browser.close()

        # Compile images to PDF
        pdf_path = output_dir / "carousel.pdf"
        print("[Info] Compiling slides into carousel.pdf for LinkedIn upload...")
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in image_paths]))

        print(f"\n[🚀 SUCCESS] Carousel ready! Generated {len(image_paths)} images & PDF: {pdf_path}")

        return {
            "total_slides": len(image_paths),
            "image_paths": [str(p) for p in image_paths],
            "pdf_path": str(pdf_path),
            "directory": str(output_dir)
        }
