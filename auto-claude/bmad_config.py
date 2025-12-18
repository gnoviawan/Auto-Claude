"""
BMAD Method configuration management.

Handles reading, writing, and validating BMAD configuration files.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class BMADConfig:
    """BMAD configuration data."""

    user_name: str
    project_name: str
    languages: str
    skill_level: str
    framework_mode: str

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "user_name": self.user_name,
            "project_name": self.project_name,
            "languages": self.languages,
            "skill_level": self.skill_level,
            "framework_mode": self.framework_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BMADConfig":
        """Create from dictionary."""
        return cls(
            user_name=data.get("user_name", ""),
            project_name=data.get("project_name", ""),
            languages=data.get("languages", ""),
            skill_level=data.get("skill_level", "mid"),
            framework_mode=data.get("framework_mode", "native"),
        )


def get_bmad_config_path(project_path: str) -> Path:
    """Get path to BMAD config file."""
    return Path(project_path) / "_bmad" / "bmm" / "config.yaml"


def read_bmad_config(project_path: str) -> Optional[BMADConfig]:
    """
    Read BMAD configuration from project.

    Args:
        project_path: Path to user's project directory

    Returns:
        BMADConfig object or None if not found
    """
    config_path = get_bmad_config_path(project_path)

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        # Handle both new format (5 variables) and legacy format
        return BMADConfig.from_dict(data or {})
    except Exception:
        return None


def write_bmad_config(project_path: str, config: BMADConfig) -> bool:
    """
    Write BMAD configuration to project.

    Args:
        project_path: Path to user's project directory
        config: BMADConfig object to write

    Returns:
        True if successful, False otherwise
    """
    config_path = get_bmad_config_path(project_path)

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Read existing config to preserve other fields
        existing_data = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                existing_data = yaml.safe_load(f) or {}

        # Update with new values
        existing_data.update(config.to_dict())

        # Write back
        with open(config_path, "w") as f:
            # Write header comment
            f.write("# BMM Module Configuration\n")
            f.write("# Auto Claude BMAD Integration\n\n")
            yaml.dump(existing_data, f, default_flow_style=False, sort_keys=False)

        return True
    except Exception:
        return False


def get_default_config(project_path: str) -> BMADConfig:
    """
    Get default BMAD configuration for a project.

    Args:
        project_path: Path to user's project directory

    Returns:
        BMADConfig with default values
    """
    project_name = Path(project_path).name

    # Try to get system username
    user_name = os.environ.get("USER") or os.environ.get("USERNAME") or "Developer"

    # Detect languages (placeholder - will be implemented in Story 7.4)
    languages = detect_project_languages(project_path)

    return BMADConfig(
        user_name=user_name,
        project_name=project_name,
        languages=languages,
        skill_level="mid",
        framework_mode="native",
    )


def detect_project_languages(project_path: str) -> str:
    """
    Detect primary programming languages in project.

    Args:
        project_path: Path to project directory

    Returns:
        Comma-separated list of detected languages
    """
    # Simple detection based on file extensions
    project_path_obj = Path(project_path)
    languages = set()

    # Language markers
    language_files = {
        "python": ["*.py", "requirements.txt", "setup.py", "pyproject.toml"],
        "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
        "javascript": ["*.js", "*.jsx", "package.json"],
        "rust": ["*.rs", "Cargo.toml"],
        "go": ["*.go", "go.mod"],
        "java": ["*.java", "pom.xml"],
        "cpp": ["*.cpp", "*.cc", "*.cxx"],
        "c": ["*.c"],
    }

    for lang, patterns in language_files.items():
        for pattern in patterns:
            if list(project_path_obj.glob(f"**/{pattern}")):
                languages.add(lang)
                break  # Found this language, move to next

    # Return sorted languages
    if languages:
        return ",".join(sorted(languages))
    else:
        return "python"  # Default to Python


def validate_config(config: BMADConfig) -> tuple[bool, list[str]]:
    """
    Validate BMAD configuration.

    Args:
        config: BMADConfig to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate user_name
    if not config.user_name or not config.user_name.strip():
        errors.append("user_name cannot be empty")
    elif not re.match(r"^[a-zA-Z0-9\s\-_]+$", config.user_name):
        errors.append(
            "user_name must contain only alphanumeric characters, spaces, hyphens, and underscores"
        )

    # Validate project_name
    if not config.project_name or not config.project_name.strip():
        errors.append("project_name cannot be empty")
    elif not re.match(r"^[a-zA-Z0-9\-_]+$", config.project_name):
        errors.append(
            "project_name must contain only alphanumeric characters, hyphens, and underscores"
        )

    # Validate languages
    if not config.languages or not config.languages.strip():
        errors.append("languages cannot be empty")
    elif not re.match(r"^[a-zA-Z0-9,\s]+$", config.languages):
        errors.append("languages must be a comma-separated list of language names")

    # Validate skill_level
    valid_skill_levels = ["junior", "mid", "senior", "principal"]
    if config.skill_level not in valid_skill_levels:
        errors.append(
            f"skill_level must be one of: {', '.join(valid_skill_levels)}"
        )

    # Validate framework_mode
    valid_frameworks = ["bmad", "native"]
    if config.framework_mode not in valid_frameworks:
        errors.append(
            f"framework_mode must be one of: {', '.join(valid_frameworks)}"
        )

    return (len(errors) == 0, errors)
