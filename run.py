#!/usr/bin/env python3
"""Runner script for the social media automation engine."""
import sys
from pathlib import Path

# Ensure virtualenv python is prioritized if available
venv_python = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
if venv_python.exists() and sys.executable != str(venv_python):
    import os
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

from src.cli import main

if __name__ == "__main__":
    main()
