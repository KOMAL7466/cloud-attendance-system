#!/usr/bin/env python3
"""
Cloud Attendance System - Local Server Runner
This file is used to run the application locally or on Render.com
"""

import os
import sys
import time
import socket
from datetime import datetime

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from local_app import app, create_demo_data

def check_port_available(port):
    """Check if a port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('0.0.0.0', port))
        sock.close()
        return result != 0
    except:
        return True

def find_available_port(start_port=5000, max_port=5010):
    """Find an available port"""
    for port in range(start_port, max_port + 1):
        if check_port_available(port):
            return port
    return start_port

def print_banner(port, admin_email, sender_email):
    """Print beautiful startup banner"""
    banner = f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     🚀  CLOUD ATTENDANCE SYSTEM - LOCAL SERVER              ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📧 Admin Email:     {admin_email:<45} ║
║  📧 Sender Email:    {sender_email:<45} ║
║  🌐 Server URL:      http://localhost:{port:<5}                 ║
║  📅 Started at:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<45} ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  🔑 Test Credentials:                                         ║
║     Admin:    username='admin', password='admin123'           ║
║                                                               ║
║  📚 Demo Students:                                            ║
║     24021541017  - Mohit Dahiya  (Science, 1st Year)         ║
║     24021541018  - Priya Patel   (Science, 1st Year)         ║
║     24021541019  - Amit Kumar    (Arts, 2nd Year)            ║
║     24021541020  - Sneha Reddy   (Commerce, Final Year)      ║
║                                                               ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📡 API Endpoints:                                            ║
║     POST   /auth                    - Login/Register         ║
║     POST   /mark-attendance         - Mark Attendance        ║
║     GET    /get-attendance          - Get Records            ║
║     GET    /admin-dashboard         - Admin Dashboard        ║
║     POST   /add-student             - Add Student            ║
║     POST   /generate-report         - Generate Report        ║
║     POST   /generate-monthly-report - Monthly Report         ║
║     POST   /send-report-to-all      - Email All Students     ║
║     GET    /health                  - Health Check           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def run_server():
    """Main function to run the server"""
    try:
        # Get port from environment or use default
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        # Check if port is available
        if not check_port_available(port):
            print(f"⚠️  Port {port} is already in use!")
            new_port = find_available_port(port + 1)
            print(f"🔄 Using available port: {new_port}")
            port = new_port
        
        # Get email config
        admin_email = os.environ.get('ADMIN_EMAIL', 'dahiyamohit764@gmail.com')
        sender_email = os.environ.get('SENDER_EMAIL', 'dahiyamohit764@gmail.com')
        
        # Print banner
        print_banner(port, admin_email, sender_email)
        
        # Create demo data
        print("📋 Creating demo data...")
        create_demo_data()
        print("✅ Demo data created successfully!\n")
        
        # Start the server
        print(f"🔥 Starting server on {host}:{port}")
        print(f"   Debug mode: {debug}")
        print(f"   Press CTRL+C to stop the server\n")
        print("=" * 60)
        
        # Run Flask app
        app.run(
            debug=debug,
            host=host,
            port=port,
            threaded=True,
            use_reloader=debug
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_server()