# CRITICAL GAP ANALYSIS - BMAD Integration

**Date:** December 18, 2025
**Severity:** CRITICAL BLOCKER
**Status:** ❌ **NOT PRODUCTION READY**

## User's Question

> "When the framework is auto-cloud. But now I have swapped to the BMAD method. Is it set up that it will start the process of using the planning phase of the BMAD method?"

## Answer

**NO.** The BMAD integration is completely isolated from the task execution flow.

---

## What I Built

I implemented:
1. ✅ BMAD workflow execution engine (`bmad_engine.py`)
2. ✅ BMAD CLI commands (`--run-workflow`, `--list-workflows`)
3. ✅ Multi-agent Party Mode
4. ✅ Framework detection utilities
5. ✅ Configuration management
6. ✅ State persistence

**These work IF you manually run BMAD CLI commands:**
```bash
python auto-claude/run.py --run-workflow create-prd
```

---

## What I DIDN'T Build

**The integration layer that connects UI task creation → BMAD workflows.**

---

## Current Task Execution Flow (Traced from Source)

### 1. UI: User Creates Task
**File:** `auto-claude-ui/src/main/ipc-handlers/task/execution-handlers.ts:75`
```typescript
agentManager.startSpecCreation(task.specId, project.path, taskDescription, specDir, task.metadata);
```

### 2. AgentManager: Starts Spec Creation
**File:** `auto-claude-ui/src/main/agent/agent-manager.ts:122`
```typescript
const args = [specRunnerPath, '--task', taskDescription, '--project-dir', projectPath];
```
**Calls:** `spec_runner.py` (Auto Claude's NATIVE spec creator)

### 3. spec_runner.py: Creates Spec
**File:** `auto-claude/runners/spec_runner.py`
```python
# Uses SpecOrchestrator (native Auto Claude)
# NO BMAD detection
# NO framework checking
```
**Result:** Creates spec using Auto Claude's native 3-8 phase pipeline.

### 4. UI: User Starts Task
**File:** `auto-claude-ui/src/main/ipc-handlers/task/execution-handlers.ts:104`
```typescript
agentManager.startTaskExecution(taskId, project.path, task.specId, options);
```

### 5. AgentManager: Starts Task Execution
**File:** `auto-claude-ui/src/main/agent/agent-manager.ts:174`
```typescript
const args = [runPath, '--spec', specId, '--project-dir', projectPath];
```
**Calls:** `run.py --spec [id]`

### 6. run.py: Main CLI Entry
**File:** `auto-claude/run.py:31`
```python
from cli import main
```

### 7. CLI Main: Routes to Build Command
**File:** `auto-claude/cli/main.py:392`
```python
handle_build_command(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model=model,
    # ... options
)
```

### 8. Build Command: Runs Native Agent
**File:** `auto-claude/cli/build_commands.py:82`
```python
from agent import run_autonomous_agent

# Later...
run_autonomous_agent(...)  # Native Auto Claude coder
```

**Result:** Uses Auto Claude's native planner and coder agents.

---

## Evidence: NO BMAD Detection

### spec_runner.py
```bash
$ grep -i "bmad\|framework" auto-claude/runners/spec_runner.py
# NO MATCHES
```

### run.py
```bash
$ grep -i "bmad\|framework" auto-claude/run.py
3:Auto Claude Framework
6:A multi-session autonomous coding framework
# Only in docstring, not in logic
```

### cli/main.py
```bash
$ grep -n "bmad\|framework" auto-claude/cli/main.py
225:    # BMAD installation
227:        "--install-bmad",
298:    # Handle --install-bmad command
305:    # Handle --update-bmad command
# Only installation commands, NOT in execution flow
```

### cli/build_commands.py
```bash
$ grep -i "bmad\|framework" auto-claude/cli/build_commands.py
# NO MATCHES
```

---

## What's Missing: The Integration Layer

To make BMAD work with the UI task flow, we need:

### 1. Framework Detection in Execution Flow
**Where:** `spec_runner.py` or `run.py` entry points

**What's needed:**
```python
from bmad_detector import get_active_framework

# At the start of execution
framework = get_active_framework(project_path)

if framework == "bmad":
    # Route to BMAD workflows
    execute_bmad_planning_workflow(project_path, task_description)
else:
    # Use native Auto Claude
    execute_native_spec_creation(...)
```

### 2. BMAD Planning Workflow Router
**Where:** New module `bmad_task_router.py`

**What's needed:**
```python
def execute_bmad_planning_workflow(project_path: str, task_description: str):
    """
    Execute BMAD planning workflow instead of native spec creation.

    Flow:
    1. Run create-product-brief workflow
    2. Run create-prd workflow
    3. Run create-architecture workflow
    4. Run create-epics-and-stories workflow
    5. Create implementation plan from stories
    """
    from bmad_engine import WorkflowEngine

    engine = WorkflowEngine(project_path)

    # Phase 1: Product Brief
    result = engine.execute_workflow("create-product-brief", context={
        "task_description": task_description
    })

    # Phase 2: PRD
    result = engine.execute_workflow("create-prd")

    # Phase 3: Architecture
    result = engine.execute_workflow("create-architecture")

    # Phase 4: Epics & Stories
    result = engine.execute_workflow("create-epics-and-stories")

    # Convert BMAD stories to Auto Claude implementation plan
    create_implementation_plan_from_stories(project_path, result)
```

### 3. BMAD Development Workflow Router
**Where:** `cli/build_commands.py`

**What's needed:**
```python
def handle_build_command(...):
    # Add at the start:
    from bmad_detector import get_active_framework

    framework = get_active_framework(project_dir)

    if framework == "bmad":
        # Use BMAD dev workflow
        execute_bmad_development_workflow(project_dir, spec_dir)
        return

    # Otherwise use native Auto Claude
    run_autonomous_agent(...)
```

### 4. BMAD Artifact → Auto Claude Format Converter
**Where:** New module `bmad_converters.py`

**What's needed:**
```python
def create_implementation_plan_from_stories(project_path: str, epics_result: dict):
    """
    Convert BMAD epics and stories to Auto Claude implementation_plan.json

    BMAD format:
    - Epics with user stories in _bmad-output/epics/

    Auto Claude format:
    - implementation_plan.json with phases and subtasks in .auto-claude/specs/XXX/
    """
    bmad_output_dir = Path(project_path) / "_bmad-output"
    epic_files = list(bmad_output_dir.glob("epics/*.md"))

    # Parse epics and stories
    phases = []
    for epic_file in epic_files:
        epic = parse_epic_file(epic_file)

        # Convert stories to subtasks
        subtasks = []
        for story in epic["stories"]:
            subtasks.append({
                "id": story["id"],
                "description": story["description"],
                "acceptance_criteria": story["acceptance_criteria"],
                "status": "pending"
            })

        phases.append({
            "name": epic["title"],
            "subtasks": subtasks
        })

    # Write to Auto Claude format
    spec_dir = find_or_create_spec_dir(project_path)
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps({
        "phases": phases,
        "framework": "bmad"
    }, indent=2))
```

### 5. BMAD QA Workflow Integration
**Where:** `cli/build_commands.py` or `qa_loop.py`

**What's needed:**
```python
def run_qa_validation_loop(...):
    framework = get_active_framework(project_dir)

    if framework == "bmad":
        # Use BMAD testarch workflows
        execute_bmad_qa_workflow(project_dir, spec_dir)
    else:
        # Use native Auto Claude QA
        run_native_qa_reviewer(...)
```

---

## Artifact Storage Mismatch

### Current Behavior
**Auto Claude stores in:** `.auto-claude/specs/XXX/`
- spec.md
- requirements.json
- context.json
- implementation_plan.json
- qa_report.md

**BMAD expects storage in:** `_bmad-output/`
- analysis/product-brief.md
- planning/prd.md
- solutioning/architecture.md
- solutioning/epics/*.md
- implementation/stories/*.md

**These are INCOMPATIBLE.** We need a bridge.

---

## What Actually Works Right Now

### ✅ Manual BMAD CLI
```bash
# These work fine:
python auto-claude/run.py --install-bmad
python auto-claude/run.py --list-workflows
python auto-claude/run.py --run-workflow create-prd
```

### ❌ UI Task Creation → BMAD
```
User creates task in UI → Uses NATIVE Auto Claude (ignores BMAD)
```

---

## Production Readiness: REVISED ASSESSMENT

### Previous Assessment: ✅ PRODUCTION READY
**This was WRONG.**

I tested individual BMAD components in isolation. They work when called directly via CLI.

### Corrected Assessment: ❌ NOT PRODUCTION READY

**Critical Gap:** BMAD is not integrated with the task execution flow.

**What's Missing:**
1. Framework detection in execution entry points
2. BMAD planning workflow router
3. BMAD development workflow router
4. Artifact format conversion (BMAD ↔ Auto Claude)
5. QA workflow integration

**Estimated Work:**
- 5 new modules (~500-800 lines of code)
- Modifications to 4 existing files
- End-to-end testing required
- UI updates may be needed

---

## Correct Answer to User's Question

> "When the framework is auto-cloud. But now I have swapped to the BMAD method. Is it set up that it will start the process of using the planning phase of the BMAD method?"

**NO.**

Currently:
1. BMAD configuration can be set
2. BMAD is detected as installed
3. But the task execution flow IGNORES it

**What happens:**
1. User creates task in UI
2. System runs NATIVE Auto Claude spec creation (spec_runner.py)
3. System runs NATIVE Auto Claude coder (run_autonomous_agent)
4. BMAD workflows are NEVER executed
5. Artifacts are stored in `.auto-claude/specs/`, not `_bmad-output/`

---

## Required Work to Make It Production Ready

### Epic 11: Task Execution Integration (NEW)
**Estimated:** 20-25 stories

#### Phase 1: Planning Integration (8 stories)
- Story 11.1: Add framework detection to spec_runner.py entry point
- Story 11.2: Create bmad_task_router.py module
- Story 11.3: Implement execute_bmad_planning_workflow()
- Story 11.4: Create workflow sequence (brief → PRD → architecture → epics)
- Story 11.5: Add progress callbacks for UI integration
- Story 11.6: Handle workflow errors and rollback
- Story 11.7: Update spec_runner.py to route based on framework
- Story 11.8: Test planning flow end-to-end

#### Phase 2: Development Integration (7 stories)
- Story 11.9: Add framework detection to run.py/build_commands.py
- Story 11.10: Create execute_bmad_development_workflow()
- Story 11.11: Implement dev-story workflow execution
- Story 11.12: Handle story-level execution and status tracking
- Story 11.13: Integrate with existing worktree system
- Story 11.14: Update progress reporting for UI
- Story 11.15: Test development flow end-to-end

#### Phase 3: Artifact Conversion (5 stories)
- Story 11.16: Create bmad_converters.py module
- Story 11.17: Implement BMAD stories → implementation_plan.json converter
- Story 11.18: Implement BMAD artifacts → Auto Claude spec.md converter
- Story 11.19: Bi-directional sync for mixed workflows
- Story 11.20: Test artifact conversion edge cases

#### Phase 4: QA Integration (5 stories)
- Story 11.21: Add framework detection to qa_loop.py
- Story 11.22: Create execute_bmad_qa_workflow()
- Story 11.23: Map BMAD testarch workflows to QA phases
- Story 11.24: Integrate QA results with UI
- Story 11.25: Test QA flow end-to-end

---

## Conclusion

I built BMAD integration components that work in isolation, but **failed to connect them to the actual task execution flow.**

This is like building a car engine without connecting it to the transmission and wheels.

**The engine works perfectly, but the car doesn't move.**

To make BMAD actually usable from the UI, we need Epic 11: Task Execution Integration.

**Apologies for the misleading "production ready" assessment.** I should have traced the full execution flow before making that claim.
