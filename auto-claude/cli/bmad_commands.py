"""
BMAD installation and management commands for Auto Claude CLI.

Handles installation, updates, and status reporting for BMAD Method framework.
"""

import sys
from pathlib import Path

from bmad_installer import (
    InstallResult,
    get_installation_info,
    install_bmad,
    update_bmad,
)
from ui import Icons, color, icon


def handle_install_bmad_command(project_dir: Path, force: bool = False) -> None:
    """
    Handle --install-bmad command.

    Args:
        project_dir: Project directory path
        force: If True, force reinstall even if BMAD exists
    """
    print(f"\n{icon(Icons.PACKAGE)} Installing BMAD Method to project...")
    print(f"{icon(Icons.FOLDER)} Project: {project_dir}\n")

    # Check if already installed
    if not force:
        install_info = get_installation_info(str(project_dir))
        if install_info and install_info["installed"]:
            print(
                f"{icon(Icons.WARNING)} BMAD Method is already installed (version {install_info['version']})"
            )
            print(f"{icon(Icons.INFO)} Location: {install_info['path']}\n")
            print("Options:")
            print(
                f"  {icon(Icons.ARROW)} Update BMAD:  python auto-claude/run.py --update-bmad"
            )
            print(
                f"  {icon(Icons.ARROW)} Force reinstall: python auto-claude/run.py --install-bmad --force\n"
            )
            sys.exit(0)

    # Perform installation
    result: InstallResult = install_bmad(str(project_dir), force=force)

    # Display result
    if result.status == "success":
        print(f"{icon(Icons.SUCCESS)} {result.message}")
        if result.details:
            print(f"\n{icon(Icons.INFO)} Installation Details:")
            print(f"  Target: {result.details.get('target_path', 'N/A')}")
            print(f"  Output: {result.details.get('output_path', 'N/A')}")
            print(f"  Version: {result.details.get('version', 'unknown')}")
        print(f"\n{icon(Icons.ROCKET)} Next Steps:")
        print("  1. Configure BMAD: Edit _bmad/bmm/config.yaml")
        print("  2. Run workflows: python auto-claude/run.py --spec <spec-name>")
        print("  3. Or via UI: Select BMAD framework in spec creation\n")

    elif result.status == "skipped":
        print(f"{icon(Icons.INFO)} {result.message}")
        if result.details and result.details.get("update_available"):
            print(
                f"\n{icon(Icons.ARROW)} Run update: python auto-claude/run.py --update-bmad\n"
            )

    else:  # failed
        print(f"{icon(Icons.ERROR)} {result.message}")
        if result.details:
            print(f"\n{icon(Icons.INFO)} Error Details:")
            for key, value in result.details.items():
                print(f"  {key}: {value}")
        print(f"\n{icon(Icons.INFO)} Troubleshooting:")
        print("  1. Ensure auto-claude/_bmad/ bundle exists")
        print("  2. Check file permissions")
        print("  3. Try with --force flag\n")
        sys.exit(1)


def handle_update_bmad_command(project_dir: Path) -> None:
    """
    Handle --update-bmad command.

    Args:
        project_dir: Project directory path
    """
    print(f"\n{icon(Icons.PACKAGE)} Updating BMAD Method installation...")
    print(f"{icon(Icons.FOLDER)} Project: {project_dir}\n")

    # Check if BMAD is installed
    install_info = get_installation_info(str(project_dir))
    if not install_info or not install_info["installed"]:
        print(
            f"{icon(Icons.ERROR)} BMAD Method is not installed in this project"
        )
        print(
            f"\n{icon(Icons.ARROW)} Install BMAD first: python auto-claude/run.py --install-bmad\n"
        )
        sys.exit(1)

    print(f"{icon(Icons.INFO)} Current version: {install_info.get('version', 'unknown')}")

    # Get bundle version
    bundle_path = Path(__file__).parent.parent / "_bmad"
    from bmad_installer import get_bmad_version

    bundle_version = get_bmad_version(bundle_path)
    print(f"{icon(Icons.INFO)} Bundle version: {bundle_version}\n")

    if install_info.get("version") == bundle_version:
        print(
            f"{icon(Icons.SUCCESS)} BMAD is already up to date ({bundle_version})\n"
        )
        sys.exit(0)

    # Perform update
    print(f"{icon(Icons.GEAR)} Updating BMAD (preserving configuration)...")
    result: InstallResult = update_bmad(str(project_dir), preserve_config=True)

    # Display result
    if result.status == "success":
        print(f"{icon(Icons.SUCCESS)} {result.message}")
        if result.details:
            print(f"\n{icon(Icons.INFO)} Update Details:")
            print(f"  Version: {result.details.get('version', 'unknown')}")
            print(f"  Location: {result.details.get('target_path', 'N/A')}")
        print(
            f"\n{icon(Icons.INFO)} Your project configuration has been preserved.\n"
        )

    else:  # failed
        print(f"{icon(Icons.ERROR)} {result.message}")
        if result.details:
            print(f"\n{icon(Icons.INFO)} Error Details:")
            for key, value in result.details.items():
                print(f"  {key}: {value}")
        print(f"\n{icon(Icons.INFO)} Troubleshooting:")
        print("  1. Backup your _bmad/bmm/config.yaml manually")
        print("  2. Try reinstall: python auto-claude/run.py --install-bmad --force")
        print("  3. Restore your config.yaml backup\n")
        sys.exit(1)
