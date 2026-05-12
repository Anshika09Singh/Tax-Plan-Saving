from __future__ import annotations

import os
import sys
import subprocess

def main():
    """
    Main entry point for the Tax Saving Assistant.
    Launches the Flask server to host the HTML/CSS/JS frontend.
    """
    print("--- Tax Saving Assistant ---")
    print("Launching the modern web interface...")
    
    # Check if dependencies are installed
    try:
        import flask
        import groq
        import dotenv
    except ImportError:
        print("Missing dependencies. Installing from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # Run the Flask server
    import server
    server.app.run(host="127.0.0.1", port=8503, debug=True)

if __name__ == "__main__":
    main()
