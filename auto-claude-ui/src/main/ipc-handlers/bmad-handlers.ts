/**
 * IPC handlers for BMAD Method installation and management
 */

import { ipcMain } from 'electron';
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import type { IPCResult } from '../../shared/types';

// ============================================
// BMAD Installation Types
// ============================================

export interface BMADInstallResult {
  status: 'success' | 'skipped' | 'failed';
  message: string;
  details?: {
    target_path?: string;
    output_path?: string;
    version?: string;
    current_version?: string;
    bundle_version?: string;
    update_available?: boolean;
    missing_files?: string[];
    [key: string]: unknown;
  };
}

export interface BMADInstallationInfo {
  installed: boolean;
  path?: string;
  version?: string;
  valid?: boolean;
  missing_files?: string[];
}

// ============================================
// Helper Functions
// ============================================

/**
 * Execute Python CLI command and parse JSON result
 */
function executePythonCLI(
  projectPath: string,
  command: string
): BMADInstallResult {
  try {
    const autoClaude = path.join(projectPath, 'auto-claude');
    const result = execSync(command, {
      cwd: projectPath,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe']
    });

    // Parse JSON output if available
    try {
      return JSON.parse(result);
    } catch {
      // If not JSON, return success with output as message
      return {
        status: 'success',
        message: result.trim()
      };
    }
  } catch (error: unknown) {
    const err = error as { stderr?: string; stdout?: string; message?: string };
    return {
      status: 'failed',
      message: err.stderr || err.stdout || err.message || 'Unknown error'
    };
  }
}

/**
 * Check if BMAD is installed in project
 */
function checkBMADInstallation(projectPath: string): BMADInstallationInfo {
  const bmadPath = path.join(projectPath, '_bmad');
  const bmadConfigPath = path.join(bmadPath, 'bmm', 'config.yaml');
  const versionPath = path.join(bmadPath, 'VERSION');

  if (!existsSync(bmadPath)) {
    return { installed: false };
  }

  let version: string | undefined;
  if (existsSync(versionPath)) {
    try {
      const fs = require('fs');
      version = fs.readFileSync(versionPath, 'utf-8').trim();
    } catch {
      version = undefined;
    }
  }

  const valid = existsSync(bmadConfigPath);

  return {
    installed: true,
    path: bmadPath,
    version,
    valid
  };
}

// ============================================
// IPC Handlers
// ============================================

/**
 * Register all BMAD-related IPC handlers
 */
export function registerBMADHandlers(): void {
  /**
   * Install BMAD Method to project
   */
  ipcMain.handle(
    'bmad:install',
    async (
      _event,
      {
        projectPath,
        force = false
      }: { projectPath: string; force?: boolean }
    ): Promise<IPCResult<BMADInstallResult>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        // Check if auto-claude directory exists
        const autoClaudePath = path.join(projectPath, 'auto-claude');
        if (!existsSync(autoClaudePath)) {
          return {
            success: false,
            error: 'auto-claude directory not found in project'
          };
        }

        // Build command
        const forceFlag = force ? ' --force' : '';
        const command = `python auto-claude/run.py --install-bmad${forceFlag}`;

        // Execute installation
        const result = executePythonCLI(projectPath, command);

        return {
          success: result.status === 'success',
          data: result,
          error: result.status !== 'success' ? result.message : undefined
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `BMAD installation failed: ${err.message}`
        };
      }
    }
  );

  /**
   * Update BMAD Method installation
   */
  ipcMain.handle(
    'bmad:update',
    async (
      _event,
      { projectPath }: { projectPath: string }
    ): Promise<IPCResult<BMADInstallResult>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        // Check if BMAD is installed
        const installInfo = checkBMADInstallation(projectPath);
        if (!installInfo.installed) {
          return {
            success: false,
            error: 'BMAD is not installed. Install it first using bmad:install'
          };
        }

        // Execute update
        const command = 'python auto-claude/run.py --update-bmad';
        const result = executePythonCLI(projectPath, command);

        return {
          success: result.status === 'success',
          data: result,
          error: result.status !== 'success' ? result.message : undefined
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `BMAD update failed: ${err.message}`
        };
      }
    }
  );

  /**
   * Get BMAD installation info
   */
  ipcMain.handle(
    'bmad:get-info',
    async (
      _event,
      { projectPath }: { projectPath: string }
    ): Promise<IPCResult<BMADInstallationInfo>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        const info = checkBMADInstallation(projectPath);

        return {
          success: true,
          data: info
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to get BMAD info: ${err.message}`
        };
      }
    }
  );

  /**
   * Check if BMAD bundle exists in auto-claude
   */
  ipcMain.handle(
    'bmad:check-bundle',
    async (
      _event,
      { projectPath }: { projectPath: string }
    ): Promise<IPCResult<{ exists: boolean; version?: string }>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        const bundlePath = path.join(projectPath, 'auto-claude', '_bmad');
        const versionPath = path.join(bundlePath, 'VERSION');

        if (!existsSync(bundlePath)) {
          return {
            success: true,
            data: { exists: false }
          };
        }

        let version: string | undefined;
        if (existsSync(versionPath)) {
          try {
            const fs = require('fs');
            version = fs.readFileSync(versionPath, 'utf-8').trim();
          } catch {
            version = undefined;
          }
        }

        return {
          success: true,
          data: {
            exists: true,
            version
          }
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to check BMAD bundle: ${err.message}`
        };
      }
    }
  );

  /**
   * Get BMAD configuration
   */
  ipcMain.handle(
    'bmad:get-config',
    async (
      _event,
      { projectPath }: { projectPath: string }
    ): Promise<IPCResult<Record<string, unknown>>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        const command = 'python -c "import sys; sys.path.insert(0, \'auto-claude\'); from bmad_config import read_bmad_config; import json; config = read_bmad_config(\'.\'); print(json.dumps(config.to_dict() if config else {}))"';
        const result = execSync(command, {
          cwd: projectPath,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe']
        });

        const config = JSON.parse(result.trim());

        return {
          success: true,
          data: config
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to get BMAD config: ${err.message}`
        };
      }
    }
  );

  /**
   * Save BMAD configuration
   */
  ipcMain.handle(
    'bmad:save-config',
    async (
      _event,
      {
        projectPath,
        config
      }: { projectPath: string; config: Record<string, unknown> }
    ): Promise<IPCResult<{ success: boolean; errors?: string[] }>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        if (!config) {
          return {
            success: false,
            error: 'Config data is required'
          };
        }

        const configJson = JSON.stringify(config).replace(/"/g, '\\"');
        const command = `python -c "import sys; sys.path.insert(0, 'auto-claude'); from bmad_config import write_bmad_config, BMADConfig, validate_config; import json; data = json.loads('${configJson}'); config = BMADConfig.from_dict(data); valid, errors = validate_config(config); print(json.dumps({'valid': valid, 'errors': errors, 'saved': write_bmad_config('.', config) if valid else False}))"`;

        const result = execSync(command, {
          cwd: projectPath,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe']
        });

        const response = JSON.parse(result.trim());

        if (!response.valid) {
          return {
            success: false,
            error: 'Validation failed',
            data: { success: false, errors: response.errors }
          };
        }

        if (!response.saved) {
          return {
            success: false,
            error: 'Failed to save configuration'
          };
        }

        return {
          success: true,
          data: { success: true }
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to save BMAD config: ${err.message}`
        };
      }
    }
  );

  /**
   * Get default BMAD configuration
   */
  ipcMain.handle(
    'bmad:get-default-config',
    async (
      _event,
      { projectPath }: { projectPath: string }
    ): Promise<IPCResult<Record<string, unknown>>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        const command = 'python -c "import sys; sys.path.insert(0, \'auto-claude\'); from bmad_config import get_default_config; import json; config = get_default_config(\'.\'); print(json.dumps(config.to_dict()))"';
        const result = execSync(command, {
          cwd: projectPath,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe']
        });

        const config = JSON.parse(result.trim());

        return {
          success: true,
          data: config
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to get default config: ${err.message}`
        };
      }
    }
  );

  /**
   * List available BMAD workflows
   */
  ipcMain.handle(
    'bmad:list-workflows',
    async (
      _event,
      { projectPath }: { projectPath: string }
    ): Promise<IPCResult<Array<Record<string, unknown>>>> => {
      try {
        if (!projectPath) {
          return {
            success: false,
            error: 'Project path is required'
          };
        }

        const command = 'python -c "import sys; sys.path.insert(0, \'auto-claude\'); from bmad_engine import WorkflowEngine; import json; engine = WorkflowEngine(\'.\'); workflows = engine.list_workflows(); print(json.dumps(workflows))"';
        const result = execSync(command, {
          cwd: projectPath,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe']
        });

        const workflows = JSON.parse(result.trim());

        return {
          success: true,
          data: workflows
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to list workflows: ${err.message}`
        };
      }
    }
  );

  /**
   * Get workflow state/status
   */
  ipcMain.handle(
    'bmad:workflow-status',
    async (
      _event,
      {
        projectPath,
        workflowName
      }: { projectPath: string; workflowName: string }
    ): Promise<IPCResult<Record<string, unknown>>> => {
      try {
        if (!projectPath || !workflowName) {
          return {
            success: false,
            error: 'Project path and workflow name are required'
          };
        }

        const command = `python -c "import sys; sys.path.insert(0, 'auto-claude'); from bmad_state import WorkflowStateManager; import json; sm = WorkflowStateManager('.'); state = sm.get_state('${workflowName}'); print(json.dumps(state))"`;
        const result = execSync(command, {
          cwd: projectPath,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe']
        });

        const state = JSON.parse(result.trim());

        return {
          success: true,
          data: state
        };
      } catch (error: unknown) {
        const err = error as Error;
        return {
          success: false,
          error: `Failed to get workflow status: ${err.message}`
        };
      }
    }
  );
}
