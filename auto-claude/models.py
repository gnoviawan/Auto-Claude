"""
Unified data models for Auto Claude.

Provides framework-agnostic models for tasks, epics, and artifacts.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Task:
    """Unified task/story model."""

    title: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    status: str = "pending"  # "pending" | "in_progress" | "completed" | "blocked"
    priority: str = "P2"  # "P0" | "P1" | "P2" | "P3"
    epic_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    subtasks: Optional[List["Task"]] = None
    estimated_effort: Optional[str] = None
    technical_notes: Optional[str] = None
    dependencies: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "status": self.status,
            "priority": self.priority,
            "epic_id": self.epic_id,
            "assigned_agent": self.assigned_agent,
            "estimated_effort": self.estimated_effort,
            "technical_notes": self.technical_notes,
            "dependencies": self.dependencies,
        }


@dataclass
class Epic:
    """Unified epic model."""

    title: str
    description: str
    user_value: str
    stories: List[Task] = field(default_factory=list)
    status: str = "not_started"  # "not_started" | "in_progress" | "completed"
    phase: str = "planning"  # "planning" | "solutioning" | "implementation"
    dependencies: Optional[List[str]] = None
    priority: str = "P1"
    estimated_effort: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "user_value": self.user_value,
            "stories": [s.to_dict() for s in self.stories],
            "status": self.status,
            "phase": self.phase,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
        }


@dataclass
class Artifact:
    """Unified artifact model (PRD, Architecture, UX, etc.)."""

    type: str  # "prd" | "architecture" | "ux" | "epic" | "story"
    title: str
    content: str
    metadata: Optional[dict] = None
    path: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "path": self.path,
        }
