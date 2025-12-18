"""
Framework adapter pattern for Auto Claude.

Provides unified interface for BMAD and Native framework operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from models import Task, Epic, Artifact


class FrameworkAdapter(ABC):
    """
    Abstract adapter for framework-specific artifact creation and management.
    """

    def __init__(self, project_path: str):
        """
        Initialize adapter.

        Args:
            project_path: Path to project directory
        """
        self.project_path = Path(project_path)

    @abstractmethod
    def create_task(self, task: Task) -> str:
        """
        Create a task/story in framework-specific format.

        Args:
            task: Unified task model

        Returns:
            Task identifier (file path or ID)
        """
        pass

    @abstractmethod
    def update_task(self, task_id: str, updates: Dict) -> bool:
        """
        Update existing task with new data.

        Args:
            task_id: Task identifier
            updates: Dict of fields to update

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def create_epic(self, epic: Epic) -> str:
        """
        Create an epic in framework-specific format.

        Args:
            epic: Unified epic model

        Returns:
            Epic identifier
        """
        pass

    @abstractmethod
    def update_epic(self, epic_id: str, updates: Dict) -> bool:
        """
        Update existing epic.

        Args:
            epic_id: Epic identifier
            updates: Dict of fields to update

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def create_artifact(self, artifact: Artifact) -> str:
        """
        Create an artifact (PRD, Architecture, etc.).

        Args:
            artifact: Unified artifact model

        Returns:
            Artifact path
        """
        pass

    @abstractmethod
    def get_artifacts_directory(self) -> Path:
        """
        Get directory where artifacts are stored.

        Returns:
            Path to artifacts directory
        """
        pass


class BMADAdapter(FrameworkAdapter):
    """
    BMAD Method adapter implementation.

    Stores artifacts in _bmad-output/ directory.
    """

    def get_artifacts_directory(self) -> Path:
        """Get BMAD output directory."""
        return self.project_path / "_bmad-output"

    def create_task(self, task: Task) -> str:
        """
        Create task as story in epic file.

        BMAD stores stories within epic markdown files.

        Args:
            task: Task to create

        Returns:
            Story identifier
        """
        # In BMAD, stories are embedded in epic files
        # So this updates the parent epic file
        if not task.epic_id:
            raise ValueError("Task must have epic_id for BMAD adapter")

        epic_file = self.get_artifacts_directory() / f"{task.epic_id}.md"

        # Read epic file, append story
        # (Simplified - real implementation would parse and insert)

        story_id = f"{task.epic_id}-{task.title.lower().replace(' ', '-')}"
        return story_id

    def update_task(self, task_id: str, updates: Dict) -> bool:
        """Update task in epic file."""
        # Parse epic file, find story, update fields
        # (Simplified implementation)
        return True

    def create_epic(self, epic: Epic) -> str:
        """
        Create epic as markdown file.

        Args:
            epic: Epic to create

        Returns:
            Epic file path
        """
        output_dir = self.get_artifacts_directory()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate epic filename
        epic_id = epic.title.lower().replace(" ", "-")
        epic_file = output_dir / f"epic-{epic_id}.md"

        # Generate markdown content
        content = self._generate_epic_markdown(epic)

        # Write file
        epic_file.write_text(content)

        return str(epic_file)

    def update_epic(self, epic_id: str, updates: Dict) -> bool:
        """Update epic file."""
        epic_file = self.get_artifacts_directory() / f"{epic_id}.md"

        if not epic_file.exists():
            return False

        # Read, update, write
        # (Simplified implementation)
        return True

    def create_artifact(self, artifact: Artifact) -> str:
        """
        Create artifact file.

        Args:
            artifact: Artifact to create

        Returns:
            Artifact file path
        """
        output_dir = self.get_artifacts_directory()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        if artifact.path:
            artifact_file = output_dir / artifact.path
        else:
            artifact_file = output_dir / f"{artifact.type}.md"

        # Write content
        artifact_file.write_text(artifact.content)

        return str(artifact_file)

    def _generate_epic_markdown(self, epic: Epic) -> str:
        """
        Generate epic markdown content.

        Args:
            epic: Epic model

        Returns:
            Markdown content
        """
        lines = [
            f"# Epic: {epic.title}",
            "",
            f"**Status:** {epic.status}",
            f"**Phase:** {epic.phase}",
            f"**Priority:** {epic.priority}",
            "",
            "## Description",
            "",
            epic.description,
            "",
            "## User Value",
            "",
            epic.user_value,
            "",
        ]

        if epic.dependencies:
            lines.extend(
                [
                    "## Dependencies",
                    "",
                    *[f"- {dep}" for dep in epic.dependencies],
                    "",
                ]
            )

        lines.extend(["## Stories", ""])

        for i, story in enumerate(epic.stories, 1):
            lines.extend(
                [
                    f"### Story {i}: {story.title}",
                    "",
                    story.description,
                    "",
                    "**Acceptance Criteria:**",
                    "",
                    *[f"- {ac}" for ac in story.acceptance_criteria],
                    "",
                ]
            )

        return "\n".join(lines)


class NativeAdapter(FrameworkAdapter):
    """
    Native Auto Claude adapter implementation.

    Stores artifacts in .auto-claude/specs/ directory.
    """

    def get_artifacts_directory(self) -> Path:
        """Get native specs directory."""
        return self.project_path / ".auto-claude" / "specs"

    def create_task(self, task: Task) -> str:
        """Create task as spec file."""
        specs_dir = self.get_artifacts_directory()
        specs_dir.mkdir(parents=True, exist_ok=True)

        # Generate spec number
        existing_specs = list(specs_dir.glob("*"))
        spec_num = len(existing_specs) + 1

        # Generate spec directory
        task_id = f"{spec_num:03d}-{task.title.lower().replace(' ', '-')}"
        spec_dir = specs_dir / task_id
        spec_dir.mkdir(exist_ok=True)

        # Create spec.md
        spec_file = spec_dir / "spec.md"
        content = self._generate_spec_markdown(task)
        spec_file.write_text(content)

        return task_id

    def update_task(self, task_id: str, updates: Dict) -> bool:
        """Update task spec file."""
        spec_file = self.get_artifacts_directory() / task_id / "spec.md"

        if not spec_file.exists():
            return False

        # Update spec file
        # (Simplified implementation)
        return True

    def create_epic(self, epic: Epic) -> str:
        """
        Create epic - in Native, epics are collections of specs.

        Args:
            epic: Epic to create

        Returns:
            Epic identifier
        """
        # In Native framework, epics don't have special files
        # Each story becomes a separate spec
        epic_id = epic.title.lower().replace(" ", "-")

        for story in epic.stories:
            story.epic_id = epic_id
            self.create_task(story)

        return epic_id

    def update_epic(self, epic_id: str, updates: Dict) -> bool:
        """Update epic (updates constituent specs)."""
        return True

    def create_artifact(self, artifact: Artifact) -> str:
        """
        Create artifact file.

        Args:
            artifact: Artifact to create

        Returns:
            Artifact file path
        """
        output_dir = self.get_artifacts_directory().parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        if artifact.path:
            artifact_file = output_dir / artifact.path
        else:
            artifact_file = output_dir / f"{artifact.type}.md"

        # Write content
        artifact_file.write_text(artifact.content)

        return str(artifact_file)

    def _generate_spec_markdown(self, task: Task) -> str:
        """Generate spec.md content."""
        lines = [
            f"# {task.title}",
            "",
            task.description,
            "",
            "## Acceptance Criteria",
            "",
            *[f"- {ac}" for ac in task.acceptance_criteria],
            "",
        ]

        if task.technical_notes:
            lines.extend(["## Technical Notes", "", task.technical_notes, ""])

        return "\n".join(lines)


def get_adapter(project_path: str) -> FrameworkAdapter:
    """
    Get appropriate framework adapter for project.

    Args:
        project_path: Path to project directory

    Returns:
        Framework adapter instance
    """
    from bmad_detector import get_active_framework

    framework = get_active_framework(project_path)

    if framework == "bmad":
        return BMADAdapter(project_path)
    else:
        return NativeAdapter(project_path)
