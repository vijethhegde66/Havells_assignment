"""Main application for interactive agent testing and scenario execution."""
import sys
import argparse
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from device import SmartDevice
from agent import NaiveDeviceAgent
from reset_detector import ResetDetector


console = Console()


class AgentController:
    """
    Orchestrates the agent, device, and reset detector.
    
    This is the main integration point that:
    1. Accepts user input
    2. Passes to agent
    3. Checks for context poisoning
    4. Triggers resets when needed
    5. Displays results
    """
    
    def __init__(self):
        """Initialize the controller with all components."""
        self.device = SmartDevice()
        self.agent = NaiveDeviceAgent(self.device)
        self.detector = ResetDetector()
        
        self.conversation_log = []
    
    def process_user_input(self, user_input: str) -> str:
        """
        Process a user input through the full pipeline.
        
        Args:
            user_input: User's message
            
        Returns:
            Agent's response
        """
        # Get agent response
        response = self.agent.process_turn(user_input)
        
        # Log the interaction
        self.conversation_log.append({
            "turn": self.agent.turn_count,
            "user": user_input,
            "assistant": response
        })
        
        # Check if reset is needed
        agent_stats = self.agent.get_stats()
        recent_messages = self.agent.get_conversation_history()[-10:]
        
        should_reset, reason = self.detector.should_reset(
            agent_stats,
            recent_messages,
            response
        )
        
        if should_reset:
            console.print(f"\n[yellow]🔄 RESET TRIGGERED: {reason}[/yellow]")
            self.agent.reset_history()
            self.detector.record_reset(self.agent.turn_count)
            
            # Inform user about reset
            reset_message = (
                "\n[System: I've cleared my conversation history to provide you "
                "with a fresh start. How can I help you?]"
            )
            return response + reset_message
        
        return response
    
    def run_interactive(self):
        """Run in interactive mode."""
        console.print(Panel.fit(
            "[bold blue]Smart Device Control Agent[/bold blue]\n"
            "Control your smart fan and light with natural language.\n"
            "Type 'quit' or 'exit' to stop, 'stats' for statistics, "
            "'device' for device status.",
            border_style="blue"
        ))
        
        while True:
            try:
                user_input = console.input("\n[bold green]You:[/bold green] ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ["quit", "exit"]:
                    self._display_final_stats()
                    break
                elif user_input.lower() == "stats":
                    self._display_stats()
                    continue
                elif user_input.lower() == "device":
                    self._display_device_status()
                    continue
                elif user_input.lower() == "reset":
                    self.agent.reset_history()
                    console.print("[yellow]Conversation history cleared.[/yellow]")
                    continue
                
                # Process normal input
                response = self.process_user_input(user_input)
                console.print(f"[bold cyan]Agent:[/bold cyan] {response}")
                
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Interrupted. Exiting...[/yellow]")
                self._display_final_stats()
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                if "--debug" in sys.argv:
                    raise
    
    def _display_stats(self):
        """Display agent and detector statistics."""
        agent_stats = self.agent.get_stats()
        detector_stats = self.detector.get_stats()
        
        console.print("\n[bold]Agent Statistics:[/bold]")
        console.print(f"  Turns: {agent_stats['turn_count']}")
        console.print(f"  Tool calls: {agent_stats['tool_call_count']}")
        console.print(f"  Turns since last tool call: {agent_stats['turns_since_last_tool_call']}")
        console.print(f"  Message history size: {agent_stats['message_count']}")
        
        console.print("\n[bold]Reset Detector Statistics:[/bold]")
        console.print(f"  Resets triggered: {detector_stats['reset_count']}")
        console.print(f"  Detection calls: {detector_stats['detection_calls']}")
        console.print(f"  Latency (mean): {detector_stats['latency_stats']['mean_ms']:.2f} ms")
        console.print(f"  Latency (max): {detector_stats['latency_stats']['max_ms']:.2f} ms")
        console.print(f"  Latency (p95): {detector_stats['latency_stats']['p95_ms']:.2f} ms")
        console.print(f"  Within budget (<500ms): {detector_stats['within_budget']}")
    
    def _display_device_status(self):
        """Display current device status."""
        status = self.device.get_status()
        console.print("\n[bold]Device Status:[/bold]")
        if status["success"]:
            state = status["state"]
            console.print(f"  Power: {'ON' if state['power'] else 'OFF'}")
            console.print(f"  Fan speed: {state['speed']}/5")
            console.print(f"  Brightness: {state['brightness']}%")
            console.print(f"  Connection: {state['connection']}")
        else:
            console.print(f"  [red]Error: {status['message']}[/red]")
    
    def _display_final_stats(self):
        """Display final statistics on exit."""
        console.print("\n" + "="*60)
        console.print("[bold]Session Summary[/bold]")
        console.print("="*60)
        self._display_stats()
        console.print("\n[dim]Thank you for using the Smart Device Control Agent![/dim]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Smart Device Control Agent with Auto Session Reset"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (default)"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Run a specific test scenario (use 'scenarios.py' for this)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with full error traces"
    )
    
    args = parser.parse_args()
    
    # Default to interactive mode
    controller = AgentController()
    controller.run_interactive()


if __name__ == "__main__":
    main()
