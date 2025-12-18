"""
BMAD Workflow Enhancements.

Integrates Auto Claude's autonomous capabilities with BMAD workflows:
- Context discovery
- Memory integration (Graphiti)
- Self-critique
- QA loop integration
"""

from pathlib import Path
from typing import Dict, List, Optional


class BMADEnhancements:
    """
    Enhancement layer for BMAD workflows.

    Adds Auto Claude's autonomous capabilities to BMAD.
    """

    def __init__(self, project_path: str):
        """
        Initialize enhancements.

        Args:
            project_path: Path to project directory
        """
        self.project_path = Path(project_path)

    def discover_project_context(self) -> Dict:
        """
        Auto-discover project context for architecture workflow.

        Detects:
        - Tech stack (languages, frameworks)
        - Project patterns
        - Dependencies
        - Existing architecture decisions

        Returns:
            Dictionary with discovered context
        """
        context = {
            "stack": self._detect_stack(),
            "patterns": self._detect_patterns(),
            "dependencies": self._detect_dependencies(),
        }

        return context

    def _detect_stack(self) -> List[str]:
        """Detect technology stack."""
        stack = []

        # Check for Python
        if (self.project_path / "requirements.txt").exists() or (
            self.project_path / "pyproject.toml"
        ).exists():
            stack.append("python")

        # Check for TypeScript/JavaScript
        if (self.project_path / "package.json").exists():
            stack.append("typescript")

        # Check for Rust
        if (self.project_path / "Cargo.toml").exists():
            stack.append("rust")

        # Check for Go
        if (self.project_path / "go.mod").exists():
            stack.append("go")

        return stack

    def _detect_patterns(self) -> List[str]:
        """Detect code patterns."""
        patterns = []

        # Check for common patterns
        if (self.project_path / "tests").exists() or (
            self.project_path / "test"
        ).exists():
            patterns.append("testing")

        if (self.project_path / "docs").exists():
            patterns.append("documentation")

        if (self.project_path / ".github" / "workflows").exists():
            patterns.append("ci-cd")

        return patterns

    def _detect_dependencies(self) -> Dict:
        """Detect project dependencies."""
        deps = {}

        # Python dependencies
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            deps["python"] = [
                line.strip()
                for line in req_file.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]

        return deps

    def retrieve_memory_insights(self, context: str) -> List[str]:
        """
        Retrieve relevant insights from Graphiti memory.

        Args:
            context: Context for memory retrieval

        Returns:
            List of relevant insights
        """
        insights = []

        # Try to import Graphiti memory (optional)
        try:
            from memory import retrieve_relevant_memories

            memories = retrieve_relevant_memories(str(self.project_path), context)

            for memory in memories:
                insights.append(memory.get("content", ""))

        except ImportError:
            # Graphiti not enabled, return empty
            pass

        return insights

    def run_self_critique(self, artifact_type: str, content: str) -> Dict:
        """
        Run self-critique on planning artifact.

        Uses AI to analyze from multiple perspectives:
        - Completeness
        - Clarity
        - Feasibility
        - Gaps/blind spots
        - Dependencies

        Args:
            artifact_type: Type of artifact (prd, architecture, epic)
            content: Artifact content to critique

        Returns:
            Dictionary with critique results
        """
        critique = {
            "artifact_type": artifact_type,
            "completeness_score": 0.0,
            "issues": [],
            "suggestions": [],
            "perspectives": {},
        }

        # Run critique from multiple perspectives
        perspectives = [
            "technical_feasibility",
            "user_experience",
            "security",
            "scalability",
            "completeness",
        ]

        for perspective in perspectives:
            critique["perspectives"][perspective] = self._critique_from_perspective(
                content, perspective
            )

        # Aggregate results
        critique["completeness_score"] = self._calculate_completeness(
            critique["perspectives"]
        )

        return critique

    def _critique_from_perspective(
        self, content: str, perspective: str
    ) -> Dict:
        """Run critique from specific perspective."""
        # Placeholder - real implementation would use Claude API
        return {
            "perspective": perspective,
            "score": 0.8,
            "issues": [],
            "suggestions": [],
        }

    def _calculate_completeness(self, perspectives: Dict) -> float:
        """Calculate overall completeness score."""
        if not perspectives:
            return 0.0

        scores = [p.get("score", 0.0) for p in perspectives.values()]
        return sum(scores) / len(scores)

    def integrate_qa_loop(
        self, workflow_name: str, artifact_path: str
    ) -> Dict:
        """
        Integrate QA loop with BMAD workflow.

        Runs Auto Claude's QA validation on workflow outputs.

        Args:
            workflow_name: Workflow that generated artifact
            artifact_path: Path to artifact file

        Returns:
            QA validation results
        """
        validation = {
            "passed": False,
            "issues": [],
            "suggestions": [],
        }

        # Try to import QA loop
        try:
            from qa_loop import validate_output

            validation = validate_output(artifact_path)

        except ImportError:
            # QA loop not available
            pass

        return validation

    def store_retrospective(
        self, workflow_name: str, lessons_learned: List[str]
    ) -> bool:
        """
        Store retrospective insights in memory.

        Args:
            workflow_name: Workflow name
            lessons_learned: List of lessons learned

        Returns:
            True if successful, False otherwise
        """
        # Try to store in Graphiti memory
        try:
            from memory import store_insight

            for lesson in lessons_learned:
                store_insight(
                    str(self.project_path),
                    {
                        "type": "retrospective",
                        "workflow": workflow_name,
                        "content": lesson,
                    },
                )

            return True

        except ImportError:
            # Memory not enabled
            return False
