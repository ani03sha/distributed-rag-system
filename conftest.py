import sys
from pathlib import Path

# Make service source roots importable as 'src.*' in tests
sys.path.insert(0, str(Path(__file__).parent / "services" / "query"))
sys.path.insert(0, str(Path(__file__).parent / "services" / "worker"))
