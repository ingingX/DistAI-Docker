"""
Pytest configuration and fixtures for coordinator tests
"""

import sys
from pathlib import Path

# Add coordinator module to path
coordinator_path = Path(__file__).parent.parent / "coordinator"
sys.path.insert(0, str(coordinator_path))
