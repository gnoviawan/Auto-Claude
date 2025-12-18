# BMAD Integration Debug Guide

**Date:** December 18, 2025
**Purpose:** Troubleshooting guide for BMAD Method integration with Auto Claude

---

## Quick Start: Enable Debug Mode

```bash
# Enable debug logging
export DEBUG=true

# Set verbosity level (1=basic, 2=detailed, 3=verbose)
export DEBUG_LEVEL=2

# Optional: Log to file
export DEBUG_LOG_FILE=.auto-claude/logs/bmad-debug.log

# Run BMAD planning
python auto-claude/runners/spec_runner.py \
  --task "Your task" \
  --framework bmad \
  --auto-approve
```

---

## Debug Levels

### Level 1: Basic (Default)
- Workflow start/complete messages
- Epic/story counts
- Critical errors

```bash
export DEBUG_LEVEL=1
```

**Example Output:**
```
[12:34:56.789] [DEBUG] [bmad_integration] Planning configuration
[12:34:57.123] [OK] [bmad_integration] Directories configured
[12:35:00.456] [DEBUG] [bmad_integration] Starting PRD workflow
[12:36:45.789] [OK] [bmad_integration] PRD workflow completed
```

### Level 2: Detailed
- Workflow context
- Artifact parsing details
- Implementation plan structure

```bash
export DEBUG_LEVEL=2
```

**Example Output:**
```
[12:34:56.789] [DEBUG] [bmad_integration] Planning configuration
  task_description: Add user authentication
  model: claude-opus-4-5-20251101
  auto_approve: True

[12:34:57.123] [DEBUG] [bmad_integration] Workflow context prepared
  context: {
    "project_dir": "/path/to/project",
    "task_description": "Add user authentication",
    "model": "claude-opus-4-5-20251101",
    "verbose": True
  }

[12:36:50.123] [DEBUG] [bmad_integration] Story breakdown
  total_stories: 12
  stories_by_epic: {
    "1": 5,
    "2": 7
  }
```

### Level 3: Verbose
- Full implementation plan JSON
- Detailed conversion logs
- Complete error tracebacks

```bash
export DEBUG_LEVEL=3
```

**Example Output:**
```
[12:37:00.456] [DEBUG] [bmad_integration] Converting epic 1
  epic_id: 1
  epic_title: User Authentication
  story_count: 5

[12:37:00.789] [DEBUG] [bmad_integration] Implementation plan generated
  plan: {
    "phases": [
      {
        "name": "Epic 1: User Authentication",
        "description": "Implement authentication system",
        "subtasks": [...]
      }
    ],
    "framework": "bmad",
    "total_stories": 12
  }
```

---

## Debug Locations by Component

### 1. Planning Phase

**Module:** `bmad_integration`

**Key Debug Points:**
- `Planning configuration` - Initial setup
- `Workflow context prepared` - Context passed to workflows
- `Starting [Workflow] workflow` - Each workflow execution
- `[Workflow] workflow completed` - Success confirmation
- `Parsed work units` - BMAD artifact parsing
- `Implementation plan saved` - Conversion complete

**Common Issues:**

#### No BMAD workflows found
```
[ERROR] [bmad_integration] PRD workflow failed
  status: failed
  error: Workflow 'create-prd' not found
```

**Solution:** Check BMAD installation
```bash
ls -la _bmad/bmm/workflows/2-plan-workflows/prd/
# Should show workflow.md
```

#### Empty BMAD output
```
[ERROR] [bmad_integration] No epics found in BMAD output
  bmad_output: /path/to/project/_bmad-output
```

**Solution:** Check workflow execution succeeded
```bash
ls -la _bmad-output/
# Should show: prd.md, architecture.md, epics.md, sprint-status.yaml
```

### 2. Workflow Execution

**Module:** `bmad_engine`

**Key Debug Points:**
- Workflow loading
- Step execution
- Artifact creation

**To add debug logging to engine (future):**
```python
# In bmad_engine.py
from debug import debug, debug_success, debug_error

def execute_workflow(self, workflow_name: str, ...):
    debug("bmad_engine", "Loading workflow", name=workflow_name)
    # ... workflow execution
    debug_success("bmad_engine", "Workflow complete")
```

### 3. Artifact Parsing

**Module:** `adapters/bmad/adapter`

**Key Debug Points:**
- Sprint status file location
- Story file discovery
- Epic/story parsing

**To add debug logging to adapter (future):**
```python
# In adapters/bmad/adapter.py
from debug import debug, debug_detailed

def parse_work_units(self, project_path: Path):
    debug("bmad_adapter", "Parsing work units", path=str(project_path))
    # ... parsing logic
    debug_detailed("bmad_adapter", "Parsed epics", epic_count=len(epics))
```

### 4. Development Phase

**Module:** `bmad_integration`

**Key Debug Points:**
- `Development configuration` - Initial settings
- `Implementation plan loaded` - Plan reading
- `Workspace mode selected` - Workspace setup
- `Agent execution completed` - Success

**Common Issues:**

#### Implementation plan not found
```
[WARN] [bmad_integration] Implementation plan not found
  expected_path: .auto-claude/specs/001/implementation_plan.json
```

**Solution:** Check planning completed successfully
```bash
cat .auto-claude/specs/001/implementation_plan.json
```

---

## Troubleshooting Workflow

### 1. Planning Fails

**Enable debug mode:**
```bash
DEBUG=true DEBUG_LEVEL=2 python auto-claude/runners/spec_runner.py \
  --task "Test task" \
  --framework bmad \
  --auto-approve \
  --no-build
```

**Check logs for:**
- ✅ `Workflow context prepared` - Context OK
- ❌ `[Workflow] workflow failed` - Which workflow failed?
- ✅ `Parsed work units` - Artifacts created

**Debug checklist:**
```bash
# 1. Verify BMAD installed
ls _bmad/bmm/workflows/

# 2. Check workflow files exist
ls _bmad/bmm/workflows/2-plan-workflows/prd/workflow.md
ls _bmad/bmm/workflows/3-solutioning/create-architecture/workflow.md
ls _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/workflow.md

# 3. Check BMAD output directory
ls -la _bmad-output/

# 4. Verify artifacts created
cat _bmad-output/prd.md
cat _bmad-output/architecture.md
cat _bmad-output/sprint-status.yaml
```

### 2. Artifact Parsing Fails

**Symptoms:**
```
[ERROR] [bmad_integration] No epics found in BMAD output
```

**Debug steps:**
```bash
# 1. Check sprint-status.yaml exists
cat _bmad-output/sprint-status.yaml

# 2. Check story files exist
ls -la _bmad-output/stories/

# 3. Manually test adapter
python -c "
from adapters.bmad.adapter import BMADAdapter
adapter = BMADAdapter()
work_units = adapter.parse_work_units('.')
print(f'Found {len(work_units)} epics')
"
```

### 3. Conversion Fails

**Symptoms:**
```
[ERROR] [bmad_integration] BMAD planning failed
  error: 'WorkUnit' object has no attribute 'tasks'
```

**Debug steps:**
```bash
# Enable verbose logging
DEBUG=true DEBUG_LEVEL=3 python auto-claude/runners/spec_runner.py \
  --task "Test" \
  --framework bmad \
  --auto-approve \
  --no-build

# Check full error traceback in logs
tail -100 .auto-claude/logs/bmad-debug.log
```

### 4. Development Fails

**Symptoms:**
```
[ERROR] [bmad_integration] BMAD development failed
```

**Debug steps:**
```bash
# 1. Check implementation plan exists
cat .auto-claude/specs/001/implementation_plan.json

# 2. Verify plan structure
python -c "
import json
plan = json.load(open('.auto-claude/specs/001/implementation_plan.json'))
print(f'Framework: {plan.get(\"framework\")}')
print(f'Phases: {len(plan.get(\"phases\", []))}')
print(f'Stories: {plan.get(\"total_stories\")}')
"

# 3. Run development with debug
DEBUG=true DEBUG_LEVEL=2 python auto-claude/run.py \
  --spec 001 \
  --framework bmad \
  --force
```

---

## Debug Log Analysis

### Reading Debug Logs

**Log format:**
```
[HH:MM:SS.mmm] [LEVEL] [module] message
  key1: value1
  key2: value2
```

**Example:**
```
[12:34:56.789] [DEBUG] [bmad_integration] Planning configuration
  task_description: Add user authentication
  model: claude-opus-4-5-20251101
  auto_approve: True
  no_build: False
```

### Log Levels

- `[DEBUG]` - Informational (cyan)
- `[INFO]` - Status update (cyan)
- `[OK]` - Success (green)
- `[WARN]` - Warning (yellow)
- `[ERROR]` - Error (red)

### Filtering Logs

```bash
# Only BMAD integration logs
grep "\[bmad_integration\]" .auto-claude/logs/bmad-debug.log

# Only errors
grep "\[ERROR\]" .auto-claude/logs/bmad-debug.log

# Specific workflow
grep "PRD workflow" .auto-claude/logs/bmad-debug.log

# Conversion details
grep "Converting" .auto-claude/logs/bmad-debug.log
```

---

## Performance Debugging

### Enable Timing

Debug timers are automatic in debug mode:

```bash
DEBUG=true python auto-claude/runners/spec_runner.py \
  --task "Test" \
  --framework bmad
```

**Output:**
```
[12:34:56.789] [DEBUG] [bmad_integration] Starting run_bmad_planning()
[12:36:45.123] [OK] [bmad_integration] Completed run_bmad_planning()
  elapsed_ms: 108334.5ms
```

### Identify Slow Workflows

```bash
# Find workflow execution times
grep "workflow completed" .auto-claude/logs/bmad-debug.log
```

---

## Common Error Patterns

### 1. Module Import Errors

```
[ERROR] [bmad_integration] BMAD planning failed
  error: No module named 'bmad_planning'
  error_type: ModuleNotFoundError
```

**Solution:** Check Python path
```bash
python -c "import bmad_planning; print('OK')"
```

### 2. Workflow Not Found

```
[ERROR] [bmad_integration] PRD workflow failed
  error: Workflow 'create-prd' not found
```

**Solution:** Reinstall BMAD
```bash
python auto-claude/run.py --install-bmad
```

### 3. Parsing Errors

```
[ERROR] [bmad_integration] No epics found in BMAD output
  bmad_output: /path/to/_bmad-output
```

**Solution:** Check workflow completed
```bash
cat _bmad-output/sprint-status.yaml
# Should contain epic entries
```

### 4. Conversion Errors

```
[ERROR] [bmad_integration] BMAD planning failed
  error: 'NoneType' object has no attribute 'value'
  error_type: AttributeError
```

**Solution:** Check BMAD artifact format
```bash
DEBUG=true DEBUG_LEVEL=3 python -c "
from adapters.bmad.adapter import BMADAdapter
adapter = BMADAdapter()
work_units = adapter.parse_work_units('.')
for wu in work_units:
    print(f'Epic {wu.id}: {wu.title}')
    print(f'  Status: {wu.status}')
    for task in wu.tasks:
        print(f'  - {task.title} ({task.status})')
"
```

---

## Debug Best Practices

### 1. Start with Level 2

```bash
export DEBUG=true
export DEBUG_LEVEL=2
```

Level 2 provides enough detail without overwhelming output.

### 2. Use Log Files for Complex Issues

```bash
export DEBUG_LOG_FILE=.auto-claude/logs/bmad-$(date +%Y%m%d-%H%M%S).log
```

This creates timestamped log files for each run.

### 3. Isolate the Problem

```bash
# Test planning only
python auto-claude/runners/spec_runner.py \
  --task "Test" \
  --framework bmad \
  --auto-approve \
  --no-build

# Test development only (after planning succeeds)
python auto-claude/run.py --spec 001 --framework bmad --force
```

### 4. Check Each Layer

1. **BMAD workflows exist** - `ls _bmad/bmm/workflows/`
2. **Workflows execute** - Check debug logs for workflow completion
3. **Artifacts created** - `ls _bmad-output/`
4. **Parsing works** - Test adapter manually
5. **Conversion works** - Check implementation_plan.json
6. **Development works** - Run with debug mode

---

## Reporting Issues

When reporting BMAD integration issues, include:

1. **Environment:**
   ```bash
   python --version
   echo $DEBUG
   echo $DEBUG_LEVEL
   ```

2. **BMAD installation status:**
   ```bash
   ls -la _bmad/bmm/workflows/
   ```

3. **Debug logs:** (Level 2 or 3)
   ```bash
   DEBUG=true DEBUG_LEVEL=2 python ... > debug.log 2>&1
   ```

4. **BMAD output:**
   ```bash
   ls -la _bmad-output/
   ```

5. **Implementation plan:**
   ```bash
   cat .auto-claude/specs/XXX/implementation_plan.json
   ```

6. **Error traceback:** (if available)

---

## Advanced Debugging

### Add Custom Debug Points

You can add debug logging anywhere in the code:

```python
from debug import debug, debug_detailed, debug_verbose

# Basic log
debug("my_module", "Doing something")

# Detailed log (level 2)
debug_detailed("my_module", "Processing item",
               item_id=123,
               status="pending")

# Verbose log (level 3)
debug_verbose("my_module", "Full data dump",
              data=large_object)
```

### Conditional Debugging

```python
from debug import is_debug_enabled

if is_debug_enabled():
    # Expensive debug operation
    analyze_and_log_data()
```

### Debug Decorators

```python
from debug import debug_timer, debug_async_timer

@debug_timer("my_module")
def expensive_function():
    # ...

@debug_async_timer("my_module")
async def async_function():
    # ...
```

---

## Summary

**Quick Debug Commands:**

```bash
# Basic debugging
DEBUG=true python auto-claude/runners/spec_runner.py \
  --task "Test" --framework bmad --auto-approve

# Detailed debugging
DEBUG=true DEBUG_LEVEL=2 python auto-claude/runners/spec_runner.py \
  --task "Test" --framework bmad --auto-approve

# Verbose debugging with log file
DEBUG=true DEBUG_LEVEL=3 DEBUG_LOG_FILE=debug.log \
  python auto-claude/runners/spec_runner.py \
  --task "Test" --framework bmad --auto-approve
```

**Key Debug Modules:**
- `bmad_integration` - Planning & development routing
- `bmad_engine` - Workflow execution
- `bmad_planning` - Workflow API
- `bmad_adapter` - Artifact parsing

**Happy Debugging! 🐛**
