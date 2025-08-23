
"""
Script to start all HCE Analyzer Pro services
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def start_service(command, name, background=True):
    """Start a service with the given command"""
    print(f"🚀 Starting {name}...")
    
    try:
        if background:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            print(f"✅ {name} started with PID {process.pid}")
            return process
        else:
            subprocess.run(command, shell=True, check=True)
            print(f"✅ {name} completed")
            return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def main():
    """Main function to start all services"""
    print("🏥 HCE Analyzer Pro - Starting Services")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)
    
    services = []
    
    # Start Redis (if available)
    print("🔄 Checking Redis...")
    redis_process = start_service("redis-server --daemonize yes", "Redis Cache", background=False)
    
    # Start FastAPI server
    api_process = start_service(
        "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload",
        "FastAPI Server",
        background=True
    )
    if api_process:
        services.append(("FastAPI", api_process))
    
    # Wait a moment for API to start
    time.sleep(3)
    
    # Start Streamlit app
    streamlit_process = start_service(
        "streamlit run main.py --server.port 8501 --server.address 0.0.0.0",
        "Streamlit App",
        background=True
    )
    if streamlit_process:
        services.append(("Streamlit", streamlit_process))
    
    print("\n🎉 All services started successfully!")
    print("=" * 50)
    print("📊 Access Points:")
    print("   • Streamlit App: http://localhost:8501")
    print("   • FastAPI Docs:  http://localhost:8000/docs")
    print("   • API Health:    http://localhost:8000/health")
    print("\n💡 Press Ctrl+C to stop all services")
    
    try:
        # Keep script running and monitor services
        while True:
            time.sleep(10)
            
            # Check if services are still running
            for name, process in services:
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
                    
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        
        # Stop all services
        for name, process in services:
            print(f"🔄 Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
        
        print("👋 All services stopped. Goodbye!")

if __name__ == "__main__":
    main()
