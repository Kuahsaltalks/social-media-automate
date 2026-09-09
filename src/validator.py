"""Strict character counter and constraint validator for social media platforms."""
from typing import Dict, Any, Tuple, List
import json
import re
from pathlib import Path

# Default hard limits
DEFAULT_LIMITS = {
    "x": 280,
    "threads": 500,
    "linkedin": 3000,
    "carousel_slide": 220,
    "substack_note": 1000
}

def load_platform_limits(rules_path: Path = None) -> Dict[str, Any]:
    """Load platform limits from rules/platform_limits.json if available."""
    if rules_path is None:
        rules_path = Path(__file__).resolve().parent.parent / "rules" / "platform_limits.json"
    
    if rules_path.exists():
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def validate_post_length(platform: str, text: str, custom_limit: int = None) -> Dict[str, Any]:
    """
    Validate that text strictly satisfies the platform limit.
    Returns a dict with verification details:
    {
        "platform": platform,
        "length": int,
        "max_allowed": int,
        "is_valid": bool,
        "overage": int,
        "remaining": int
    }
    """
    clean_text = text.strip()
    length = len(clean_text)
    
    if custom_limit is not None:
        limit = custom_limit
    else:
        limits = load_platform_limits()
        if platform in limits and "max_characters" in limits[platform]:
            limit = limits[platform]["max_characters"]
        else:
            limit = DEFAULT_LIMITS.get(platform, 3000)
    
    is_valid = (length <= limit)
    overage = max(0, length - limit)
    remaining = max(0, limit - length)
    
    return {
        "platform": platform,
        "length": length,
        "max_allowed": limit,
        "is_valid": is_valid,
        "overage": overage,
        "remaining": remaining
    }

def validate_carousel_slides(slides: List[Dict[str, str]], per_slide_limit: int = 220) -> Dict[str, Any]:
    """Validate each slide in a carousel against per-slide character limit."""
    results = []
    all_valid = True
    for i, slide in enumerate(slides, start=1):
        content = slide.get("content", "").strip()
        length = len(content)
        valid = (length <= per_slide_limit)
        if not valid:
            all_valid = False
        results.append({
            "slide_number": i,
            "title": slide.get("title", f"Slide {i}"),
            "length": length,
            "max_allowed": per_slide_limit,
            "is_valid": valid,
            "overage": max(0, length - per_slide_limit)
        })
    
    return {
        "total_slides": len(slides),
        "is_valid": all_valid,
        "slides": results
    }

def enforce_strict_trim(text: str, limit: int) -> str:
    """
    Emergency strict trimmer: if an AI model exceeds the limit by a few characters,
    safely trims at the nearest sentence or word boundary so that len <= limit.
    Never leaves trailing raw cuts or exceeds the ceiling by even 1 character.
    """
    clean_text = text.strip()
    if len(clean_text) <= limit:
        return clean_text
    
    # Target cut point
    truncated = clean_text[:limit].rstrip()
    
    # Try finding last period, question mark, or newline within the last 40 chars
    last_punct = max(truncated.rfind('.'), truncated.rfind('?'), truncated.rfind('!'), truncated.rfind('\n'))
    if last_punct > limit - 60 and last_punct > 0:
        return truncated[:last_punct + 1].strip()
    
    # Fallback to last whitespace
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space].rstrip()
    
    return truncated
