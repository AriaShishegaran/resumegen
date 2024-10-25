# user_interface.py

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.syntax import Syntax
from difflib import unified_diff

console = Console()

class UserInterface:
    @staticmethod
    def success(message):
        console.print(f"✓ [bold green]{message}[/bold green]")

    @staticmethod
    def error(message):
        console.print(f"✗ [bold red]{message}[/bold red]")

    @staticmethod
    def progress(message):
        console.print(f"→ [cyan]{message}[/cyan]")

    @staticmethod
    def info(message):
        console.print(f"ℹ [blue]{message}[/blue]")

    @staticmethod
    def debug(message):
        console.print(f"➤ [magenta]{message}[/magenta]")

    @staticmethod
    def warning(message):
        console.print(f"⚠ [yellow]{message}[/yellow]")

    @staticmethod
    def print_requirements(requirements):
        console.print("\n[bold underline cyan]Key Requirements:[/bold underline cyan]")
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAVY)
        table.add_column("No.", justify="right", width=4)
        table.add_column("Requirement", justify="left")
        for idx, req in enumerate(requirements, start=1):
            table.add_row(f"{idx}", req)
        console.print(table)

    @staticmethod
    def section_status(current, total, section_type):
        console.print(f"→ [cyan]Processing {section_type} {current}/{total}[/cyan]")

    @staticmethod
    def print_input_output(input_text, output_text):
        console.print(Panel(f":inbox_tray: [bold underline]Input Text[/bold underline]\n{input_text}", title="Input", style="dim"))
        console.print(Panel(f":outbox_tray: [bold underline]Output Text[/bold underline]\n{output_text}", title="Output", style="dim"))

    @staticmethod
    def print_diff(input_text, output_text):
        diff = unified_diff(
            input_text.splitlines(),
            output_text.splitlines(),
            fromfile='Original',
            tofile='Adjusted',
            lineterm=''
        )
        diff_text = '\n'.join(diff)
        if diff_text:
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
            console.print(syntax)
        else:
            console.print("[green]No changes made in this section.[/green]")
