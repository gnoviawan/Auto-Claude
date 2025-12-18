/**
 * BmadConfigDialog - Dialog for configuring BMAD Method settings
 *
 * Allows users to configure the 5 required BMAD variables:
 * - user_name
 * - project_name
 * - languages
 * - skill_level
 * - framework_mode
 */

import { useState, useEffect } from 'react';
import { Loader2, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';
import { Alert, AlertDescription } from './ui/alert';
import { useProjectStore } from '../stores/project-store';

/**
 * BMAD Configuration interface
 */
interface BMADConfig {
  user_name: string;
  project_name: string;
  languages: string;
  skill_level: 'junior' | 'mid' | 'senior' | 'principal';
  framework_mode: 'bmad' | 'native';
}

/**
 * Props for BmadConfigDialog
 */
interface BmadConfigDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Optional callback when config is saved successfully */
  onSaved?: () => void;
}

/**
 * BmadConfigDialog component
 */
export function BmadConfigDialog({
  open,
  onOpenChange,
  onSaved
}: BmadConfigDialogProps): JSX.Element {
  const { currentProject } = useProjectStore();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const [config, setConfig] = useState<BMADConfig>({
    user_name: '',
    project_name: '',
    languages: '',
    skill_level: 'mid',
    framework_mode: 'native'
  });

  // Load config when dialog opens
  useEffect(() => {
    if (open && currentProject) {
      loadConfig();
    }
  }, [open, currentProject]);

  /**
   * Load BMAD configuration
   */
  const loadConfig = async (): Promise<void> => {
    if (!currentProject) return;

    setLoading(true);
    setError(null);

    try {
      // Try to load existing config
      const result = await window.electron.invoke('bmad:get-config', {
        projectPath: currentProject.path
      });

      if (result.success && result.data && Object.keys(result.data).length > 0) {
        setConfig(result.data as BMADConfig);
      } else {
        // Load defaults if no existing config
        const defaultResult = await window.electron.invoke(
          'bmad:get-default-config',
          {
            projectPath: currentProject.path
          }
        );

        if (defaultResult.success) {
          setConfig(defaultResult.data as BMADConfig);
        }
      }
    } catch (err) {
      setError(
        `Failed to load configuration: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setLoading(false);
    }
  };

  /**
   * Save BMAD configuration
   */
  const handleSave = async (): Promise<void> => {
    if (!currentProject) return;

    setSaving(true);
    setError(null);
    setValidationErrors([]);
    setSuccess(false);

    try {
      const result = await window.electron.invoke('bmad:save-config', {
        projectPath: currentProject.path,
        config
      });

      if (result.success) {
        setSuccess(true);
        setTimeout(() => {
          onSaved?.();
          onOpenChange(false);
        }, 1500);
      } else {
        if (result.data?.errors) {
          setValidationErrors(result.data.errors);
        }
        setError(result.error || 'Failed to save configuration');
      }
    } catch (err) {
      setError(
        `Failed to save configuration: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setSaving(false);
    }
  };

  /**
   * Handle field changes
   */
  const handleFieldChange = (
    field: keyof BMADConfig,
    value: string
  ): void => {
    setConfig((prev) => ({ ...prev, [field]: value }));
    setError(null);
    setValidationErrors([]);
    setSuccess(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>BMAD Method Configuration</DialogTitle>
          <DialogDescription>
            Configure BMAD framework settings for this project
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid gap-4 py-4">
            {/* User Name */}
            <div className="grid gap-2">
              <Label htmlFor="user_name">User Name</Label>
              <Input
                id="user_name"
                value={config.user_name}
                onChange={(e) =>
                  handleFieldChange('user_name', e.target.value)
                }
                placeholder="Your name"
                disabled={saving}
              />
            </div>

            {/* Project Name */}
            <div className="grid gap-2">
              <Label htmlFor="project_name">Project Name</Label>
              <Input
                id="project_name"
                value={config.project_name}
                onChange={(e) =>
                  handleFieldChange('project_name', e.target.value)
                }
                placeholder="Project identifier"
                disabled={saving}
              />
            </div>

            {/* Languages */}
            <div className="grid gap-2">
              <Label htmlFor="languages">Languages</Label>
              <Input
                id="languages"
                value={config.languages}
                onChange={(e) =>
                  handleFieldChange('languages', e.target.value)
                }
                placeholder="python,typescript,rust"
                disabled={saving}
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list of programming languages
              </p>
            </div>

            {/* Skill Level */}
            <div className="grid gap-2">
              <Label htmlFor="skill_level">Skill Level</Label>
              <Select
                value={config.skill_level}
                onValueChange={(value) =>
                  handleFieldChange(
                    'skill_level',
                    value as BMADConfig['skill_level']
                  )
                }
                disabled={saving}
              >
                <SelectTrigger id="skill_level">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="junior">Junior</SelectItem>
                  <SelectItem value="mid">Mid (Default)</SelectItem>
                  <SelectItem value="senior">Senior</SelectItem>
                  <SelectItem value="principal">Principal</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Framework Mode */}
            <div className="grid gap-2">
              <Label htmlFor="framework_mode">Framework Mode</Label>
              <Select
                value={config.framework_mode}
                onValueChange={(value) =>
                  handleFieldChange(
                    'framework_mode',
                    value as BMADConfig['framework_mode']
                  )
                }
                disabled={saving}
              >
                <SelectTrigger id="framework_mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="native">
                    Native (Auto Claude Default)
                  </SelectItem>
                  <SelectItem value="bmad">BMAD Method</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Select which planning framework to use
              </p>
            </div>

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <ul className="list-disc list-inside">
                    {validationErrors.map((err, index) => (
                      <li key={index}>{err}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {/* Error Message */}
            {error && !validationErrors.length && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Success Message */}
            {success && (
              <Alert className="border-green-500 bg-green-50 text-green-900">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription>
                  Configuration saved successfully!
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={loading || saving || success}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Configuration
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
