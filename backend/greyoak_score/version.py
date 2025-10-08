"""Version and build information."""

import hashlib
from datetime import datetime, timezone
from typing import Dict

__version__ = "1.0.0"
__build_date__ = datetime.now(timezone.utc).isoformat()


def get_version_info() -> Dict[str, str]:
    """Get version information for audit trail.
    
    Returns:
        Dictionary with version, build date, and git commit (if available).
    """
    return {
        "version": __version__,
        "build_date": __build_date__,
    }
