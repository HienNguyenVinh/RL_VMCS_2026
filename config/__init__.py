"""Configuration package for PROCON DP-MARL."""
import os
from pathlib import Path
from typing import Any, Dict
import yaml

CONFIG_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default.yaml"


def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load configuration from a YAML file, falling back to default.yaml."""
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not target_path.exists():
        target_path = DEFAULT_CONFIG_PATH

    with open(target_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Override with environment variables if present
    if "PROCON_BASE_URL" in os.environ:
        config.setdefault("server", {})["base_url"] = os.environ["PROCON_BASE_URL"]
    if "PROCON_POLL_INTERVAL" in os.environ:
        try:
            config.setdefault("server", {})["poll_interval"] = float(os.environ["PROCON_POLL_INTERVAL"])
        except ValueError:
            pass

    return config
