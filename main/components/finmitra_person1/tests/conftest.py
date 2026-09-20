"""
Pytest configuration for FinMitra Person 1.
Ensures finmitra_person1 package is importable.
"""
import sys
from pathlib import Path

# Add package root and parent directory to sys.path
TEST_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = TEST_DIR.parent
PARENT_DIR = PACKAGE_DIR.parent

for p in [str(PACKAGE_DIR), str(PARENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)
