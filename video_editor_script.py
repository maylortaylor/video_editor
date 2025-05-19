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
    "vertical_portrait": {"width": 1080, "height": 1920, "description": "Vertical Portrait (9:16)"},
    "instagram_square": {"width": 1080, "height": 1080, "description": "Instagram Square (1:1)"},
}

# Panning types
class PanDirection(Enum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"

# Easing functions for smooth panning
class EasingType(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"

def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: FFmpeg is not installed or not in PATH. Please install FFmpeg to use this script.")
        return False

def get_video_duration(video_path):
    """Get the duration of a video in seconds using FFmpeg."""
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return float(result.stdout.strip())

def get_video_dimensions(video_path):
    """Get the width and height of a video using FFmpeg."""
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-select_streams', 'v:0', 
        '-show_entries', 'stream=width,height', 
        '-of', 'csv=s=x:p=0', 
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    dimensions = result.stdout.strip().split('x')
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
    elif 1800 < duration <= 3600:  # 30 minutes to 1 hour
        return "long"
    else:
        return "invalid"

def determine_scaling_filter(video_path, target_aspect):
    """Determine how to scale and pad/crop video to match target aspect ratio."""
    width, height = get_video_dimensions(video_path)
    video_aspect = width / height
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]
    target_ratio = target_width / target_height
    
    # For vertical videos (Instagram Reels, TikTok)
    if target_ratio < 1:  # Target is portrait/vertical
        if video_aspect > 1:  # Input is landscape
            # Scale to match target height while maintaining aspect ratio
            scale_height = target_height
            scale_width = int(target_height * video_aspect)
            # Center crop to target width
            crop_x = (scale_width - target_width) // 2
            return f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=1,crop={target_width}:{target_height}:{crop_x}:0"
        else:  # Input is already portrait/vertical or square
            # Scale to match target width while maintaining aspect ratio
            scale_width = target_width
            scale_height = int(target_width / video_aspect)
            if scale_height < target_height:
                # If scaled height is smaller, scale to target height instead
                scale_height = target_height
                scale_width = int(scale_height * video_aspect)
                crop_x = (scale_width - target_width) // 2
                return f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=1,crop={target_width}:{target_height}:{crop_x}:0"
            else:
                crop_y = (scale_height - target_height) // 2
                return f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=1,crop={target_width}:{target_height}:0:{crop_y}"
    
    # For square videos (Instagram Square)
    else:  # Target is square (1:1)
        if video_aspect > 1:  # Input is landscape
            # Scale to target height while maintaining aspect ratio
            scale_height = target_height
            scale_width = int(scale_height * video_aspect)
            crop_x = (scale_width - target_width) // 2
            return f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=1,crop={target_width}:{target_height}:{crop_x}:0"
        else:  # Input is portrait/vertical
            # Scale to target width while maintaining aspect ratio
            scale_width = target_width
            scale_height = int(scale_width / video_aspect)
            crop_y = (scale_height - target_height) // 2
            return f"scale={scale_width}:{scale_height}:force_original_aspect_ratio=1,crop={target_width}:{target_height}:0:{crop_y}"

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

def generate_ultra_simple_pan_filter(direction, duration, pan_speed=1.0, pan_distance=0.2, easing_type=EasingType.LINEAR):
    """
    Generate an ultra-simplified zoompan filter string for FFmpeg using minimal expressions
    that are guaranteed to parse correctly.
    """
    fps = 30
    frames = max(2, int(duration * fps))
    zoom_factor = 1.0 + pan_distance

    if direction == PanDirection.LEFT_TO_RIGHT:
        return f'scale={zoom_factor}*iw:-1,zoompan=z=1:x=\'iw*{pan_distance}*(n/{frames})\':y=0:fps={fps}:d={frames}'
    elif direction == PanDirection.RIGHT_TO_LEFT:
        return f'scale={zoom_factor}*iw:-1,zoompan=z=1:x=\'iw*{pan_distance}*(1-n/{frames})\':y=0:fps={fps}:d={frames}'
    elif direction == PanDirection.TOP_TO_BOTTOM:
        return f'scale={zoom_factor}*iw:-1,zoompan=z=1:x=0:y=\'ih*{pan_distance}*(n/{frames})\':fps={fps}:d={frames}'
    elif direction == PanDirection.BOTTOM_TO_TOP:
        return f'scale={zoom_factor}*iw:-1,zoompan=z=1:x=0:y=\'ih*{pan_distance}*(1-n/{frames})\':fps={fps}:d={frames}'
    elif direction == PanDirection.ZOOM_IN:
        return f'scale={zoom_factor}*iw:-1,zoompan=z=\'1+{pan_distance}*(n/{frames})\':x=\'(iw-iw/z)/2\':y=\'(ih-ih/z)/2\':fps={fps}:d={frames}'
    elif direction == PanDirection.ZOOM_OUT:
        return f'scale={zoom_factor}*iw:-1,zoompan=z=\'1+{pan_distance}*(1-n/{frames})\':x=\'(iw-iw/z)/2\':y=\'(ih-ih/z)/2\':fps={fps}:d={frames}'
    else:
        return f'scale={zoom_factor}*iw:-1,crop=iw/{zoom_factor}:ih/{zoom_factor}'


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
    if "short" in categorized_videos and len(categorized_videos["short"]) < 3 and len(categorized_videos) == 1:
        print(f"Error: At least 3 short videos are required. Only {len(categorized_videos['short'])} provided.")
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
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        audio_data_file = temp_file.name

    try:
        # Extract audio levels using FFmpeg's volumedetect filter
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-af', f'astats=metadata=1:reset={segment_duration},ametadata=print:key=lavfi.astats.Overall.RMS_level',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        # Parse the output to find timestamps with high audio levels
        audio_levels = []
        current_time = 0
        
        for line in result.stderr.split('\n'):
            if 'RMS_level' in line:
                try:
                    level = float(line.split('=')[1])
                    audio_levels.append((current_time, level))
                    current_time += segment_duration
                except (ValueError, IndexError):
                    continue
        
        # Sort segments by audio level (highest to lowest)
        audio_levels.sort(key=lambda x: x[1], reverse=True)
        
        # Return timestamps of the highest energy segments
        return [timestamp for timestamp, _ in audio_levels[:20]]  # Return top 20 segments
        
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
    
    segments = []
    
    # First, add segments from high-energy parts
    for timestamp in high_energy_timestamps:
        if timestamp + target_duration <= duration:
            segments.append((timestamp, target_duration))
    
    # If we need more segments, add some from regular intervals
    if len(segments) < num_segments:
        # Calculate how many more segments we need
        remaining_segments = num_segments - len(segments)
        interval = (duration - target_duration) / (remaining_segments + 1)
        
        for i in range(remaining_segments):
            start_time = (i + 1) * interval
            if start_time + target_duration <= duration:
                # Check if this segment overlaps with existing ones
                overlaps = any(abs(start_time - s[0]) < target_duration for s in segments)
                if not overlaps:
                    segments.append((start_time, target_duration))
    
    # Shuffle to get a random selection
    random.shuffle(segments)
    
    # Limit to requested number of segments
    return segments[:num_segments]

def get_segment_range(segment_count):
    """Get min and max segments based on segment count setting."""
    if segment_count == "few":
        return random.randint(3, 7)
    elif segment_count == "some":
        return random.randint(6, 12)
    elif segment_count == "lots":
        return random.randint(10, 25)
    else:
        # Default to "some" if invalid value provided
        return random.randint(6, 12)

def test_filter_string(filter_string):
    """
    Test if a filter string is valid before using it in FFmpeg.
    Returns True if valid, False if invalid.
    """
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_in:
        test_input = temp_in.name

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_out:
        test_output = temp_out.name

    # Create a slightly longer test video (2 seconds)
    cmd1 = [
        'ffmpeg',
        '-y',
        '-f', 'lavfi',
        '-i', 'color=c=black:s=10x10:d=2',
        test_input
    ]
    try:
        subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        print("Failed to create test video")
        return False

    cmd2 = [
        'ffmpeg',
        '-y',
        '-i', test_input,
        '-vf', filter_string,
        '-t', '0.1',
        '-f', 'null',
        '-'
    ]

    print("Testing with command:", ' '.join(cmd2))
    try:
        result = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
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
    """
    Generate and test multiple filter strings with various parameters
    to find ones that work reliably with FFmpeg.
    """
    test_results = []

    # Base components for filter strings
    base_scale_h = 'scale=2*iw:-1'
    base_scale_v = 'scale=-1:2*ih'
    base_crop_h = 'crop=iw/2:ih'
    base_crop_v = 'crop=iw:ih/2'
    fps_str = 'fps=30'
    duration_str = 'd=30'

    # Test all pan directions with basic parameters
    for direction in list(PanDirection):
        # Try ultra simple version first with basic expressions
        if direction == PanDirection.LEFT_TO_RIGHT:
            filter_parts = [
                base_scale_h,
                base_crop_h,
                'select=1',
                'zoompan=x=0:y=0:z=1:fps=30:d=90'
            ]
            filter_string = ','.join(filter_parts)
        elif direction == PanDirection.RIGHT_TO_LEFT:
            filter_parts = [
                base_scale_h,
                base_crop_h,
                'select=1',
                'zoompan=x=iw/2:y=0:z=1:fps=30:d=90'
            ]
            filter_string = ','.join(filter_parts)
        elif direction == PanDirection.TOP_TO_BOTTOM:
            filter_parts = [
                base_scale_v,
                base_crop_v,
                'select=1',
                'zoompan=x=0:y=0:z=1:fps=30:d=90'
            ]
            filter_string = ','.join(filter_parts)
        elif direction == PanDirection.BOTTOM_TO_TOP:
            filter_parts = [
                base_scale_v,
                base_crop_v,
                'select=1',
                'zoompan=x=0:y=ih/2:z=1:fps=30:d=90'
            ]
            filter_string = ','.join(filter_parts)
        elif direction == PanDirection.ZOOM_IN:
            filter_parts = [
                'select=1',
                'zoompan=x=iw/4:y=ih/4:z=2:fps=30:d=90'
            ]
            filter_string = ','.join(filter_parts)
        elif direction == PanDirection.ZOOM_OUT:
            filter_parts = [
                'select=1',
                'zoompan=x=0:y=0:z=0.5:fps=30:d=90'
            ]
            filter_string = ','.join(filter_parts)
        else:
            filter_string = 'scale=1.2*iw:-1,crop=iw/1.2:ih/1.2'

        success = test_filter_string(filter_string)
        test_results.append({
            'direction': direction.value,
            'filter_string': filter_string,
            'success': success
        })

        if not success:
            # Try even simpler version with minimal expressions
            if direction == PanDirection.LEFT_TO_RIGHT:
                simpler_filter = f'{base_scale_h},{base_crop_h}'
            elif direction == PanDirection.RIGHT_TO_LEFT:
                simpler_filter = f'{base_scale_h},{base_crop_h}'
            elif direction == PanDirection.TOP_TO_BOTTOM:
                simpler_filter = f'{base_scale_v},{base_crop_v}'
            elif direction == PanDirection.BOTTOM_TO_TOP:
                simpler_filter = f'{base_scale_v},{base_crop_v}'
            elif direction == PanDirection.ZOOM_IN:
                simpler_filter = 'scale=2*iw:-1,crop=iw/2:ih/2'
            elif direction == PanDirection.ZOOM_OUT:
                simpler_filter = 'scale=2*iw:-1,crop=iw/2:ih/2'
            else:
                simpler_filter = 'scale=1.2*iw:-1,crop=iw/1.2:ih/1.2'

            retry_success = test_filter_string(simpler_filter)
            test_results.append({
                'direction': f"{direction.value}_simpler",
                'filter_string': simpler_filter,
                'success': retry_success
            })

    # Print results
    print("\nFILTER TEST RESULTS:")
    print("====================")
    for result in test_results:
        status = "✓ WORKS" if result['success'] else "✗ FAILS"
        print(f"\n{result['direction']}: {status}")
        print(f"Filter: {result['filter_string']}")

    # Return only working filters
    return [r for r in test_results if r['success']]

def create_reliable_filter(video_path, target_aspect, direction, duration):
    """
    Create a reliable filter string that works with all FFmpeg versions
    using the simplest possible expressions.
    """
    # Get target dimensions from aspect ratio
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]

    # For short segments, skip panning to avoid issues
    if duration < 2.0:
        return determine_scaling_filter(video_path, target_aspect)

    # Base components for filter strings
    fps_str = 'fps=30'
    duration_frames = int(duration * 30)
    duration_str = f'd={duration_frames}'

    # Generate filter based on direction using simple expressions
    if direction == PanDirection.LEFT_TO_RIGHT:
        filter_parts = [
            'scale=2*iw:-1',  # Double width, maintain aspect
            f'crop=iw/2:ih',  # Crop to original width
            'select=1',
            f'zoompan=x=0:y=0:z=1:{fps_str}:{duration_str}',
            f'scale={target_width}:{target_height}'  # Final scaling to target size
        ]
        pan_filter = ','.join(filter_parts)
    elif direction == PanDirection.RIGHT_TO_LEFT:
        filter_parts = [
            'scale=2*iw:-1',
            f'crop=iw/2:ih',
            'select=1',
            f'zoompan=x=iw/2:y=0:z=1:{fps_str}:{duration_str}',
            f'scale={target_width}:{target_height}'
        ]
        pan_filter = ','.join(filter_parts)
    elif direction == PanDirection.TOP_TO_BOTTOM:
        filter_parts = [
            'scale=-1:2*ih',  # Double height, maintain aspect
            f'crop=iw:ih/2',  # Crop to original height
            'select=1',
            f'zoompan=x=0:y=0:z=1:{fps_str}:{duration_str}',
            f'scale={target_width}:{target_height}'
        ]
        pan_filter = ','.join(filter_parts)
    elif direction == PanDirection.BOTTOM_TO_TOP:
        filter_parts = [
            'scale=-1:2*ih',
            f'crop=iw:ih/2',
            'select=1',
            f'zoompan=x=0:y=ih/2:z=1:{fps_str}:{duration_str}',
            f'scale={target_width}:{target_height}'
        ]
        pan_filter = ','.join(filter_parts)
    elif direction == PanDirection.ZOOM_IN:
        filter_parts = [
            'select=1',
            f'zoompan=x=iw/4:y=ih/4:z=2:{fps_str}:{duration_str}',
            f'scale={target_width}:{target_height}'
        ]
        pan_filter = ','.join(filter_parts)
    elif direction == PanDirection.ZOOM_OUT:
        filter_parts = [
            'select=1',
            f'zoompan=x=0:y=0:z=0.5:{fps_str}:{duration_str}',
            f'scale={target_width}:{target_height}'
        ]
        pan_filter = ','.join(filter_parts)
    else:
        # Default to no panning, just scale to target size
        pan_filter = f'scale={target_width}:{target_height}'

    return pan_filter

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
        if current_length + len(word) + (1 if current_length > 0 else 0) <= max_chars_per_line:
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
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
    
    # Add the last line if there is one
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def calculate_text_layout(text, target_aspect, base_size, margin_percent=20, min_font_size=36):
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

def create_text_overlay_filter(video_duration, text_array=None, display_duration=5, gap_duration=3, style="default", target_aspect="vertical_portrait"):
    """
    Create FFmpeg filter complex string for text overlays with enhanced effects.
    Now includes margin handling, dynamic font sizing, and multi-line text support.
    """
    if text_array is None:
        text_array = ['@Suite.E.Studios']
    
    fade_duration = 2  # Fixed 2-second fade in/out
    margin_percent = 20  # 20% total margins (10% each side)
    
    # Get target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]
    
    # Calculate margins
    h_margin = int(target_width * (margin_percent / 200))
    
    # Style-specific base font sizes (reduced by 20%)
    if style == "pulse":
        base_fontsize = 58  # was 72
        y_pos_base = "h*0.85"
        min_font_size = 29  # was 36
    elif style == "concert":
        base_fontsize = 77  # was 96
        y_pos_base = "h*0.5"
        min_font_size = 38  # was 48
    elif style == "promo":
        base_fontsize = 38  # was 48
        y_pos_base = "h*0.9"
        min_font_size = 29  # was 36
    else:
        base_fontsize = 58  # was 72
        y_pos_base = "h*0.85"
        min_font_size = 29  # was 36
    
    filter_parts = []
    current_time = 0
    
    for text in text_array:
        # Skip if we've exceeded video duration
        if current_time >= video_duration:
            break
        
        # Calculate timing
        start_time = current_time
        full_opacity_start = start_time + fade_duration
        full_opacity_end = min(full_opacity_start + display_duration, video_duration)
        end_time = min(full_opacity_end + fade_duration, video_duration)
        
        # Calculate font size and wrap text
        font_size, wrapped_lines, line_spacing = calculate_text_layout(
            text, target_aspect, base_fontsize, margin_percent, min_font_size
        )
        
        # Calculate vertical position adjustment for multiple lines
        total_height = len(wrapped_lines) * line_spacing
        if style == "concert":
            y_start = f"(h-{total_height})/2"  # Center all lines vertically
        else:
            # Adjust base position up by half the height of additional lines
            y_start = f"{y_pos_base}-{(len(wrapped_lines)-1)*line_spacing}/2"
        
        # Create a filter for each line of text
        for i, line in enumerate(wrapped_lines):
            # Properly escape the text for FFmpeg
            escaped_text = line.replace("'", "'\\\\''")  # Escape single quotes
            escaped_text = escaped_text.encode('unicode-escape').decode()  # Handle emoji and special chars
            
            # Calculate y position for this line
            y_pos = f"{y_start}+{i*line_spacing}"
            
            # For pulsing effect, adjust the size variation based on the calculated font size
            if style == "pulse":
                size_variation = font_size * 0.1  # 10% size variation
                size_expr = f"{font_size}+{size_variation}*sin(2*PI*t/1.5)"
            else:
                size_expr = str(font_size)
            
            # Build the filter string with proper escaping
            filter_parts.append(
                f"drawtext="
                f"text='{escaped_text}':"
                f"fontsize={size_expr}:"
                f"fontcolor=white:"
                f"fontfile=Arial:"
                f"borderw=3:"
                f"bordercolor=black:"
                f"x=if(gte(tw\\,{target_width-2*h_margin})\\,{h_margin}\\,max({h_margin}\\,(w-tw)/2)):"
                f"y={y_pos}:"
                f"enable=between(t\\,{start_time}\\,{end_time}):"
                f"alpha=if(lt(t\\,{full_opacity_start})\\,(t-{start_time})/{fade_duration}\\,"
                f"if(gt(t\\,{full_opacity_end})\\,1-(t-{full_opacity_end})/{fade_duration}\\,1))"
            )
            
            # Add glow effect for concert style
            if style == "concert":
                filter_parts[-1] += ":shadowcolor=black@0.5:shadowx=2:shadowy=2"
        
        # Update time for next text
        current_time = end_time + gap_duration
    
    # Join all filter parts with commas
    if not filter_parts:
        return ""
    
    return ','.join(filter_parts)

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
            result = subprocess.run(['sysctl', 'machdep.cpu.brand_string'], 
                                 capture_output=True, text=True)
            if 'Apple' in result.stdout:
                # M1/M2 optimization
                return 'h264_videotoolbox', None, thread_count
            # For Intel Macs with VideoToolbox
            return 'h264_videotoolbox', None, thread_count
        except:
            return None, None, thread_count
    
    # Check for NVIDIA GPU
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            # Get GPU memory info
            memory_info = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
                capture_output=True, text=True
            )
            gpu_memory = int(memory_info.stdout.strip())
            # Enable parallel processing if GPU has enough memory (>8GB)
            parallel_streams = min(3, gpu_memory // 4000) if gpu_memory > 8000 else 1
            return 'h264_nvenc', None, parallel_streams
    except:
        pass
    
    return None, None, thread_count

def create_ffmpeg_command(input_file, output_file, vf_filter, duration=None, hw_encoder=None, thread_count=4):
    """
    Create an FFmpeg command with hardware acceleration if available.
    """
    cmd = ['ffmpeg', '-y']
    
    # System-specific optimizations
    if hw_encoder == 'h264_videotoolbox':
        # M1/M2 optimizations
        cmd.extend([
            '-threads', str(thread_count),
            '-filter_threads', str(thread_count),
            '-filter_complex_threads', str(thread_count)
        ])
    elif hw_encoder == 'h264_nvenc':
        # NVIDIA optimizations
        cmd.extend([
            '-threads', str(thread_count),
            '-extra_hw_frames', '3',  # Buffer for hardware frames
            '-gpu_init_delay', '0.1'  # Faster GPU initialization
        ])
    else:
        # CPU optimizations
        cmd.extend([
            '-threads', str(thread_count),
            '-filter_threads', str(thread_count),
            '-filter_complex_threads', str(thread_count)
        ])
    
    # Input file
    if hw_encoder in ['h264_qsv', 'h264_nvenc']:
        cmd.extend(['-hwaccel', 'auto'])
    cmd.extend(['-i', input_file])
    
    # Add duration limit if specified
    if duration:
        cmd.extend(['-t', str(duration)])
    
    # Video filter
    cmd.extend(['-vf', vf_filter])
    
    # Video codec settings
    if hw_encoder:
        cmd.extend(['-c:v', hw_encoder])
        
        if hw_encoder == 'h264_nvenc':
            cmd.extend([
                '-preset', 'p4',          # Highest quality preset
                '-rc', 'vbr',            # Variable bitrate
                '-cq', '20',             # Quality-based VBR
                '-b:v', '10M',           # Higher bitrate for better quality
                '-maxrate', '15M',       # Maximum bitrate
                '-bufsize', '15M',       # Buffer size
                '-spatial-aq', '1',      # Spatial adaptive quantization
                '-temporal-aq', '1'      # Temporal adaptive quantization
            ])
        elif hw_encoder == 'h264_videotoolbox':
            cmd.extend([
                '-b:v', '10M',           # Higher bitrate for M2 Max
                '-maxrate', '15M',       # Maximum bitrate
                '-bufsize', '15M',       # Buffer size
                '-tag:v', 'avc1',        # Ensure compatibility
                '-movflags', '+faststart' # Optimize for streaming
            ])
    else:
        # Fallback to CPU encoding with good quality settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23'
        ])
    
    # Audio codec
    cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
    
    # Output file
    cmd.append(output_file)
    
    return cmd

def process_intro_segment(intro_video_path, target_aspect, temp_dir):
    """Process the intro video segment with proper scaling and formatting."""
    if not intro_video_path or not os.path.exists(intro_video_path):
        return None
        
    intro_segment_file = os.path.join(temp_dir, "intro_segment.mp4")
    
    # Get the scaling filter for the intro video
    scaling_filter = determine_scaling_filter(intro_video_path, target_aspect)
    
    # Detect hardware encoder
    hw_encoder, _, _ = detect_hardware_encoders()
    
    # Create FFmpeg command with hardware acceleration
    cmd = create_ffmpeg_command(
        input_file=intro_video_path,
        output_file=intro_segment_file,
        vf_filter=scaling_filter,
        hw_encoder=hw_encoder
    )
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    if result.returncode != 0 or not os.path.exists(intro_segment_file):
        print(f"Warning: Failed to process intro video: {result.stderr}")
        return None
        
    return intro_segment_file

def create_concat_file(segment_files, temp_dir):
    """Create a concatenated video file from segment files."""
    # Create a file with list of segments for FFmpeg concat
    concat_file = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_file, 'w') as f:
        for segment_file in segment_files:
            f.write(f"file '{segment_file}'\n")
    
    # Concatenate all segments
    temp_output = os.path.join(temp_dir, "temp_output.mp4")
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c:v', 'copy',  # Copy video stream
        '-c:a', 'aac',   # Convert audio to AAC
        '-b:a', '192k',  # Set audio bitrate
        temp_output
    ]
    print(f"Creating intermediate file: {temp_output}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
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
        with open(concat_file, 'r') as f:
            print(f.read())
        return None
    
    return temp_output

def fallback_create_output(segment_files, output_path, video_duration, target_aspect):
    """Fallback method: Create output video by directly encoding all segments into one file."""
    print("Using fallback method to create video...")
    
    # Set target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]
    
    # Generate a complex filtergraph to chain all segments together
    filter_complex = []
    inputs = []
    
    for i, segment_file in enumerate(segment_files):
        inputs.extend(['-i', segment_file])
        filter_complex.append(f"[{i}:v]scale={target_width}:{target_height}[v{i}]")
    
    # Concatenate all video streams
    vid_concat = ';'.join(filter_complex) + ";" + ''.join([f"[v{i}]" for i in range(len(segment_files))]) + f"concat=n={len(segment_files)}:v=1:a=0[outv]"
    
    # Add text overlay
    text_filter = create_text_overlay_filter(video_duration)
    vid_concat += f";[outv]{text_filter}[out]"
    
    # Build the full command
    cmd = ['ffmpeg', '-y']
    cmd.extend(inputs)
    cmd.extend([
        '-filter_complex', vid_concat,
        '-map', '[out]',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-t', str(video_duration),
        output_path
    ])
    
    print("Executing fallback FFmpeg command...")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    if result.returncode != 0:
        print("FFmpeg Error in fallback method:")
        print(result.stderr)
        raise Exception("Both regular and fallback methods failed to create output video")
    
    if not os.path.exists(output_path):
        raise Exception("Fallback method didn't create output file")

def parse_input_string(input_string):
    """Parse input string to extract video name, format, and input videos."""
    parts = input_string.strip().split(',')
    if len(parts) < 3:
        print("Error: Input string must contain at least: output name, format, and one input video")
        return None, None, None
    
    output_name = parts[0].strip()
    
    # Validate format
    format_name = parts[1].strip().lower()
    if format_name not in ASPECT_RATIOS:
        print(f"Error: Format '{format_name}' not supported. Choose from: {', '.join(ASPECT_RATIOS.keys())}")
        return output_name, None, None
    
    # Get input videos
    input_videos = [video.strip() for video in parts[2:]]
    
    return output_name, format_name, input_videos

def create_video_segment(video_path, start_time, segment_duration, output_file, target_aspect, direction):
    """
    Create a single video segment with reliable panning effect.
    
    Args:
        video_path: Input video path
        start_time: Start time in seconds
        segment_duration: Duration of segment in seconds
        output_file: Output file path
        target_aspect: Target aspect ratio
        direction: PanDirection enum value
    """
    # Create a very simple and reliable filter
    filter_string = create_reliable_filter(video_path, target_aspect, direction, segment_duration)
    
    # Extract segment using FFmpeg with the reliable filter
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output files
        '-i', video_path,
        '-ss', str(start_time),
        '-t', str(segment_duration),
        '-vf', filter_string,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        output_file
    ]
    
    # Debug info
    print(f"Creating segment from {video_path}")
    print(f"Filter string: {filter_string}")
    print(f"FFmpeg command: {' '.join(cmd)}")
    
    # Run FFmpeg
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    # Check for errors
    if result.returncode != 0:
        print(f"Error creating segment with panning effect:")
        print(result.stderr)
        
        # If panning fails, try with just basic scaling (fallback)
        basic_filter = determine_scaling_filter(video_path, target_aspect)
        fallback_cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(segment_duration),
            '-vf', basic_filter,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            output_file
        ]
        
        print(f"Retrying with basic scaling: {basic_filter}")
        fallback_result = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        # If fallback also fails, print error
        if fallback_result.returncode != 0:
            print(f"Fallback also failed:")
            print(fallback_result.stderr)
            return False
    
    # Check if file was created successfully
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        return True
    else:
        print(f"Warning: Segment file not created or empty: {output_file}")
        return False
    
def create_video_montage(video_paths, output_duration, output_path, target_aspect="vertical_portrait", 
                         enable_panning=True, pan_strategy="random", pan_speed=1.0, 
                         pan_distance=0.2, easing_type=EasingType.EASE_IN_OUT, segment_count="some",
                         text_array=None, text_display_duration=5, text_gap_duration=3,
                         text_style="default", intro_video=None, intro_audio=None,
                         intro_audio_duration=5.0, intro_audio_volume=2.0):
    """Create a montage video with hardware acceleration if available."""
    
    # Detect available hardware encoder
    hw_encoder, _, thread_count = detect_hardware_encoders()
    if hw_encoder:
        print(f"Using hardware encoder: {hw_encoder} with {thread_count} threads")
        if hw_encoder == 'h264_videotoolbox':
            print("Optimized for Apple Silicon")
        elif hw_encoder == 'h264_nvenc':
            print("Optimized for NVIDIA GPU")
    else:
        print(f"Using CPU encoding (libx264) with {thread_count} threads")
    
    segments_to_use = []
    
    # Calculate number of segments based on segment_count setting
    num_segments_needed = get_segment_range(segment_count)
    print(f"Creating {num_segments_needed} segments...")
    
    # Calculate segment duration to match output duration
    total_segments = num_segments_needed
    if intro_video:
        intro_duration = get_video_duration(intro_video)
        remaining_duration = max(0, output_duration - intro_duration)
        segment_duration = remaining_duration / num_segments_needed
    else:
        segment_duration = output_duration / num_segments_needed
    
    print(f"Each segment will be approximately {segment_duration:.2f} seconds")
    
    # Extract segments from each video
    for video_path in video_paths:
        duration = get_video_duration(video_path)
        segments = extract_interesting_segments(video_path, num_segments_needed * 2, segment_duration)  # Get more segments than needed
        
        # Add segments with their timestamps
        for start_time, seg_duration in segments:
            segments_to_use.append((video_path, start_time, min(seg_duration, segment_duration)))
    
    # Shuffle and limit to what we need
    random.shuffle(segments_to_use)
    if len(segments_to_use) > num_segments_needed:
        segments_to_use = segments_to_use[:num_segments_needed]
    
    # Create temporary directory for segment files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        segment_files = []
        
        # Process intro video if provided
        intro_segment = None
        if intro_video:
            intro_segment = process_intro_segment(intro_video, target_aspect, temp_dir)
            if intro_segment:
                segment_files.append(intro_segment)
                print(f"Added intro video segment: {get_video_duration(intro_segment):.2f} seconds")
        
        # Extract regular segments to temporary files
        for i, (video_path, start_time, segment_duration) in enumerate(segments_to_use):
            segment_file = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
            
            # Get basic scaling filter
            scaling_filter = determine_scaling_filter(video_path, target_aspect)
            
            # Add panning if enabled
            if enable_panning:
                try:
                    if pan_strategy == "random":
                        pan_direction = random.choice(list(PanDirection))
                    elif pan_strategy == "sequence":
                        pan_direction = list(PanDirection)[i % len(list(PanDirection))]
                    elif isinstance(pan_strategy, PanDirection):
                        pan_direction = pan_strategy
                    else:
                        pan_direction = random.choice(list(PanDirection))
                    
                    filter_string = create_reliable_filter(video_path, target_aspect, pan_direction, segment_duration)
                except Exception as e:
                    print(f"Warning: Failed to generate panning filter: {e}")
                    filter_string = scaling_filter
            else:
                filter_string = scaling_filter
            
            # Create FFmpeg command with hardware acceleration
            cmd = create_ffmpeg_command(
                input_file=video_path,
                output_file=segment_file,
                vf_filter=filter_string,
                duration=segment_duration,
                hw_encoder=hw_encoder,
                thread_count=thread_count
            )
            
            print(f"Creating segment {i+1}/{len(segments_to_use)}: {segment_file}")
            print(f"Duration: {segment_duration:.2f} seconds")
            print(f"Filter: {filter_string}")
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            if result.returncode == 0 and os.path.exists(segment_file) and os.path.getsize(segment_file) > 0:
                actual_duration = get_video_duration(segment_file)
                print(f"Segment created successfully. Duration: {actual_duration:.2f} seconds")
                segment_files.append(segment_file)
            else:
                print(f"Warning: Failed to create segment: {result.stderr}")
        
        if not segment_files:
            raise Exception("No valid segments were created. Cannot create montage.")
        
        try:
            # Create concat file
            temp_output = create_concat_file(segment_files, temp_dir)
            
            if temp_output:
                # Add text overlay
                text_filter = create_text_overlay_filter(
                    video_duration=output_duration,
                    text_array=text_array,
                    display_duration=text_display_duration,
                    gap_duration=text_gap_duration,
                    style=text_style,
                    target_aspect=target_aspect
                )
                
                # Set target dimensions
                target_width = ASPECT_RATIOS[target_aspect]["width"]
                target_height = ASPECT_RATIOS[target_aspect]["height"]
                
                # Prepare final FFmpeg command
                filter_complex = []
                inputs = ['-i', temp_output]  # Main video input
                
                # Add intro audio if provided
                if intro_audio and os.path.exists(intro_audio):
                    inputs.extend(['-i', intro_audio])
                    
                    # Create complex filter for audio mixing
                    filter_complex.extend([
                        # Original audio with volume adjustment after intro
                        f"[0:a]volume=enable='gte(t,{intro_audio_duration})':"
                        f"volume='min(1,(t-{intro_audio_duration})/2)'[main_audio]",
                        
                        # Intro audio with fade out
                        f"[1:a]volume={intro_audio_volume}:"
                        f"enable='lte(t,{intro_audio_duration+2})':"
                        f"volume='max(0,1-(t-{intro_audio_duration})/2)'[intro_audio]",
                        
                        # Mix both audio streams
                        "[main_audio][intro_audio]amix=inputs=2:duration=longest[aout]"
                    ])
                
                # Add video filters
                if text_filter:
                    filter_complex.append(f"[0:v]{text_filter}[vout]")
                
                # Build the final FFmpeg command
                cmd = ['ffmpeg', '-y']
                cmd.extend(inputs)
                
                if filter_complex:
                    cmd.extend(['-filter_complex', ';'.join(filter_complex)])
                    if text_filter:
                        cmd.extend(['-map', '[vout]'])
                    if intro_audio:
                        cmd.extend(['-map', '[aout]'])
                    else:
                        cmd.extend(['-map', '0:a'])  # Map original audio if no intro audio
                else:
                    cmd.extend(['-map', '0:v', '-map', '0:a'])  # Map both video and audio
                
                cmd.extend([
                    '-s', f"{target_width}x{target_height}",
                    output_path
                ])
                
                print(f"Executing final FFmpeg command to create: {output_path}")
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                
                if result.returncode != 0:
                    print("FFmpeg Error:")
                    print(result.stderr)
                    raise Exception(f"FFmpeg failed with return code {result.returncode}")
                
            else:
                # Fallback to direct encoding if concat fails
                fallback_create_output(segment_files, output_path, output_duration, target_aspect)
                
        except Exception as e:
            print(f"Error during montage creation: {e}")
            print("Trying direct encoding fallback method...")
            fallback_create_output(segment_files, output_path, output_duration, target_aspect)

def main():
    parser = argparse.ArgumentParser(description='Create an exciting video montage from input videos for social media.')
    parser.add_argument('--input-string', '-i', help='Input string in format: "output_name, format, video1, video2, ..."')
    parser.add_argument('--output', '-o', required=True, help='Output video file')
    parser.add_argument('--format', '-f', required=True, choices=['vertical_portrait', 'instagram_square'], 
                       help='Output video format/aspect ratio')
    parser.add_argument('--duration', '-d', type=int, choices=[30, 60, 90], default=60,
                       help='Output video duration in seconds (30, 60, or 90)')
    parser.add_argument('--segments', choices=['few', 'some', 'lots'], default='some',
                       help='Number of segments to create (few=3-7, some=6-12, lots=10-25)')
    parser.add_argument('--panning', action='store_true', help='Enable panning effects')
    parser.add_argument('--pan-strategy', choices=[d.value for d in PanDirection] + ['random', 'sequence'], default='random',
                       help='Panning strategy: specific direction, random, or sequence')
    parser.add_argument('--pan-speed', type=float, default=1.0, help='Panning speed factor (default: 1.0)')
    parser.add_argument('--pan-distance', type=float, default=0.2, help='Panning distance as percentage of frame (0.0-1.0)')
    parser.add_argument('--easing', choices=[e.value for e in EasingType], default=EasingType.EASE_IN_OUT.value,
                       help='Easing function for smooth panning')
    parser.add_argument('--intro-video', help='Video to play at the start before random segments')
    parser.add_argument('--intro-audio', help='Audio file to play at the start (will fade into video audio)')
    parser.add_argument('--intro-audio-duration', type=float, default=5.0,
                       help='Duration of intro audio in seconds (default: 5.0)')
    parser.add_argument('--intro-audio-volume', type=float, default=2.0,
                       help='Volume multiplier for intro audio (default: 2.0)')
    parser.add_argument('--text', nargs='+', help='Array of text strings to display')
    parser.add_argument('--text-duration', type=int, default=5,
                       help='Duration to display each text (in seconds)')
    parser.add_argument('--text-gap', type=int, default=3,
                       help='Gap between displaying texts (in seconds)')
    parser.add_argument('--text-style', choices=['default', 'pulse', 'concert', 'promo'], default='default',
                       help='Style of text overlay (default, pulse, concert, promo)')
    parser.add_argument('input_video', nargs='?', help='Input video file')

    args = parser.parse_args()
    
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
    print(f"Creating a {args.duration}-second {ASPECT_RATIOS[args.format]['description']} montage from {len(all_videos)} video(s)...")
    
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
            print("Warning: No working pan filters found. Will use static filters only.")
            enable_panning = False
        else:
            print(f"Found {len(working_filters)} working filter configurations.")
            
        create_video_montage(
            all_videos, 
            args.duration, 
            args.output, 
            args.format,
            enable_panning=args.panning,
            pan_strategy=pan_strategy,
            pan_speed=args.pan_speed,
            pan_distance=args.pan_distance,
            easing_type=easing_type,
            segment_count=args.segments,
            text_array=args.text,
            text_display_duration=args.text_duration,
            text_gap_duration=args.text_gap,
            text_style=args.text_style,
            intro_video=args.intro_video,
            intro_audio=args.intro_audio,
            intro_audio_duration=args.intro_audio_duration,
            intro_audio_volume=args.intro_audio_volume
        )
        abs_output_path = os.path.abspath(args.output)
        
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
