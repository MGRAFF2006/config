#!/usr/bin/env python3
"""Launch the compatible user-local DMS UI, or its built-in fallback."""

import os
from pathlib import Path
import sys


launcher = Path(__file__).resolve().parents[4] / "scripts/configure-dms-smooth-sliders.py"
os.execv(sys.executable, [sys.executable, str(launcher), "--launch"])
