#!/usr/bin/env python3
import os
import sys
import random
import argparse
import subprocess
import tempfile
import math
from pathlib import Path
from datetime import datetime
from enum import Enum

# Social media aspect ratios
ASPECT_RATIOS = {
    "vertical_portrait": {
        "width": 1080,
        "height": 1920,
        "description": "Vertical Portrait (9:16)",
    },
    "instagram_square": {
        "width": 1080,
        "height": 1080,
        "description": "Instagram Square (1:1)",
    },
}


# Panning types
class PanDirection(Enum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


# Easing functions for smooth panning
class EasingType(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


# Text motion types
class TextMotionType(Enum):
    NONE = "none"
    DVD_BOUNCE = "dvd_bounce"


def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print(
            "Error: FFmpeg is not installed or not in PATH. Please install FFmpeg to use this script."
        )
        return False


def get_video_duration(video_path):
    """Get the duration of a video in seconds using FFmpeg."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    return float(result.stdout.strip())


def get_video_dimensions(video_path):
    """Get the width and height of a video using FFmpeg."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=s=x:p=0",
        video_path,
    ]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    dimensions = result.stdout.strip().split("x")
    return int(dimensions[0]), int(dimensions[1])


def categorize_video(video_path):
    """Categorize a video as short, medium, or long based on its duration."""
    duration = get_video_duration(video_path)

    if 30 <= duration <= 60:  # 30 seconds to 1 minute
        return "short"
    elif 60 < duration <= 300:  # 1-5 minutes
        return "medium"
    elif 300 < duration <= 1800:  # 5-30 minutes
        return "medium_long"
    elif 1800 < duration <= 7200:  # 30 minutes to 2 hours
        return "long"
    else:
        return "invalid"


def determine_scaling_filter(video_path, target_aspect):
    """Determine how to scale and pad video to match target aspect ratio."""
    # Get target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]

    # Get input video dimensions
    input_width, input_height = get_video_dimensions(video_path)

    # Calculate scaling factors
    width_scale = target_width / input_width
    height_scale = target_height / input_height

    # Use the larger scale to ensure we fill the frame
    scale_factor = max(width_scale, height_scale)

    # Calculate new dimensions after scaling
    new_width = int(input_width * scale_factor)
    new_height = int(input_height * scale_factor)

    # Calculate padding
    pad_x = max(0, (new_width - target_width) // 2)
    pad_y = max(0, (new_height - target_height) // 2)

    # Create filter string that scales first, then crops to target size
    filter_string = (
        f"scale={new_width}:{new_height}:force_original_aspect_ratio=1,"
        f"crop={target_width}:{target_height}:{pad_x}:{pad_y}"
    )

    return filter_string


def generate_easing_expression(easing_type, t_str):
    """Generate easing expressions for smooth panning effects"""
    if easing_type == EasingType.LINEAR:
        return t_str
    elif easing_type == EasingType.EASE_IN:
        return f"pow({t_str},2)"
    elif easing_type == EasingType.EASE_OUT:
        return f"(1-pow(1-{t_str},2))"
    elif easing_type == EasingType.EASE_IN_OUT:
        return f"((1-cos(PI*{t_str}))/2)"
    else:
        return t_str


def generate_ultra_simple_pan_filter(
    direction, duration, pan_speed=1.0, pan_distance=0.2, easing_type=EasingType.LINEAR
):
    """Generate a simple filter string for basic scaling and padding."""
    return "scale=1080:1920:force_original_aspect_ratio=1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"


def validate_inputs(video_paths):
    """Validate that the input videos meet the requirements."""
    categorized_videos = {}

    for path in video_paths:
        if not os.path.exists(path):
            print(f"Error: Video file not found: {path}")
            return None

        category = categorize_video(path)

        # Accept all non-invalid categories
        if category != "invalid":
            if category not in categorized_videos:
                categorized_videos[category] = []
            categorized_videos[category].append(path)
        else:
            # Only reject truly invalid videos (outside all ranges)
            if "invalid" not in categorized_videos:
                categorized_videos["invalid"] = []
            categorized_videos["invalid"].append(path)

    # Check if we have enough short videos if that's what was provided
    if (
        "short" in categorized_videos
        and len(categorized_videos["short"]) < 3
        and len(categorized_videos) == 1
    ):
        print(
            f"Error: At least 3 short videos are required. Only {len(categorized_videos['short'])} provided."
        )
        return None

    # If we have invalid videos, alert the user
    if "invalid" in categorized_videos:
        print(f"Error: Some videos don't match the required durations:")
        for path in categorized_videos["invalid"]:
            duration = get_video_duration(path)
            print(f"  - {path}: {duration:.2f} seconds")
            print(f"  Acceptable ranges: 30-3600 seconds (excluding 0-30 seconds)")
        return None

    return categorized_videos


def analyze_audio_levels(video_path, segment_duration=3):
    """
    Analyze audio levels in the video to find high-energy segments.
    Returns a list of timestamps where the audio energy is highest.
    """
    # Create a temporary file for audio data
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        audio_data_file = temp_file.name

    try:
        # Extract audio levels using FFmpeg's volumedetect filter
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-af",
            f"astats=metadata=1:reset={segment_duration},ametadata=print:key=lavfi.astats.Overall.RMS_level",
            "-f",
            "null",
            "-",
        ]

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )

        # Parse the output to find timestamps with high audio levels
        audio_levels = []
        current_time = 0

        for line in result.stderr.split("\n"):
            if "RMS_level" in line:
                try:
                    level = float(line.split("=")[1])
                    audio_levels.append((current_time, level))
                    current_time += segment_duration
                except (ValueError, IndexError):
                    continue

        # Sort segments by audio level (highest to lowest)
        audio_levels.sort(key=lambda x: x[1], reverse=True)

        # Return timestamps of the highest energy segments
        return [
            timestamp for timestamp, _ in audio_levels[:20]
        ]  # Return top 20 segments

    except Exception as e:
        print(f"Warning: Audio analysis failed: {e}")
        return []


def extract_interesting_segments(video_path, num_segments=10, target_duration=3):
    """
    Extract timestamps of potentially interesting segments from a video.

    Args:
        video_path: Path to the video file
        num_segments: Number of segments to extract
        target_duration: Target duration for each segment in seconds
    """
    duration = get_video_duration(video_path)

    # Get high-energy segments based on audio analysis
    high_energy_timestamps = analyze_audio_levels(video_path)

    # Create a list of all possible segment start times
    all_possible_segments = []

    # Add high-energy segments first
    for timestamp in high_energy_timestamps:
        if timestamp + target_duration <= duration:
            all_possible_segments.append(timestamp)

    # If we don't have enough segments, add evenly spaced ones
    if len(all_possible_segments) < num_segments * 2:  # Get more than needed
        # Calculate interval for evenly spaced segments
        interval = (duration - target_duration) / (num_segments * 2)

        # Add evenly spaced segments
        for i in range(num_segments * 2):
            start_time = i * interval
            if start_time + target_duration <= duration:
                all_possible_segments.append(start_time)

    # Remove duplicates and sort
    all_possible_segments = sorted(list(set(all_possible_segments)))

    # Select segments ensuring minimum distance between them
    selected_segments = []
    min_gap = target_duration * 0.5  # Minimum gap between segments

    # First pass: Try to get segments with good spacing
    for start_time in all_possible_segments:
        # Check if this segment is too close to any already selected segment
        if not any(abs(start_time - s[0]) < min_gap for s in selected_segments):
            selected_segments.append((start_time, target_duration))
            if len(selected_segments) >= num_segments:
                break

    # If we still don't have enough segments, add more with less strict spacing
    if len(selected_segments) < num_segments:
        for start_time in all_possible_segments:
            if not any(s[0] == start_time for s in selected_segments):
                selected_segments.append((start_time, target_duration))
                if len(selected_segments) >= num_segments:
                    break

    # Shuffle the selected segments
    random.shuffle(selected_segments)

    # Print debug information
    print(f"Total possible segments: {len(all_possible_segments)}")
    print(f"Selected segments: {len(selected_segments)}")
    for i, (start, dur) in enumerate(selected_segments):
        print(f"Segment {i+1}: {start:.2f}s - {start+dur:.2f}s")

    return selected_segments[:num_segments]


def get_segment_range(segment_count):
    """Get min and max segments based on segment count setting."""
    if segment_count == "few":
        return 4  # Fixed number for better duration control
    elif segment_count == "some":
        return 6  # Fixed number for better duration control
    elif segment_count == "lots":
        return 8  # Fixed number for better duration control
    else:
        # Default to "some" if invalid value provided
        return 6


def test_filter_string(filter_string):
    """
    Test if a filter string is valid before using it in FFmpeg.
    Returns True if valid, False if invalid.
    """
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_in:
        test_input = temp_in.name

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_out:
        test_output = temp_out.name

    # Create a slightly longer test video (2 seconds)
    cmd1 = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=10x10:d=2",
        test_input,
    ]
    try:
        subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        print("Failed to create test video")
        return False

    cmd2 = [
        "ffmpeg",
        "-y",
        "-i",
        test_input,
        "-vf",
        filter_string,
        "-t",
        "0.1",
        "-f",
        "null",
        "-",
    ]

    print("Testing with command:", " ".join(cmd2))
    try:
        result = subprocess.run(
            cmd2,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.returncode != 0:
            print("Filter test failed with error:")
            print(result.stderr)
            return False
        return True
    except Exception as e:
        print(f"Exception during filter test: {e}")
        return False
    finally:
        try:
            os.unlink(test_input)
            os.unlink(test_output)
        except:
            pass


def generate_and_test_filters():
    test_results = []
    base_scale_pad = "scale=1080:1920:force_original_aspect_ratio=1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    for direction in list(PanDirection):
        filter_string = base_scale_pad
        success = test_filter_string(filter_string)
        test_results.append(
            {
                "direction": direction.value,
                "filter_string": filter_string,
                "success": success,
            }
        )
    print("\nFILTER TEST RESULTS:")
    print("====================")
    for result in test_results:
        status = "✓ WORKS" if result["success"] else "✗ FAILS"
        print(f"\n{result['direction']}: {status}")
        print(f"Filter: {result['filter_string']}")
    return [r for r in test_results if r["success"]]


def create_reliable_filter(
    video_path, target_aspect, direction, duration, easing_type=EasingType.EASE_IN_OUT
):
    """
    Create a reliable filter string that works with all FFmpeg versions
    using the simplest possible expressions.
    """
    # Get target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]

    # Get input video dimensions
    input_width, input_height = get_video_dimensions(video_path)

    # For short segments or if panning is disabled, use simple scaling and cropping
    if duration < 2.0:
        # Calculate scaling factors
        width_scale = target_width / input_width
        height_scale = target_height / input_height
        scale_factor = max(width_scale, height_scale)

        # Calculate new dimensions after scaling
        new_width = int(input_width * scale_factor)
        new_height = int(input_height * scale_factor)

        # Calculate crop offsets
        crop_x = max(0, (new_width - target_width) // 2)
        crop_y = max(0, (new_height - target_height) // 2)

        return (
            f"scale={new_width}:{new_height}:force_original_aspect_ratio=1,"
            f"crop={target_width}:{target_height}:{crop_x}:{crop_y}"
        )

    # Base components for filter strings
    fps_str = "fps=30"
    duration_frames = int(duration * 30)
    duration_str = f"d={duration_frames}"
    frames = duration_frames

    # Calculate scaling factors for panning
    width_scale = target_width / input_width
    height_scale = target_height / input_height
    scale_factor = max(width_scale, height_scale)

    # Calculate new dimensions after scaling
    new_width = int(input_width * scale_factor)
    new_height = int(input_height * scale_factor)

    # Calculate crop offsets
    crop_x = max(0, (new_width - target_width) // 2)
    crop_y = max(0, (new_height - target_height) // 2)

    # Base filter for scaling and cropping
    base_filter = (
        f"scale={new_width}:{new_height}:force_original_aspect_ratio=1,"
        f"crop={target_width}:{target_height}:{crop_x}:{crop_y}"
    )

    # Generate easing expression
    t_str = f"n/{frames}"
    easing_expr = generate_easing_expression(easing_type, t_str)

    # Add panning effect with easing expressions
    if direction == PanDirection.LEFT_TO_RIGHT:
        filter_string = f"{base_filter},select=1,zoompan=x='iw*0.1*({easing_expr})':y=0:z=1:{fps_str}:{duration_str}"
    elif direction == PanDirection.RIGHT_TO_LEFT:
        filter_string = f"{base_filter},select=1,zoompan=x='iw*0.1*(1-{easing_expr})':y=0:z=1:{fps_str}:{duration_str}"
    elif direction == PanDirection.ZOOM_IN:
        filter_string = f"{base_filter},select=1,zoompan=x='iw/4':y='ih/4':z='1+0.1*({easing_expr})':{fps_str}:{duration_str}"
    elif direction == PanDirection.ZOOM_OUT:
        filter_string = f"{base_filter},select=1,zoompan=x=0:y=0:z='1+0.1-0.1*({easing_expr})':{fps_str}:{duration_str}"
    else:
        filter_string = base_filter

    return filter_string


def wrap_text(text, max_chars_per_line):
    """
    Wrap text into multiple lines, trying to break at spaces when possible.
    """
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        # Check if adding this word would exceed max length
        if (
            current_length + len(word) + (1 if current_length > 0 else 0)
            <= max_chars_per_line
        ):
            current_line.append(word)
            current_length += len(word) + (1 if current_length > 0 else 0)
        else:
            # If current line is empty but word is too long, force split the word
            if not current_line and len(word) > max_chars_per_line:
                while word:
                    lines.append(word[:max_chars_per_line])
                    word = word[max_chars_per_line:]
            else:
                # Add current line and start new one
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

    # Add the last line if there is one
    if current_line:
        lines.append(" ".join(current_line))

    return lines


def calculate_text_layout(
    text, target_aspect, base_size, margin_percent=20, min_font_size=36
):
    """
    Calculate appropriate font size and line wrapping for text.
    Returns tuple of (font_size, wrapped_text, line_spacing).
    """
    # Get target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]

    # Calculate available width (accounting for margins)
    margin_width = int(target_width * (margin_percent / 100))
    available_width = target_width - (2 * margin_width)

    # Estimate max characters per line at base font size
    # FFmpeg uses approximately 0.6 * fontsize for each character width
    chars_per_line = int(available_width / (base_size * 0.6))

    # Try different font sizes until we find one that works
    current_size = base_size
    while current_size >= min_font_size:
        chars_this_size = int(available_width / (current_size * 0.6))
        wrapped_lines = wrap_text(text, chars_this_size)

        # If we have 3 or fewer lines, this size works
        if len(wrapped_lines) <= 3:
            line_spacing = current_size * 1.2  # 120% of font size for line spacing
            return current_size, wrapped_lines, line_spacing

        # Reduce font size and try again
        current_size -= 4

    # If we get here, use minimum size and force wrap
    wrapped_lines = wrap_text(text, int(available_width / (min_font_size * 0.6)))
    line_spacing = min_font_size * 1.2
    return min_font_size, wrapped_lines[:3], line_spacing  # Limit to 3 lines maximum


def calculate_dynamic_text_size(text, target_aspect, style="default"):
    """
    Calculate optimal font size based on text length and style.
    Returns a tuple of (base_size, min_size, max_size).
    """
    # Get target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]

    # Style-specific base sizes
    if style == "pulse":
        base_size = 60
        min_size = 40
        max_size = 100
    elif style == "concert":
        base_size = 80
        min_size = 40
        max_size = 100
    elif style == "promo":
        base_size = 60
        min_size = 40
        max_size = 80
    else:  # default
        base_size = 60
        min_size = 40
        max_size = 100

    # Calculate text length factor (inverse relationship)
    text_length = len(text)
    if text_length <= 5:
        size_factor = 1.5  # 150% for very short text
    elif text_length <= 10:
        size_factor = 1.2  # 120% for short text
    elif text_length <= 20:
        size_factor = 1.0  # 100% for medium text
    elif text_length <= 30:
        size_factor = 0.8  # 80% for longer text
    else:
        size_factor = 0.6  # 60% for very long text

    # Calculate final size
    final_size = int(base_size * size_factor)

    # Ensure size is within bounds
    final_size = max(min_size, min(max_size, final_size))

    return final_size, min_size, max_size


def create_text_overlay_filter(
    video_duration,
    text=None,
    display_duration=5,
    style="default",
    target_aspect="vertical_portrait",
    motion_type="none",
):
    """
    Create FFmpeg filter string for a single text overlay.
    """
    if not text:
        return ""

    fade_duration = 2  # Fixed 2-second fade in/out
    margin_percent = 20  # 20% total margins (10% each side)

    # Get target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]

    # Calculate margins
    h_margin = int(target_width * (margin_percent / 200))

    # Calculate dynamic font size based on text length and style
    base_fontsize, min_size, max_size = calculate_dynamic_text_size(
        text, target_aspect, style
    )

    # Set vertical position based on style
    if style == "pulse":
        y_pos = "h*0.75"
    elif style == "concert":
        y_pos = "h*0.75"
    elif style == "promo":
        y_pos = "h*0.75"
    else:
        y_pos = "h*0.75"

    # Calculate timing
    start_time = 0
    full_opacity_start = start_time + fade_duration
    full_opacity_end = min(full_opacity_start + display_duration, video_duration)
    end_time = min(full_opacity_end + fade_duration, video_duration)

    # Properly escape the text for FFmpeg
    escaped_text = text.replace("'", "\\'")
    escaped_text = escaped_text.replace(":", "\\:")
    escaped_text = escaped_text.replace("\\", "\\\\")

    # For pulsing effect, adjust the size variation
    if style == "pulse":
        size_variation = base_fontsize * 0.1  # 10% size variation
        size_expr = f"min({max_size},max({min_size},{base_fontsize}+{size_variation}*sin(2*PI*t/1.5)))"
    else:
        size_expr = str(base_fontsize)

    # Handle DVD bounce motion
    if motion_type == TextMotionType.DVD_BOUNCE.value:
        x_pos = f"mod(t*100,{target_width}-tw)"
        y_pos = f"mod(t*50,{target_height}-th)"

        filter_string = (
            f"drawtext="
            f"text='{escaped_text}':"
            f"fontsize={size_expr}:"
            f"fontcolor=white:"
            f"fontfile=/System/Library/Fonts/Arial Black.ttc:"  # Use system font
            f"borderw=3:"
            f"bordercolor=black:"
            f"x='{x_pos}':"
            f"y='{y_pos}':"
            f"enable=between(t\\,{start_time}\\,{end_time}):"
            f"alpha=if(lt(t\\,{full_opacity_start})\\,(t-{start_time})/{fade_duration}\\,"
            f"if(gt(t\\,{full_opacity_end})\\,1-(t-{full_opacity_end})/{fade_duration}\\,1))"
        )
    else:
        # Base filter string with common parameters
        filter_string = (
            f"drawtext="
            f"text='{escaped_text}':"
            f"fontsize={size_expr}:"
            f"fontcolor=white:"
            f"fontfile=/System/Library/Fonts/Arial Black.ttc:"  # Use system font
            f"x=if(gte(tw\\,{target_width-2*h_margin})\\,{h_margin}\\,max({h_margin}\\,(w-tw)/2)):"
            f"y={y_pos}:"
            f"enable=between(t\\,{start_time}\\,{end_time}):"
            f"alpha=if(lt(t\\,{full_opacity_start})\\,(t-{start_time})/{fade_duration}\\,"
            f"if(gt(t\\,{full_opacity_end})\\,1-(t-{full_opacity_end})/{fade_duration}\\,1))"
        )

        # Add style-specific effects
        if style == "concert":
            # Enhanced concert style with multiple layers for better glow effect
            filter_string = (
                # Main text with thick black outline
                f"drawtext="
                f"text='{escaped_text}':"
                f"fontsize={size_expr}:"
                f"fontcolor=white:"
                f"fontfile=/System/Library/Fonts/Arial Black.ttc:"
                f"borderw=6:"  # Thicker border
                f"bordercolor=black@0.9:"  # More opaque border
                f"x=if(gte(tw\\,{target_width-2*h_margin})\\,{h_margin}\\,max({h_margin}\\,(w-tw)/2)):"
                f"y={y_pos}:"
                f"enable=between(t\\,{start_time}\\,{end_time}):"
                f"alpha=if(lt(t\\,{full_opacity_start})\\,(t-{start_time})/{fade_duration}\\,"
                f"if(gt(t\\,{full_opacity_end})\\,1-(t-{full_opacity_end})/{fade_duration}\\,1))"
                f","
                # Outer glow effect
                f"drawtext="
                f"text='{escaped_text}':"
                f"fontsize={size_expr}:"
                f"fontcolor=white:"
                f"fontfile=/System/Library/Fonts/Arial Black.ttc:"
                f"borderw=12:"  # Very thick border for glow
                f"bordercolor=white@0.3:"  # Semi-transparent white for glow
                f"x=if(gte(tw\\,{target_width-2*h_margin})\\,{h_margin}\\,max({h_margin}\\,(w-tw)/2)):"
                f"y={y_pos}:"
                f"enable=between(t\\,{start_time}\\,{end_time}):"
                f"alpha=if(lt(t\\,{full_opacity_start})\\,(t-{start_time})/{fade_duration}\\,"
                f"if(gt(t\\,{full_opacity_end})\\,1-(t-{full_opacity_end})/{fade_duration}\\,1))"
                f","
                # Inner glow effect
                f"drawtext="
                f"text='{escaped_text}':"
                f"fontsize={size_expr}:"
                f"fontcolor=white:"
                f"fontfile=/System/Library/Fonts/Arial Black.ttc:"
                f"borderw=3:"  # Thin border for inner glow
                f"bordercolor=white@0.5:"  # Semi-transparent white for inner glow
                f"x=if(gte(tw\\,{target_width-2*h_margin})\\,{h_margin}\\,max({h_margin}\\,(w-tw)/2)):"
                f"y={y_pos}:"
                f"enable=between(t\\,{start_time}\\,{end_time}):"
                f"alpha=if(lt(t\\,{full_opacity_start})\\,(t-{start_time})/{fade_duration}\\,"
                f"if(gt(t\\,{full_opacity_end})\\,1-(t-{full_opacity_end})/{fade_duration}\\,1))"
            )
        else:
            # Add standard border for other styles
            filter_string += f":borderw=3:bordercolor=black"

    return filter_string


def detect_hardware_encoders():
    """
    Detect available hardware encoders on the system.
    Returns a tuple of (video_encoder, device, thread_count) or (None, None, None) if no hardware acceleration is available.
    """
    thread_count = os.cpu_count() or 4

    # Check for macOS (Apple Silicon or Intel)
    if sys.platform == "darwin":
        try:
            # Check for Apple Silicon (M1/M2) VideoToolbox
            result = subprocess.run(
                ["sysctl", "machdep.cpu.brand_string"], capture_output=True, text=True
            )
            if "Apple" in result.stdout:
                # M1/M2 optimization
                return "h264_videotoolbox", None, thread_count
            # For Intel Macs with VideoToolbox
            return "h264_videotoolbox", None, thread_count
        except:
            return None, None, thread_count

    # Check for NVIDIA GPU
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode == 0:
            # Get GPU memory info
            memory_info = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
            )
            gpu_memory = int(memory_info.stdout.strip())
            # Enable parallel processing if GPU has enough memory (>8GB)
            parallel_streams = min(3, gpu_memory // 4000) if gpu_memory > 8000 else 1
            return "h264_nvenc", None, parallel_streams
    except:
        pass

    return None, None, thread_count


def create_ffmpeg_command(
    input_file, output_file, vf_filter, duration=None, hw_encoder=None, thread_count=4
):
    """
    Create an FFmpeg command with hardware acceleration if available.
    """
    cmd = ["ffmpeg", "-y"]

    # System-specific optimizations
    if hw_encoder == "h264_videotoolbox":
        # M1/M2 optimizations
        cmd.extend(
            [
                "-threads",
                str(thread_count),
                "-filter_threads",
                str(thread_count),
                "-filter_complex_threads",
                str(thread_count),
            ]
        )
    elif hw_encoder == "h264_nvenc":
        # NVIDIA optimizations
        cmd.extend(
            [
                "-threads",
                str(thread_count),
                "-extra_hw_frames",
                "3",  # Buffer for hardware frames
                "-gpu_init_delay",
                "0.1",  # Faster GPU initialization
            ]
        )
    else:
        # CPU optimizations
        cmd.extend(
            [
                "-threads",
                str(thread_count),
                "-filter_threads",
                str(thread_count),
                "-filter_complex_threads",
                str(thread_count),
            ]
        )

    # Input file
    if hw_encoder in ["h264_qsv", "h264_nvenc"]:
        cmd.extend(["-hwaccel", "auto"])
    cmd.extend(["-i", input_file])

    # Add duration limit if specified
    if duration:
        cmd.extend(["-t", str(duration)])

    # Video filter
    cmd.extend(["-vf", vf_filter])

    # Video codec settings
    if hw_encoder:
        cmd.extend(["-c:v", hw_encoder])

        if hw_encoder == "h264_nvenc":
            cmd.extend(
                [
                    "-preset",
                    "p4",  # Highest quality preset
                    "-rc",
                    "vbr",  # Variable bitrate
                    "-cq",
                    "20",  # Quality-based VBR
                    "-b:v",
                    "10M",  # Higher bitrate for better quality
                    "-maxrate",
                    "15M",  # Maximum bitrate
                    "-bufsize",
                    "15M",  # Buffer size
                    "-spatial-aq",
                    "1",  # Spatial adaptive quantization
                    "-temporal-aq",
                    "1",  # Temporal adaptive quantization
                ]
            )
        elif hw_encoder == "h264_videotoolbox":
            cmd.extend(
                [
                    "-b:v",
                    "10M",  # Higher bitrate for M2 Max
                    "-maxrate",
                    "15M",  # Maximum bitrate
                    "-bufsize",
                    "15M",  # Buffer size
                    "-tag:v",
                    "avc1",  # Ensure compatibility
                    "-movflags",
                    "+faststart",  # Optimize for streaming
                ]
            )
    else:
        # Fallback to CPU encoding with good quality settings
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])

    # Audio codec
    cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    # Output file
    cmd.append(output_file)

    return cmd


def process_intro_segment(
    intro_video_path, target_aspect, temp_dir, max_intro_length=20
):
    """Process the intro video segment with proper scaling and formatting."""
    if not intro_video_path or not os.path.exists(intro_video_path):
        return None

    intro_segment_file = os.path.join(temp_dir, "intro_segment.mp4")

    try:
        # Get the scaling filter for the intro video
        scaling_filter = determine_scaling_filter(intro_video_path, target_aspect)

        # Detect hardware encoder
        hw_encoder, _, _ = detect_hardware_encoders()

        # Get intro video duration
        intro_duration = get_video_duration(intro_video_path)

        # If intro video is longer than max_intro_length, create a segment of that length
        if intro_duration > max_intro_length:
            print(
                f"Intro video is {intro_duration:.1f} seconds long. Creating a {max_intro_length}-second segment..."
            )
            # Create FFmpeg command with hardware acceleration and duration limit
            cmd = create_ffmpeg_command(
                input_file=intro_video_path,
                output_file=intro_segment_file,
                vf_filter=scaling_filter,
                hw_encoder=hw_encoder,
                duration=max_intro_length,  # Use the specified max length
            )
        else:
            print(f"Using full intro video ({intro_duration:.1f} seconds)...")
            # Create FFmpeg command with hardware acceleration
            cmd = create_ffmpeg_command(
                input_file=intro_video_path,
                output_file=intro_segment_file,
                vf_filter=scaling_filter,
                hw_encoder=hw_encoder,
            )

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )

        if result.returncode != 0 or not os.path.exists(intro_segment_file):
            print(f"Warning: Failed to process intro video: {result.stderr}")
            return None

        # Verify the processed intro segment
        processed_duration = get_video_duration(intro_segment_file)
        print(f"Processed intro segment duration: {processed_duration:.1f} seconds")

        return intro_segment_file
    except Exception as e:
        print(f"Error processing intro segment: {e}")
        return None


def create_concat_file(segment_files, temp_dir):
    """Create a concatenated video file from segment files."""
    # Create a file with list of segments for FFmpeg concat
    concat_file = os.path.join(temp_dir, "concat_list.txt")
    try:
        with open(concat_file, "w") as f:
            for segment_file in segment_files:
                f.write(f"file '{segment_file}'\n")

        # Concatenate all segments
        temp_output = os.path.join(temp_dir, "temp_output.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c:v",
            "libx264",  # Use libx264 for video
            "-c:a",
            "aac",  # Use AAC for audio
            "-b:a",
            "192k",  # Set audio bitrate
            "-strict",
            "experimental",  # Allow experimental codecs
            "-map",
            "0:v",  # Map video stream
            "-map",
            "0:a",  # Map audio stream
            temp_output,
        ]
        print(f"Creating intermediate file: {temp_output}")
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )

        # Check if the command was successful
        if result.returncode != 0:
            print("FFmpeg Error during concat:")
            print(result.stderr)
            return None

        # Verify the temp file was created
        if not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
            print("Temp directory contents:")
            for file in os.listdir(temp_dir):
                print(f"  - {file}")
            print("Concat file contents:")
            with open(concat_file, "r") as f:
                print(f.read())
            return None

        return temp_output
    except Exception as e:
        print(f"Error creating concat file: {e}")
        return None


def fallback_create_output(
    segment_files,
    output_path,
    video_duration,
    target_aspect,
    text=None,
    text_style="default",
    text_motion="none",
    text_display_duration=5,
    intro_video=None,
    intro_audio=None,
    intro_audio_duration=5.0,
    intro_audio_volume=2.0,
):
    """Fallback method: Create output video by directly encoding all segments into one file."""
    print("Using fallback method to create video...")

    # Set target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]

    # Generate a complex filtergraph to chain all segments together
    filter_complex = []
    inputs = []

    # Add intro video if provided
    if intro_video and os.path.exists(intro_video):
        inputs.extend(["-i", intro_video])
        filter_complex.append(f"[0:v]scale={target_width}:{target_height}[intro_v]")
        filter_complex.append(
            f"[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[intro_a]"
        )

    # Add main segments
    for i, segment_file in enumerate(segment_files):
        inputs.extend(["-i", segment_file])
        filter_complex.append(f"[{i+1}:v]scale={target_width}:{target_height}[v{i}]")
        filter_complex.append(
            f"[{i+1}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]"
        )

    # Concatenate video streams
    if intro_video and os.path.exists(intro_video):
        # Concatenate intro with main segments
        vid_concat = (
            "".join(
                [
                    f"[intro_v]" if i == 0 else f"[v{i-1}]"
                    for i in range(len(segment_files) + 1)
                ]
            )
            + f"concat=n={len(segment_files) + 1}:v=1:a=0[outv]"
        )
    else:
        # Concatenate only main segments
        vid_concat = (
            "".join([f"[v{i}]" for i in range(len(segment_files))])
            + f"concat=n={len(segment_files)}:v=1:a=0[outv]"
        )

    # Handle audio mixing
    if (
        intro_video
        and os.path.exists(intro_video)
        and intro_audio
        and os.path.exists(intro_audio)
    ):
        # Mix intro audio with main audio
        audio_mix = (
            "".join(
                [
                    f"[intro_a]" if i == 0 else f"[a{i-1}]"
                    for i in range(len(segment_files) + 1)
                ]
            )
            + f"concat=n={len(segment_files) + 1}:v=0:a=1[outa]"
        )
    else:
        # Concatenate only main audio
        audio_mix = (
            "".join([f"[a{i}]" for i in range(len(segment_files))])
            + f"concat=n={len(segment_files)}:v=0:a=1[outa]"
        )

    # Add text overlay if provided
    if text:
        text_filter = create_text_overlay_filter(
            video_duration=video_duration,
            text=text,
            display_duration=text_display_duration,
            style=text_style,
            target_aspect=target_aspect,
            motion_type=text_motion,
        )
        if text_filter:
            vid_concat += f";[outv]{text_filter}[finalv]"
            video_output = "[finalv]"
        else:
            video_output = "[outv]"
    else:
        video_output = "[outv]"

    # Combine all filter parts
    filter_complex.extend([vid_concat, audio_mix])
    filter_complex_str = ";".join(filter_complex)

    # Build the full command
    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend(
        [
            "-filter_complex",
            filter_complex_str,
            "-map",
            video_output,
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            str(video_duration),
            output_path,
        ]
    )

    print("Executing fallback FFmpeg command...")
    print("Command:", " ".join(cmd))
    print("Filter complex:", filter_complex_str)

    # First, test if the filter complex is valid
    test_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=1920x1080:rate=30",
        "-filter_complex",
        filter_complex_str,
        "-f",
        "null",
        "-",
    ]
    try:
        test_result = subprocess.run(
            test_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if test_result.returncode != 0:
            print("Filter complex test failed:")
            print(test_result.stderr)
            raise Exception("Invalid filter complex string")
    except Exception as e:
        print(f"Error testing filter complex: {e}")
        raise

    # Execute the actual command
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )

    if result.returncode != 0:
        print("FFmpeg Error in fallback method:")
        print(result.stderr)
        raise Exception(
            "Both regular and fallback methods failed to create output video"
        )

    if not os.path.exists(output_path):
        raise Exception("Fallback method didn't create output file")


def parse_input_string(input_string):
    """Parse input string to extract video name, format, and input videos."""
    parts = input_string.strip().split(",")
    if len(parts) < 3:
        print(
            "Error: Input string must contain at least: output name, format, and one input video"
        )
        return None, None, None

    output_name = parts[0].strip()

    # Validate format
    format_name = parts[1].strip().lower()
    if format_name not in ASPECT_RATIOS:
        print(
            f"Error: Format '{format_name}' not supported. Choose from: {', '.join(ASPECT_RATIOS.keys())}"
        )
        return output_name, None, None

    # Get input videos
    input_videos = [video.strip() for video in parts[2:]]

    return output_name, format_name, input_videos


def create_video_segment(
    video_path, start_time, segment_duration, output_file, target_aspect, direction
):
    """Create a single video segment with the specified parameters."""
    try:
        # Get target dimensions
        target_width = ASPECT_RATIOS[target_aspect]["width"]
        target_height = ASPECT_RATIOS[target_aspect]["height"]

        # Get input video dimensions
        input_width, input_height = get_video_dimensions(video_path)

        # Calculate scaling factors - scale up by 20% to allow for movement
        width_scale = (target_width * 1.2) / input_width
        height_scale = (target_height * 1.2) / input_height
        scale_factor = max(width_scale, height_scale)

        # Calculate new dimensions after scaling
        new_width = int(input_width * scale_factor)
        new_height = int(input_height * scale_factor)

        # Calculate crop offsets
        crop_x = max(0, (new_width - target_width) // 2)
        crop_y = max(0, (new_height - target_height) // 2)

        # Base filter for scaling
        base_filter = f"scale={new_width}:{new_height}:force_original_aspect_ratio=1"

        # Add panning if needed
        if direction and segment_duration >= 2.0:
            # Calculate frames for duration
            fps = 30  # Assuming 30fps
            duration_frames = int(segment_duration * fps)

            # Create panning filter based on direction
            if direction == PanDirection.LEFT_TO_RIGHT:
                # Pan from left to right using frame number
                pan_filter = f"crop=w={target_width}:h={target_height}:x='{crop_x}+({new_width-target_width})*0.2*n/{duration_frames}':y={crop_y}"
            elif direction == PanDirection.RIGHT_TO_LEFT:
                # Pan from right to left using frame number
                pan_filter = f"crop=w={target_width}:h={target_height}:x='{crop_x}+({new_width-target_width})*0.2*(1-n/{duration_frames})':y={crop_y}"
            elif direction == PanDirection.ZOOM_IN:
                # Zoom in effect using frame number
                pan_filter = f"crop=w='{target_width}*(1+0.2*n/{duration_frames})':h='{target_height}*(1+0.2*n/{duration_frames})':x='({new_width}-{target_width}*(1+0.2*n/{duration_frames}))/2':y='({new_height}-{target_height}*(1+0.2*n/{duration_frames}))/2'"
            elif direction == PanDirection.ZOOM_OUT:
                # Zoom out effect using frame number
                pan_filter = f"crop=w='{target_width}*(1+0.2-0.2*n/{duration_frames})':h='{target_height}*(1+0.2-0.2*n/{duration_frames})':x='({new_width}-{target_width}*(1+0.2-0.2*n/{duration_frames}))/2':y='({new_height}-{target_height}*(1+0.2-0.2*n/{duration_frames}))/2'"
            else:
                pan_filter = ""

            # Combine filters
            if pan_filter:
                filter_string = f"{base_filter},{pan_filter}"
            else:
                filter_string = base_filter
        else:
            # If no panning, just crop to target size
            filter_string = (
                f"{base_filter},crop={target_width}:{target_height}:{crop_x}:{crop_y}"
            )

        # Create FFmpeg command with hardware acceleration if available
        hw_encoder, _, thread_count = detect_hardware_encoders()

        cmd = ["ffmpeg", "-y"]

        # Add hardware acceleration if available
        if hw_encoder:
            if hw_encoder == "h264_videotoolbox":
                cmd.extend(
                    [
                        "-threads",
                        str(thread_count),
                        "-filter_threads",
                        str(thread_count),
                        "-filter_complex_threads",
                        str(thread_count),
                    ]
                )
            elif hw_encoder == "h264_nvenc":
                cmd.extend(
                    [
                        "-threads",
                        str(thread_count),
                        "-extra_hw_frames",
                        "3",
                        "-gpu_init_delay",
                        "0.1",
                    ]
                )

        # Add input parameters
        cmd.extend(
            ["-ss", str(start_time), "-i", video_path, "-t", str(segment_duration)]
        )

        # Add video filter
        cmd.extend(["-vf", filter_string])

        # Add codec settings
        if hw_encoder:
            cmd.extend(["-c:v", hw_encoder])
            if hw_encoder == "h264_nvenc":
                cmd.extend(
                    [
                        "-preset",
                        "p4",
                        "-rc",
                        "vbr",
                        "-cq",
                        "20",
                        "-b:v",
                        "10M",
                        "-maxrate",
                        "15M",
                        "-bufsize",
                        "15M",
                        "-spatial-aq",
                        "1",
                        "-temporal-aq",
                        "1",
                    ]
                )
            elif hw_encoder == "h264_videotoolbox":
                cmd.extend(
                    [
                        "-b:v",
                        "10M",
                        "-maxrate",
                        "15M",
                        "-bufsize",
                        "15M",
                        "-tag:v",
                        "avc1",
                        "-movflags",
                        "+faststart",
                    ]
                )
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])

        # Add audio settings
        cmd.extend(["-c:a", "aac", "-b:a", "192k", output_file])

        # Execute command with detailed error logging
        print(f"\nCreating segment with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"FFmpeg Error Output:")
            print(result.stderr)
            return None

        # Verify the output file exists and has content
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            print(f"Error: Output file was not created or is empty: {output_file}")
            return None

        return output_file

    except Exception as e:
        print(f"Error creating video segment: {str(e)}")
        return None


def create_video_montage(
    video_paths,
    output_duration,
    output_path,
    target_aspect="vertical_portrait",
    enable_panning=True,
    pan_strategy="random",
    pan_speed=1.0,
    pan_distance=0.2,
    easing_type=EasingType.EASE_IN_OUT,
    segment_count="some",
    text=None,
    text_display_duration=5,
    text_style="default",
    text_motion="none",
    intro_video=None,
    intro_audio=None,
    intro_audio_duration=5.0,
    intro_audio_volume=2.0,
    max_intro_length=20,
):
    """Create a montage video with hardware acceleration if available."""

    # Create a temporary directory that will be automatically cleaned up
    temp_dir = tempfile.mkdtemp(prefix="video_montage_")
    try:
        print(f"\nUsing temporary directory: {temp_dir}")
        segment_files = []

        # Process intro video if provided
        intro_segment = None
        if intro_video and os.path.exists(intro_video):
            intro_segment = process_intro_segment(
                intro_video, target_aspect, temp_dir, max_intro_length
            )
            if intro_segment:
                segment_files.append(intro_segment)
                print(
                    f"Added intro video segment: {get_video_duration(intro_segment):.2f} seconds"
                )

        # Detect available hardware encoder
        hw_encoder, _, thread_count = detect_hardware_encoders()
        if hw_encoder:
            print(f"Using hardware encoder: {hw_encoder} with {thread_count} threads")
            if hw_encoder == "h264_videotoolbox":
                print("Optimized for Apple Silicon")
            elif hw_encoder == "h264_nvenc":
                print("Optimized for NVIDIA GPU")
        else:
            print(f"Using CPU encoding (libx264) with {thread_count} threads")

        # Get fixed number of segments based on segment_count setting
        num_segments_needed = get_segment_range(segment_count)
        print(f"Creating {num_segments_needed} segments...")

        # Calculate segment duration to match output duration
        if intro_segment:
            intro_duration = get_video_duration(intro_segment)
            remaining_duration = max(0, output_duration - intro_duration)
            segment_duration = remaining_duration / num_segments_needed
        else:
            segment_duration = output_duration / num_segments_needed

        print(f"Each segment will be exactly {segment_duration:.2f} seconds")

        # Extract segments from each video
        all_segments = []
        for video_path in video_paths:
            # Get segments for this video
            segments = extract_interesting_segments(
                video_path, num_segments_needed * 3, segment_duration
            )

            # Add segments with their source video
            for start_time, _ in segments:
                all_segments.append(
                    (video_path, start_time, segment_duration)
                )  # Use exact segment duration

        # Shuffle all segments
        random.shuffle(all_segments)

        # Select unique segments with minimum spacing
        selected_segments = []
        min_gap = segment_duration * 0.5  # Minimum gap between segments

        # First pass: Try to get segments with good spacing
        for segment in all_segments:
            # Check if this segment is too close to any already selected segment
            if not any(abs(segment[1] - s[1]) < min_gap for s in selected_segments):
                selected_segments.append(segment)
                if len(selected_segments) >= num_segments_needed:
                    break

        # Second pass: If we don't have enough segments, add more with less strict spacing
        if len(selected_segments) < num_segments_needed:
            for segment in all_segments:
                if segment not in selected_segments:
                    selected_segments.append(segment)
                    if len(selected_segments) >= num_segments_needed:
                        break

        # Verify we have enough segments
        if len(selected_segments) < num_segments_needed:
            raise Exception(
                f"Could not find enough unique segments. Found {len(selected_segments)}, needed {num_segments_needed}"
            )

        # Print selected segments for verification
        print("\nSelected segments for montage:")
        for i, (video_path, start_time, duration) in enumerate(selected_segments):
            print(
                f"Segment {i+1}: {os.path.basename(video_path)} at {start_time:.2f}s for {duration:.2f}s"
            )

        # Extract regular segments to temporary files
        successful_segments = 0
        for i, (video_path, start_time, duration) in enumerate(selected_segments):
            segment_file = os.path.join(temp_dir, f"segment_{i:03d}.mp4")

            # Determine panning direction for this segment
            current_direction = None
            if enable_panning:
                if pan_strategy == "random":
                    current_direction = random.choice(list(PanDirection))
                elif pan_strategy == "sequence":
                    # Cycle through directions in sequence
                    current_direction = list(PanDirection)[i % len(PanDirection)]
                elif isinstance(pan_strategy, PanDirection):
                    current_direction = pan_strategy

            # Create segment using the panning approach
            result = create_video_segment(
                video_path=video_path,
                start_time=start_time,
                segment_duration=duration,
                output_file=segment_file,
                target_aspect=target_aspect,
                direction=current_direction,
            )

            if result:
                actual_duration = get_video_duration(segment_file)
                print(
                    f"Segment {i+1}/{len(selected_segments)} created successfully. Duration: {actual_duration:.2f}s"
                )
                if current_direction:
                    print(f"Using panning direction: {current_direction.value}")
                segment_files.append(segment_file)
                successful_segments += 1
            else:
                print(f"Warning: Failed to create segment {i+1}")
                # Try again with a different segment
                for alt_segment in all_segments:
                    if alt_segment not in selected_segments:
                        alt_result = create_video_segment(
                            video_path=alt_segment[0],
                            start_time=alt_segment[1],
                            segment_duration=duration,
                            output_file=segment_file,
                            target_aspect=target_aspect,
                            direction=current_direction,
                        )
                        if alt_result:
                            actual_duration = get_video_duration(segment_file)
                            print(
                                f"Alternative segment created successfully. Duration: {actual_duration:.2f}s"
                            )
                            segment_files.append(segment_file)
                            successful_segments += 1
                            break

        if successful_segments < num_segments_needed:
            raise Exception(
                f"Could not create enough valid segments. Created {successful_segments}, needed {num_segments_needed}"
            )

        if not segment_files:
            raise Exception("No valid segments were created. Cannot create montage.")

        try:
            # Create concat file
            temp_output = create_concat_file(segment_files, temp_dir)

            if temp_output:
                # Add text overlay
                text_filter = create_text_overlay_filter(
                    video_duration=output_duration,
                    text=text,
                    display_duration=text_display_duration,
                    style=text_style,
                    target_aspect=target_aspect,
                    motion_type=text_motion,
                )

                # Set target dimensions
                target_width = ASPECT_RATIOS[target_aspect]["width"]
                target_height = ASPECT_RATIOS[target_aspect]["height"]

                # Prepare final FFmpeg command
                filter_complex = []
                inputs = ["-i", temp_output]

                # Add intro audio if provided
                if intro_audio and os.path.exists(intro_audio):
                    inputs.extend(["-i", intro_audio])

                    # Create complex filter for audio mixing
                    filter_complex.extend(
                        [
                            # Original audio with volume adjustment after intro
                            f"[0:a]volume=enable='gte(t,{intro_audio_duration})':"
                            f"volume='min(1,(t-{intro_audio_duration})/2)'[main_audio]",
                            # Intro audio with fade out
                            f"[1:a]volume={intro_audio_volume}:"
                            f"enable='lte(t,{intro_audio_duration+2})':"
                            f"volume='max(0,1-(t-{intro_audio_duration})/2)'[intro_audio]",
                            # Mix both audio streams
                            "[main_audio][intro_audio]amix=inputs=2:duration=longest[aout]",
                        ]
                    )

                # Build the final FFmpeg command
                cmd = ["ffmpeg", "-y"]
                cmd.extend(inputs)

                if text_filter:
                    # Create filter complex with text overlay
                    filter_complex.append(f"[0:v]{text_filter}[vout]")

                    # Join all filter parts with semicolons
                    filter_complex_str = ";".join(filter_complex)
                    cmd.extend(["-filter_complex", filter_complex_str])
                    cmd.extend(["-map", "[vout]"])
                else:
                    cmd.extend(["-map", "0:v"])

                # Map audio based on whether we have intro audio
                if intro_audio and os.path.exists(intro_audio):
                    cmd.extend(["-map", "[aout]"])
                else:
                    cmd.extend(["-map", "0:a"])

                # Add video codec settings
                cmd.extend(
                    [
                        "-c:v",
                        "libx264",  # Use libx264 for video
                        "-preset",
                        "medium",  # Balance between speed and quality
                        "-crf",
                        "23",  # Constant Rate Factor for quality
                        "-c:a",
                        "aac",  # Use AAC for audio
                        "-b:a",
                        "192k",  # Set audio bitrate
                        "-s",
                        f"{target_width}x{target_height}",
                        "-t",
                        str(output_duration),  # Ensure correct duration
                        output_path,
                    ]
                )

                print(f"\nExecuting final FFmpeg command to create: {output_path}")
                print("Command:", " ".join(cmd))
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )

                if result.returncode != 0:
                    print("FFmpeg Error:")
                    print(result.stderr)
                    raise Exception(
                        f"FFmpeg failed with return code {result.returncode}"
                    )

                # Verify the output file
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    actual_duration = get_video_duration(output_path)
                    print(f"\nOutput video created successfully:")
                    print(f"Duration: {actual_duration:.2f}s")
                    print(f"Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

                    # Verify duration
                    if (
                        abs(actual_duration - output_duration) > 0.5
                    ):  # Allow 0.5s tolerance
                        print(
                            f"Warning: Output duration mismatch. Expected {output_duration}s, got {actual_duration}s"
                        )
                        raise Exception(
                            "Output video duration does not match requested duration"
                        )
                else:
                    raise Exception("Output file was not created or is empty")

            else:
                # Fallback to direct encoding if concat fails
                fallback_create_output(
                    segment_files=segment_files,
                    output_path=output_path,
                    video_duration=output_duration,
                    target_aspect=target_aspect,
                    text=text,
                    text_style=text_style,
                    text_motion=text_motion,
                    text_display_duration=text_display_duration,
                    intro_video=intro_video,
                    intro_audio=intro_audio,
                    intro_audio_duration=intro_audio_duration,
                    intro_audio_volume=intro_audio_volume,
                )

        except Exception as e:
            print(f"Error during montage creation: {e}")
            print("Trying direct encoding fallback method...")
            fallback_create_output(
                segment_files=segment_files,
                output_path=output_path,
                video_duration=output_duration,
                target_aspect=target_aspect,
                text=text,
                text_style=text_style,
                text_motion=text_motion,
                text_display_duration=text_display_duration,
                intro_video=intro_video,
                intro_audio=intro_audio,
                intro_audio_duration=intro_audio_duration,
                intro_audio_volume=intro_audio_volume,
            )
    finally:
        # Clean up temporary files
        print("\nCleaning up temporary files...")
        try:
            # Remove all files in the temp directory
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting temporary file {file_path}: {e}")

            # Remove the temp directory itself
            os.rmdir(temp_dir)
            print("Temporary files cleaned up successfully")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Create an exciting video montage from input videos for social media."
    )
    parser.add_argument(
        "--input-string",
        "-i",
        help='Input string in format: "output_name, format, video1, video2, ..."',
    )
    parser.add_argument("--output", "-o", required=True, help="Output video file")
    parser.add_argument(
        "--format",
        "-f",
        required=True,
        choices=["vertical_portrait", "instagram_square"],
        help="Output video format/aspect ratio",
    )
    parser.add_argument(
        "--duration",
        "-d",
        type=int,
        choices=[30, 60, 90],
        default=60,
        help="Output video duration in seconds (30, 60, or 90)",
    )
    parser.add_argument(
        "--segments",
        choices=["few", "some", "lots"],
        default="some",
        help="Number of segments to create (few=3-7, some=6-12, lots=10-25)",
    )
    parser.add_argument("--panning", action="store_true", help="Enable panning effects")
    parser.add_argument(
        "--pan-strategy",
        choices=[d.value for d in PanDirection] + ["random", "sequence"],
        default="random",
        help="Panning strategy: specific direction, random, or sequence",
    )
    parser.add_argument(
        "--pan-speed",
        type=float,
        default=1.0,
        help="Panning speed factor (default: 1.0)",
    )
    parser.add_argument(
        "--pan-distance",
        type=float,
        default=0.2,
        help="Panning distance as percentage of frame (0.0-1.0)",
    )
    parser.add_argument(
        "--easing",
        choices=[e.value for e in EasingType],
        default=EasingType.EASE_IN_OUT.value,
        help="Easing function for smooth panning",
    )
    parser.add_argument(
        "--intro-video", help="Video to play at the start before random segments"
    )
    parser.add_argument(
        "--intro-audio",
        help="Audio file to play at the start (will fade into video audio)",
    )
    parser.add_argument(
        "--intro-audio-duration",
        type=float,
        default=5.0,
        help="Duration of intro audio in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--intro-audio-volume",
        type=float,
        default=2.0,
        help="Volume multiplier for intro audio (default: 2.0)",
    )
    parser.add_argument(
        "--intro-video-length",
        type=int,
        default=20,
        help="Maximum length of intro video in seconds (5-30 seconds, default: 20)",
    )
    parser.add_argument("--text", help="Text string to display")
    parser.add_argument(
        "--text-duration",
        type=int,
        default=5,
        help="Duration to display text (in seconds)",
    )
    parser.add_argument(
        "--text-style",
        choices=["default", "pulse", "concert", "promo"],
        default="default",
        help="Style of text overlay (default, pulse, concert, promo)",
    )
    parser.add_argument(
        "--text-motion",
        choices=[m.value for m in TextMotionType],
        default=TextMotionType.NONE.value,
        help="Type of text motion effect (none, dvd_bounce)",
    )
    parser.add_argument("input_video", nargs="?", help="Input video file")

    args = parser.parse_args()

    # Validate intro video length
    if args.intro_video_length < 5 or args.intro_video_length > 30:
        print("Error: Intro video length must be between 5 and 30 seconds")
        sys.exit(1)

    if not check_ffmpeg():
        sys.exit(1)

    # Check if input video is provided
    if not args.input_video:
        print("Error: Input video file is required")
        parser.print_help()
        sys.exit(1)

    # Use the input video directly
    videos = [args.input_video]

    categorized_videos = validate_inputs(videos)
    if not categorized_videos:
        sys.exit(1)

    # Flatten the list of videos
    all_videos = []
    for video_list in categorized_videos.values():
        all_videos.extend(video_list)

    print(f"Current working directory: {os.path.abspath(os.getcwd())}")
    print(
        f"Creating a {args.duration}-second {ASPECT_RATIOS[args.format]['description']} montage from {len(all_videos)} video(s)..."
    )

    # Convert string arguments to enums
    easing_type = EasingType(args.easing)
    pan_strategy = args.pan_strategy

    if pan_strategy in [d.value for d in PanDirection]:
        pan_strategy = PanDirection(pan_strategy)

    try:
        # Test filters before starting the main processing
        print("Testing filter compatibility with your FFmpeg installation...")
        working_filters = generate_and_test_filters()
        if not working_filters:
            print(
                "Warning: No working pan filters found. Will use static filters only."
            )
            enable_panning = False
        else:
            print(f"Found {len(working_filters)} working filter configurations.")

        # Modify output filename to include text style and duration
        output_path = args.output
        if output_path:
            # Split the path into directory, filename, and extension
            directory = os.path.dirname(output_path)
            filename = os.path.splitext(os.path.basename(output_path))[0]
            extension = os.path.splitext(output_path)[1]

            # Add text style and duration to filename
            new_filename = f"{filename}_{args.text_style}_{args.duration}s{extension}"
            output_path = os.path.join(directory, new_filename) if directory else new_filename

        create_video_montage(
            all_videos,
            args.duration,
            output_path,
            args.format,
            enable_panning=args.panning,
            pan_strategy=pan_strategy,
            pan_speed=args.pan_speed,
            pan_distance=args.pan_distance,
            easing_type=easing_type,
            segment_count=args.segments,
            text=args.text,
            text_display_duration=args.text_duration,
            text_style=args.text_style,
            text_motion=args.text_motion,
            intro_video=args.intro_video,
            intro_audio=args.intro_audio,
            intro_audio_duration=args.intro_audio_duration,
            intro_audio_volume=args.intro_audio_volume,
            max_intro_length=args.intro_video_length,
        )
        abs_output_path = os.path.abspath(output_path)

        # Check if the file was actually created
        if os.path.exists(abs_output_path):
            file_size = os.path.getsize(abs_output_path) / (1024 * 1024)  # Size in MB
            print(f"Success! Video montage saved to: {abs_output_path}")
            print(f"File size: {file_size:.2f} MB")
        else:
            print(f"Warning: File was not found at: {abs_output_path}")
            print("The operation may have failed or saved to a different location.")
    except Exception as e:
        print(f"Error creating video montage: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
