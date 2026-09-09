"""Configuration and directory loader for rules, skills, and learnings."""
import os
from pathlib import Path
from typing import Dict

# Base project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = PROJECT_ROOT / "rules"
SKILLS_DIR = PROJECT_ROOT / "skills"
LEARNINGS_DIR = PROJECT_ROOT / "learnings"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

def load_file_content(path: Path) -> str:
    """Safely read text from a path."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            return f"[Error loading {path.name}: {e}]"
    return ""

def load_system_knowledge() -> Dict[str, str]:
    """
    Collect all rules, skills, and learning contexts into a structured memory dict
    to inject into the Gemini model prompt.
    """
    knowledge = {
        # Rules
        "platform_limits": load_file_content(RULES_DIR / "platform_limits.md"),
        "hooks_and_triggers": load_file_content(RULES_DIR / "hooks_and_triggers.md"),
        "linkedin_storytelling": load_file_content(RULES_DIR / "linkedin_storytelling.md"),
        "human_writing_formula": load_file_content(RULES_DIR / "human_writing_formula.md"),
        
        # Skills
        "x_skill": load_file_content(SKILLS_DIR / "x_crafting.md"),
        "threads_skill": load_file_content(SKILLS_DIR / "threads_crafting.md"),
        "linkedin_skill": load_file_content(SKILLS_DIR / "linkedin_storytelling.md"),
        "carousel_skill": load_file_content(SKILLS_DIR / "carousel_builder.md"),
        "substack_notes_skill": load_file_content(SKILLS_DIR / "substack_notes.md"),
        "substack_skill": load_file_content(SKILLS_DIR / "substack_essay.md"),
        
        # Learnings / Memory
        "user_voice": load_file_content(LEARNINGS_DIR / "user_voice_profile.md"),
        "anti_patterns": load_file_content(LEARNINGS_DIR / "anti_patterns.md"),
        "successful_posts": load_file_content(LEARNINGS_DIR / "successful_posts.md"),
    }
    return knowledge

def get_env_config() -> Dict[str, str]:
    """Retrieve environment variables with sensible defaults."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        # Simple parser for .env if python-dotenv is not yet installed
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass

    return {
        "api_key": os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")),
        "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "temperature": float(os.environ.get("TEMPERATURE", "0.7"))
    }
