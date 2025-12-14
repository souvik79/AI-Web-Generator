#!/usr/bin/env python3
import subprocess
import sys
import os
import platform
import webbrowser
import time

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    return True

def install_dependencies():
    """Install required Python packages"""
    print("Installing required Python packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def check_ollama():
    """Check if Ollama is installed and running"""
    system = platform.system()
    
    # Check if Ollama is installed
    try:
        if system == "Windows":
            result = subprocess.run(["where", "ollama"], capture_output=True, text=True)
        else:  # macOS or Linux
            result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ Ollama is not installed. Please install it from https://ollama.ai/")
            webbrowser.open("https://ollama.ai/")
            return False
        
        print("✅ Ollama is installed")
        
        # Check if Ollama is running
        try:
            response = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/version"],
                capture_output=True,
                text=True
            )
            
            if "version" in response.stdout:
                print("✅ Ollama is running")
            else:
                print("❌ Ollama is installed but not running")
                print("Please start Ollama and try again")
                return False
                
        except subprocess.CalledProcessError:
            print("❌ Ollama is installed but not running")
            print("Please start Ollama and try again")
            return False
            
        # Check if llama2 model is available
        try:
            response = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True
            )
            
            if "llama2" in response.stdout:
                print("✅ llama2 model is available")
            else:
                print("❓ llama2 model might not be available")
                print("Attempting to pull llama2 model...")
                subprocess.run(["ollama", "pull", "llama2"])
                
        except subprocess.CalledProcessError:
            print("❓ Could not check if llama2 model is available")
            print("Please run 'ollama pull llama2' manually")
            
        return True
            
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def main():
    """Main setup function"""
    print("Setting up Web Page Generator...")
    
    if not check_python_version():
        return
    
    if not install_dependencies():
        return
    
    if not check_ollama():
        return
    
    print("\n✅ Setup completed successfully!")
    print("\nTo start the application, run:")
    print("python app.py")
    
    start_app = input("\nWould you like to start the application now? (y/n): ")
    if start_app.lower() == 'y':
        print("\nStarting the application...")
        subprocess.Popen([sys.executable, "app.py"])
        print("Waiting for the server to start...")
        time.sleep(2)  # Give the server some time to start
        webbrowser.open("http://127.0.0.1:5000")
        print("\nOpening http://127.0.0.1:5000 in your browser")
        print("Press Ctrl+C in the terminal to stop the server when you're done")

if __name__ == "__main__":
    main()
