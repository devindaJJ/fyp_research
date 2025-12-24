import os
import sys
import time
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.google_maps_client import GoogleMapsClient
from src.core.location_service import LocationService
from src.core.traffic_analyzer import TrafficAnalyzer, TrafficAnalysis
from src.core.route_optimizer import RouteOptimizer
from src.utils.logger import setup_logger

console = Console()
logger = setup_logger(__name__)


class UrbanTrafficSystem:
    """Main application class for urban traffic analysis in Sri Lanka."""
    
    def __init__(self):
        """Initialize the traffic system."""
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not self.api_key:
            console.print("[red]ERROR: Google Maps API key not found![/red]")
            console.print("[yellow]Please create a .env file with:[/yellow]")
            console.print("[cyan]GOOGLE_MAPS_API_KEY=your_key_here[/cyan]")
            exit(1)
        
        # Initialize components
        self.gmaps_client = GoogleMapsClient(self.api_key)
        self.location_service = LocationService(self.gmaps_client.client)
        self.traffic_analyzer = TrafficAnalyzer(self.gmaps_client)
        self.route_optimizer = RouteOptimizer(self.gmaps_client)
        
        console.print("[green]Urban Traffic System Initialized[/green]")
        console.print("[cyan]Automatic location detection enabled[/cyan]")
    
    def analyze_route_with_auto_location(self, destination: str) -> Optional[TrafficAnalysis]:
        """
        Automatically detect current location and analyze route to destination.
        Returns comprehensive traffic analysis.
        """
        console.print(f"\n[bold cyan]AUTOMATIC ROUTE ANALYSIS[/bold cyan]")
        console.print(f"[yellow]Destination: {destination}[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            # Step 1: Detect current location
            progress.add_task("Detecting your current location...", total=None)
            current_location = self.location_service.detect_current_location()
            
            if not current_location:
                console.print("[red]Could not detect your current location[/red]")
                console.print("[yellow]Please enter your starting location manually[/yellow]")
                return None
            
            console.print(f"[green]Location detected: {current_location.address}[/green]")
            
            # Step 2: Analyze route
            progress.add_task("Analyzing traffic conditions...", total=None)
            analysis = self.traffic_analyzer.analyze_route(
                current_location.address,
                destination
            )
        
        return analysis
    
    def display_analysis_results(self, analysis: TrafficAnalysis):
        """Display traffic analysis results in a user-friendly format."""
        console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
        console.print(f"[bold green]TRAFFIC ANALYSIS REPORT[/bold green]")
        console.print(f"[bold cyan]{'='*70}[/bold cyan]")
        
        # Route Information
        route_table = Table(show_header=False, box=None)
        route_table.add_row("[bold]From:[/bold]", f"[cyan]{analysis.primary_route.origin}[/cyan]")
        route_table.add_row("[bold]To:[/bold]", f"[cyan]{analysis.primary_route.destination}[/cyan]")
        route_table.add_row("[bold]Analysis Time:[/bold]", f"[yellow]{analysis.analysis_time.strftime('%Y-%m-%d %H:%M:%S')}[/yellow]")
        console.print(route_table)
        
        # Current Traffic Conditions
        current_traffic = Panel(
            f"[bold]{analysis.congestion_level.get_description()}[/bold]\n\n"
            f"Distance: {analysis.primary_route.distance_text}\n"
            f"Normal Time: {analysis.primary_route.normal_duration:.1f} minutes\n"
            f"Current Time: {analysis.primary_route.traffic_duration:.1f} minutes\n"
            f"Delay: {analysis.delay_minutes:.1f} minutes ({analysis.primary_route.delay_percentage:.1f}% increase)\n"
            f"Primary Route: {analysis.primary_route.summary}",
            title="Current Traffic Conditions",
            border_style="green" if analysis.congestion_level.value == "light" else 
                        "yellow" if analysis.congestion_level.value == "moderate" else
                        "red"
        )
        console.print(current_traffic)
        
        # Alternative Routes
        if analysis.alternatives:
            alt_table = Table(title="Available Alternative Routes", box=None)
            alt_table.add_column("#", style="cyan", no_wrap=True)
            alt_table.add_column("Route", style="yellow")
            alt_table.add_column("Time", style="green")
            alt_table.add_column("Delay", style="red")
            alt_table.add_column("Traffic", style="magenta")
            
            for i, alt in enumerate(analysis.alternatives, 1):
                alt_table.add_row(
                    str(i),
                    alt.summary[:30] + "..." if len(alt.summary) > 30 else alt.summary,
                    f"{alt.traffic_duration:.1f} min",
                    f"{alt.delay_minutes:.1f} min",
                    f"{alt.traffic_level.name.title()}"
                )
            
            console.print(alt_table)
        
        # Rerouting Recommendation
        if analysis.should_reroute:
            if analysis.recommended_alternative:
                recommendation = Panel(
                    f"[bold green]RECOMMENDATION: Take Alternative Route[/bold green]\n\n"
                    f"Route: [cyan]{analysis.recommended_alternative.summary}[/cyan]\n"
                    f"Estimated Savings: [green]{analysis.delay_minutes - analysis.recommended_alternative.delay_minutes:.1f} minutes[/green]\n"
                    f"New Travel Time: [yellow]{analysis.recommended_alternative.traffic_duration:.1f} minutes[/yellow]\n"
                    f"Traffic Level: {analysis.recommended_alternative.traffic_level.name.title()}",
                    title="Optimization Suggestion",
                    border_style="green"
                )
            else:
                recommendation = Panel(
                    f"[bold yellow]RECOMMENDATION: Consider Delaying Your Trip[/bold yellow]\n\n"
                    f"All alternative routes also have heavy traffic.\n"
                    f"Waiting 30-60 minutes might improve conditions.",
                    title="Optimization Suggestion",
                    border_style="yellow"
                )
        else:
            recommendation = Panel(
                f"[bold green]RECOMMENDATION: Continue on Current Route[/bold green]\n\n"
                f"Traffic conditions are acceptable.\n"
                f"No significant time savings from alternative routes.",
                title="Optimization Suggestion",
                border_style="green"
            )
        
        console.print(recommendation)
        console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    def get_user_destination(self) -> str:
        """Get destination input from user with suggestions."""
        console.print("\n[bold cyan]ENTER DESTINATION[/bold cyan]")
        console.print("[yellow]Examples:[/yellow]")
        console.print("  • Galle Fort, Sri Lanka")
        console.print("  • Kandy City Center")
        console.print("  • Bandaranaike International Airport")
        console.print("  • 123 Galle Road, Colombo")
        
        destination = console.input("\n[cyan]Where do you want to go? [/cyan]").strip()
        
        if not destination:
            console.print("[red]Destination cannot be empty[/red]")
            return self.get_user_destination()
        
        # Add Sri Lanka if not specified
        if "sri lanka" not in destination.lower():
            destination = f"{destination}, Sri Lanka"
        
        return destination
    
    def run_single_analysis(self):
        """Run a single route analysis with automatic location detection."""
        try:
            destination = self.get_user_destination()
            analysis = self.analyze_route_with_auto_location(destination)
            
            if analysis:
                self.display_analysis_results(analysis)
                
                if console.input("\nView detailed rerouting advice? (y/n): ").lower() == 'y':
                    advice = self.traffic_analyzer.get_detailed_reroute_advice(analysis)
                    
                    console.print("\n[bold cyan]DETAILED REROUTING ADVICE[/bold cyan]")
                    for key, value in advice.items():
                        if isinstance(value, list):
                            console.print(f"[yellow]{key.replace('_', ' ').title()}:[/yellow]")
                            for item in value:
                                console.print(f"  • {item}")
                        elif isinstance(value, dict):
                            console.print(f"[yellow]{key.replace('_', ' ').title()}:[/yellow]")
                            for k, v in value.items():
                                console.print(f"  {k.replace('_', ' ').title()}: {v}")
                        else:
                            console.print(f"[yellow]{key.replace('_', ' ').title()}:[/yellow] {value}")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            console.print(f"[red]Analysis failed: {str(e)}[/red]")
    
    def run_continuous_monitoring(self, destination: str, interval_minutes: int = 10):
        """Continuously monitor a route and alert on changes."""
        console.print(f"\n[bold green]STARTING CONTINUOUS MONITORING[/bold green]")
        console.print(f"Update interval: {interval_minutes} minutes")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
        
        previous_analysis = None
        
        try:
            while True:
                analysis = self.analyze_route_with_auto_location(destination)
                
                if analysis:
                    if previous_analysis:
                        delay_change = analysis.delay_minutes - previous_analysis.delay_minutes
                        traffic_change = (analysis.congestion_level != previous_analysis.congestion_level)
                        
                        if abs(delay_change) > 5 or traffic_change:
                            console.print(f"\n[bold yellow]TRAFFIC CONDITIONS CHANGED[/bold yellow]")
                            console.print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
                            console.print(f"Delay Change: {'+' if delay_change > 0 else ''}{delay_change:.1f} minutes")
                            console.print(f"New Traffic Level: {analysis.congestion_level.name.title()}")
                            
                            if analysis.should_reroute and analysis.recommended_alternative:
                                console.print(f"[green]New Recommendation: Take {analysis.recommended_alternative.summary}[/green]")
                    
                    # Brief status update
                    time_str = datetime.now().strftime("%H:%M:%S")
                    console.print(f"[cyan]{time_str}[/cyan] - "
                                 f"Delay: [bold]{analysis.delay_minutes:.1f} min[/bold] - "
                                 f"Traffic: {analysis.congestion_level.name.title()}")
                    
                    previous_analysis = analysis
                
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Monitoring stopped[/yellow]")
    
    def show_main_menu(self):
        """Display the main menu."""
        console.print(Panel.fit(
            "[bold cyan]URBAN TRAFFIC SYSTEM - SRI LANKA[/bold cyan]\n"
            "[yellow]Automatic Location Detection & Smart Routing[/yellow]",
            border_style="green"
        ))
        
        menu_table = Table(show_header=False, box=None)
        menu_table.add_row("1", "Analyze route to destination (auto-location)")
        menu_table.add_row("2", "Monitor route continuously")
        menu_table.add_row("3", "Compare multiple destinations")
        menu_table.add_row("4", "Get current location info")
        menu_table.add_row("5", "Exit")
        
        console.print(menu_table)
    
    def run(self):
        """Run the main application loop."""
        console.print("[green]Starting Urban Traffic System...[/green]")
        
        # Test API connection
        try:
            test_location = self.location_service.detect_current_location()
            if test_location:
                console.print(f"[green]System ready. Your location: {test_location.city}[/green]")
        except Exception as e:
            console.print(f"[yellow]Location service limited: {str(e)}[/yellow]")
        
        while True:
            self.show_main_menu()
            
            choice = console.input("\n[cyan]Select an option (1-5): [/cyan]").strip()
            
            if choice == '1':
                self.run_single_analysis()
            
            elif choice == '2':
                destination = self.get_user_destination()
                try:
                    interval = int(console.input("Update interval (minutes, default 10): ") or "10")
                    self.run_continuous_monitoring(destination, interval)
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
            
            elif choice == '3':
                self.compare_multiple_destinations()
            
            elif choice == '4':
                self.show_current_location_info()
            
            elif choice == '5':
                console.print("\n[green]Thank you for using Urban Traffic System![/green]")
                break
            
            else:
                console.print("[red]Invalid choice. Please select 1-5.[/red]")
            
            console.input("\nPress Enter to continue...")
    
    def compare_multiple_destinations(self):
        """Compare traffic to multiple destinations from current location."""
        console.print("\n[bold cyan]COMPARE MULTIPLE DESTINATIONS[/bold cyan]")
        console.print("[yellow]Enter destinations separated by commas[/yellow]")
        
        destinations_input = console.input("\nDestinations: ").strip()
        destinations = [d.strip() for d in destinations_input.split(',') if d.strip()]
        
        if len(destinations) < 2:
            console.print("[red]Please enter at least 2 destinations[/red]")
            return
        
        # Detect current location
        current_location = self.location_service.detect_current_location()
        if not current_location:
            console.print("[red]Could not detect current location[/red]")
            return
        
        console.print(f"\n[green]Starting from: {current_location.address}[/green]")
        
        results = []
        with Progress() as progress:
            task = progress.add_task("Analyzing destinations...", total=len(destinations))
            
            for destination in destinations:
                try:
                    analysis = self.traffic_analyzer.analyze_route(
                        current_location.address,
                        destination
                    )
                    
                    if analysis:
                        results.append({
                            'destination': destination,
                            'time': analysis.primary_route.traffic_duration,
                            'delay': analysis.delay_minutes,
                            'traffic': analysis.congestion_level
                        })
                    
                    progress.update(task, advance=1)
                    time.sleep(1)  # Avoid rate limiting
                    
                except Exception as e:
                    logger.error(f"Failed to analyze {destination}: {e}")
        
        if results:
            # Sort by travel time
            results.sort(key=lambda x: x['time'])
            
            # Display comparison
            table = Table(title="Destination Comparison", box=None)
            table.add_column("Destination", style="cyan")
            table.add_column("Travel Time", style="yellow")
            table.add_column("Delay", style="red")
            table.add_column("Traffic", style="green")
            
            for result in results:
                table.add_row(
                    result['destination'][:30] + ("..." if len(result['destination']) > 30 else ""),
                    f"{result['time']:.1f} min",
                    f"{result['delay']:.1f} min",
                    f"{result['traffic'].name.title()}"
                )
            
            console.print(table)
            
            # Show fastest option
            fastest = results[0]
            console.print(f"\n[bold green]Fastest Option: {fastest['destination']}[/bold green]")
            console.print(f"   Travel Time: {fastest['time']:.1f} minutes")
            console.print(f"   Traffic: {fastest['traffic'].name.title()}")
    
    def show_current_location_info(self):
        """Show detailed information about current location."""
        console.print("\n[bold cyan]CURRENT LOCATION INFORMATION[/bold cyan]")
        
        location = self.location_service.detect_current_location()
        
        if location:
            info_panel = Panel(
                f"[bold]Address:[/bold] {location.address}\n"
                f"[bold]City:[/bold] {location.city}\n"
                f"[bold]Country:[/bold] {location.country}\n"
                f"[bold]Coordinates:[/bold] {location.latitude:.6f}, {location.longitude:.6f}\n"
                f"[bold]Accuracy:[/bold] {location.accuracy * 100:.1f}%\n"
                f"[bold]Detection Method:[/bold] {location.source}\n"
                f"[bold]Timestamp:[/bold] {location.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                title="Location Details",
                border_style="cyan"
            )
            console.print(info_panel)
        else:
            console.print("[red]Could not determine current location[/red]")


def main():
    """Application entry point."""
    try:
        app = UrbanTrafficSystem()
        app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user[/yellow]")
    except Exception as e:
        logger.error(f"Application error: {e}")
        console.print(f"[red]Fatal error: {str(e)}[/red]")


if __name__ == "__main__":
    main()
