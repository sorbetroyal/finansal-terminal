"""
Launcher for Streamlit App - This script starts the Streamlit server and opens the browser.
"""
import subprocess
import sys
import os
import webbrowser
import time
import socket

def find_free_port():
    """Find a free port to run the server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def main():
    # Get the directory where the exe/script is located
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    app_path = os.path.join(app_dir, "app.py")
    
    # Find a free port
    port = find_free_port()
    url = f"http://localhost:{port}"
    
    print(f"Finansal Terminal başlatılıyor...")
    print(f"Tarayıcınızda açılacak: {url}")
    print("Kapatmak için bu pencereyi kapatın veya Ctrl+C yapın.")
    
    # Start streamlit in the background
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", app_path, 
         "--server.port", str(port),
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=app_dir
    )
    
    # Wait a bit for the server to start
    time.sleep(3)
    
    # Open the browser
    webbrowser.open(url)
    
    try:
        # Keep running until user closes
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        print("\nUygulama kapatıldı.")

if __name__ == "__main__":
    main()
