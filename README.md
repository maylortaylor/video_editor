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
- **Robust logo overlay feature that works with or without text overlays**
- **Debug output for logo filter construction**
- **Customizable thumbnail support with flexible scaling options**

## Recent Changes

- **Logo overlay is now robust and always appears as the last step in the filter graph.**
- **Text overlays (if present) are applied before the logo overlay.**
- **No fade in/out for logo by default (can be added if needed).**
- **Filter graph construction is now compatible with FFmpeg's requirements.**
- **Script prints debug output for the logo filter.**
- **Added thumbnail support with customizable duration and scaling options.**

## Examples

Here are some example commands to get you started. Note that the input video file must be provided as the last argument, and text arguments should use the `--text=` format:

1. Basic Pro Highlight (30s):
```bash
python3 video_editor_script.py \
     -o pro_highlight.mp4 \
     -f vertical_portrait \
     -d 30 \
     --text="@Suite.E.Studios" \
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
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

3. Professional Promo with Intro (30s):
```bash
python3 video_editor_script.py \
     -o promo_video.mp4 \
     -f vertical_portrait \
     -d 30 \
     --intro-video "/Users/matttaylor/Documents/Maylor/videos/FunnyVoices.mp4" \
     --intro-video-length 5 \
     --intro-audio "/Users/matttaylor/Documents/Maylor/test.MP4" \
     --text-style promo \
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
     --text-style pro \
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
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

6. Simple Pro Montage (30s):
```bash
python3 video_editor_script.py \
     -o pro_montage.mp4 \
     -f vertical_portrait \
     -d 30 \
     --segments few \
     --text-style pro \
     --text="@Suite.E.Studios" \
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
     --intro-video "/Users/matttaylor/Documents/Maylor/videos/FunnyVoices.mp4" \
     --intro-video-length 10 \
     --intro-audio "/Users/matttaylor/Documents/Maylor/test.MP4" \
     --text-style promo \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

8. Impact Style Highlight (30s):
```bash
python3 video_editor_script.py \
     -o impact_highlight.mp4 \
     -f vertical_portrait \
     -d 30 \
     --text-style impact \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

9. Logo Overlay Example (30s):
```bash
python3 video_editor_script.py \
     -o logo_highlight.mp4 \
     -f vertical_portrait \
     -d 30 \
     --logo "/Users/matttaylor/Documents/Maylor/SuiteE_vector_WHITE.png" \
     --text-style pro \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

10. Thumbnail with Custom Duration (30s):
```bash
python3 video_editor_script.py \
     -o thumbnail_montage.mp4 \
     -f vertical_portrait \
     -d 30 \
     --thumbnail "/Users/matttaylor/Documents/Maylor/matt.png" \
     --thumbnail-duration 1.0 \
     --thumbnail-scale fill \
     --text-style pro \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

11. Thumbnail with Custom Duration (30s):
```bash
python3 video_editor_script.py \
     -o thumbnail_montage.mp4 \
     -f vertical_portrait \
     -d 30 \
     --thumbnail "/Users/matttaylor/Documents/Maylor/matt.png" \
     --thumbnail-duration 3.0 \
     --thumbnail-scale fit \
     --text-style pro \
     --text="@Suite.E.Studios" \
     "/Users/matttaylor/Documents/Maylor/test.MP4"
```

## Logo Overlay Features

- Supports transparent PNG images
- Automatically scales logo to 30% of video width while maintaining aspect ratio
- Positions logo near the top of the video (20% from top)
- **Logo overlay is always applied after any text overlays**
- **No fade in/out by default (can be added if needed)**
- Works alongside text overlays
- Centered horizontally
- Prints debug output for the logo filter string

## Troubleshooting Logo Overlay

If your logo is not appearing on the video:

1. **Check the PNG file:**
   - Ensure it is a valid PNG with transparency (alpha channel).
   - Make sure the file path is correct and accessible.
2. **Check the filter graph order:**
   - The script now applies text overlays first, then logo overlay as the last step. This is required for FFmpeg compatibility.
3. **Check debug output:**
   - The script prints the exact filter string used for the logo overlay. Review this output for errors or typos.
4. **No fade in/out:**
   - The current version does not apply fade in/out to the logo overlay. If you need this, request it and it can be added robustly.
5. **Still not working?**
   - Try running FFmpeg manually with the printed filter string to isolate issues.
   - Ensure your FFmpeg version is up to date (7.x or later recommended).

## Advanced: Filter Graph Order

For advanced users, the correct filter graph order for overlays is:

- `[0:v]drawtext=...[tmp1];movie=logo.png,scale=...:h=...[logo];[tmp1][logo]overlay=...:y=...[vout]`
- If no text: `[0:v]movie=logo.png,scale=...:h=...[logo];[0:v][logo]overlay=...:y=...[vout]`

This ensures the logo is always the topmost overlay.

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
| `--text` | Text overlay to display (single text string) |
| `--text-style` | Text style: `default`, `pulse`, `pro`, `promo`, or `impact` |
| `--logo` | Path to a transparent PNG logo to overlay on the video |
| `--thumbnail` | Path to a thumbnail image to display at the start of the video |
| `--thumbnail-duration` | Duration of the thumbnail in seconds (default: 1.0) |
| `--thumbnail-scale` | How to scale the thumbnail: 'fit' (with padding) or 'fill' (with cropping) |
| `--intro-video` | Video to play at the start |
| `--intro-video-length` | Maximum length of intro video in seconds (5-30 seconds, default: 20) |
| `--intro-audio` | Audio file to play at the start |
| `--intro-audio-duration` | Duration of intro audio in seconds (default: 5.0) |
| `--intro-audio-volume` | Volume multiplier for intro audio (default: 2.0) |
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

## Testing

The project includes a comprehensive test suite to ensure reliability and prevent regressions. The tests cover all major functionality including panning, zooming, aspect ratio handling, and error cases.

### Running Tests

To run the test suite:

```bash
python3 -m unittest test_video_editor.py -v
```

For more detailed output:

```bash
python3 -m unittest test_video_editor.py -v -f
```

### Test Coverage

The test suite includes:

1. **Basic Video Operations**
   - Video duration detection
   - Video dimension detection
   - Scaling filter generation

2. **Panning and Zooming**
   - All panning directions (LEFT_TO_RIGHT, RIGHT_TO_LEFT)
   - Zoom effects (ZOOM_IN, ZOOM_OUT)
   - Segment duration verification with panning

3. **Filter Validation**
   - Valid and invalid filter string testing
   - FFmpeg filter parsing verification

4. **Montage Creation**
   - Different segment counts (few, some, lots)
   - Output duration accuracy
   - Panning strategy verification

5. **Aspect Ratio Handling**
   - All supported aspect ratios
   - Output dimension verification

6. **Error Handling**
   - Invalid video paths
   - Invalid aspect ratios
   - Invalid filter strings

7. **Duration Accuracy**
   - Segment duration verification
   - Montage duration verification

### Test Environment

The test suite:
- Creates temporary test videos using FFmpeg's testsrc
- Uses a temporary directory for all test outputs
- Automatically cleans up all test files
- Provides detailed error reporting
- Uses subTests for better organization

### Adding New Tests

When adding new features, please add corresponding tests to ensure:
1. The feature works as expected
2. Edge cases are handled properly
3. Error conditions are caught
4. Performance is maintained

## Thumbnail Features

The script now supports adding a thumbnail image at the start of your video with the following options:

### Scaling Modes

1. **Fit Mode** (default)
   - Scales the image to fit within the target dimensions
   - Maintains aspect ratio
   - Adds padding if needed
   - No cropping
   - Best for: Images you want to see in full

2. **Fill Mode**
   - Scales the image to fill the target dimensions
   - Maintains aspect ratio
   - Crops if needed
   - No padding
   - Best for: Images where you want to fill the frame completely

### Best Practices for Thumbnails

1. **Image Quality**
   - Use high-resolution images (at least 1080p)
   - For vertical videos (9:16), use images with a similar aspect ratio
   - For square videos (1:1), square images work best
   - Supported formats: JPG, PNG, WebP
   - PNG recommended for images with transparency
   - Use JPG for photographs
   - Keep file sizes reasonable (under 5MB recommended)

2. **Scaling Mode Selection**
   - Use `fit` mode when:
     - The image is important to see in full
     - The image has a different aspect ratio than the output
     - You want to avoid any cropping
   - Use `fill` mode when:
     - The image needs to fill the entire frame
     - The image has important content in the center
     - You want a more immersive look

3. **Duration**
   - Default duration is 1 second
   - Consider your audience's attention span
   - Longer durations (2-3 seconds) work well for:
     - Complex images that need time to be understood
     - Text-heavy thumbnails
     - Brand logos or important visual elements

4. **File Paths**
   - Use absolute paths for best reliability
   - For macOS/Linux: `/Users/username/path/to/image.png`
   - For Windows: `C:\Users\username\path\to\image.png`
   - Avoid spaces in file paths (use underscores instead)
   - Make sure the path is accessible to the script
