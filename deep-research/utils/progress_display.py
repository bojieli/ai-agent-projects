import sys
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

class ResearchProgress:
    def __init__(self):
        self.console = Console()
        self.current_step = ""
        self.current_details = ""
        self.start_time = datetime.now()
        
    def update(self, step: str, details: Optional[str] = None):
        """Update progress display without clearing previous output"""
        self.current_step = step
        self.current_details = details or ""
        
        elapsed = datetime.now() - self.start_time
        
        # Create status display
        status = Text()
        status.append("🔍 Research in Progress\n", style="bold blue")
        status.append(f"⏱️  Elapsed: {str(elapsed).split('.')[0]}\n", style="yellow")
        status.append(f"📍 Current: {self.current_step}\n", style="green")
        
        if self.current_details:
            status.append(f"\n{self.current_details}", style="dim")
            
        # Print status without clearing screen
        self.console.print("\n")  # Add spacing from previous output
        self.console.print(Panel(status, title="Deep Research Agent"))
        
    def complete(self, output_path: str):
        """Show completion message"""
        elapsed = datetime.now() - self.start_time
        
        status = Text()
        status.append("✅ Research Complete!\n", style="bold green")
        status.append(f"⏱️  Total time: {str(elapsed).split('.')[0]}\n", style="yellow")
        status.append(f"📄 Report saved to: {output_path}", style="blue")
        
        # Print completion without clearing screen
        self.console.print("\n")
        self.console.print(Panel(status, title="Deep Research Agent"))
        
    def show_error(self, error: Exception):
        """Show error message"""
        status = Text()
        status.append("❌ Research Failed!\n", style="bold red")
        
        if hasattr(error, 'status_code'):
            status.append(f"Status Code: {error.status_code}\n", style="yellow")
        
        status.append(f"Error: {str(error)}", style="red")
        
        if hasattr(error, 'response_body'):
            status.append(f"\n\nResponse Details:\n{error.response_body}", style="dim red")
            
        # Print error without clearing screen
        self.console.print("\n")
        self.console.print(Panel(status, title="Deep Research Agent")) 