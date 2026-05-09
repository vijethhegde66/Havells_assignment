"""Quick validation test to ensure everything is set up correctly."""
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()


def test_imports():
    """Test that all required modules can be imported."""
    console.print("\n[bold]Testing imports...[/bold]")
    
    try:
        import openai
        console.print("  ✓ openai")
    except ImportError as e:
        console.print(f"  ✗ openai: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        console.print("  ✓ python-dotenv")
    except ImportError as e:
        console.print(f"  ✗ python-dotenv: {e}")
        return False
    
    try:
        from rich import print as rprint
        console.print("  ✓ rich")
    except ImportError as e:
        console.print(f"  ✗ rich: {e}")
        return False
    
    return True


def test_config():
    """Test that configuration is valid."""
    console.print("\n[bold]Testing configuration...[/bold]")
    
    try:
        from config import Config
        console.print(f"  ✓ Config loaded")
        console.print(f"    - Endpoint: {Config.AZURE_OPENAI_ENDPOINT[:40]}...")
        console.print(f"    - Model: {Config.LLM_MODEL}")
        console.print(f"    - Latency budget: {Config.RESET_LATENCY_BUDGET_MS} ms")
        return True
    except Exception as e:
        console.print(f"  ✗ Configuration error: {e}")
        return False


def test_device():
    """Test that device module works."""
    console.print("\n[bold]Testing device module...[/bold]")
    
    try:
        from device import SmartDevice, DeviceState
        
        device = SmartDevice()
        
        # Test power on
        result = device.power_on()
        assert result["success"] is True
        console.print("  ✓ power_on works")
        
        # Test speed setting
        result = device.set_speed(3)
        assert result["success"] is True
        assert device.speed == 3
        console.print("  ✓ set_speed works")
        
        # Test failure injection
        device.inject_failure(DeviceState.OFFLINE, duration=1)
        result = device.power_off()
        assert result["success"] is False
        console.print("  ✓ failure injection works")
        
        return True
    except Exception as e:
        console.print(f"  ✗ Device test failed: {e}")
        return False


def test_reset_detector():
    """Test that reset detector works."""
    console.print("\n[bold]Testing reset detector...[/bold]")
    
    try:
        from reset_detector import ResetDetector
        
        detector = ResetDetector()
        
        # Test tool starvation detection
        agent_stats = {
            "turn_count": 4,
            "tool_call_count": 1,
            "last_tool_call_turn": 1,
            "turns_since_last_tool_call": 3
        }
        
        messages = [
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "I'll turn on the fan"},
            {"role": "user", "content": "Turn on the fan"},
            {"role": "assistant", "content": "The device is offline"}
        ]
        
        should_reset, reason = detector.should_reset(
            agent_stats,
            messages,
            "The device is offline"
        )
        
        console.print(f"  ✓ Detection works (reset={should_reset}, reason={reason})")
        
        # Check latency
        stats = detector.get_stats()
        mean_latency = stats['latency_stats']['mean_ms']
        console.print(f"  ✓ Latency: {mean_latency:.2f} ms (budget: 500 ms)")
        
        if mean_latency < 500:
            console.print(f"  ✓ Within budget!")
        else:
            console.print(f"  ✗ Exceeds budget!")
            return False
        
        return True
    except Exception as e:
        console.print(f"  ✗ Reset detector test failed: {e}")
        return False


def test_agent():
    """Test that agent can be initialized (doesn't make API calls)."""
    console.print("\n[bold]Testing agent initialization...[/bold]")
    
    try:
        from device import SmartDevice
        from agent import NaiveDeviceAgent
        
        device = SmartDevice()
        agent = NaiveDeviceAgent(device)
        
        console.print("  ✓ Agent initialized")
        console.print(f"    - System prompt: {agent.SYSTEM_PROMPT[:50]}...")
        console.print(f"    - Initial turns: {agent.turn_count}")
        
        return True
    except Exception as e:
        console.print(f"  ✗ Agent initialization failed: {e}")
        return False


def main():
    """Run all validation tests."""
    console.print(Panel.fit(
        "[bold blue]Quick Validation Test[/bold blue]\n"
        "This will verify your setup is correct.",
        border_style="blue"
    ))
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Device Module", test_device()))
    results.append(("Reset Detector", test_reset_detector()))
    results.append(("Agent", test_agent()))
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold]Validation Summary[/bold]")
    console.print("="*60 + "\n")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        color = "green" if passed else "red"
        console.print(f"[{color}]{status}[/{color}] {name}")
        if not passed:
            all_passed = False
    
    console.print("\n" + "="*60)
    
    if all_passed:
        console.print(Panel.fit(
            "[bold green]✓ All tests passed![/bold green]\n\n"
            "Your environment is ready. Next steps:\n\n"
            "1. Run interactive mode:  python main.py\n"
            "2. Run all scenarios:     python scenarios.py\n"
            "3. Check transcripts:     ls test_transcripts/",
            border_style="green"
        ))
        return 0
    else:
        console.print(Panel.fit(
            "[bold red]✗ Some tests failed[/bold red]\n\n"
            "Please fix the issues above before proceeding.\n"
            "Check QUICKSTART.md for troubleshooting help.",
            border_style="red"
        ))
        return 1


if __name__ == "__main__":
    sys.exit(main())
