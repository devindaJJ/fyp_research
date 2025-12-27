import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import googlemaps
from geopy.geocoders import Nominatim
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv()

console = Console()

class SriLankaGoogleTraffic:
    def __init__(self):
        """Initialize Google Maps client for Sri Lanka."""
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not self.api_key:
            console.print("[red]❌ ERROR: Google Maps API key not found![/red]")
            console.print("[yellow]Please create a .env file with:[/yellow]")
            console.print("[cyan]GOOGLE_MAPS_API_KEY=your_key_here[/cyan]")
            exit(1)
        
        # Initialize Google Maps client
        self.gmaps = googlemaps.Client(key=self.api_key)
        
        # Initialize geocoder for Sri Lanka addresses
        self.geolocator = Nominatim(user_agent="sri_lanka_traffic_app")
        
        # Load Sri Lanka locations
        self.load_sri_lanka_locations()
        
        console.print("[green]✅ Sri Lanka Traffic Monitor (Google Maps)[/green]")
        console.print(f"[cyan]📍 Loaded {len(self.cities)} Sri Lankan cities[/cyan]")
    
    def load_sri_lanka_locations(self):
        """Load Sri Lanka locations from config file."""
        try:
            with open(r'/Users/devindajayathilake/Documents/UrbanTrafficSystem/config/sri_lanka_locations.json', 'r') as f:
                data = json.load(f)
                self.cities = data['major_cities']
                self.routes = data['popular_routes']
                self.hotspots = data['traffic_hotspots']
        except FileNotFoundError:
            console.print("[yellow]⚠️ Config file not found. Using default cities.[/yellow]")
            self.cities = {
                "Colombo": {"latitude": 6.9271, "longitude": 79.8612},
                "Kandy": {"latitude": 7.2906, "longitude": 80.6337},
                "Galle": {"latitude": 6.0535, "longitude": 80.2210},
            }
            self.routes = {}
            self.hotspots = {}
    
    def geocode_sri_lanka_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Convert Sri Lankan address to coordinates."""
        try:
            # Add Sri Lanka to address for better results
            if "sri lanka" not in address.lower():
                address += ", Sri Lanka"
            
            location = self.geolocator.geocode(address, timeout=10)
            
            if location:
                # Validate coordinates are in Sri Lanka
                if 5.5 <= location.latitude <= 10.0 and 79.5 <= location.longitude <= 82.0:
                    return (location.latitude, location.longitude)
                else:
                    console.print("[red]❌ Address is not in Sri Lanka[/red]")
                    return None
            else:
                console.print("[red]❌ Address not found. Try being more specific.[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ Geocoding error: {e}[/red]")
            return None
    
    def get_route_traffic(self, origin: str, destination: str) -> Dict:
        """Get traffic information for a route using Google Maps Directions API."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Fetching traffic data...", total=None)
                
                # Get directions with current traffic
                now = datetime.now()
                directions_result = self.gmaps.directions(
                    origin=origin,
                    destination=destination,
                    mode="driving",
                    departure_time=now,
                    traffic_model="best_guess",
                    alternatives=True  # Get multiple routes if available
                )
                
                if not directions_result:
                    return {"error": "No routes found"}
                
                # Process the best route
                best_route = directions_result[0]
                leg = best_route['legs'][0]
                
                # Calculate traffic information
                normal_duration = leg['duration']['value']  # in seconds
                traffic_duration = leg.get('duration_in_traffic', {}).get('value', normal_duration)
                
                delay_seconds = traffic_duration - normal_duration
                delay_minutes = delay_seconds / 60
                
                # Determine traffic level
                if delay_minutes <= 5:
                    traffic_level = "🟢 Light"
                    level_emoji = "🟢"
                elif delay_minutes <= 15:
                    traffic_level = "🟡 Moderate"
                    level_emoji = "🟡"
                elif delay_minutes <= 30:
                    traffic_level = "🟠 Heavy"
                    level_emoji = "🟠"
                else:
                    traffic_level = "🔴 Severe"
                    level_emoji = "🔴"
                
                # Get alternative routes
                alternatives = []
                if len(directions_result) > 1:
                    for i, route in enumerate(directions_result[1:3], 2):  # Max 2 alternatives
                        alt_leg = route['legs'][0]
                        alt_traffic = alt_leg.get('duration_in_traffic', {}).get('value', alt_leg['duration']['value'])
                        alternatives.append({
                            'route': i,
                            'duration': alt_traffic / 60,  # minutes
                            'distance': alt_leg['distance']['text']
                        })
                
                return {
                    'success': True,
                    'origin': origin,
                    'destination': destination,
                    'normal_duration_minutes': normal_duration / 60,
                    'traffic_duration_minutes': traffic_duration / 60,
                    'delay_minutes': delay_minutes,
                    'distance': leg['distance']['text'],
                    'traffic_level': traffic_level,
                    'level_emoji': level_emoji,
                    'route_summary': best_route.get('summary', 'Route'),
                    'alternatives': alternatives,
                    'steps': len(leg['steps']),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        except Exception as e:
            return {"error": f"API Error: {str(e)}"}
    
    def get_city_traffic_snapshot(self, city_name: str) -> Dict:
        """Get traffic snapshot for a city by checking multiple routes within it."""
        if city_name not in self.cities:
            return {"error": f"City '{city_name}' not in database"}
        
        city = self.cities[city_name]
        
        # Create routes within the city
        routes = []
        
        # Example routes within city
        if city_name == "Colombo":
            routes = [
                ("Colombo Fort", "Bambalapitiya"),
                ("Pettah", "Nugegoda"),
                ("Marine Drive Start", "Marine Drive End")
            ]
        elif city_name == "Kandy":
            routes = [
                ("Kandy City Center", "Peradeniya"),
                ("Temple of the Tooth", "Katugastota")
            ]
        else:
            # Generic routes
            center = city.get('center', f"{city_name} Center")
            routes = [(center, f"{city_name} Outskirts")]
        
        results = []
        for origin, destination in routes[:2]:  # Check max 2 routes
            try:
                route_info = self.get_route_traffic(
                    f"{origin}, {city_name}, Sri Lanka",
                    f"{destination}, {city_name}, Sri Lanka"
                )
                if 'success' in route_info:
                    results.append(route_info)
                time.sleep(0.5)  # Avoid rate limiting
            except:
                continue
        
        if results:
            # Calculate average delay
            avg_delay = sum(r['delay_minutes'] for r in results) / len(results)
            
            return {
                'city': city_name,
                'avg_delay_minutes': avg_delay,
                'routes_checked': len(results),
                'worst_route': max(results, key=lambda x: x['delay_minutes']),
                'best_route': min(results, key=lambda x: x['delay_minutes']),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {"error": "Could not retrieve traffic data"}
    
    def display_route_traffic(self, route_info: Dict):
        """Display route traffic information in a beautiful format."""
        if 'error' in route_info:
            console.print(f"[red]❌ Error: {route_info['error']}[/red]")
            return
        
        console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
        console.print(f"[bold green]🚗 ROUTE TRAFFIC REPORT[/bold green]")
        console.print(f"[bold cyan]{'='*70}[/bold cyan]")
        
        # Route Info
        table = Table(show_header=False, box=None)
        table.add_row("📍 [bold]From:[/bold]", f"[cyan]{route_info['origin']}[/cyan]")
        table.add_row("📍 [bold]To:[/bold]", f"[cyan]{route_info['destination']}[/cyan]")
        table.add_row("🕐 [bold]Time:[/bold]", f"[yellow]{route_info['timestamp']}[/yellow]")
        console.print(table)
        
        # Traffic Summary
        summary_panel = Panel(
            f"[bold]{route_info['level_emoji']} {route_info['traffic_level']}[/bold]\n\n"
            f"📏 Distance: {route_info['distance']}\n"
            f"⏱️ Normal Time: {route_info['normal_duration_minutes']:.1f} minutes\n"
            f"🚦 Current Time: {route_info['traffic_duration_minutes']:.1f} minutes\n"
            f"⚠️ Delay: {route_info['delay_minutes']:.1f} minutes\n"
            f"🛣️ Route: {route_info['route_summary']}",
            title="Traffic Summary",
            border_style="green"
        )
        console.print(summary_panel)
        
        # Alternative Routes
        if route_info.get('alternatives'):
            alt_table = Table(title="Alternative Routes", box=None)
            alt_table.add_column("Route", style="cyan")
            alt_table.add_column("Time", style="yellow")
            alt_table.add_column("Distance", style="green")
            
            for alt in route_info['alternatives']:
                alt_table.add_row(
                    f"Option {alt['route']}",
                    f"{alt['duration']:.1f} min",
                    alt['distance']
                )
            
            console.print(alt_table)
        
        console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    def display_city_traffic(self, city_info: Dict):
        """Display city traffic summary."""
        if 'error' in city_info:
            console.print(f"[red]❌ Error: {city_info['error']}[/red]")
            return
        
        console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
        console.print(f"[bold green]🏙️ CITY TRAFFIC SNAPSHOT: {city_info['city'].upper()}[/bold green]")
        console.print(f"[bold cyan]{'='*70}[/bold cyan]")
        
        # City Summary
        summary = f"""
📊 [bold]Overall City Traffic:[/bold]
   🕐 Time: {city_info['timestamp']}
   📍 Routes Checked: {city_info['routes_checked']}
   ⚠️ Average Delay: {city_info['avg_delay_minutes']:.1f} minutes

🚗 [bold]Worst Route:[/bold]
   • {city_info['worst_route']['origin']} → {city_info['worst_route']['destination']}
   • Delay: {city_info['worst_route']['delay_minutes']:.1f} minutes
   • Traffic: {city_info['worst_route']['traffic_level']}

✅ [bold]Best Route:[/bold]
   • {city_info['best_route']['origin']} → {city_info['best_route']['destination']}
   • Delay: {city_info['best_route']['delay_minutes']:.1f} minutes
   • Traffic: {city_info['best_route']['traffic_level']}
        """
        
        console.print(Panel(summary, border_style="cyan"))
        console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    def compare_cities(self, city_names: List[str]):
        """Compare traffic between multiple Sri Lankan cities."""
        console.print(f"\n[bold green]📊 COMPARING TRAFFIC IN {len(city_names)} CITIES[/bold green]")
        
        results = []
        with Progress() as progress:
            task = progress.add_task("Checking cities...", total=len(city_names))
            
            for city in city_names:
                if city in self.cities:
                    city_data = self.get_city_traffic_snapshot(city)
                    if 'avg_delay_minutes' in city_data:
                        results.append({
                            'city': city,
                            'delay': city_data['avg_delay_minutes'],
                            'level': city_data['worst_route']['traffic_level'],
                            'routes': city_data['routes_checked']
                        })
                    progress.update(task, advance=1)
                    time.sleep(1)  # Avoid rate limiting
        
        if results:
            # Sort by worst traffic first
            results.sort(key=lambda x: x['delay'], reverse=True)
            
            # Create comparison table
            table = Table(title="City Traffic Comparison", box=None)
            table.add_column("City", style="cyan", no_wrap=True)
            table.add_column("Avg Delay", style="red")
            table.add_column("Traffic Level", style="yellow")
            table.add_column("Routes Checked", style="green")
            
            for result in results:
                table.add_row(
                    result['city'],
                    f"{result['delay']:.1f} min",
                    result['level'],
                    str(result['routes'])
                )
            
            console.print(table)
            
            # Display worst city
            worst = results[0]
            console.print(f"\n[bold red]🚨 Worst Traffic: {worst['city']} "
                         f"({worst['delay']:.1f} minutes average delay)[/bold red]")
            
            # Display best city
            best = results[-1]
            console.print(f"[bold green]✅ Best Traffic: {best['city']} "
                         f"({best['delay']:.1f} minutes average delay)[/bold green]")
        else:
            console.print("[red]❌ Could not compare cities[/red]")
    
    def monitor_route_continuously(self, origin: str, destination: str, interval_minutes: int = 5):
        """Monitor a route continuously."""
        console.print(f"\n[bold green]📡 STARTING CONTINUOUS MONITORING[/bold green]")
        console.print(f"📍 Route: {origin} → {destination}")
        console.print(f"🔄 Update interval: {interval_minutes} minutes")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
        
        previous_delay = None
        
        try:
            while True:
                route_info = self.get_route_traffic(origin, destination)
                
                if 'success' in route_info:
                    current_delay = route_info['delay_minutes']
                    
                    # Display update
                    time_str = datetime.now().strftime("%H:%M:%S")
                    console.print(f"[cyan]{time_str}[/cyan] - "
                                 f"Delay: [bold]{current_delay:.1f} min[/bold] - "
                                 f"Traffic: {route_info['traffic_level']}")
                    
                    # Alert if significant change
                    if previous_delay is not None:
                        change = current_delay - previous_delay
                        if change > 5:  # If delay increased by more than 5 minutes
                            console.print(f"[red]⚠️ Traffic getting worse! Increased by {change:.1f} minutes[/red]")
                        elif change < -5:  # If delay decreased by more than 5 minutes
                            console.print(f"[green]↓ Traffic improving! Decreased by {-change:.1f} minutes[/green]")
                    
                    previous_delay = current_delay
                
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            console.print(f"\n[yellow]🛑 Stopped monitoring[/yellow]")
    
    def export_to_csv(self, route_info: Dict, filename: str = "traffic_data.csv"):
        """Export traffic data to CSV."""
        try:
            # Create DataFrame
            df = pd.DataFrame([{
                'timestamp': route_info['timestamp'],
                'origin': route_info['origin'],
                'destination': route_info['destination'],
                'normal_duration_min': route_info['normal_duration_minutes'],
                'traffic_duration_min': route_info['traffic_duration_minutes'],
                'delay_min': route_info['delay_minutes'],
                'distance': route_info['distance'],
                'traffic_level': route_info['traffic_level']
            }])
            
            # Save to file
            os.makedirs('data/exports', exist_ok=True)
            filepath = f'data/exports/{filename}'
            df.to_csv(filepath, index=False)
            
            console.print(f"[green]✅ Data exported to {filepath}[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Export failed: {e}[/red]")
    
    def show_main_menu(self):
        """Display the main menu."""
        console.print(Panel.fit(
            "[bold cyan]🇱🇰 SRI LANKA TRAFFIC MONITOR[/bold cyan]\n"
            "[yellow]Powered by Google Maps API[/yellow]",
            border_style="green"
        ))
        
        menu_table = Table(box=None, show_header=False)
        menu_table.add_row("1️⃣", "Check traffic for a route")
        menu_table.add_row("2️⃣", "Check city traffic snapshot")
        menu_table.add_row("3️⃣", "Compare multiple cities")
        menu_table.add_row("4️⃣", "Monitor a route continuously")
        menu_table.add_row("5️⃣", "Use predefined routes")
        menu_table.add_row("6️⃣", "Export current data")
        menu_table.add_row("7️⃣", "List available cities")
        menu_table.add_row("8️⃣", "Exit")
        
        console.print(menu_table)
    
    def show_predefined_routes_menu(self):
        """Show predefined routes."""
        if not self.routes:
            console.print("[yellow]No predefined routes available[/yellow]")
            return
        
        console.print("\n[bold green]🗺️ PREDEFINED ROUTES[/bold green]")
        
        table = Table(box=None)
        table.add_column("ID", style="cyan")
        table.add_column("Route", style="yellow")
        table.add_column("Normal Time", style="green")
        table.add_column("Distance", style="magenta")
        
        for i, (route_id, route_info) in enumerate(self.routes.items(), 1):
            table.add_row(
                str(i),
                route_info['name'],
                route_info['normal_time'],
                f"{route_info.get('distance_km', '?')} km"
            )
        
        console.print(table)
        
        try:
            choice = console.input("\nSelect route (1-5) or 0 to go back: ")
            if choice == '0':
                return
            
            route_idx = int(choice) - 1
            route_keys = list(self.routes.keys())
            
            if 0 <= route_idx < len(route_keys):
                route_id = route_keys[route_idx]
                route_info = self.routes[route_id]
                
                console.print(f"\n[cyan]Selected: {route_info['name']}[/cyan]")
                
                # Get traffic for this route
                result = self.get_route_traffic(
                    f"{route_info['start']}, Sri Lanka",
                    f"{route_info['end']}, Sri Lanka"
                )
                
                self.display_route_traffic(result)
                
                # Ask if user wants to monitor this route
                if console.input("\nMonitor this route continuously? (y/n): ").lower() == 'y':
                    self.monitor_route_continuously(
                        f"{route_info['start']}, Sri Lanka",
                        f"{route_info['end']}, Sri Lanka"
                    )
            else:
                console.print("[red]❌ Invalid selection[/red]")
                
        except ValueError:
            console.print("[red]❌ Please enter a number[/red]")
    
    def run(self):
        """Run the interactive application."""
        console.print("[green]🚀 Starting Sri Lanka Traffic Monitor...[/green]")
        
        # Test API connection
        console.print("[cyan]Testing Google Maps API connection...[/cyan]")
        try:
            # Simple geocode test
            test_result = self.gmaps.geocode("Colombo, Sri Lanka")
            if test_result:
                console.print("[green]✅ API connection successful![/green]")
            else:
                console.print("[yellow]⚠️ API connected but no test results[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ API connection failed: {e}[/red]")
            console.print("[yellow]Please check your API key and internet connection[/yellow]")
            return
        
        while True:
            self.show_main_menu()
            
            choice = console.input("\nSelect an option (1-8): ").strip()
            
            if choice == '1':
                # Check custom route
                console.print("\n[bold cyan]📍 ENTER ROUTE DETAILS[/bold cyan]")
                origin = console.input("Start location: ").strip()
                destination = console.input("Destination: ").strip()
                
                if origin and destination:
                    result = self.get_route_traffic(origin, destination)
                    self.display_route_traffic(result)
                    
                    # Offer to save data
                    if 'success' in result:
                        if console.input("\nExport this data to CSV? (y/n): ").lower() == 'y':
                            filename = console.input("Filename (default: traffic.csv): ") or "traffic.csv"
                            self.export_to_csv(result, filename)
                else:
                    console.print("[red]❌ Please enter both locations[/red]")
            
            elif choice == '2':
                # City traffic snapshot
                console.print(f"\nAvailable cities: {', '.join(self.cities.keys())}")
                city = console.input("Enter city name: ").strip().title()
                
                if city in self.cities:
                    result = self.get_city_traffic_snapshot(city)
                    self.display_city_traffic(result)
                else:
                    console.print(f"[red]❌ City '{city}' not found[/red]")
            
            elif choice == '3':
                # Compare cities
                console.print(f"\nAvailable cities: {', '.join(self.cities.keys())}")
                cities_input = console.input("Enter city names (comma separated): ").strip()
                cities_list = [c.strip().title() for c in cities_input.split(',')]
                
                valid_cities = [c for c in cities_list if c in self.cities]
                
                if len(valid_cities) >= 2:
                    self.compare_cities(valid_cities)
                else:
                    console.print("[red]❌ Need at least 2 valid cities[/red]")
            
            elif choice == '4':
                # Continuous monitoring
                console.print("\n[bold cyan]📡 CONTINUOUS MONITORING[/bold cyan]")
                origin = console.input("Start location: ").strip()
                destination = console.input("Destination: ").strip()
                
                try:
                    interval = int(console.input("Update interval (minutes, default 5): ") or "5")
                    if origin and destination:
                        self.monitor_route_continuously(origin, destination, interval)
                    else:
                        console.print("[red]❌ Please enter both locations[/red]")
                except ValueError:
                    console.print("[red]❌ Please enter a valid number[/red]")
            
            elif choice == '5':
                # Predefined routes
                self.show_predefined_routes_menu()
            
            elif choice == '6':
                # Export data (requires previous route check)
                console.print("[yellow]⚠️ Please check a route first to export data[/yellow]")
            
            elif choice == '7':
                # List cities
                console.print("\n[bold green]🏙️ AVAILABLE SRI LANKAN CITIES[/bold green]")
                
                table = Table(box=None)
                table.add_column("City", style="cyan")
                table.add_column("Coordinates", style="yellow")
                table.add_column("Major Roads", style="green")
                
                for city, info in self.cities.items():
                    roads = info.get('major_roads', [])
                    roads_display = ", ".join(roads[:2]) + ("..." if len(roads) > 2 else "")
                    table.add_row(
                        city,
                        f"{info['latitude']:.4f}, {info['longitude']:.4f}",
                        roads_display
                    )
                
                console.print(table)
            
            elif choice == '8':
                console.print("\n[green]👋 Thank you for using Sri Lanka Traffic Monitor![/green]")
                break
            
            else:
                console.print("[red]❌ Invalid choice. Please select 1-8.[/red]")
            
            console.input("\nPress Enter to continue...")


def quick_test():
    """Quick test function."""
    console = Console()
    console.print("[cyan]🔧 Testing Google Maps API for Sri Lanka...[/cyan]")
    
    # Load API key
    load_dotenv()
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        console.print("[red]❌ API key not found in .env file[/red]")
        return
    
    # Test with Colombo to Kandy route
    console.print("[yellow]Testing route: Colombo to Kandy[/yellow]")
    
    try:
        gmaps = googlemaps.Client(key=api_key)
        
        directions = gmaps.directions(
            origin="Colombo, Sri Lanka",
            destination="Kandy, Sri Lanka",
            mode="driving",
            departure_time=datetime.now(),
            traffic_model="best_guess"
        )
        
        if directions:
            leg = directions[0]['legs'][0]
            normal = leg['duration']['text']
            traffic = leg.get('duration_in_traffic', {}).get('text', normal)
            
            console.print(f"[green]✅ API Working![/green]")
            console.print(f"   Normal time: {normal}")
            console.print(f"   Current time: {traffic}")
        else:
            console.print("[yellow]⚠️ No route found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == "__main__":
    # Uncomment to run quick test
    # quick_test()
    
    # Run full application
    app = SriLankaGoogleTraffic()
    app.run()