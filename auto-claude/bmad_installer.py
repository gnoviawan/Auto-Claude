"""
BMAD Method installer for Auto Claude.

Handles installation of BMAD framework to user projects, including:
- Copying BMAD bundle to project directory
- Detecting and handling existing installations
- Validating installation integrity
- Creating output directories
"""

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class InstallResult:
    """Result of BMAD installation operation."""

    status: str  # "success", "skipped", "failed"
    message: str
    details: Optional[dict] = None


def install_bmad(project_path: str, force: bool = False) -> InstallResult:
    """
    Copy BMAD Method from bundle to user project.

    Args:
        project_path: Path to user's project directory
        force: If True, overwrite existing installation

    Returns:
        InstallResult with status (success/skipped/failed) and message
    """
    bundle_path = Path(__file__).parent / "_bmad"
    target_path = Path(project_path) / "_bmad"
    output_path = Path(project_path) / "_bmad-output"

    # Verify bundle exists
    if not bundle_path.exists():
        return InstallResult(
            status="failed",
            message="BMAD bundle not found in Auto Claude installation",
            details={"bundle_path": str(bundle_path)},
        )

    # Detect existing installation
    if target_path.exists():
        if not force:
            return handle_existing_installation(target_path, bundle_path)
        else:
            # Remove existing installation for forced reinstall
            shutil.rmtree(target_path)

    # Copy directory structure
    try:
        shutil.copytree(
            bundle_path,
            target_path,
            ignore=shutil.ignore_patterns("_memory", "_config", "__pycache__", "*.pyc"),
        )
    except Exception as e:
        return InstallResult(
            status="failed", message=f"Failed to copy BMAD files: {str(e)}"
        )

    # Create output directory
    try:
        output_path.mkdir(exist_ok=True)
        # Create subdirectories for different artifact types
        (output_path / "project-planning-artifacts").mkdir(exist_ok=True)
        (output_path / "implementation-artifacts").mkdir(exist_ok=True)
    except Exception as e:
        return InstallResult(
            status="failed",
            message=f"Failed to create output directory: {str(e)}",
        )

    # Validate installation
    validation_result = validate_bmad_structure(target_path)
    if validation_result["valid"]:
        return InstallResult(
            status="success",
            message="BMAD Method installed successfully",
            details={
                "target_path": str(target_path),
                "output_path": str(output_path),
                "version": get_bmad_version(target_path),
            },
        )
    else:
        return InstallResult(
            status="failed",
            message="Installation validation failed",
            details=validation_result,
        )


def handle_existing_installation(
    target_path: Path, bundle_path: Path
) -> InstallResult:
    """
    Handle existing BMAD installation.

    Detects version and offers update if newer version available.

    Args:
        target_path: Path to existing BMAD installation
        bundle_path: Path to BMAD bundle

    Returns:
        InstallResult with recommendation
    """
    current_version = get_bmad_version(target_path)
    bundle_version = get_bmad_version(bundle_path)

    if current_version == bundle_version:
        return InstallResult(
            status="skipped",
            message=f"BMAD Method already installed (version {current_version})",
            details={
                "current_version": current_version,
                "bundle_version": bundle_version,
                "target_path": str(target_path),
            },
        )
    else:
        return InstallResult(
            status="skipped",
            message=f"BMAD Method already installed. Update available: {current_version} → {bundle_version}",
            details={
                "current_version": current_version,
                "bundle_version": bundle_version,
                "target_path": str(target_path),
                "update_available": True,
            },
        )


def update_bmad(project_path: str, preserve_config: bool = True) -> InstallResult:
    """
    Update existing BMAD installation while preserving configuration.

    Args:
        project_path: Path to user's project directory
        preserve_config: If True, preserve existing config.yaml

    Returns:
        InstallResult with status
    """
    target_path = Path(project_path) / "_bmad"

    # Verify existing installation
    if not target_path.exists():
        return InstallResult(
            status="failed",
            message="No existing BMAD installation found. Use install_bmad() instead.",
        )

    # Preserve config if requested
    config_backup = None
    config_path = target_path / "bmm" / "config.yaml"
    if preserve_config and config_path.exists():
        with open(config_path, "r") as f:
            config_backup = f.read()

    # Remove old installation and reinstall
    result = install_bmad(project_path, force=True)

    # Restore config if we backed it up
    if result.status == "success" and config_backup:
        try:
            with open(config_path, "w") as f:
                f.write(config_backup)
            result.message += " (configuration preserved)"
        except Exception as e:
            result.details["config_restore_error"] = str(e)

    return result


def validate_bmad_structure(bmad_path: Path) -> dict:
    """
    Validates BMAD directory structure.

    Args:
        bmad_path: Path to BMAD installation directory

    Returns:
        Dict with 'valid' bool and 'missing_files' list
    """
    required_files = [
        "bmm/config.yaml",
        "bmm/workflows/1-analysis/",
        "bmm/workflows/2-plan-workflows/",
        "bmm/workflows/3-solutioning/",
        "bmm/workflows/4-implementation/",
        "bmm/agents/pm.md",
        "bmm/agents/dev.md",
        "bmm/agents/tea.md",
        "bmm/agents/architect.md",
        "bmm/agents/sm.md",
        "core/",
        "VERSION",
        "README.md",
    ]

    missing_files = []
    for required in required_files:
        full_path = bmad_path / required
        if not full_path.exists():
            missing_files.append(required)

    return {"valid": len(missing_files) == 0, "missing_files": missing_files}


def get_bmad_version(bmad_path: Path) -> Optional[str]:
    """
    Returns BMAD version from VERSION file or config.

    Args:
        bmad_path: Path to BMAD installation directory

    Returns:
        Version string or None if not found
    """
    # Try VERSION file first
    version_file = bmad_path / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Fallback to config.yaml
    config_file = bmad_path / "bmm" / "config.yaml"
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                # Check for version in config comments (e.g., "# Version: 6.0.0-alpha.17")
                f.seek(0)
                for line in f:
                    if line.startswith("# Version:"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass

    return None


def compute_checksum(file_path: Path) -> str:
    """
    Compute SHA256 checksum of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of checksum
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def validate_file_integrity(bmad_path: Path, bundle_path: Path) -> dict:
    """
    Validate file integrity by comparing checksums.

    Args:
        bmad_path: Path to installed BMAD
        bundle_path: Path to BMAD bundle

    Returns:
        Dict with 'valid' bool and 'mismatched_files' list
    """
    critical_files = [
        "bmm/config.yaml",
        "bmm/agents/pm.md",
        "bmm/agents/dev.md",
        "bmm/agents/tea.md",
        "bmm/agents/architect.md",
        "bmm/agents/sm.md",
        "VERSION",
    ]

    mismatched_files = []
    for file_path in critical_files:
        target_file = bmad_path / file_path
        bundle_file = bundle_path / file_path

        if not target_file.exists():
            mismatched_files.append(f"{file_path} (missing)")
            continue

        if not bundle_file.exists():
            # Skip validation if bundle file doesn't exist
            continue

        target_checksum = compute_checksum(target_file)
        bundle_checksum = compute_checksum(bundle_file)

        if target_checksum != bundle_checksum:
            mismatched_files.append(f"{file_path} (checksum mismatch)")

    return {"valid": len(mismatched_files) == 0, "mismatched_files": mismatched_files}


def get_installation_info(project_path: str) -> Optional[dict]:
    """
    Get information about BMAD installation in project.

    Args:
        project_path: Path to user's project directory

    Returns:
        Dict with installation info or None if not installed
    """
    target_path = Path(project_path) / "_bmad"

    if not target_path.exists():
        return None

    validation = validate_bmad_structure(target_path)
    version = get_bmad_version(target_path)

    return {
        "installed": True,
        "path": str(target_path),
        "version": version,
        "valid": validation["valid"],
        "missing_files": validation.get("missing_files", []),
    }
