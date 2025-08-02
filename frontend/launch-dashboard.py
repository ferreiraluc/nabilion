#!/usr/bin/env python3
"""
Nabilion Dashboard Launcher
Generates data and serves the dashboard
"""

import os
import sys
import json
import http.server
import socketserver
import threading
import webbrowser
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import importlib.util
import sys

# Import the data integration module
spec = importlib.util.spec_from_file_location("data_integration", 
    os.path.join(os.path.dirname(__file__), "data-integration.py"))
data_integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_integration)
DashboardDataIntegrator = data_integration.DashboardDataIntegrator

class DashboardServer:
    def __init__(self, port=8000):
        self.port = port
        self.integrator = DashboardDataIntegrator()
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
    def create_request_handler(self):
        base_path = self.base_path
        integrator = self.integrator
        
        class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=base_path, **kwargs)
            
            def do_GET(self):
                if self.path == '/api/dashboard-data':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    try:
                        # Generate fresh data for each request
                        data = integrator.generate_dashboard_data()
                        response = json.dumps(data, default=str, indent=2)
                        self.wfile.write(response.encode('utf-8'))
                    except Exception as e:
                        error_response = {
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                            "message": "Failed to generate dashboard data"
                        }
                        self.wfile.write(json.dumps(error_response).encode('utf-8'))
                        
                elif self.path == '/api/ml-analysis':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    ml_data = integrator.load_ml_analysis()
                    self.wfile.write(json.dumps(ml_data, default=str).encode('utf-8'))
                    
                elif self.path == '/api/performance':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    performance_data = integrator.load_trading_performance()
                    self.wfile.write(json.dumps(performance_data, default=str).encode('utf-8'))
                    
                else:
                    # Serve static files
                    super().do_GET()
                    
            def log_message(self, format, *args):
                # Suppress log messages for cleaner output
                if not self.path.startswith('/api/'):
                    return
                print(f"📡 API Request: {self.path}")
        
        return DashboardRequestHandler
    
    def start_server(self):
        """Start the dashboard server"""
        try:
            handler = self.create_request_handler()
            httpd = socketserver.TCPServer(("", self.port), handler)
            
            print("🚀 Nabilion Trading Dashboard")
            print("=" * 50)
            print(f"📊 Dashboard URL: http://localhost:{self.port}/dashboard.html")
            print(f"🏠 Home Page: http://localhost:{self.port}/index.html")
            print(f"📡 API Endpoint: http://localhost:{self.port}/api/dashboard-data")
            print("=" * 50)
            print("💡 Press Ctrl+C to stop the server")
            print()
            
            # Open browser automatically
            dashboard_url = f"http://localhost:{self.port}/dashboard.html"
            threading.Timer(1.0, lambda: webbrowser.open(dashboard_url)).start()
            
            print("🔥 Server starting...")
            httpd.serve_forever()
            
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down dashboard server...")
            httpd.shutdown()
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"❌ Port {self.port} is already in use.")
                print(f"💡 Try a different port: python launch-dashboard.py --port 8001")
            else:
                print(f"❌ Server error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Launch Nabilion Trading Dashboard')
    parser.add_argument('--port', type=int, default=8000, 
                       help='Port to run the server on (default: 8000)')
    parser.add_argument('--generate-only', action='store_true',
                       help='Only generate data file, don\'t start server')
    parser.add_argument('--no-browser', action='store_true',
                       help='Don\'t open browser automatically')
    
    args = parser.parse_args()
    
    if args.generate_only:
        print("📊 Generating dashboard data...")
        integrator = DashboardDataIntegrator()
        output_file = integrator.save_dashboard_data()
        print(f"✅ Data generated: {output_file}")
        return 0
    
    # Check if required files exist
    base_path = os.path.dirname(os.path.abspath(__file__))
    required_files = ['dashboard.html', 'dashboard.css', 'dashboard.js']
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(base_path, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("💡 Make sure all dashboard files are in the frontend directory")
        return 1
    
    # Start the server
    server = DashboardServer(port=args.port)
    server.start_server()
    
    return 0

if __name__ == "__main__":
    exit(main())