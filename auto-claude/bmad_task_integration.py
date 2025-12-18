"""
BMAD Task Integration
=====================

Routes task creation and execution to BMAD workflows.
Integrates BMAD natively by executing actual BMAD workflows from /_bmad/
and parsing artifacts from /_bmad-output/.

This module provides the bridge between Auto Claude's task execution flow
and BMAD Method workflows.

Debug Mode:
    Set DEBUG=true to enable detailed logging:
    - Workflow execution steps
    - Artifact parsing details
    - Conversion process
    - Error traces
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List

from debug import (
    debug,
    debug_detailed,
    debug_verbose,
    debug_success,
    debug_error,
    debug_warning,
    debug_section,
    debug_async_timer,
    is_debug_enabled,
)
from ui import Icons, icon, muted, print_section, print_status


async def run_bmad_planning(
    project_dir: Path,
    task_description: str,
    spec_dir: Optional[Path] = None,
    model: str = "claude-opus-4-5-20251101",
    auto_approve: bool = False,
    no_build: bool = False,
) -> Path:
    """
    Run BMAD planning workflows and convert artifacts to Auto Claude format.

    Flow:
    1. Execute BMAD workflows (outputs to _bmad-output/)
       - create-prd
       - create-architecture
       - create-epics-and-stories
    2. Parse BMAD artifacts from _bmad-output/
    3. Convert to implementation_plan.json in .auto-claude/specs/
    4. Optionally start build (run.py)

    Args:
        project_dir: Project root directory
        task_description: Task to build
        spec_dir: Existing spec directory (from UI), if None will create new
        model: Claude model to use
        auto_approve: Skip human review checkpoint
        no_build: Don't start build after planning

    Returns:
        Path to spec directory (.auto-claude/specs/XXX/)

    Raises:
        Exception: If BMAD workflows fail
    """
    from bmad_planning import BMADPlanning
    from adapters.bmad.adapter import BMADAdapter
    from review import ReviewState

    debug_section("bmad_integration", "BMAD Planning Started")
    debug("bmad_integration", "Planning configuration",
          task_description=task_description[:200],  # Truncate long descriptions
          model=model,
          auto_approve=auto_approve,
          no_build=no_build)

    # 1. Setup directories
    if not spec_dir:
        spec_dir = create_next_spec_dir(project_dir)
        debug("bmad_integration", "Created new spec directory", spec_dir=str(spec_dir))
    else:
        debug("bmad_integration", "Using existing spec directory", spec_dir=str(spec_dir))

    spec_dir = Path(spec_dir)
    spec_dir.mkdir(parents=True, exist_ok=True)

    # BMAD artifacts will go to _bmad-output/ (BMAD's native location)
    bmad_output = project_dir / "_bmad-output"
    bmad_output.mkdir(parents=True, exist_ok=True)

    debug_success("bmad_integration", "Directories configured",
                  spec_dir=str(spec_dir),
                  bmad_output=str(bmad_output))

    print()
    print_section("BMAD PLANNING", Icons.ROCKET)
    print()
    print(f"Task: {task_description}")
    print(f"Spec directory: {spec_dir}")
    print(f"BMAD output: {bmad_output}")
    print()

    # 2. Execute BMAD planning workflows
    print_status("Executing BMAD workflows from /_bmad/", "info")
    print()

    debug("bmad_integration", "Initializing BMAD planning engine",
          project_dir=str(project_dir))

    planner = BMADPlanning(str(project_dir))

    try:
        # Prepare context for workflow execution
        workflow_context = {
            "project_dir": str(project_dir),
            "task_description": task_description,
            "model": model,
            "verbose": is_debug_enabled(),  # Use debug mode for verbosity
        }

        debug_detailed("bmad_integration", "Workflow context prepared",
                      context=workflow_context)

        # Phase 1: Create Product Brief (optional - quick tasks may skip)
        # print_status("Phase 1: Creating product brief...", "info")
        # brief_result = planner.create_product_brief(
        #     context=workflow_context,
        #     callbacks=_create_workflow_callbacks("Product Brief")
        # )

        # Phase 2: Create PRD
        debug("bmad_integration", "Starting PRD workflow")
        print_status("Phase 1: Creating PRD...", "info")

        prd_result = planner.create_prd(
            context=workflow_context,
            callbacks=_create_workflow_callbacks("PRD")
        )

        if prd_result.status != "success":
            debug_error("bmad_integration", "PRD workflow failed",
                       status=prd_result.status,
                       error=prd_result.error)
            raise Exception(f"PRD creation failed: {prd_result.error}")

        debug_success("bmad_integration", "PRD workflow completed",
                     outputs=prd_result.outputs)
        print_status("✓ PRD created", "success")
        print()

        # Phase 3: Create Architecture
        debug("bmad_integration", "Starting Architecture workflow")
        print_status("Phase 2: Creating architecture...", "info")

        arch_result = planner.create_architecture(
            context=workflow_context,
            callbacks=_create_workflow_callbacks("Architecture")
        )

        if arch_result.status != "success":
            debug_error("bmad_integration", "Architecture workflow failed",
                       status=arch_result.status,
                       error=arch_result.error)
            raise Exception(f"Architecture creation failed: {arch_result.error}")

        debug_success("bmad_integration", "Architecture workflow completed",
                     outputs=arch_result.outputs)
        print_status("✓ Architecture created", "success")
        print()

        # Phase 4: Create Epics & Stories
        debug("bmad_integration", "Starting Epics & Stories workflow")
        print_status("Phase 3: Creating epics and stories...", "info")

        epics_result = planner.create_epics_and_stories(
            context=workflow_context,
            callbacks=_create_workflow_callbacks("Epics & Stories")
        )

        if epics_result.status != "success":
            debug_error("bmad_integration", "Epics workflow failed",
                       status=epics_result.status,
                       error=epics_result.error)
            raise Exception(f"Epics creation failed: {epics_result.error}")

        debug_success("bmad_integration", "Epics & Stories workflow completed",
                     outputs=epics_result.outputs)
        print_status("✓ Epics and stories created", "success")
        print()

        # 3. Parse BMAD artifacts from _bmad-output/
        debug("bmad_integration", "Parsing BMAD artifacts from _bmad-output/",
              bmad_output=str(bmad_output))
        print_status("Parsing BMAD artifacts...", "info")

        adapter = BMADAdapter()
        work_units = adapter.parse_work_units(project_dir)  # Epics

        if not work_units:
            debug_error("bmad_integration", "No epics found in BMAD output",
                       bmad_output=str(bmad_output))
            raise Exception("No epics found in BMAD output")

        debug_success("bmad_integration", "Parsed work units",
                     epic_count=len(work_units),
                     epic_ids=[wu.id for wu in work_units])
        print_status(f"✓ Parsed {len(work_units)} epics", "success")

        # Count total stories
        total_stories = sum(len(wu.tasks) for wu in work_units)

        debug_detailed("bmad_integration", "Story breakdown",
                      total_stories=total_stories,
                      stories_by_epic={wu.id: len(wu.tasks) for wu in work_units})
        print_status(f"✓ Found {total_stories} stories", "success")
        print()

        # 4. Convert BMAD artifacts to Auto Claude implementation_plan.json
        debug("bmad_integration", "Converting BMAD artifacts to implementation plan")
        print_status("Converting to implementation plan...", "info")

        implementation_plan = convert_bmad_to_implementation_plan(work_units)

        debug_verbose("bmad_integration", "Implementation plan generated",
                     plan=implementation_plan)

        # Save implementation plan to spec directory
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(implementation_plan, indent=2))

        debug_success("bmad_integration", "Implementation plan saved",
                     plan_file=str(plan_file),
                     total_phases=len(implementation_plan["phases"]),
                     total_stories=implementation_plan["total_stories"])
        print_status("✓ Implementation plan created", "success")
        print()

        # 5. Create spec.md summary
        debug("bmad_integration", "Generating spec.md summary")
        spec_md = spec_dir / "spec.md"
        spec_content = generate_spec_summary(task_description, work_units, bmad_output)
        spec_md.write_text(spec_content)

        debug_success("bmad_integration", "Spec summary created",
                     spec_file=str(spec_md))
        print_status("✓ Spec summary created", "success")
        print()

        # 6. Set approval state
        if auto_approve:
            review_state = ReviewState(approved=True, approved_by="auto-approved")
            review_state.save(spec_dir)
            print_status("Spec auto-approved", "success")

        print()
        print_status("BMAD planning complete", "success")
        print()
        print(f"  BMAD artifacts: {bmad_output}")
        print(f"  Implementation plan: {spec_dir}/implementation_plan.json")
        print()

        # 7. Start build if requested
        if not no_build:
            if not auto_approve:
                print()
                print_status("Review required before building", "info")
                print()
                print(f"  {muted('To approve and start build:')}")
                print(f"  python auto-claude/review.py --spec-dir {spec_dir}")
                print()
                return spec_dir

            # Start build with run.py
            print()
            print_section("STARTING BUILD", Icons.LIGHTNING)
            print()

            run_script = Path(__file__).parent / "run.py"
            run_cmd = [
                sys.executable,
                str(run_script),
                "--spec",
                spec_dir.name,
                "--project-dir",
                str(project_dir),
                "--framework",
                "bmad",
                "--auto-continue",
                "--force",  # Bypass approval check since we just approved
            ]

            print(f"  {muted('Running:')} {' '.join(run_cmd)}")
            print()

            # Execute run.py - replace current process
            os.execv(sys.executable, run_cmd)

        return spec_dir

    except Exception as e:
        debug_error("bmad_integration", "BMAD planning failed",
                   error=str(e),
                   error_type=type(e).__name__)

        # Log full traceback in debug mode
        if is_debug_enabled():
            import traceback
            debug_verbose("bmad_integration", "Full error traceback",
                         traceback=traceback.format_exc())

        print()
        print_status(f"BMAD planning failed: {e}", "error")

        # Only print traceback if not in debug mode (debug mode already logged it)
        if not is_debug_enabled():
            import traceback
            traceback.print_exc()

        raise


def run_bmad_development(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    max_iterations: Optional[int] = None,
    verbose: bool = False,
    auto_continue: bool = False,
    skip_qa: bool = False,
    base_branch: Optional[str] = None,
) -> None:
    """
    Run BMAD development workflow.

    Reads implementation_plan.json (converted from BMAD artifacts) and
    executes using Auto Claude's autonomous agent.

    Future: Could execute BMAD dev-story workflow for each subtask.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory (.auto-claude/specs/XXX/)
        model: Claude model to use
        max_iterations: Max agent iterations
        verbose: Verbose output
        auto_continue: Auto-continue mode
        skip_qa: Skip QA validation
        base_branch: Base branch for worktree

    Raises:
        Exception: If development fails
    """
    from agent import run_autonomous_agent
    from workspace import (
        WorkspaceMode,
        choose_workspace,
        finalize_workspace,
        setup_workspace,
    )

    debug_section("bmad_integration", "BMAD Development Started")
    debug("bmad_integration", "Development configuration",
          spec_dir=str(spec_dir),
          model=model,
          max_iterations=max_iterations,
          auto_continue=auto_continue,
          skip_qa=skip_qa)

    print()
    print_section("BMAD DEVELOPMENT", Icons.GEAR)
    print()
    print("Executing BMAD stories using Auto Claude agent")
    print(f"Reading plan from: {spec_dir}/implementation_plan.json")
    print()

    # Read and log implementation plan
    plan_file = spec_dir / "implementation_plan.json"
    if plan_file.exists():
        plan_data = json.loads(plan_file.read_text())
        debug_detailed("bmad_integration", "Implementation plan loaded",
                      framework=plan_data.get("framework"),
                      total_stories=plan_data.get("total_stories"),
                      phases=len(plan_data.get("phases", [])))
    else:
        debug_warning("bmad_integration", "Implementation plan not found",
                     expected_path=str(plan_file))

    # Workspace setup (same as native)
    debug("bmad_integration", "Configuring workspace")
    workspace_mode = choose_workspace(
        force_isolated=False,  # Let Auto Claude decide
        force_direct=False,
    )
    debug("bmad_integration", "Workspace mode selected",
          mode=str(workspace_mode))

    workspace_path, worktree_path, source_spec_dir = setup_workspace(
        project_dir=project_dir,
        spec_dir=spec_dir,
        mode=workspace_mode,
        base_branch=base_branch,
    )

    debug_success("bmad_integration", "Workspace configured",
                 workspace_path=str(workspace_path),
                 worktree_path=str(worktree_path) if worktree_path else "none")

    # Run the autonomous agent
    # This will execute the subtasks from implementation_plan.json
    try:
        debug("bmad_integration", "Starting autonomous agent execution")

        run_autonomous_agent(
            project_dir=workspace_path,
            spec_dir=spec_dir,
            source_spec_dir=source_spec_dir,
            model=model,
            max_iterations=max_iterations,
            verbose=verbose,
            auto_continue=auto_continue,
        )

        debug_success("bmad_integration", "Agent execution completed")

        # Finalize workspace (merge or keep isolated)
        debug("bmad_integration", "Finalizing workspace")

        finalize_workspace(
            project_dir=project_dir,
            spec_dir=spec_dir,
            mode=workspace_mode,
            worktree_path=worktree_path,
            skip_qa=skip_qa,
            model=model,
        )

        debug_success("bmad_integration", "BMAD development complete")

    except Exception as e:
        debug_error("bmad_integration", "BMAD development failed",
                   error=str(e),
                   error_type=type(e).__name__)

        if is_debug_enabled():
            import traceback
            debug_verbose("bmad_integration", "Full error traceback",
                         traceback=traceback.format_exc())

        print()
        print_status(f"BMAD development failed: {e}", "error")
        raise


# =============================================================================
# Helper Functions
# =============================================================================


def _create_workflow_callbacks(workflow_name: str) -> Dict:
    """
    Create callback functions for workflow execution.

    Args:
        workflow_name: Name of the workflow for display

    Returns:
        Dictionary of callback functions
    """
    def on_step_start(step_num: int, step_name: str):
        print(f"  Step {step_num}: {step_name}")

    def on_step_complete(step_num: int, output: str):
        print(f"  ✓ Step {step_num} complete")

    def on_workflow_complete(result: Dict):
        print(f"  ✓ {workflow_name} workflow complete")

    def on_error(error_msg: str):
        print(f"  ✗ Error: {error_msg}")

    return {
        "on_step_start": on_step_start,
        "on_step_complete": on_step_complete,
        "on_workflow_complete": on_workflow_complete,
        "on_error": on_error,
    }


def convert_bmad_to_implementation_plan(work_units: List) -> Dict:
    """
    Convert BMAD epics/stories to Auto Claude implementation_plan.json.

    Args:
        work_units: List of WorkUnit objects (epics) from BMADAdapter

    Returns:
        Implementation plan dictionary
    """
    debug_detailed("bmad_integration", "Converting work units to implementation plan",
                  epic_count=len(work_units))

    phases = []

    for epic in work_units:
        debug_verbose("bmad_integration", f"Converting epic {epic.id}",
                     epic_id=epic.id,
                     epic_title=epic.title,
                     story_count=len(epic.tasks))
        # Each epic becomes a phase
        subtasks = []

        for i, story in enumerate(epic.tasks, 1):
            # Each story becomes a subtask
            subtasks.append({
                "id": f"{epic.id}.{i}",
                "description": story.title,
                "details": story.description if hasattr(story, 'description') else "",
                "acceptance_criteria": story.checkpoints if hasattr(story, 'checkpoints') else [
                    "Story completed according to acceptance criteria",
                    "Tests passing",
                    "Code reviewed"
                ],
                "status": story.status.value if hasattr(story.status, 'value') else "pending",
            })

        phases.append({
            "name": epic.title,
            "description": epic.description if hasattr(epic, 'description') else f"Epic {epic.id}",
            "subtasks": subtasks
        })

    total_stories = sum(len(phase["subtasks"]) for phase in phases)

    return {
        "phases": phases,
        "framework": "bmad",
        "total_stories": total_stories,
        "bmad_output_path": "_bmad-output",  # Reference to BMAD artifacts
    }


def generate_spec_summary(
    task_description: str,
    work_units: List,
    bmad_output: Path
) -> str:
    """
    Generate spec.md summary from BMAD artifacts.

    Args:
        task_description: Original task description
        work_units: List of WorkUnit objects (epics)
        bmad_output: Path to BMAD output directory

    Returns:
        Markdown content for spec.md
    """
    lines = [
        "# Task Specification",
        "",
        "## Description",
        "",
        task_description,
        "",
        "## Planning Framework",
        "",
        "This spec was created using the **BMAD Method**.",
        "",
        f"BMAD artifacts are stored in: `{bmad_output}`",
        "",
        "### Planning Artifacts",
        "",
        "- PRD: `_bmad-output/prd.md`",
        "- Architecture: `_bmad-output/architecture.md`",
        "- Epics: `_bmad-output/epics.md`",
        "- Stories: `_bmad-output/stories/`",
        "",
        "## Implementation Plan",
        "",
        f"**Total Epics:** {len(work_units)}",
        f"**Total Stories:** {sum(len(wu.tasks) for wu in work_units)}",
        "",
        "### Epics",
        "",
    ]

    for epic in work_units:
        lines.append(f"#### Epic {epic.id}: {epic.title}")
        lines.append("")
        lines.append(f"**Stories:** {len(epic.tasks)}")
        lines.append(f"**Status:** {epic.status.value if hasattr(epic.status, 'value') else 'pending'}")
        lines.append("")

    lines.extend([
        "## Execution",
        "",
        "Stories are executed sequentially by Auto Claude's autonomous agent.",
        "Progress is tracked in `implementation_plan.json`.",
        "",
    ])

    return "\n".join(lines)


def create_next_spec_dir(project_dir: Path) -> Path:
    """
    Create next available spec directory in .auto-claude/specs/.

    Args:
        project_dir: Project root

    Returns:
        Path to new spec directory
    """
    specs_base = project_dir / ".auto-claude" / "specs"
    specs_base.mkdir(parents=True, exist_ok=True)

    # Find next available number
    existing_specs = [
        d for d in specs_base.iterdir()
        if d.is_dir() and d.name.split("-")[0].isdigit()
    ]

    if not existing_specs:
        next_num = 1
    else:
        numbers = [
            int(d.name.split("-")[0])
            for d in existing_specs
            if d.name.split("-")[0].isdigit()
        ]
        next_num = max(numbers) + 1

    # Create spec directory
    spec_name = f"{next_num:03d}-bmad-task"
    spec_dir = specs_base / spec_name

    return spec_dir
