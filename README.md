# Video Montage Creator

A Python script that creates exciting video montages optimized for social media platforms. Perfect for creating engaging content for Instagram Reels, TikTok, and Instagram Square posts.

## Features

- Creates montages from long videos (5-60 minutes)
- Handles both landscape and portrait orientations
- Outputs vertical format for social media
- Includes panning effects and text overlays
- Hardware acceleration support for M2 Max and NVIDIA GPUs
- Smart segment selection based on audio energy
- Multiple text overlay styles with dynamic sizing

## Examples

Here are some example commands to get you started. Note that the input video file must be provided as the last argument, and text arguments should use the `--text=` format:

1. Basic Concert Highlight (30s):
```bash
python3 video_editor_script.py \
     -o concert_highlight.mp4 \
     -f vertical_portrait \
     -d 30 \
     --text="@Suite.E.Studios" \
     --text="#FinalFriday" \
     --text="@StPeteMusic" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

2. Dynamic Panning Sequence (30s):
```bash
python3 video_editor_script.py \
     -o panning_montage.mp4 \
     -f vertical_portrait \
     -d 30 \
     --panning \
     --pan-strategy sequence \
     --pan-speed 1.0 \
     --pan-distance 0.2 \
     --easing ease_in_out \
     --segments some \
     --text-style pulse \
     --text="@Suite.E.Studios" \
     --text="#FinalFriday" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

3. Professional Promo with Intro (30s):
```bash
python3 video_editor_script.py \
     -o promo_video.mp4 \
     -f vertical_portrait \
     -d 30 \
     --intro-video "/Users/matttaylor/Documents/Maylor/test.MP4" \
     --intro-audio "/Users/matttaylor/Documents/Maylor/test.MP4" \
     --text-style promo \
     --text="Professional Studio" \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

4. Multi-Video Instagram Reel (60s):
```bash
python3 video_editor_script.py \
     -o instagram_reel.mp4 \
     -f vertical_portrait \
     -d 60 \
     --segments lots \
     --panning \
     --text-style concert \
     --text="@StPeteMusic" \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

5. Square Post with Zoom Effects (30s):
```bash
python3 video_editor_script.py \
     -o square_post.mp4 \
     -f instagram_square \
     -d 30 \
     --pan-strategy zoom_in \
     --text-style default \
     --text="Behind the Scenes" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

6. Simple Concert Montage (30s):
```bash
python3 video_editor_script.py \
     -o concert_montage.mp4 \
     -f vertical_portrait \
     -d 30 \
     --segments few \
     --text-style concert \
     --text="@Suite.E.Studios" \
     --text="#FinalFriday" \
     --text="@StPeteMusic" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

7. Full Featured Promo (90s):
```bash
python3 video_editor_script.py \
     -o full_promo.mp4 \
     -f vertical_portrait \
     -d 90 \
     --segments lots \
     --panning \
     --intro-video "/Users/matttaylor/Documents/Maylor/test.MP4" \
     --intro-audio "/Users/matttaylor/Documents/Maylor/test.MP4" \
     --text-style promo \
     --text="Professional Studio" \
     --text="Book Your Session" \
     --text="Limited Time Offer" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

## Prerequisites

- Python 3.6 or higher
- FFmpeg installed and accessible in PATH
- For hardware acceleration:
  - Apple Silicon (M1/M2) or Intel Mac with VideoToolbox
  - NVIDIA GPU with NVENC support

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/video-montage-creator.git
cd video-montage-creator
```

2. Install FFmpeg:

macOS (using Homebrew):
```bash
brew install ffmpeg
```

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

Windows:
- Download FFmpeg from https://ffmpeg.org/download.html
- Add FFmpeg to your system PATH

## Usage

Basic usage (note that the input video must be the last argument):
```bash
python3 video_editor_script.py -o output.mp4 -f vertical_portrait "/Users/matttaylor/Documents/Maylor/test.MP4"
```

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `-o, --output` | Output video file (required) |
| `-f, --format` | Output format: `vertical_portrait` or `instagram_square` (required) |
| `-d, --duration` | Output duration in seconds (30, 60, or 90) |
| `--segments` | Number of segments: `few` (3-7), `some` (6-12), or `lots` (10-25) |
| `--panning` | Enable panning effects |
| `--pan-strategy` | Panning direction or strategy |
| `--text` | Text overlay(s) to display (use `--text="text"` format) |
| `--text-style` | Text style: `default`, `pulse`, `concert`, or `promo` |
| `--intro-video` | Video to play at the start |
| `--intro-audio` | Audio file to play at the start |
| `input_video` | Input video file (required, must be last argument) |

### Supported Formats

| Format | Dimensions | Description |
|--------|------------|-------------|
| `vertical_portrait` | 1080x1920 | Vertical video for Reels/TikTok |
| `instagram_square` | 1080x1080 | Square format for Instagram posts |

### Video Orientation

- For Reels/TikTok (9:16), input videos should be in landscape orientation (16:9). The script will handle conversion to vertical format.
- For Instagram Square (1:1), both landscape and portrait videos are acceptable. The script will automatically crop and center the content.

### Best Practices

1. Use high-quality landscape videos for Reels/TikTok
2. Ensure input videos are at least 1080p resolution
3. Avoid using still images directly - convert them to video first
4. Use videos with good resolution and movement for panning effects
5. For panning effects to work properly:
   - Use videos with actual movement (not still images)
   - Ensure the video has enough resolution for the panning effect
   - Videos should be at least 1080p for best results
   - The video should have some content in the areas that will be panned to

## Hardware Acceleration

The script automatically detects and uses hardware acceleration when available:

- Apple Silicon (M1/M2): Uses VideoToolbox for optimal performance
- NVIDIA GPU: Uses NVENC for hardware encoding
- CPU: Falls back to libx264 with multi-threading

## License

MIT License - feel free to use this in your projects!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
