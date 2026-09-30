"""
NeosisLM Streamlit Root Entrypoint
Delegates to the active testbed in ui/app.py
"""
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import ui.app
