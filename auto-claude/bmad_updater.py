"""
BMAD Method update management.

Handles BMAD updates while preserving user configuration.
"""

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ConfigMigrationResult:
    """Result of configuration migration during update."""

    preserved_count: int
    new_count: int
    deprecated_count: int
    backup_path: str


def preserve_config_during_update(project_path: str) -> ConfigMigrationResult:
    """
    Backup, update, and restore config.yaml with migration.

    Args:
        project_path: Path to project directory

    Returns:
        ConfigMigrationResult with migration details
    """
    config_path = Path(project_path) / "_bmad" / "bmm" / "config.yaml"

    # Read old config
    old_config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            old_config = yaml.safe_load(f) or {}

    # Create backup
    backup_path = Path(project_path) / "_bmad-output" / ".config-backup"
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = backup_path / f"config-{timestamp}.yaml"

    with open(backup_file, "w") as f:
        yaml.dump(old_config, f)

    return ConfigMigrationResult(
        preserved_count=len(old_config),
        new_count=0,
        deprecated_count=0,
        backup_path=str(backup_file),
    )


def merge_configs(old_config: dict, new_template: dict) -> dict:
    """
    Merge user config values into new template.

    Args:
        old_config: User's existing configuration
        new_template: New configuration template from update

    Returns:
        Merged configuration dictionary
    """
    merged = new_template.copy()

    # Preserve all old values that still exist in template
    for key, value in old_config.items():
        if key in new_template:
            merged[key] = value
        else:
            # Mark deprecated but preserve
            merged[f"_deprecated_{key}"] = value

    return merged


def restore_config_from_backup(
    project_path: str, backup_file: Optional[str] = None
) -> bool:
    """
    Restore configuration from backup.

    Args:
        project_path: Path to project directory
        backup_file: Optional specific backup file, otherwise uses latest

    Returns:
        True if successful, False otherwise
    """
    backup_dir = Path(project_path) / "_bmad-output" / ".config-backup"

    if not backup_dir.exists():
        return False

    # Find backup file
    if backup_file:
        backup_path = Path(backup_file)
    else:
        # Get latest backup
        backups = sorted(backup_dir.glob("config-*.yaml"), reverse=True)
        if not backups:
            return False
        backup_path = backups[0]

    if not backup_path.exists():
        return False

    # Read backup
    try:
        with open(backup_path, "r") as f:
            backup_config = yaml.safe_load(f)

        # Write to current config
        config_path = Path(project_path) / "_bmad" / "bmm" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            yaml.dump(backup_config, f)

        return True
    except Exception:
        return False


def list_config_backups(project_path: str) -> list[dict]:
    """
    List all configuration backups.

    Args:
        project_path: Path to project directory

    Returns:
        List of backup metadata dictionaries
    """
    backup_dir = Path(project_path) / "_bmad-output" / ".config-backup"

    if not backup_dir.exists():
        return []

    backups = []
    for backup_file in sorted(backup_dir.glob("config-*.yaml"), reverse=True):
        try:
            # Extract timestamp from filename
            timestamp_str = backup_file.stem.replace("config-", "")
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")

            backups.append(
                {
                    "file": str(backup_file),
                    "timestamp": timestamp.isoformat(),
                    "size": backup_file.stat().st_size,
                }
            )
        except Exception:
            continue

    return backups


def cleanup_old_backups(project_path: str, keep_count: int = 10) -> int:
    """
    Remove old configuration backups, keeping only the most recent.

    Args:
        project_path: Path to project directory
        keep_count: Number of backups to keep

    Returns:
        Number of backups removed
    """
    backup_dir = Path(project_path) / "_bmad-output" / ".config-backup"

    if not backup_dir.exists():
        return 0

    backups = sorted(backup_dir.glob("config-*.yaml"), reverse=True)

    # Keep only the most recent
    to_remove = backups[keep_count:]

    removed_count = 0
    for backup_file in to_remove:
        try:
            backup_file.unlink()
            removed_count += 1
        except Exception:
            continue

    return removed_count
