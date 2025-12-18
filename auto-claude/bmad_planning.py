"""
BMAD Planning Workflows integration.

Provides high-level API for running BMAD planning workflows.
"""

from typing import Dict, Optional

from bmad_engine import WorkflowEngine, WorkflowResult
from framework_adapter import get_adapter


class BMADPlanning:
    """
    High-level API for BMAD planning workflows.

    Integrates workflow engine with framework adapters.
    """

    def __init__(self, project_path: str):
        """
        Initialize planning API.

        Args:
            project_path: Path to project directory
        """
        self.project_path = project_path
        self.engine = WorkflowEngine(project_path)
        self.adapter = get_adapter(project_path)

    def create_product_brief(
        self, context: Optional[Dict] = None, callbacks: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        Run create-product-brief workflow (Phase 1: Analysis).

        Args:
            context: Optional execution context
            callbacks: Optional UI callbacks

        Returns:
            WorkflowResult
        """
        return self.engine.execute_workflow(
            "create-product-brief", context=context or {}, callbacks=callbacks
        )

    def create_prd(
        self, context: Optional[Dict] = None, callbacks: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        Run create-prd workflow (Phase 2: Planning).

        11-step collaborative PRD creation with PM facilitation.

        Args:
            context: Optional execution context
            callbacks: Optional UI callbacks

        Returns:
            WorkflowResult
        """
        return self.engine.execute_workflow(
            "create-prd", context=context or {}, callbacks=callbacks
        )

    def create_architecture(
        self, context: Optional[Dict] = None, callbacks: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        Run create-architecture workflow (Phase 3: Solutioning).

        8-step collaborative architecture design.

        Args:
            context: Optional execution context
            callbacks: Optional UI callbacks

        Returns:
            WorkflowResult
        """
        return self.engine.execute_workflow(
            "create-architecture", context=context or {}, callbacks=callbacks
        )

    def create_ux_design(
        self, context: Optional[Dict] = None, callbacks: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        Run create-ux-design workflow (Phase 3: Solutioning).

        UX pattern and design system planning.

        Args:
            context: Optional execution context
            callbacks: Optional UI callbacks

        Returns:
            WorkflowResult
        """
        return self.engine.execute_workflow(
            "create-ux-design", context=context or {}, callbacks=callbacks
        )

    def create_epics_and_stories(
        self, context: Optional[Dict] = None, callbacks: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        Run create-epics-and-stories workflow (Phase 3: Solutioning).

        Epic breakdown with user stories.

        Args:
            context: Optional execution context
            callbacks: Optional UI callbacks

        Returns:
            WorkflowResult
        """
        return self.engine.execute_workflow(
            "create-epics-and-stories", context=context or {}, callbacks=callbacks
        )

    def check_implementation_readiness(
        self, context: Optional[Dict] = None, callbacks: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        Run check-implementation-readiness workflow (Phase 3: Solutioning).

        Validation workflow to ensure planning artifacts are complete.

        Args:
            context: Optional execution context
            callbacks: Optional UI callbacks

        Returns:
            WorkflowResult
        """
        return self.engine.execute_workflow(
            "check-implementation-readiness", context=context or {}, callbacks=callbacks
        )

    def list_planning_workflows(self) -> list[Dict]:
        """
        List all available planning workflows.

        Returns:
            List of workflow metadata
        """
        all_workflows = self.engine.list_workflows()

        # Filter to planning-related workflows (phases 1-3)
        planning_phases = ["1-analysis", "2-plan-workflows", "3-solutioning"]

        return [
            wf
            for wf in all_workflows
            if any(phase in wf.get("phase", "") for phase in planning_phases)
        ]
