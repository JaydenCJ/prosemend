"""Make the src/ layout importable when running pytest from a clean checkout.

An editable install (`pip install -e .`) makes this a no-op; without one, the
tests still run because the package has zero runtime dependencies.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
