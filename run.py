"""Run GCS directly from a source checkout."""

import sys
from pathlib import Path

# nkr_protocol is a standalone ROS Python package kept in this repository.
# Add its package root when running without an installed workspace overlay.
_ROOT = Path(__file__).resolve().parent
_PROTOCOL_ROOT = _ROOT / "nkr_protocol"
if str(_PROTOCOL_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROTOCOL_ROOT))

from nkr_gcs.app import main


if __name__ == "__main__":
    main()
