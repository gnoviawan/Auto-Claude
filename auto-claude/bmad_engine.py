"""
BMAD Method Workflow Execution Engine.

Orchestrates BMAD workflow execution by parsing workflow.yaml files
and executing steps sequentially using Auto Claude's agent system.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

# Import Auto Claude's agent system
from agents.session import run_agent_session
from core.client import create_client
from task_logger import LogPhase


@dataclass
class WorkflowStep:
    """Represents a single workflow step."""

    file: str
    name: str
    agent: str
    content: Optional[str] = None


@dataclass
class Workflow:
    """Represents a BMAD workflow."""

    name: str
    description: str
    phase: str
    path: Path
    steps: List[WorkflowStep]
    agent: Optional[str] = None
    category: Optional[str] = None
    dependencies: Optional[List[Dict]] = None
    outputs: Optional[List[Dict]] = None


@dataclass
class StepResult:
    """Result of step execution."""

    status: str  # "success", "failed"
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    status: str  # "success", "failed", "interrupted"
    outputs: Optional[Dict] = None
    failed_step: Optional[int] = None
    error: Optional[str] = None


class WorkflowNotFoundError(Exception):
    """Raised when workflow cannot be found."""

    pass


class WorkflowEngine:
    """
    Orchestrates BMAD workflow execution.

    This engine:
    1. Loads workflow.yaml files
    2. Parses workflow metadata and steps
    3. Executes steps sequentially using Auto Claude agents
    4. Tracks state and allows resumption
    """

    def __init__(self, project_path: str):
        """
        Initialize workflow engine.

        Args:
            project_path: Path to project directory
        """
        self.project_path = Path(project_path)
        self.bmad_path = self.project_path / "_bmad"
        self.workflows_path = self.bmad_path / "bmm" / "workflows"

        # Import state manager (Story 7.9)
        try:
            from bmad_state import WorkflowStateManager

            self.state_manager = WorkflowStateManager(project_path)
        except ImportError:
            # Fallback if state manager not yet implemented
            self.state_manager = None

    def find_workflow(self, workflow_name: str) -> Optional[Path]:
        """
        Find workflow directory by name.

        Searches across all phase directories.

        Args:
            workflow_name: Workflow identifier (e.g., "create-prd")

        Returns:
            Path to workflow directory or None
        """
        if not self.workflows_path.exists():
            return None

        # Search in all phase directories
        for phase_dir in sorted(self.workflows_path.iterdir()):
            if not phase_dir.is_dir():
                continue

            # Check direct child directories
            workflow_dir = phase_dir / workflow_name
            if workflow_dir.exists() and (workflow_dir / "workflow.md").exists():
                return workflow_dir

        return None

    def load_workflow(self, workflow_name: str) -> Workflow:
        """
        Load workflow metadata from workflow.md frontmatter.

        Args:
            workflow_name: Workflow to load (e.g., "create-prd")

        Returns:
            Workflow object with parsed metadata

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        workflow_path = self.find_workflow(workflow_name)
        if not workflow_path:
            raise WorkflowNotFoundError(f"Workflow '{workflow_name}' not found")

        workflow_file = workflow_path / "workflow.md"

        # Parse frontmatter
        metadata = self._parse_frontmatter(workflow_file)

        # Load step files
        steps = self._load_steps(workflow_path, metadata.get("steps", []))

        return Workflow(
            name=metadata.get("name", workflow_name),
            description=metadata.get("description", ""),
            phase=metadata.get("phase", ""),
            path=workflow_path,
            steps=steps,
            agent=metadata.get("agent"),
            category=metadata.get("category"),
            dependencies=metadata.get("dependencies", []),
            outputs=metadata.get("outputs", []),
        )

    def _parse_frontmatter(self, file_path: Path) -> Dict:
        """
        Parse YAML frontmatter from markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            Parsed frontmatter dictionary
        """
        content = file_path.read_text()

        if not content.startswith("---"):
            return {}

        # Find end of frontmatter
        end_marker = content.find("---", 3)
        if end_marker == -1:
            return {}

        frontmatter = content[3:end_marker].strip()

        try:
            return yaml.safe_load(frontmatter) or {}
        except Exception:
            return {}

    def _load_steps(
        self, workflow_path: Path, steps_metadata: List[Dict]
    ) -> List[WorkflowStep]:
        """
        Load workflow steps from metadata.

        Args:
            workflow_path: Path to workflow directory
            steps_metadata: Steps metadata from workflow.yaml

        Returns:
            List of WorkflowStep objects
        """
        steps = []

        # If steps not in frontmatter, scan steps/ directory
        if not steps_metadata:
            steps_dir = workflow_path / "steps"
            if steps_dir.exists():
                for step_file in sorted(steps_dir.glob("step-*.md")):
                    # Parse step metadata from its frontmatter
                    step_meta = self._parse_frontmatter(step_file)
                    steps.append(
                        WorkflowStep(
                            file=str(step_file.relative_to(workflow_path)),
                            name=step_meta.get(
                                "name", step_file.stem.replace("-", " ").title()
                            ),
                            agent=step_meta.get("agent", "pm"),
                        )
                    )
        else:
            # Use steps from metadata
            for step_meta in steps_metadata:
                steps.append(
                    WorkflowStep(
                        file=step_meta.get("file", ""),
                        name=step_meta.get("name", ""),
                        agent=step_meta.get("agent", "pm"),
                    )
                )

        return steps

    def execute_workflow(
        self,
        workflow_name: str,
        context: Optional[Dict] = None,
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> WorkflowResult:
        """
        Execute workflow steps sequentially.

        Args:
            workflow_name: Workflow to execute
            context: Execution context (project settings, etc.)
            callbacks: Optional callbacks for UI updates:
                - on_step_start(step_num, step_name)
                - on_step_complete(step_num, output)
                - on_workflow_complete(result)
                - on_error(error_message)

        Returns:
            WorkflowResult with status and outputs
        """
        context = context or {}
        callbacks = callbacks or {}

        try:
            workflow = self.load_workflow(workflow_name)
        except WorkflowNotFoundError as e:
            if "on_error" in callbacks:
                callbacks["on_error"](str(e))
            return WorkflowResult(status="failed", error=str(e))

        # Get workflow state (if state manager available)
        state = {}
        if self.state_manager:
            state = self.state_manager.get_state(workflow_name)

        # Resume from last completed step
        completed_steps = state.get("stepsCompleted", [])
        start_index = len(completed_steps)

        results = []

        for i, step in enumerate(workflow.steps[start_index:], start=start_index):
            step_num = i + 1

            # Callback: step start
            if "on_step_start" in callbacks:
                callbacks["on_step_start"](step_num, step.name)

            # Execute step
            step_result = self._execute_step(workflow, step, context)

            if step_result.status == "failed":
                error_msg = f"Step {step_num} failed: {step_result.error}"
                if "on_error" in callbacks:
                    callbacks["on_error"](error_msg)

                return WorkflowResult(
                    status="failed", failed_step=step_num, error=step_result.error
                )

            # Update state
            if self.state_manager:
                self.state_manager.mark_step_complete(workflow_name, step.name)

            results.append(step_result)

            # Callback: step complete
            if "on_step_complete" in callbacks:
                callbacks["on_step_complete"](step_num, step_result.output)

        # Mark workflow complete
        if self.state_manager:
            self.state_manager.mark_workflow_complete(workflow_name)

        # Collect outputs
        outputs = self._collect_outputs(workflow, results)

        # Callback: workflow complete
        if "on_workflow_complete" in callbacks:
            callbacks["on_workflow_complete"](outputs)

        return WorkflowResult(status="success", outputs=outputs)

    def _execute_step(
        self, workflow: Workflow, step: WorkflowStep, context: Dict
    ) -> StepResult:
        """
        Execute a single workflow step using Auto Claude's agent system.

        This method:
        1. Reads step markdown content
        2. Creates a Claude SDK client
        3. Runs an interactive agent session with the step content
        4. Returns result

        Args:
            workflow: Parent workflow
            step: Step to execute
            context: Execution context with keys:
                - project_dir: Project root directory (default: self.project_path)
                - spec_dir: Spec directory for memory (default: {project_path}/_bmad-output/.workflow-state)
                - model: Claude model to use (default: "claude-sonnet-4")
                - verbose: Show detailed output (default: False)

        Returns:
            StepResult with output or error
        """
        # Read step content
        step_file = workflow.path / step.file
        if not step_file.exists():
            return StepResult(status="failed", error=f"Step file not found: {step.file}")

        step_content = step_file.read_text()

        # Get execution parameters from context
        project_dir = Path(context.get("project_dir", self.project_path))
        spec_dir = Path(
            context.get(
                "spec_dir",
                self.project_path / "_bmad-output" / ".workflow-state" / workflow.name,
            )
        )
        spec_dir.mkdir(parents=True, exist_ok=True)

        model = context.get("model", "claude-sonnet-4")
        verbose = context.get("verbose", False)

        # Map BMAD agent types to Auto Claude agent types
        # BMAD agents: pm, dev, tea, architect, analyst, ux-designer
        # Auto Claude agents: planner, coder, qa_reviewer
        agent_type_mapping = {
            "pm": "planner",
            "dev": "coder",
            "tea": "qa_reviewer",
            "architect": "planner",
            "analyst": "planner",
            "ux-designer": "planner",
        }
        agent_type = agent_type_mapping.get(step.agent, "coder")

        try:
            # Create Claude SDK client for this step
            client = create_client(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model=model,
                agent_type=agent_type,
            )

            # Build the initial message from step content
            # This message contains the workflow step instructions
            initial_message = f"""You are executing a BMAD Method workflow step.

**Workflow:** {workflow.name}
**Step:** {step.name}
**Your Role:** {step.agent}

{step_content}

Please follow the instructions in the step carefully. This is a collaborative workflow - ask questions, gather user input, and work interactively to complete this step."""

            # Run the agent session (this is async, so we need to run it)
            status, response_text = asyncio.run(
                run_agent_session(
                    client=client,
                    message=initial_message,
                    spec_dir=spec_dir,
                    verbose=verbose,
                    phase=LogPhase.PLANNING,  # BMAD workflows are planning/design phase
                )
            )

            # Check result status
            if status == "complete" or status == "continue":
                return StepResult(
                    status="success",
                    output=response_text,
                )
            else:
                return StepResult(
                    status="failed",
                    error=f"Agent session ended with status: {status}",
                    output=response_text,
                )

        except Exception as e:
            return StepResult(
                status="failed",
                error=f"Error executing step: {str(e)}",
            )

    def _collect_outputs(
        self, workflow: Workflow, results: List[StepResult]
    ) -> Dict:
        """
        Collect workflow outputs from results.

        Args:
            workflow: Workflow definition
            results: List of step results

        Returns:
            Dictionary of collected outputs
        """
        outputs = {}

        # Collect defined outputs if they exist
        if workflow.outputs:
            for output_def in workflow.outputs:
                output_path = Path(self.project_path) / output_def["path"]
                if output_path.exists():
                    outputs[output_def["path"]] = {
                        "exists": True,
                        "size": output_path.stat().st_size,
                        "description": output_def.get("description", ""),
                    }

        return outputs

    def list_workflows(self) -> List[Dict]:
        """
        List all available workflows.

        Returns:
            List of workflow metadata dictionaries
        """
        workflows = []

        if not self.workflows_path.exists():
            return workflows

        for phase_dir in sorted(self.workflows_path.iterdir()):
            if not phase_dir.is_dir():
                continue

            for workflow_dir in sorted(phase_dir.iterdir()):
                if not workflow_dir.is_dir():
                    continue

                workflow_file = workflow_dir / "workflow.md"
                if not workflow_file.exists():
                    continue

                try:
                    metadata = self._parse_frontmatter(workflow_file)
                    workflows.append(
                        {
                            "name": metadata.get("name", workflow_dir.name),
                            "identifier": workflow_dir.name,
                            "description": metadata.get("description", ""),
                            "phase": metadata.get("phase", phase_dir.name),
                            "category": metadata.get("category", ""),
                            "path": str(workflow_dir),
                        }
                    )
                except Exception:
                    continue

        return workflows
