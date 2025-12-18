"""
Agent routing for Auto Claude.

Routes to appropriate agents based on framework detection.
"""

from pathlib import Path
from typing import Dict, Optional

from bmad_detector import get_active_framework, detect_bmad


class AgentRouter:
    """
    Routes execution to appropriate agents based on framework.

    BMAD projects → BMAD agents (pm.md, dev.md, tea.md)
    Native projects → Native prompts (planner.md, coder.md, qa_reviewer.md)
    """

    def __init__(self, project_path: str):
        """
        Initialize router.

        Args:
            project_path: Path to project directory
        """
        self.project_path = Path(project_path)
        self.framework = get_active_framework(str(project_path))

    def get_agent_prompt_path(self, agent_type: str) -> Optional[Path]:
        """
        Get path to agent prompt file.

        Args:
            agent_type: Type of agent (planner, coder, qa_reviewer, pm, dev, tea, etc.)

        Returns:
            Path to agent prompt file or None if not found
        """
        if self.framework == "bmad":
            return self._get_bmad_agent_path(agent_type)
        else:
            return self._get_native_agent_path(agent_type)

    def _get_bmad_agent_path(self, agent_type: str) -> Optional[Path]:
        """
        Get BMAD agent prompt path.

        Maps Auto Claude agent types to BMAD agents:
        - planner → pm (Product Manager)
        - coder → dev (Developer)
        - qa_reviewer → tea (Test Engineer & Architect)
        - qa_fixer → dev (Developer)
        """
        # Map Auto Claude agent types to BMAD agents
        agent_mapping = {
            "planner": "pm",
            "coder": "dev",
            "qa_reviewer": "tea",
            "qa_fixer": "dev",
            "architect": "architect",
        }

        bmad_agent = agent_mapping.get(agent_type, agent_type)

        bmad_agents_dir = self.project_path / "_bmad" / "bmm" / "agents"
        agent_file = bmad_agents_dir / f"{bmad_agent}.md"

        if agent_file.exists():
            return agent_file

        return None

    def _get_native_agent_path(self, agent_type: str) -> Optional[Path]:
        """Get Native agent prompt path."""
        prompts_dir = self.project_path / "auto-claude" / "prompts"
        agent_file = prompts_dir / f"{agent_type}.md"

        if agent_file.exists():
            return agent_file

        return None

    def get_agent_display_name(self, agent_type: str) -> str:
        """
        Get display name for agent (for UI/terminal).

        Args:
            agent_type: Type of agent

        Returns:
            Display name (e.g., "BMAD PM Agent", "Native Planner")
        """
        if self.framework == "bmad":
            # Map to BMAD agent names
            bmad_names = {
                "planner": "BMAD PM Agent",
                "coder": "BMAD Developer",
                "qa_reviewer": "BMAD Test Engineer",
                "qa_fixer": "BMAD Developer",
                "architect": "BMAD Architect",
                "pm": "BMAD PM Agent",
                "dev": "BMAD Developer",
                "tea": "BMAD Test Engineer",
                "sm": "BMAD Scrum Master",
            }
            return bmad_names.get(agent_type, f"BMAD {agent_type.title()}")
        else:
            # Native agent names
            native_names = {
                "planner": "Native Planner",
                "coder": "Native Coder",
                "qa_reviewer": "Native QA Reviewer",
                "qa_fixer": "Native QA Fixer",
            }
            return native_names.get(agent_type, f"Native {agent_type.title()}")

    def should_use_bmad_workflow(self, workflow_name: str) -> bool:
        """
        Check if BMAD workflow should be used.

        Args:
            workflow_name: Workflow identifier

        Returns:
            True if BMAD workflow should be used
        """
        return self.framework == "bmad" and detect_bmad(str(self.project_path))

    def get_framework_info(self) -> Dict:
        """
        Get framework information.

        Returns:
            Dictionary with framework details
        """
        info = {
            "framework": self.framework,
            "bmad_installed": detect_bmad(str(self.project_path)),
        }

        if info["bmad_installed"]:
            from bmad_detector import get_bmad_version

            info["bmad_version"] = get_bmad_version(str(self.project_path))

        return info
