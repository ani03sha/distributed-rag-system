import sys
from pathlib import Path

_worker_root = str(Path(__file__).parent.parent)
if _worker_root in sys.path:
    sys.path.remove(_worker_root)
sys.path.insert(0, _worker_root)
