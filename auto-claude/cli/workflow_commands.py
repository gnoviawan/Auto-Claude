"""
BMAD Workflow execution commands for CLI.

Handles workflow listing, execution, and status checking.
"""

import sys
from pathlib import Path

from bmad_detector import detect_bmad, is_bmad_ready
from bmad_engine import WorkflowEngine, WorkflowNotFoundError
from ui import Icons, icon


def handle_list_workflows_command(project_dir: Path) -> None:
    """
    Handle --list-workflows command.

    Args:
        project_dir: Project directory path
    """
    print(f"\n{icon(Icons.PACKAGE)} BMAD Workflows\n")

    # Check BMAD installation
    if not detect_bmad(str(project_dir)):
        print(f"{icon(Icons.ERROR)} BMAD is not installed")
        print(
            f"\n{icon(Icons.ARROW)} Install BMAD: python auto-claude/run.py --install-bmad\n"
        )
        sys.exit(1)

    # List workflows
    engine = WorkflowEngine(str(project_dir))
    workflows = engine.list_workflows()

    if not workflows:
        print(f"{icon(Icons.INFO)} No workflows found\n")
        return

    # Group by phase
    by_phase = {}
    for workflow in workflows:
        phase = workflow.get("phase", "unknown")
        if phase not in by_phase:
            by_phase[phase] = []
        by_phase[phase].append(workflow)

    # Display grouped workflows
    for phase in sorted(by_phase.keys()):
        print(f"\n{icon(Icons.FOLDER)} {phase}")
        for wf in by_phase[phase]:
            print(f"  • {wf['name']}")
            print(f"    ID: {wf['identifier']}")
            if wf.get("description"):
                print(f"    {wf['description']}")

    print()


def handle_run_workflow_command(
    project_dir: Path, workflow_name: str, resume: bool = False
) -> None:
    """
    Handle --run-workflow command.

    Args:
        project_dir: Project directory path
        workflow_name: Workflow to execute
        resume: Whether to resume from last checkpoint
    """
    print(f"\n{icon(Icons.ROCKET)} Running BMAD Workflow: {workflow_name}\n")

    # Check BMAD readiness
    ready, issues = is_bmad_ready(str(project_dir))
    if not ready:
        print(f"{icon(Icons.ERROR)} BMAD is not ready:")
        for issue in issues:
            print(f"  • {issue}")
        print()
        sys.exit(1)

    # Initialize engine
    engine = WorkflowEngine(str(project_dir))

    # Define callbacks for progress
    def on_step_start(step_num: int, step_name: str):
        print(f"{icon(Icons.GEAR)} Step {step_num}: {step_name}")

    def on_step_complete(step_num: int, output: str):
        print(f"{icon(Icons.SUCCESS)} Step {step_num} completed")

    def on_workflow_complete(outputs: dict):
        print(f"\n{icon(Icons.SUCCESS)} Workflow completed successfully")
        if outputs:
            print(f"\n{icon(Icons.INFO)} Outputs:")
            for path, details in outputs.items():
                print(f"  • {path}")

    def on_error(error_msg: str):
        print(f"\n{icon(Icons.ERROR)} {error_msg}")

    # Execute workflow
    try:
        result = engine.execute_workflow(
            workflow_name,
            context={"project_path": str(project_dir)},
            callbacks={
                "on_step_start": on_step_start,
                "on_step_complete": on_step_complete,
                "on_workflow_complete": on_workflow_complete,
                "on_error": on_error,
            },
        )

        if result.status == "success":
            sys.exit(0)
        else:
            sys.exit(1)

    except WorkflowNotFoundError as e:
        print(f"{icon(Icons.ERROR)} {str(e)}")
        print(
            f"\n{icon(Icons.INFO)} List available workflows: python auto-claude/run.py --list-workflows\n"
        )
        sys.exit(1)
    except Exception as e:
        print(f"{icon(Icons.ERROR)} Workflow execution failed: {str(e)}\n")
        sys.exit(1)


def handle_workflow_status_command(project_dir: Path, workflow_name: str) -> None:
    """
    Handle --workflow-status command.

    Args:
        project_dir: Project directory path
        workflow_name: Workflow to check
    """
    from bmad_state import WorkflowStateManager

    print(f"\n{icon(Icons.INFO)} Workflow Status: {workflow_name}\n")

    state_manager = WorkflowStateManager(str(project_dir))
    state = state_manager.get_state(workflow_name)

    # Display status
    status = state.get("status", "not_started")
    print(f"Status: {status}")

    if status == "not_started":
        print("No execution history")
    else:
        if "startedAt" in state:
            print(f"Started: {state['startedAt']}")

        completed = state.get("stepsCompleted", [])
        print(f"Steps completed: {len(completed)}")

        if completed:
            print("\nCompleted steps:")
            for step in completed:
                print(f"  ✓ {step}")

        if status == "completed" and "completedAt" in state:
            print(f"\nCompleted: {state['completedAt']}")

        if status == "failed":
            if "lastError" in state:
                print(f"\nError: {state['lastError']}")
            if "failedAtStep" in state:
                print(f"Failed at step: {state['failedAtStep']}")

    print()
