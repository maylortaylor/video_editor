#!/usr/bin/env python3
"""
Video Montage Creator - Launcher Script
This script launches the GUI application for the Video Montage Creator.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

# Add the directory containing this script to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check for required dependencies
try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("Error: Tkinter is not available. This is required for the GUI.")
    print("On Linux, you can install it with: sudo apt-get install python3-tk")
    print("On macOS with Homebrew: brew install python-tk")
    sys.exit(1)

# Check for FFmpeg
def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

# Import the main application
try:
    from video_montage_gui import VideoMontageCreatorGUI
except ImportError as e:
    messagebox.showerror("Import Error", f"Could not import VideoMontageCreatorGUI: {str(e)}")
    sys.exit(1)

def main():
    """Main function to launch the application."""
    # Check for FFmpeg
    if not check_ffmpeg():
        messagebox.showwarning(
            "FFmpeg Not Found", 
            "FFmpeg could not be found in your system PATH. The application may not work correctly.\n\n"
            "Please install FFmpeg before using this application:\n"
            "- Windows: Download from https://ffmpeg.org/download.html\n"
            "- macOS: Use 'brew install ffmpeg'\n"
            "- Linux: Use 'sudo apt install ffmpeg' or equivalent"
        )
    
    # Check for the video_editor_script.py
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_editor_script.py")
    if not os.path.exists(script_path):
        messagebox.showerror(
            "Script Not Found", 
            f"The video editor script was not found at:\n{script_path}\n\n"
            "Please make sure the video_editor_script.py file is in the same directory as this launcher."
        )
        sys.exit(1)
    
    # Create and run the application
    root = tk.Tk()
    root.title("Video Montage Creator")
    
    # Set application icon if available
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except:
            pass  # Skip if icon file isn't valid
    
    # Create the application instance
    app = VideoMontageCreatorGUI(root)
    
    # Configure style
    style = ttk.Style()
    style.theme_use('clam')  # Use a modern theme if available
    
    # Run the application
    root.mainloop()

if __name__ == "__main__":
    main()