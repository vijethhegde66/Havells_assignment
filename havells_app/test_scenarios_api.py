"""Automated test runner for all scenarios via API."""
import requests
import time
import json
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

API_BASE_URL = "http://localhost:8000"


class ScenarioTester:
    def __init__(self):
        self.session_id = None
        self.results = []
    
    def create_session(self):
        """Create a new test session."""
        response = requests.post(f"{API_BASE_URL}/session/create")
        if response.status_code == 200:
            self.session_id = response.json()["session_id"]
            console.print(f"[green]✓[/green] Session created: {self.session_id[:8]}...")
            return True
        else:
            console.print("[red]✗[/red] Failed to create session")
            return False
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message and get response."""
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"session_id": self.session_id, "message": message}
        )
        return response.json() if response.status_code == 200 else None
    
    def inject_failure(self, failure_type: str, duration: int):
        """Inject device failure."""
        requests.post(
            f"{API_BASE_URL}/session/{self.session_id}/device/inject-failure",
            json={"failure_type": failure_type, "duration": duration}
        )
    
    def clear_failure(self):
        """Clear device failures."""
        requests.post(f"{API_BASE_URL}/session/{self.session_id}/device/clear-failure")
    
    def reset_session(self):
        """Reset conversation."""
        requests.post(f"{API_BASE_URL}/session/{self.session_id}/reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        response = requests.get(f"{API_BASE_URL}/session/{self.session_id}/stats")
        return response.json() if response.status_code == 200 else None
    
    def run_scenario_1(self):
        """Scenario 1: Clean Control"""
        console.print("\n[bold blue]Scenario 1: Clean Control[/bold blue]")
        
        self.reset_session()
        self.clear_failure()
        
        inputs = [
            "Turn on the fan",
            "Set fan speed to 3",
            "Turn on the light",
            "Set brightness to 75%",
            "Get device status"
        ]
        
        for i, msg in enumerate(inputs, 1):
            console.print(f"[dim]Turn {i}:[/dim] {msg}")
            result = self.send_message(msg)
            if result:
                console.print(f"[cyan]Response:[/cyan] {result['response'][:80]}...")
                if result['reset_triggered']:
                    console.print(f"[yellow]⚠ Reset: {result['reset_reason']}[/yellow]")
        
        stats = self.get_stats()
        self.results.append({
            "scenario": "Scenario 1: Clean Control",
            "expected_resets": 0,
            "actual_resets": stats['detector_stats']['reset_count'],
            "turns": stats['agent_stats']['turn_count'],
            "tool_calls": stats['agent_stats']['tool_call_count'],
            "latency_mean": stats['detector_stats']['latency_stats']['mean_ms']
        })
    
    def run_scenario_2(self):
        """Scenario 2: Transient Failure"""
        console.print("\n[bold blue]Scenario 2: Transient Failure[/bold blue]")
        
        self.reset_session()
        self.clear_failure()
        
        # Inject 1 operation failure
        self.inject_failure("offline", 1)
        console.print("[yellow]Injected offline failure (duration=1)[/yellow]")
        
        console.print("[dim]Turn 1:[/dim] Turn on the fan")
        result = self.send_message("Turn on the fan")
        console.print(f"[cyan]Response:[/cyan] {result['response'][:80]}...")
        
        time.sleep(2)
        
        console.print("[dim]Turn 2:[/dim] Please try turning on the fan again")
        result = self.send_message("Please try turning on the fan again")
        console.print(f"[cyan]Response:[/cyan] {result['response'][:80]}...")
        if result['reset_triggered']:
            console.print(f"[yellow]⚠ Reset: {result['reset_reason']}[/yellow]")
        
        stats = self.get_stats()
        self.results.append({
            "scenario": "Scenario 2: Transient Failure",
            "expected_resets": "0-1",
            "actual_resets": stats['detector_stats']['reset_count'],
            "turns": stats['agent_stats']['turn_count'],
            "tool_calls": stats['agent_stats']['tool_call_count'],
            "latency_mean": stats['detector_stats']['latency_stats']['mean_ms']
        })
    
    def run_scenario_3(self):
        """Scenario 3: Stale-Failure Poisoning (CORE)"""
        console.print("\n[bold blue]Scenario 3: Stale-Failure Poisoning (CORE)[/bold blue]")
        
        self.reset_session()
        self.clear_failure()
        
        # Inject 1 operation failure
        self.inject_failure("offline", 1)
        console.print("[yellow]Injected offline failure (duration=1)[/yellow]")
        
        inputs = [
            "Turn on the fan",
            "Can you turn on the fan?",
            "Please turn on the fan",
            "Turn on the fan now"
        ]
        
        for i, msg in enumerate(inputs, 1):
            if i == 2:
                time.sleep(2)
                console.print("[green]Failure cleared (after 1 operation)[/green]")
            
            console.print(f"[dim]Turn {i}:[/dim] {msg}")
            result = self.send_message(msg)
            console.print(f"[cyan]Response:[/cyan] {result['response'][:80]}...")
            
            if result['reset_triggered']:
                console.print(f"[yellow]🔄 RESET TRIGGERED: {result['reset_reason']}[/yellow]")
            
            # Check if tool was called
            stats = self.get_stats()
            console.print(f"[dim]Tool calls so far: {stats['agent_stats']['tool_call_count']}[/dim]")
        
        stats = self.get_stats()
        self.results.append({
            "scenario": "Scenario 3: Stale-Failure Poisoning",
            "expected_resets": 1,
            "actual_resets": stats['detector_stats']['reset_count'],
            "turns": stats['agent_stats']['turn_count'],
            "tool_calls": stats['agent_stats']['tool_call_count'],
            "latency_mean": stats['detector_stats']['latency_stats']['mean_ms']
        })
    
    def run_scenario_4(self):
        """Scenario 4: Repeated Genuine Failures"""
        console.print("\n[bold blue]Scenario 4: Repeated Genuine Failures[/bold blue]")
        
        self.reset_session()
        self.clear_failure()
        
        # Inject 5 operation failures
        self.inject_failure("offline", 5)
        console.print("[yellow]Injected offline failure (duration=5)[/yellow]")
        
        for i in range(1, 6):
            console.print(f"[dim]Turn {i}:[/dim] Turn on the fan")
            result = self.send_message("Turn on the fan")
            console.print(f"[cyan]Response:[/cyan] {result['response'][:80]}...")
            if result['reset_triggered']:
                console.print(f"[yellow]⚠ Reset: {result['reset_reason']}[/yellow]")
        
        stats = self.get_stats()
        self.results.append({
            "scenario": "Scenario 4: Repeated Genuine Failures",
            "expected_resets": "0-2",
            "actual_resets": stats['detector_stats']['reset_count'],
            "turns": stats['agent_stats']['turn_count'],
            "tool_calls": stats['agent_stats']['tool_call_count'],
            "latency_mean": stats['detector_stats']['latency_stats']['mean_ms']
        })
    
    def run_scenario_5(self):
        """Scenario 5: Mixed Intent"""
        console.print("\n[bold blue]Scenario 5: Mixed Intent[/bold blue]")
        
        self.reset_session()
        self.clear_failure()
        
        inputs = [
            "Turn off the light and tell me a joke",
            "Set fan speed to 2 and what's the weather like?"
        ]
        
        for i, msg in enumerate(inputs, 1):
            console.print(f"[dim]Turn {i}:[/dim] {msg}")
            result = self.send_message(msg)
            console.print(f"[cyan]Response:[/cyan] {result['response'][:100]}...")
            if result['reset_triggered']:
                console.print(f"[yellow]⚠ Reset: {result['reset_reason']}[/yellow]")
        
        stats = self.get_stats()
        self.results.append({
            "scenario": "Scenario 5: Mixed Intent",
            "expected_resets": 0,
            "actual_resets": stats['detector_stats']['reset_count'],
            "turns": stats['agent_stats']['turn_count'],
            "tool_calls": stats['agent_stats']['tool_call_count'],
            "latency_mean": stats['detector_stats']['latency_stats']['mean_ms']
        })
    
    def print_summary(self):
        """Print test summary."""
        console.print("\n" + "="*80)
        console.print("[bold]Test Summary[/bold]")
        console.print("="*80 + "\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Scenario", style="cyan")
        table.add_column("Expected Resets", justify="center")
        table.add_column("Actual Resets", justify="center")
        table.add_column("Turns", justify="center")
        table.add_column("Tool Calls", justify="center")
        table.add_column("Latency (ms)", justify="right")
        table.add_column("Status", justify="center")
        
        for result in self.results:
            expected = str(result['expected_resets'])
            actual = result['actual_resets']
            
            # Determine pass/fail
            if expected.isdigit():
                status = "✓" if actual == int(expected) else "✗"
            else:
                # Range like "0-1"
                low, high = map(int, expected.split('-'))
                status = "✓" if low <= actual <= high else "✗"
            
            status_style = "green" if status == "✓" else "red"
            
            table.add_row(
                result['scenario'],
                expected,
                str(actual),
                str(result['turns']),
                str(result['tool_calls']),
                f"{result['latency_mean']:.2f}",
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        console.print(table)
        
        # Overall assessment
        all_passed = all(
            (str(r['expected_resets']).isdigit() and r['actual_resets'] == int(r['expected_resets'])) or
            (not str(r['expected_resets']).isdigit() and 
             int(r['expected_resets'].split('-')[0]) <= r['actual_resets'] <= int(r['expected_resets'].split('-')[1]))
            for r in self.results
        )
        
        avg_latency = sum(r['latency_mean'] for r in self.results) / len(self.results)
        latency_ok = avg_latency < 500
        
        console.print(f"\n[bold]Overall Status:[/bold] {'[green]PASS ✓[/green]' if all_passed and latency_ok else '[red]FAIL ✗[/red]'}")
        console.print(f"[bold]Average Latency:[/bold] {avg_latency:.2f} ms {'[green](within budget)[/green]' if latency_ok else '[red](exceeds budget)[/red]'}")


def main():
    console.print(Panel.fit(
        "[bold]Automated Scenario Testing[/bold]\n"
        "Testing all 5 scenarios via API",
        border_style="blue"
    ))
    
    # Check backend health
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code != 200:
            console.print("[red]Backend not responding. Please start the backend first.[/red]")
            return
    except:
        console.print("[red]Cannot connect to backend. Please start the backend first.[/red]")
        console.print(f"[dim]Expected at: {API_BASE_URL}[/dim]")
        return
    
    tester = ScenarioTester()
    
    if not tester.create_session():
        return
    
    try:
        tester.run_scenario_1()
        tester.run_scenario_2()
        tester.run_scenario_3()
        tester.run_scenario_4()
        tester.run_scenario_5()
        
        tester.print_summary()
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Testing interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
