"""Automated evaluation scenarios for the agent with transcript generation."""
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from rich.console import Console
from rich.panel import Panel

from device import SmartDevice, DeviceState
from agent import NaiveDeviceAgent
from reset_detector import ResetDetector


console = Console()


class ScenarioRunner:
    """Runs predefined test scenarios and generates transcripts."""
    
    def __init__(self, output_dir: str = "test_transcripts"):
        """
        Initialize scenario runner.
        
        Args:
            output_dir: Directory to save transcripts
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = []
    
    def run_scenario(
        self,
        name: str,
        description: str,
        setup_fn,
        user_inputs: List[str],
        expected_outcome: str
    ) -> Dict[str, Any]:
        """
        Run a single test scenario.
        
        Args:
            name: Scenario name
            description: Scenario description
            setup_fn: Function to set up device state
            user_inputs: List of user messages
            expected_outcome: Expected result description
            
        Returns:
            Scenario results including transcript
        """
        console.print(f"\n[bold blue]Running Scenario: {name}[/bold blue]")
        console.print(f"[dim]{description}[/dim]\n")
        
        # Initialize components
        device = SmartDevice()
        agent = NaiveDeviceAgent(device)
        detector = ResetDetector()
        
        # Run setup
        setup_fn(device)
        
        # Transcript
        transcript = []
        transcript.append(f"# Scenario: {name}\n")
        transcript.append(f"**Description:** {description}\n")
        transcript.append(f"**Expected Outcome:** {expected_outcome}\n")
        transcript.append("\n---\n\n## Conversation\n")
        
        # Process each user input
        resets_triggered = []
        
        for i, user_input in enumerate(user_inputs, 1):
            console.print(f"[green]Turn {i} - User:[/green] {user_input}")
            transcript.append(f"**Turn {i} - User:** {user_input}\n")
            
            # Get response
            response = agent.process_turn(user_input)
            console.print(f"[cyan]Agent:[/cyan] {response}\n")
            transcript.append(f"**Agent:** {response}\n")
            
            # Check for reset
            agent_stats = agent.get_stats()
            recent_messages = agent.get_conversation_history()[-10:]
            should_reset, reason = detector.should_reset(
                agent_stats,
                recent_messages,
                response
            )
            
            if should_reset:
                console.print(f"[yellow]🔄 RESET TRIGGERED: {reason}[/yellow]\n")
                transcript.append(f"\n*[System: Reset triggered - {reason}]*\n")
                agent.reset_history()
                detector.record_reset(agent.turn_count)
                resets_triggered.append({
                    "turn": i,
                    "reason": reason
                })
            
            transcript.append("\n")
        
        # Add statistics
        transcript.append("\n---\n\n## Statistics\n\n")
        agent_stats = agent.get_stats()
        detector_stats = detector.get_stats()
        
        transcript.append(f"- **Total turns:** {agent_stats['turn_count']}\n")
        transcript.append(f"- **Tool calls:** {agent_stats['tool_call_count']}\n")
        transcript.append(f"- **Resets triggered:** {len(resets_triggered)}\n")
        if resets_triggered:
            transcript.append(f"- **Reset details:**\n")
            for reset in resets_triggered:
                transcript.append(f"  - Turn {reset['turn']}: {reset['reason']}\n")
        
        transcript.append(f"\n### Latency Metrics\n\n")
        transcript.append(f"- **Mean detection latency:** {detector_stats['latency_stats']['mean_ms']:.2f} ms\n")
        transcript.append(f"- **Max detection latency:** {detector_stats['latency_stats']['max_ms']:.2f} ms\n")
        transcript.append(f"- **P95 detection latency:** {detector_stats['latency_stats']['p95_ms']:.2f} ms\n")
        transcript.append(f"- **Within budget (<500ms):** {detector_stats['within_budget']}\n")
        
        # Save transcript
        filename = f"scenario_{name.lower().replace(' ', '_')}.md"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(transcript)
        
        console.print(f"[green]✓ Transcript saved to: {filepath}[/green]\n")
        
        # Return results
        result = {
            "name": name,
            "description": description,
            "expected_outcome": expected_outcome,
            "turns": len(user_inputs),
            "tool_calls": agent_stats['tool_call_count'],
            "resets": len(resets_triggered),
            "reset_details": resets_triggered,
            "latency": detector_stats['latency_stats'],
            "within_budget": detector_stats['within_budget'],
            "transcript_file": str(filepath)
        }
        
        self.results.append(result)
        return result
    
    def run_all_scenarios(self):
        """Run all predefined scenarios."""
        console.print(Panel.fit(
            "[bold]Running All Evaluation Scenarios[/bold]\n"
            "This will test all 5 required scenarios.",
            border_style="blue"
        ))
        
        # Scenario 1: Clean control
        self.run_scenario(
            name="Scenario 1: Clean Control",
            description="User requests to turn on fan and set speed. Tool succeeds normally.",
            setup_fn=lambda device: None,  # No special setup
            user_inputs=[
                "Turn on the fan and set speed to 3"
            ],
            expected_outcome="Works normally, no reset triggered"
        )
        
        # Scenario 2: Transient failure, then recovery
        def setup_scenario_2(device):
            device.inject_failure(DeviceState.OFFLINE, duration=1)
        
        self.run_scenario(
            name="Scenario 2: Transient Failure",
            description="First call fails (device disconnected), subsequent calls succeed.",
            setup_fn=setup_scenario_2,
            user_inputs=[
                "Turn on the fan",
                "Please try turning on the fan again"
            ],
            expected_outcome="Agent retries and eventually succeeds"
        )
        
        # Scenario 3: Stale-failure poisoning (THE CORE SCENARIO)
        def setup_scenario_3(device):
            device.inject_failure(DeviceState.OFFLINE, duration=1)
        
        self.run_scenario(
            name="Scenario 3: Stale-Failure Poisoning",
            description="Tool fails once, then user asks 3 more times. Agent parrots error without retrying.",
            setup_fn=setup_scenario_3,
            user_inputs=[
                "Turn on the fan",
                "Can you turn on the fan?",
                "Please turn on the fan",
                "Turn on the fan now"
            ],
            expected_outcome="Reset fires after detecting stale error parroting, next attempt invokes tool"
        )
        
        # Scenario 4: Repeated genuine failures
        def setup_scenario_4(device):
            device.inject_failure(DeviceState.OFFLINE, duration=5)
        
        self.run_scenario(
            name="Scenario 4: Repeated Genuine Failures",
            description="Tool genuinely fails 5 times in a row.",
            setup_fn=setup_scenario_4,
            user_inputs=[
                "Turn on the fan",
                "Turn on the fan",
                "Turn on the fan",
                "Turn on the fan",
                "Turn on the fan"
            ],
            expected_outcome="Reset may fire, but errors are genuine (policy-defined behavior)"
        )
        
        # Scenario 5: Mixed intent
        self.run_scenario(
            name="Scenario 5: Mixed Intent",
            description="User requests device control AND an off-topic question.",
            setup_fn=lambda device: None,
            user_inputs=[
                "Turn off the light and tell me a joke"
            ],
            expected_outcome="Device control handled, no reset triggered by off-topic part"
        )
        
        # Generate summary report
        self._generate_summary_report()
    
    def _generate_summary_report(self):
        """Generate a summary report of all scenarios."""
        summary_path = self.output_dir / "SUMMARY.md"
        
        lines = []
        lines.append("# Test Scenarios Summary\n\n")
        lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        lines.append("## Results Overview\n\n")
        lines.append("| Scenario | Turns | Tool Calls | Resets | Mean Latency (ms) | Within Budget |\n")
        lines.append("|----------|-------|------------|--------|-------------------|---------------|\n")
        
        for result in self.results:
            lines.append(
                f"| {result['name']} | {result['turns']} | {result['tool_calls']} | "
                f"{result['resets']} | {result['latency']['mean_ms']:.2f} | "
                f"{'✓' if result['within_budget'] else '✗'} |\n"
            )
        
        lines.append("\n## Detailed Results\n\n")
        
        for result in self.results:
            lines.append(f"### {result['name']}\n\n")
            lines.append(f"- **Description:** {result['description']}\n")
            lines.append(f"- **Expected:** {result['expected_outcome']}\n")
            lines.append(f"- **Turns:** {result['turns']}\n")
            lines.append(f"- **Tool calls:** {result['tool_calls']}\n")
            lines.append(f"- **Resets triggered:** {result['resets']}\n")
            
            if result['reset_details']:
                lines.append(f"- **Reset details:**\n")
                for reset in result['reset_details']:
                    lines.append(f"  - Turn {reset['turn']}: {reset['reason']}\n")
            
            lines.append(f"- **Latency stats:**\n")
            lines.append(f"  - Mean: {result['latency']['mean_ms']:.2f} ms\n")
            lines.append(f"  - Max: {result['latency']['max_ms']:.2f} ms\n")
            lines.append(f"  - P95: {result['latency']['p95_ms']:.2f} ms\n")
            lines.append(f"- **Within budget:** {result['within_budget']}\n")
            lines.append(f"- **Transcript:** [{result['transcript_file']}]({Path(result['transcript_file']).name})\n\n")
        
        lines.append("\n## Latency Budget Analysis\n\n")
        
        all_within_budget = all(r['within_budget'] for r in self.results)
        max_latency = max(r['latency']['max_ms'] for r in self.results)
        avg_latency = sum(r['latency']['mean_ms'] for r in self.results) / len(self.results)
        
        lines.append(f"- **Overall status:** {'✓ PASS' if all_within_budget else '✗ FAIL'}\n")
        lines.append(f"- **Budget:** 500 ms\n")
        lines.append(f"- **Average mean latency:** {avg_latency:.2f} ms\n")
        lines.append(f"- **Maximum latency observed:** {max_latency:.2f} ms\n")
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        console.print(f"\n[bold green]✓ Summary report saved to: {summary_path}[/bold green]\n")
        
        # Display summary
        console.print(Panel.fit(
            f"[bold]All Scenarios Complete![/bold]\n\n"
            f"Total scenarios: {len(self.results)}\n"
            f"Latency budget: {'PASS ✓' if all_within_budget else 'FAIL ✗'}\n"
            f"Average latency: {avg_latency:.2f} ms\n"
            f"Max latency: {max_latency:.2f} ms",
            border_style="green" if all_within_budget else "red"
        ))


def main():
    """Main entry point for scenario testing."""
    runner = ScenarioRunner()
    runner.run_all_scenarios()


if __name__ == "__main__":
    main()
