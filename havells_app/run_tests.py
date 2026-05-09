"""
Test runner script - runs all tests and generates report.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --verbose    # Verbose output
    python run_tests.py --coverage   # With coverage report
"""
import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_tests(verbose=False, coverage=False):
    """Run all tests with pytest."""
    console.print(Panel.fit(
        "[bold blue]Running Test Suite[/bold blue]\n"
        "Testing all components of the Agent with Auto Session Reset",
        border_style="blue"
    ))
    
    # Build pytest command
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
    
    # Add test files
    test_files = [
        "test_config.py",
        "test_device.py",
        "test_reset_detector.py",
        "test_integration.py"
    ]
    
    cmd.extend(test_files)
    
    console.print(f"\n[dim]Running: {' '.join(cmd)}[/dim]\n")
    
    # Run tests
    try:
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode
    except FileNotFoundError:
        console.print("[red]Error: pytest not found. Install with: pip install pytest[/red]")
        return 1


def check_test_files():
    """Check that all test files exist."""
    test_files = [
        "test_config.py",
        "test_device.py",
        "test_reset_detector.py",
        "test_integration.py"
    ]
    
    missing = []
    for test_file in test_files:
        if not Path(test_file).exists():
            missing.append(test_file)
    
    if missing:
        console.print(f"[yellow]Warning: Missing test files: {', '.join(missing)}[/yellow]")
        return False
    
    return True


def display_test_summary():
    """Display test coverage summary."""
    table = Table(title="Test Coverage Summary")
    table.add_column("Module", style="cyan")
    table.add_column("Test File", style="green")
    table.add_column("Status", style="bold")
    
    tests = [
        ("config.py", "test_config.py", "✓" if Path("test_config.py").exists() else "✗"),
        ("device.py", "test_device.py", "✓" if Path("test_device.py").exists() else "✗"),
        ("reset_detector.py", "test_reset_detector.py", "✓" if Path("test_reset_detector.py").exists() else "✗"),
        ("Integration", "test_integration.py", "✓" if Path("test_integration.py").exists() else "✗"),
    ]
    
    for module, test_file, status in tests:
        table.add_row(module, test_file, status)
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run test suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Generate coverage report")
    args = parser.parse_args()
    
    # Display test files
    display_test_summary()
    
    # Check test files exist
    if not check_test_files():
        console.print("[yellow]Some test files are missing, but continuing...[/yellow]\n")
    
    # Run tests
    exit_code = run_tests(verbose=args.verbose, coverage=args.coverage)
    
    # Summary
    if exit_code == 0:
        console.print("\n")
        console.print(Panel.fit(
            "[bold green]✓ All tests passed![/bold green]\n\n"
            "Your code is working correctly.",
            border_style="green"
        ))
    else:
        console.print("\n")
        console.print(Panel.fit(
            "[bold red]✗ Some tests failed[/bold red]\n\n"
            "Please review the errors above.",
            border_style="red"
        ))
    
    if args.coverage:
        console.print("\n[dim]Coverage report generated in htmlcov/index.html[/dim]")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
