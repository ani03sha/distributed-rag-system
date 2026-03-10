import sys
from pathlib import Path

# Must be first — prevents services/worker/src from shadowing services/query/src
_query_root = str(Path(__file__).parent.parent)
if _query_root in sys.path:
    sys.path.remove(_query_root)
sys.path.insert(0, _query_root)
