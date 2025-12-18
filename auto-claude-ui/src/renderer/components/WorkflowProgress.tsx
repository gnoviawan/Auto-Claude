/**
 * WorkflowProgress - Displays BMAD workflow execution progress
 *
 * Shows:
 * - Current step (e.g., "Step 3 of 8")
 * - Progress bar
 * - Breadcrumbs of completed steps
 * - Current step name and description
 */

import { Check, Loader2, Circle } from 'lucide-react';
import { Progress } from './ui/progress';
import { cn } from '../lib/utils';

/**
 * Workflow step interface
 */
interface WorkflowStep {
  number: number;
  name: string;
  status: 'pending' | 'in_progress' | 'completed';
}

/**
 * Props for WorkflowProgress
 */
interface WorkflowProgressProps {
  /** Workflow name */
  workflowName: string;
  /** Total number of steps */
  totalSteps: number;
  /** Current step number (1-indexed) */
  currentStep: number;
  /** All steps with status */
  steps: WorkflowStep[];
  /** Optional className */
  className?: string;
}

/**
 * WorkflowProgress component
 */
export function WorkflowProgress({
  workflowName,
  totalSteps,
  currentStep,
  steps,
  className
}: WorkflowProgressProps): JSX.Element {
  const progressPercent = ((currentStep - 1) / totalSteps) * 100;

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{workflowName}</h3>
        <span className="text-sm text-muted-foreground">
          Step {currentStep} of {totalSteps}
        </span>
      </div>

      {/* Progress bar */}
      <Progress value={progressPercent} className="h-2" />

      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {steps.map((step) => (
          <div
            key={step.number}
            className="flex items-center gap-2 shrink-0"
          >
            {/* Step indicator */}
            <div
              className={cn(
                'flex items-center justify-center w-8 h-8 rounded-full border-2',
                {
                  'border-green-500 bg-green-50 text-green-700':
                    step.status === 'completed',
                  'border-blue-500 bg-blue-50 text-blue-700':
                    step.status === 'in_progress',
                  'border-gray-300 bg-white text-gray-400':
                    step.status === 'pending'
                }
              )}
            >
              {step.status === 'completed' && (
                <Check className="w-4 h-4" />
              )}
              {step.status === 'in_progress' && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              {step.status === 'pending' && (
                <Circle className="w-3 h-3" />
              )}
            </div>

            {/* Step name */}
            <div
              className={cn('text-sm', {
                'font-medium text-foreground':
                  step.status === 'in_progress',
                'text-muted-foreground': step.status !== 'in_progress'
              })}
            >
              {step.name}
            </div>

            {/* Connector line (except for last step) */}
            {step.number < totalSteps && (
              <div
                className={cn('h-0.5 w-8', {
                  'bg-green-500': step.status === 'completed',
                  'bg-gray-300': step.status !== 'completed'
                })}
              />
            )}
          </div>
        ))}
      </div>

      {/* Current step details */}
      {steps.find((s) => s.status === 'in_progress') && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <h4 className="font-medium">
              {steps.find((s) => s.status === 'in_progress')?.name}
            </h4>
          </div>
          <p className="text-sm text-muted-foreground">
            In progress...
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Example usage:
 *
 * const steps = [
 *   { number: 1, name: "Understand Product Brief", status: "completed" },
 *   { number: 2, name: "Define Objectives", status: "completed" },
 *   { number: 3, name: "Identify Stakeholders", status: "in_progress" },
 *   { number: 4, name: "Define Success Metrics", status: "pending" },
 * ];
 *
 * <WorkflowProgress
 *   workflowName="Create PRD"
 *   totalSteps={11}
 *   currentStep={3}
 *   steps={steps}
 * />
 */
