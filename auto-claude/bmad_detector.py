"""
BMAD Method detection and validation.

Provides utilities to detect, validate, and query BMAD installations.
"""

from pathlib import Path
from typing import Optional

import yaml

from bmad_config import BMADConfig


def find_project_root(start_path: str) -> Optional[Path]:
    """
    Find project root by searching up the directory tree.

    Looks for markers like .git, auto-claude/, or _bmad/

    Args:
        start_path: Starting directory path

    Returns:
        Path to project root or None if not found
    """
    current = Path(start_path).resolve()

    # Maximum depth to search (prevent infinite loops)
    max_depth = 10
    depth = 0

    while depth < max_depth:
        # Check for project markers
        if any(
            [
                (current / ".git").exists(),
                (current / "auto-claude").exists(),
                (current / "_bmad").exists(),
            ]
        ):
            return current

        # Move up one directory
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break

        current = parent
        depth += 1

    return None


def detect_bmad(project_path: str) -> bool:
    """
    Returns True if valid BMAD installation exists.

    Args:
        project_path: Path to project directory

    Returns:
        True if BMAD is installed and valid, False otherwise
    """
    bmad_path = Path(project_path) / "_bmad"

    if not bmad_path.exists():
        return False

    return validate_bmad_structure(bmad_path)


def validate_bmad_structure(bmad_path: Path) -> bool:
    """
    Validates BMAD directory structure.

    Args:
        bmad_path: Path to BMAD installation directory

    Returns:
        True if structure is valid, False otherwise
    """
    required_paths = [
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
    ]

    for required in required_paths:
        full_path = bmad_path / required
        if not full_path.exists():
            return False

    return True


def get_bmad_config(project_path: str) -> Optional[dict]:
    """
    Returns parsed config.yaml or None if not found.

    Args:
        project_path: Path to project directory

    Returns:
        Parsed configuration dictionary or None
    """
    config_path = Path(project_path) / "_bmad" / "bmm" / "config.yaml"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def get_active_framework(project_path: str) -> str:
    """
    Returns 'bmad' or 'native' based on config.

    Args:
        project_path: Path to project directory

    Returns:
        'bmad' or 'native' framework identifier
    """
    config = get_bmad_config(project_path)

    if not config:
        return "native"

    return config.get("framework_mode", "native")


def get_bmad_version(project_path: str) -> Optional[str]:
    """
    Get BMAD version from installation.

    Args:
        project_path: Path to project directory

    Returns:
        Version string or None if not found
    """
    version_path = Path(project_path) / "_bmad" / "VERSION"

    if not version_path.exists():
        return None

    try:
        return version_path.read_text().strip()
    except Exception:
        return None


def get_bmad_workflows(project_path: str) -> list[dict]:
    """
    Get list of available BMAD workflows.

    Args:
        project_path: Path to project directory

    Returns:
        List of workflow metadata dictionaries
    """
    workflows = []
    bmad_path = Path(project_path) / "_bmad" / "bmm" / "workflows"

    if not bmad_path.exists():
        return workflows

    # Scan workflow directories
    for phase_dir in sorted(bmad_path.iterdir()):
        if not phase_dir.is_dir():
            continue

        # Each workflow has a workflow.md file
        workflow_file = phase_dir / "workflow.md"
        if not workflow_file.exists():
            continue

        # Parse workflow metadata from frontmatter
        try:
            metadata = parse_workflow_metadata(workflow_file)
            if metadata:
                metadata["path"] = str(phase_dir)
                workflows.append(metadata)
        except Exception:
            continue

    return workflows


def parse_workflow_metadata(workflow_file: Path) -> Optional[dict]:
    """
    Parse workflow metadata from frontmatter.

    Args:
        workflow_file: Path to workflow.md file

    Returns:
        Metadata dictionary or None
    """
    try:
        content = workflow_file.read_text()

        # Look for YAML frontmatter (between --- markers)
        if not content.startswith("---"):
            return None

        # Find end of frontmatter
        end_marker = content.find("---", 3)
        if end_marker == -1:
            return None

        # Extract and parse frontmatter
        frontmatter = content[3:end_marker].strip()
        metadata = yaml.safe_load(frontmatter)

        return metadata
    except Exception:
        return None


def get_bmad_agents(project_path: str) -> list[dict]:
    """
    Get list of available BMAD agents.

    Args:
        project_path: Path to project directory

    Returns:
        List of agent metadata dictionaries
    """
    agents = []
    agents_path = Path(project_path) / "_bmad" / "bmm" / "agents"

    if not agents_path.exists():
        return agents

    # Scan agent files
    for agent_file in sorted(agents_path.glob("*.md")):
        try:
            # Parse agent metadata from frontmatter (if exists)
            metadata = parse_workflow_metadata(agent_file)
            if not metadata:
                # Fallback: use filename as name
                metadata = {"name": agent_file.stem}

            metadata["file"] = str(agent_file)
            agents.append(metadata)
        except Exception:
            continue

    return agents


def is_bmad_ready(project_path: str) -> tuple[bool, list[str]]:
    """
    Check if BMAD is ready to use.

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (is_ready, list_of_issues)
    """
    issues = []

    # Check installation
    if not detect_bmad(project_path):
        issues.append("BMAD is not installed")
        return (False, issues)

    # Check configuration
    config = get_bmad_config(project_path)
    if not config:
        issues.append("BMAD configuration not found")
    else:
        # Validate required config fields
        required_fields = [
            "user_name",
            "project_name",
            "languages",
            "skill_level",
            "framework_mode",
        ]
        for field in required_fields:
            if not config.get(field):
                issues.append(f"Configuration missing required field: {field}")

    # Check workflows
    workflows = get_bmad_workflows(project_path)
    if not workflows:
        issues.append("No BMAD workflows found")

    # Check agents
    agents = get_bmad_agents(project_path)
    if len(agents) < 5:
        issues.append(f"Expected 5+ agents, found {len(agents)}")

    return (len(issues) == 0, issues)
