"""
Multi-Agent Orchestrator for BMAD Party Mode.

Enables multiple agents to collaborate in parallel discussions.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# Import Auto Claude's agent system
from agents.session import run_agent_session
from core.client import create_client
from task_logger import LogPhase


@dataclass
class AgentContribution:
    """Single agent contribution to discussion."""

    agent_type: str
    agent_name: str
    round_num: int
    content: str
    timestamp: str


@dataclass
class PartyModeResult:
    """Result of Party Mode multi-agent session."""

    discussion_history: List[AgentContribution]
    synthesis: str
    status: str  # "success", "failed"


class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent collaboration sessions.

    Enables BMAD Party Mode where multiple agents participate
    in collaborative planning and discussion.
    """

    # Agent personas for BMAD Party Mode
    AGENT_PERSONAS = {
        "pm": {"name": "John", "role": "Product Manager", "style": "product-focused"},
        "architect": {
            "name": "Winston",
            "role": "Solutions Architect",
            "style": "technical-depth",
        },
        "dev": {"name": "Amelia", "role": "Developer", "style": "practical"},
        "tea": {
            "name": "Murat",
            "role": "Test Engineer & Architect",
            "style": "quality-focused",
        },
        "sm": {"name": "Sarah", "role": "Scrum Master", "style": "process-oriented"},
    }

    def __init__(self, project_path: str):
        """
        Initialize orchestrator.

        Args:
            project_path: Path to project directory
        """
        self.project_path = Path(project_path)
        self.agents = {}

    async def run_party_mode(
        self,
        agent_types: List[str],
        discussion_topic: str,
        rounds: int = 3,
        mode: str = "round-robin",
    ) -> PartyModeResult:
        """
        Run Party Mode discussion with multiple agents.

        Args:
            agent_types: List of agent types (e.g., ['pm', 'architect', 'dev', 'tea'])
            discussion_topic: Topic for discussion
            rounds: Number of discussion rounds
            mode: Discussion mode ("round-robin" or "free-form")

        Returns:
            PartyModeResult with agent outputs and synthesis
        """
        discussion_history = []

        # Run discussion rounds
        for round_num in range(1, rounds + 1):
            if mode == "round-robin":
                round_outputs = await self._run_round_robin(
                    agent_types, discussion_topic, discussion_history, round_num
                )
            else:
                round_outputs = await self._run_free_form(
                    agent_types, discussion_topic, discussion_history, round_num
                )

            discussion_history.extend(round_outputs)

        # Synthesize discussion
        synthesis = await self._synthesize_discussion(discussion_history)

        return PartyModeResult(
            discussion_history=discussion_history, synthesis=synthesis, status="success"
        )

    async def _run_round_robin(
        self,
        agent_types: List[str],
        topic: str,
        history: List[AgentContribution],
        round_num: int,
    ) -> List[AgentContribution]:
        """Run round-robin discussion round."""
        contributions = []

        # Each agent contributes in sequence
        for agent_type in agent_types:
            contribution = await self._get_agent_contribution(
                agent_type, topic, history, round_num
            )

            contributions.append(contribution)

            # Add to history so next agent sees previous contributions
            history.append(contribution)

        return contributions

    async def _run_free_form(
        self,
        agent_types: List[str],
        topic: str,
        history: List[AgentContribution],
        round_num: int,
    ) -> List[AgentContribution]:
        """Run free-form parallel discussion."""
        # All agents contribute simultaneously
        tasks = [
            self._get_agent_contribution(agent_type, topic, history, round_num)
            for agent_type in agent_types
        ]

        contributions = await asyncio.gather(*tasks)

        return list(contributions)

    async def _get_agent_contribution(
        self,
        agent_type: str,
        topic: str,
        history: List[AgentContribution],
        round_num: int,
    ) -> AgentContribution:
        """
        Get contribution from specific agent using Claude API.

        Args:
            agent_type: Type of agent
            topic: Discussion topic
            history: Previous contributions
            round_num: Current round number

        Returns:
            Agent contribution
        """
        from datetime import datetime

        persona = self.AGENT_PERSONAS.get(
            agent_type, {"name": agent_type.title(), "role": agent_type}
        )

        # Build context from history
        context_lines = [f"Discussion Topic: {topic}", ""]

        if history:
            context_lines.append("Previous Discussion:")
            for contrib in history[-10:]:  # Last 10 contributions
                context_lines.append(
                    f"[Round {contrib.round_num}] {contrib.agent_name} ({contrib.agent_type}): {contrib.content}"
                )
            context_lines.append("")

        context_lines.append(
            f"You are {persona['name']}, the {persona['role']}. "
            f"Provide a brief, focused contribution (2-3 sentences) to this discussion from your perspective. "
            f"Be specific and add value based on your expertise."
        )

        context = "\n".join(context_lines)

        # Create spec directory for this discussion
        spec_dir = self.project_path / "_bmad-output" / ".party-mode" / f"round-{round_num}"
        spec_dir.mkdir(parents=True, exist_ok=True)

        # Map BMAD agent types to Auto Claude agent types
        agent_type_mapping = {
            "pm": "planner",
            "architect": "planner",
            "dev": "coder",
            "tea": "qa_reviewer",
            "sm": "planner",
        }
        auto_claude_agent_type = agent_type_mapping.get(agent_type, "planner")

        try:
            # Create Claude SDK client
            client = create_client(
                project_dir=self.project_path,
                spec_dir=spec_dir,
                model="claude-sonnet-4",
                agent_type=auto_claude_agent_type,
            )

            # Get agent contribution
            status, response_text = await run_agent_session(
                client=client,
                message=context,
                spec_dir=spec_dir,
                verbose=False,
                phase=LogPhase.PLANNING,
            )

            # Extract the contribution (limit to reasonable length)
            content = response_text.strip()
            if len(content) > 500:
                content = content[:497] + "..."

            return AgentContribution(
                agent_type=agent_type,
                agent_name=persona["name"],
                round_num=round_num,
                content=content,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            # Fallback to simple contribution if agent execution fails
            content = f"{persona['name']} ({persona['role']}): Unable to contribute (error: {str(e)})"

            return AgentContribution(
                agent_type=agent_type,
                agent_name=persona["name"],
                round_num=round_num,
                content=content,
                timestamp=datetime.now().isoformat(),
            )

    async def _synthesize_discussion(
        self, discussion_history: List[AgentContribution]
    ) -> str:
        """
        Synthesize multi-agent discussion using Claude API.

        Args:
            discussion_history: All agent contributions

        Returns:
            Synthesized discussion summary with key insights and action items
        """
        # Group by round
        by_round = {}
        for contrib in discussion_history:
            if contrib.round_num not in by_round:
                by_round[contrib.round_num] = []
            by_round[contrib.round_num].append(contrib)

        # Build synthesis document
        synthesis_lines = ["# Multi-Agent Discussion Synthesis", ""]

        for round_num in sorted(by_round.keys()):
            synthesis_lines.extend([f"## Round {round_num}", ""])

            for contrib in by_round[round_num]:
                synthesis_lines.append(
                    f"**{contrib.agent_name} ({contrib.agent_type}):** {contrib.content}"
                )
                synthesis_lines.append("")

        # Use Claude to generate intelligent synthesis
        try:
            spec_dir = self.project_path / "_bmad-output" / ".party-mode" / "synthesis"
            spec_dir.mkdir(parents=True, exist_ok=True)

            client = create_client(
                project_dir=self.project_path,
                spec_dir=spec_dir,
                model="claude-sonnet-4",
                agent_type="planner",
            )

            synthesis_prompt = f"""Analyze this multi-agent discussion and provide:
1. Key insights (3-5 bullet points)
2. Consensus points (where agents agreed)
3. Conflicting perspectives (where agents disagreed)
4. Action items (specific next steps)

Discussion:
{chr(10).join(synthesis_lines)}

Please provide a concise synthesis in markdown format."""

            status, response_text = await run_agent_session(
                client=client,
                message=synthesis_prompt,
                spec_dir=spec_dir,
                verbose=False,
                phase=LogPhase.PLANNING,
            )

            # Append AI-generated synthesis
            synthesis_lines.extend(["", "## AI-Generated Synthesis", "", response_text])

        except Exception as e:
            # Fallback to basic synthesis if AI synthesis fails
            synthesis_lines.extend(
                [
                    "",
                    "## Synthesis (Basic)",
                    "",
                    "- Discussion captured above",
                    f"- Unable to generate AI synthesis: {str(e)}",
                    "",
                ]
            )

        return "\n".join(synthesis_lines)

    def get_recommended_agents(self, task_type: str) -> List[str]:
        """
        Get recommended agent composition for task type.

        Args:
            task_type: Type of task (planning, architecture, retrospective, etc.)

        Returns:
            List of recommended agent types
        """
        recommendations = {
            "planning": ["pm", "architect", "dev"],
            "architecture": ["architect", "dev", "tea"],
            "epic_breakdown": ["pm", "architect", "dev", "tea"],
            "retrospective": ["pm", "dev", "tea", "sm"],
            "estimation": ["architect", "dev", "tea"],
        }

        return recommendations.get(task_type, ["pm", "dev", "tea"])
