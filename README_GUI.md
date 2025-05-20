# Video Montage Creator GUI

A graphical user interface for the Video Montage Creator script that allows you to easily create exciting video montages optimized for social media platforms.

## Features

- User-friendly interface to access all script features
- File browser for selecting input videos, output location, logos, and intro media
- Organized tabs for basic and advanced settings
- Real-time command preview
- Progress tracking and output log
- Error handling and validation

## Screenshots

![Video Montage Creator GUI Main Screen](screenshot_main.png)

## Requirements

- Python 3.6 or higher
- Tkinter (included with most Python installations)
- FFmpeg installed and accessible in PATH

## Installation

1. Make sure you have Python 3.6+ installed on your system
2. Install FFmpeg:
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt update && sudo apt install ffmpeg`
3. Download or clone this repository
4. Ensure the `video_editor_script.py` file is in the same directory

## Usage

1. Run the application:
   ```bash
   python app_launcher.py
   ```
   
2. Fill in the form with your desired settings:
   - **Main Settings**: Input/output files, format, duration, text overlays
   - **Advanced Settings**: Panning effects, intro videos/audio

3. Click "Preview Command" to see the command that will be executed

4. Click "Generate Video Montage" to create your video

5. View progress and output in the Output tab

## GUI Overview

### Main Settings Tab

- **Files Section**: Input video selection and output file location
- **Basic Settings**:
  - Output Format: vertical_portrait (9:16) or instagram_square (1:1)
  - Duration: Length of the output video in seconds
  - Segments: Number of clips to include (few, some, lots)
  - Text Overlay: Text to display on the video
  - Text Style: Visual style for the text overlay
  - Logo Overlay: Option to add a transparent PNG logo

### Advanced Settings Tab

- **Panning Effects**:
  - Enable/disable panning
  - Pan Strategy: sequence, random, zoom_in, zoom_out
  - Pan Speed: How fast the panning effect moves
  - Pan Distance: How far the panning effect travels
  - Easing: Motion style (ease_in_out, linear, etc.)
  
- **Intro Settings**:
  - Intro Video: Optional video to play at the start
  - Intro Video Length: Maximum duration for the intro
  - Intro Audio: Optional audio to play at the start

### Output Tab

- **Command Preview**: Shows the exact command that will be executed
- **Output Log**: Displays real-time progress and messages from the script

## Troubleshooting

If you encounter issues:

1. Check that FFmpeg is properly installed and in your system PATH
2. Ensure the video_editor_script.py file is in the same directory as app_launcher.py
3. Verify that your input files are valid video/audio formats
4. Check the Output tab for specific error messages

## License

This software is distributed under the MIT License.

## Acknowledgments

This GUI application is a frontend for the Video Montage Creator script.