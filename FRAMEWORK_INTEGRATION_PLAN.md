# Framework Integration Implementation Plan

**Date:** December 18, 2025
**Goal:** Native BMAD integration into Auto Claude with minimal artifact conversion

---

## Understanding: Framework Selection Architecture

### UI Layer (Frontend)
**Location:** `auto-claude-ui/src/renderer/stores/framework-store.ts`

```typescript
// Framework selection stored in Zustand + localStorage
selectedFramework: 'bmad' | 'native'  // Default: 'bmad'

// Persisted to:
// localStorage key: 'auto-claude-framework'
// Project settings: project.settings.framework
```

**Storage:**
- Zustand store (runtime)
- localStorage (persistence)
- Electron's `userData/store/projects.json` (per-project)

---

### Current Flow (Broken)
```
UI: User creates task
     ↓
UI: selectedFramework = 'bmad' (from store)
     ↓
UI: agentManager.startSpecCreation(taskId, projectPath, description)
     ⚠️ NO FRAMEWORK PASSED
     ↓
AgentManager: spec_runner.py --task "..." --project-dir ...
     ⚠️ NO FRAMEWORK FLAG
     ↓
Python: spec_runner.py (always uses native)
     ⚠️ NO FRAMEWORK CHECK
```

---

### Target Flow (Fixed)
```
UI: User creates task
     ↓
UI: selectedFramework = 'bmad' (from store)
     ↓
UI: agentManager.startSpecCreation(taskId, projectPath, description, specDir, {
      framework: 'bmad'  // ✅ PASS FRAMEWORK
    })
     ↓
AgentManager: spec_runner.py --task "..." --project-dir ... --framework bmad
     ✅ FRAMEWORK PASSED
     ↓
Python: spec_runner.py checks --framework flag
     ✅ Routes to BMAD or native
     ↓
If BMAD:
  - Run BMAD planning workflows
  - Save to .auto-claude/specs/XXX/ (same structure)
  - Create implementation_plan.json from BMAD stories
     ↓
If Native:
  - Run native spec creation (existing)
```

---

## Key Principle: Native Integration

**Goal:** Make BMAD work within Auto Claude's existing structure, not create a parallel system.

### Unified Storage Structure
```
project/
├── .auto-claude/
│   └── specs/
│       └── 001-feature/           # Unified spec directory
│           ├── spec.md            # Feature spec (BMAD or Native)
│           ├── requirements.json  # User requirements
│           ├── context.json       # Codebase context
│           ├── implementation_plan.json  # Subtasks/Stories
│           │                      # BMAD: converted from epics/stories
│           │                      # Native: from planner agent
│           ├── bmad/              # BMAD-specific artifacts (optional)
│           │   ├── product-brief.md
│           │   ├── prd.md
│           │   ├── architecture.md
│           │   └── epics/
│           │       ├── epic-1.md
│           │       └── epic-2.md
│           └── memory/            # Session memory (same for both)
```

**Rationale:**
- ✅ UI's task scanning still works (reads .auto-claude/specs/)
- ✅ Worktree system still works
- ✅ Progress tracking still works
- ✅ QA system still works
- ✅ BMAD artifacts preserved in `bmad/` subfolder
- ✅ Minimal conversion: BMAD stories → implementation_plan.json

---

## Implementation Plan

### Phase 1: UI → Backend Parameter Passing

#### Story 1.1: Add Framework to Metadata
**File:** `auto-claude-ui/src/main/agent/types.ts`

```typescript
export interface SpecCreationMetadata {
  requireReviewBeforeCoding?: boolean;
  framework?: 'bmad' | 'native';  // ADD THIS
}

export interface TaskExecutionOptions {
  parallel?: boolean;
  workers?: number;
  baseBranch?: string;
  framework?: 'bmad' | 'native';  // ADD THIS
}
```

#### Story 1.2: UI Passes Framework to AgentManager
**File:** `auto-claude-ui/src/main/ipc-handlers/task/execution-handlers.ts:75`

```typescript
// Get framework from project settings
const framework = project.settings?.framework || 'bmad';

agentManager.startSpecCreation(
  task.specId,
  project.path,
  taskDescription,
  specDir,
  {
    ...task.metadata,
    framework  // ✅ PASS FRAMEWORK
  }
);
```

#### Story 1.3: AgentManager Adds --framework Flag
**File:** `auto-claude-ui/src/main/agent/agent-manager.ts:122`

```typescript
const args = [specRunnerPath, '--task', taskDescription, '--project-dir', projectPath];

// Pass spec directory if provided
if (specDir) {
  args.push('--spec-dir', specDir);
}

// Pass framework if specified
if (metadata?.framework) {
  args.push('--framework', metadata.framework);  // ✅ ADD FRAMEWORK FLAG
}
```

Similarly for `startTaskExecution` at line 174:
```typescript
const framework = options.framework || 'bmad';
args.push('--framework', framework);
```

---

### Phase 2: Python CLI Framework Routing

#### Story 2.1: Add --framework to spec_runner.py
**File:** `auto-claude/runners/spec_runner.py:150`

```python
parser.add_argument(
    "--framework",
    type=str,
    choices=["bmad", "native"],
    default="bmad",
    help="Planning framework to use (default: bmad)",
)
```

#### Story 2.2: Route Based on Framework
**File:** `auto-claude/runners/spec_runner.py` (in main function, around line 200)

```python
def main():
    args = parser.parse_args()

    # Route based on framework
    if args.framework == "bmad":
        # Run BMAD planning workflows
        run_bmad_planning(
            project_dir=args.project_dir,
            task_description=args.task,
            spec_dir=args.spec_dir,
            model=args.model,
            auto_approve=args.auto_approve,
            no_build=args.no_build
        )
    else:
        # Use existing native spec creation
        run_native_spec_creation(args)  # Existing code
```

#### Story 2.3: Create BMAD Planning Router
**File:** `auto-claude/bmad_task_integration.py` (NEW)

```python
"""
BMAD Task Integration
=====================

Routes task creation and execution to BMAD workflows.
Integrates BMAD natively into Auto Claude's structure.
"""

from pathlib import Path
from typing import Optional

from bmad_engine import WorkflowEngine
from bmad_planning import BMADPlanning


def run_bmad_planning(
    project_dir: Path,
    task_description: str,
    spec_dir: Optional[Path] = None,
    model: str = "claude-opus-4-5-20251101",
    auto_approve: bool = False,
    no_build: bool = False
) -> Path:
    """
    Run BMAD planning workflows and create unified spec structure.

    Flow:
    1. Create spec directory (if not exists)
    2. Run BMAD planning workflows
    3. Convert BMAD artifacts to implementation_plan.json
    4. Optionally start build (run.py)

    Args:
        project_dir: Project root
        task_description: Task to build
        spec_dir: Existing spec directory (from UI)
        model: Claude model to use
        auto_approve: Skip human review
        no_build: Don't start build after planning

    Returns:
        Path to spec directory
    """
    # 1. Setup spec directory
    if not spec_dir:
        spec_dir = create_next_spec_dir(project_dir)

    spec_dir.mkdir(parents=True, exist_ok=True)
    bmad_dir = spec_dir / "bmad"  # BMAD artifacts subfolder
    bmad_dir.mkdir(exist_ok=True)

    print(f"Running BMAD planning for: {task_description}")
    print(f"Spec directory: {spec_dir}")

    # 2. Run BMAD planning workflows
    planner = BMADPlanning(str(project_dir))

    # Phase 1: Product Brief
    print("\n[1/4] Creating Product Brief...")
    brief_result = planner.create_product_brief(
        context={"task_description": task_description},
        callbacks=create_progress_callbacks()
    )

    # Phase 2: PRD
    print("\n[2/4] Creating PRD...")
    prd_result = planner.create_prd()

    # Phase 3: Architecture
    print("\n[3/4] Creating Architecture...")
    arch_result = planner.create_architecture()

    # Phase 4: Epics & Stories
    print("\n[4/4] Creating Epics & Stories...")
    epics_result = planner.create_epics_and_stories()

    # 3. Convert BMAD artifacts to Auto Claude format
    convert_bmad_to_autoclaude(
        project_dir=project_dir,
        spec_dir=spec_dir,
        bmad_dir=bmad_dir
    )

    # 4. Start build if requested
    if not no_build and (auto_approve or prompt_for_approval(spec_dir)):
        start_build(project_dir, spec_dir, model)

    return spec_dir


def convert_bmad_to_autoclaude(
    project_dir: Path,
    spec_dir: Path,
    bmad_dir: Path
) -> None:
    """
    Convert BMAD artifacts to Auto Claude format.

    BMAD artifacts (in _bmad-output/):
    - analysis/product-brief.md
    - planning/prd.md
    - solutioning/architecture.md
    - solutioning/epics/*.md

    Auto Claude format (in .auto-claude/specs/XXX/):
    - spec.md (combined from PRD + architecture)
    - implementation_plan.json (from epics/stories)
    - bmad/ (original artifacts preserved)
    """
    from bmad_artifact_converter import BMADArtifactConverter

    converter = BMADArtifactConverter(str(project_dir))

    # Copy BMAD artifacts to spec/bmad/ for preservation
    bmad_output = Path(project_dir) / "_bmad-output"
    if bmad_output.exists():
        import shutil
        shutil.copytree(bmad_output, bmad_dir, dirs_exist_ok=True)

    # Convert to Auto Claude format
    converter.create_spec_md(bmad_dir, spec_dir / "spec.md")
    converter.create_implementation_plan(bmad_dir, spec_dir / "implementation_plan.json")

    print(f"\n✅ BMAD artifacts converted to Auto Claude format")
    print(f"   Spec: {spec_dir / 'spec.md'}")
    print(f"   Plan: {spec_dir / 'implementation_plan.json'}")
    print(f"   BMAD artifacts preserved: {bmad_dir}")
```

#### Story 2.4: Create BMAD Artifact Converter
**File:** `auto-claude/bmad_artifact_converter.py` (NEW)

```python
"""
BMAD Artifact Converter
=======================

Converts BMAD planning artifacts to Auto Claude format.
"""

import json
from pathlib import Path
from typing import Dict, List


class BMADArtifactConverter:
    """Converts BMAD artifacts to Auto Claude format."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def create_spec_md(self, bmad_dir: Path, output_path: Path) -> None:
        """
        Create spec.md from BMAD PRD and architecture.

        Combines:
        - bmad/planning/prd.md
        - bmad/solutioning/architecture.md

        Into unified spec.md
        """
        prd_file = bmad_dir / "planning" / "prd.md"
        arch_file = bmad_dir / "solutioning" / "architecture.md"

        spec_content = []

        # Add PRD content
        if prd_file.exists():
            spec_content.append("# Product Requirements Document\n")
            spec_content.append(prd_file.read_text())
            spec_content.append("\n---\n")

        # Add Architecture content
        if arch_file.exists():
            spec_content.append("# Architecture\n")
            spec_content.append(arch_file.read_text())

        output_path.write_text("\n".join(spec_content))

    def create_implementation_plan(self, bmad_dir: Path, output_path: Path) -> None:
        """
        Create implementation_plan.json from BMAD epics and stories.

        BMAD structure:
        - bmad/solutioning/epics/epic-1.md
        - Each epic contains stories with acceptance criteria

        Auto Claude structure:
        {
          "phases": [
            {
              "name": "Epic 1: User Authentication",
              "subtasks": [
                {
                  "id": "1.1",
                  "description": "Implement login form",
                  "acceptance_criteria": [...],
                  "status": "pending"
                }
              ]
            }
          ]
        }
        """
        epics_dir = bmad_dir / "solutioning" / "epics"

        if not epics_dir.exists():
            # No epics, create empty plan
            output_path.write_text(json.dumps({
                "phases": [],
                "framework": "bmad"
            }, indent=2))
            return

        phases = []

        # Parse each epic file
        for epic_file in sorted(epics_dir.glob("*.md")):
            epic = self.parse_epic(epic_file)

            # Convert stories to subtasks
            subtasks = []
            for story in epic.get("stories", []):
                subtasks.append({
                    "id": story.get("id", f"{len(subtasks) + 1}"),
                    "description": story.get("description", ""),
                    "acceptance_criteria": story.get("acceptance_criteria", []),
                    "status": "pending",
                    "story_type": story.get("type", "feature")  # Preserve BMAD metadata
                })

            phases.append({
                "name": epic.get("title", epic_file.stem),
                "description": epic.get("description", ""),
                "subtasks": subtasks
            })

        plan = {
            "phases": phases,
            "framework": "bmad",
            "total_stories": sum(len(p["subtasks"]) for p in phases)
        }

        output_path.write_text(json.dumps(plan, indent=2))

    def parse_epic(self, epic_file: Path) -> Dict:
        """Parse epic markdown file to extract title, description, stories."""
        content = epic_file.read_text()

        # Simple parser - can be enhanced
        epic = {
            "title": "",
            "description": "",
            "stories": []
        }

        # Extract from frontmatter or headers
        # This is a simplified implementation
        lines = content.split("\n")

        for line in lines:
            if line.startswith("# "):
                epic["title"] = line[2:].strip()
            elif line.startswith("## Story"):
                # Parse story (simplified)
                story = {"id": "", "description": "", "acceptance_criteria": []}
                epic["stories"].append(story)

        return epic
```

---

### Phase 3: Development Execution Routing

#### Story 3.1: Add --framework to run.py
**File:** `auto-claude/cli/main.py:200`

```python
parser.add_argument(
    "--framework",
    type=str,
    choices=["bmad", "native"],
    help="Framework to use (detected from spec if not specified)",
)
```

#### Story 3.2: Detect Framework from Spec
**File:** `auto-claude/cli/build_commands.py:52`

```python
def handle_build_command(...):
    # Detect framework from implementation_plan.json
    plan_file = spec_dir / "implementation_plan.json"
    framework = "native"  # default

    if plan_file.exists():
        plan = json.loads(plan_file.read_text())
        framework = plan.get("framework", "native")

    # Override from CLI arg if provided
    if args.framework:
        framework = args.framework

    print(f"Framework: {framework}")

    # Route based on framework
    if framework == "bmad":
        run_bmad_development(project_dir, spec_dir, model, ...)
    else:
        run_native_development(project_dir, spec_dir, model, ...)
```

#### Story 3.3: BMAD Development Execution
**File:** `auto-claude/bmad_task_integration.py` (extend)

```python
def run_bmad_development(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    ...
) -> None:
    """
    Run BMAD development workflow.

    Uses dev-story workflow for each subtask in implementation_plan.json
    """
    plan = load_implementation_plan(spec_dir)

    for phase in plan["phases"]:
        for subtask in phase["subtasks"]:
            if subtask["status"] != "completed":
                # Execute story using BMAD dev-story workflow
                execute_bmad_story(project_dir, spec_dir, subtask, model)
```

---

### Phase 4: QA Integration

#### Story 4.1: Framework-Aware QA
**File:** `auto-claude/qa_loop.py:50`

```python
def run_qa_validation_loop(...):
    # Detect framework
    framework = detect_framework_from_spec(spec_dir)

    if framework == "bmad":
        # Use BMAD testarch workflows
        run_bmad_qa(project_dir, spec_dir, model)
    else:
        # Use native QA reviewer
        run_native_qa(project_dir, spec_dir, model)
```

---

## Summary: Minimal Integration Approach

### What We're NOT Doing (Avoiding Complexity)
❌ Duplicate storage systems (`_bmad-output/` AND `.auto-claude/specs/`)
❌ Complex bidirectional sync
❌ Separate BMAD task tracking system
❌ Forking Auto Claude's codebase

### What We ARE Doing (Native Integration)
✅ Store everything in `.auto-claude/specs/XXX/` (Auto Claude structure)
✅ BMAD artifacts preserved in `spec/bmad/` subfolder
✅ Simple one-way conversion: BMAD → implementation_plan.json
✅ UI passes framework parameter to backend
✅ Python routes to BMAD or native based on parameter
✅ Reuse Auto Claude's worktree, progress, QA systems

### Key Files to Create/Modify

**NEW:**
1. `auto-claude/bmad_task_integration.py` - BMAD planning/dev router
2. `auto-claude/bmad_artifact_converter.py` - BMAD → Auto Claude converter

**MODIFY:**
1. `auto-claude-ui/src/main/agent/types.ts` - Add framework to metadata
2. `auto-claude-ui/src/main/ipc-handlers/task/execution-handlers.ts` - Pass framework
3. `auto-claude-ui/src/main/agent/agent-manager.ts` - Add --framework flag
4. `auto-claude/runners/spec_runner.py` - Add --framework arg, route
5. `auto-claude/cli/main.py` - Add --framework arg
6. `auto-claude/cli/build_commands.py` - Detect framework, route
7. `auto-claude/qa_loop.py` - Framework-aware QA

**Total:** 2 new files, 7 modified files (~600 lines of code)

---

## Testing Plan

1. **UI → Backend Parameter Flow**
   - Change framework in UI settings
   - Create new task
   - Verify --framework flag passed to Python

2. **BMAD Planning Flow**
   - Create task with framework='bmad'
   - Verify BMAD workflows execute
   - Verify artifacts in .auto-claude/specs/XXX/bmad/
   - Verify implementation_plan.json created

3. **BMAD Development Flow**
   - Run build on BMAD spec
   - Verify dev-story workflow executes
   - Verify progress tracking works

4. **Native Flow (Regression)**
   - Change framework to 'native'
   - Create task
   - Verify native spec creation still works

---

## Migration Path

Users with existing BMAD installs:
1. Framework setting defaults to 'bmad'
2. Existing BMAD workflows in _bmad/ still work via CLI
3. New tasks use integrated flow with unified storage

---

Ready to implement!
