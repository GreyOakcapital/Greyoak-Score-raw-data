"""Pytest fixtures and configuration for GreyOak Score Engine tests."""

import sys
from pathlib import Path
from typing import Dict

import pytest
import yaml

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from greyoak_score.core.config_manager import ConfigManager


@pytest.fixture(scope="session")
def config_dir() -> Path:
    """Get path to config directory."""
    return Path(__file__).parent.parent / "configs"


@pytest.fixture(scope="session")
def config_manager(config_dir: Path) -> ConfigManager:
    """Load configuration manager (session-scoped for performance)."""
    return ConfigManager(config_dir)


@pytest.fixture
def sample_score_config() -> Dict:
    """Sample score.yaml content for testing."""
    return {
        "version": "1.0.0",
        "mode": "production",
        "pillar_weights": {
            "trader": {
                "default": {"F": 0.12, "T": 0.32, "R": 0.16, "O": 0.08, "Q": 0.04, "S": 0.28}
            },
            "investor": {
                "default": {"F": 0.38, "T": 0.10, "R": 0.08, "O": 0.18, "Q": 0.12, "S": 0.14}
            },
        },
        "banding": {
            "production": {"strong_buy": 75, "buy": 65, "hold": 50},
            "test": {"strong_buy": 70, "buy": 60, "hold": 45},
        },
        "risk_penalty": {"caps": {"default": 20}},
    }


@pytest.fixture
def data_dir() -> Path:
    """Get path to data directory."""
    return Path(__file__).parent.parent / "data"
