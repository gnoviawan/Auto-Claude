"""
BMAD Workflow State Management.

Persists workflow execution state to enable resumption across sessions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class WorkflowStateManager:
    """
    Manages workflow execution state persistence.

    State is stored in JSON files in _bmad-output/.workflow-state/
    """

    def __init__(self, project_path: str):
        """
        Initialize state manager.

        Args:
            project_path: Path to project directory
        """
        self.project_path = Path(project_path)
        self.state_dir = self.project_path / "_bmad-output" / ".workflow-state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def get_state_file(self, workflow_name: str) -> Path:
        """
        Get path to state file for workflow.

        Args:
            workflow_name: Workflow identifier

        Returns:
            Path to state JSON file
        """
        return self.state_dir / f"{workflow_name}.json"

    def get_state(self, workflow_name: str) -> Dict:
        """
        Get workflow execution state.

        Args:
            workflow_name: Workflow identifier

        Returns:
            State dictionary with:
                - status: "not_started", "in_progress", "completed", "failed"
                - stepsCompleted: List of completed step names
                - currentStep: Current step number (0-indexed)
                - startedAt: ISO timestamp
                - completedAt: ISO timestamp (if completed)
                - lastError: Error message (if failed)
        """
        state_file = self.get_state_file(workflow_name)

        if not state_file.exists():
            return {
                "status": "not_started",
                "stepsCompleted": [],
                "currentStep": 0,
            }

        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "status": "not_started",
                "stepsCompleted": [],
                "currentStep": 0,
            }

    def save_state(self, workflow_name: str, state: Dict) -> bool:
        """
        Save workflow execution state.

        Args:
            workflow_name: Workflow identifier
            state: State dictionary to save

        Returns:
            True if successful, False otherwise
        """
        state_file = self.get_state_file(workflow_name)

        try:
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception:
            return False

    def mark_step_complete(self, workflow_name: str, step_name: str) -> bool:
        """
        Mark a workflow step as completed.

        Args:
            workflow_name: Workflow identifier
            step_name: Name of completed step

        Returns:
            True if successful, False otherwise
        """
        state = self.get_state(workflow_name)

        # Initialize if needed
        if "stepsCompleted" not in state:
            state["stepsCompleted"] = []

        # Add step if not already completed
        if step_name not in state["stepsCompleted"]:
            state["stepsCompleted"].append(step_name)

        # Update status and timestamps
        if state.get("status") == "not_started":
            state["status"] = "in_progress"
            state["startedAt"] = datetime.now().isoformat()

        state["currentStep"] = len(state["stepsCompleted"])
        state["lastUpdated"] = datetime.now().isoformat()

        return self.save_state(workflow_name, state)

    def mark_workflow_complete(self, workflow_name: str) -> bool:
        """
        Mark workflow as completed.

        Args:
            workflow_name: Workflow identifier

        Returns:
            True if successful, False otherwise
        """
        state = self.get_state(workflow_name)

        state["status"] = "completed"
        state["completedAt"] = datetime.now().isoformat()
        state["lastUpdated"] = datetime.now().isoformat()

        return self.save_state(workflow_name, state)

    def mark_workflow_failed(
        self, workflow_name: str, error: str, step_num: Optional[int] = None
    ) -> bool:
        """
        Mark workflow as failed.

        Args:
            workflow_name: Workflow identifier
            error: Error message
            step_num: Optional step number where failure occurred

        Returns:
            True if successful, False otherwise
        """
        state = self.get_state(workflow_name)

        state["status"] = "failed"
        state["lastError"] = error
        if step_num is not None:
            state["failedAtStep"] = step_num
        state["failedAt"] = datetime.now().isoformat()
        state["lastUpdated"] = datetime.now().isoformat()

        return self.save_state(workflow_name, state)

    def reset_workflow(self, workflow_name: str) -> bool:
        """
        Reset workflow state to start fresh.

        Args:
            workflow_name: Workflow identifier

        Returns:
            True if successful, False otherwise
        """
        state_file = self.get_state_file(workflow_name)

        try:
            if state_file.exists():
                state_file.unlink()
            return True
        except Exception:
            return False

    def list_workflows(self) -> List[Dict]:
        """
        List all workflows with state.

        Returns:
            List of workflow state dictionaries
        """
        workflows = []

        for state_file in sorted(self.state_dir.glob("*.json")):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)

                state["workflow_name"] = state_file.stem
                workflows.append(state)
            except Exception:
                continue

        return workflows

    def get_resume_point(self, workflow_name: str) -> Optional[int]:
        """
        Get step index to resume from.

        Args:
            workflow_name: Workflow identifier

        Returns:
            Step index (0-based) to resume from, or None if complete
        """
        state = self.get_state(workflow_name)

        if state.get("status") == "completed":
            return None

        return state.get("currentStep", 0)

    def can_resume(self, workflow_name: str) -> bool:
        """
        Check if workflow can be resumed.

        Args:
            workflow_name: Workflow identifier

        Returns:
            True if workflow is in_progress and can resume
        """
        state = self.get_state(workflow_name)

        return state.get("status") == "in_progress"
