"""Ensure the threat-assessment-agent modules are importable by name in
pytest even though their containing directory ("threat-assessment-agent")
is not a valid Python package identifier.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
