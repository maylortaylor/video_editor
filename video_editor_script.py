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
    "instagram_reel": {"width": 1080, "height": 1920, "description": "Instagram Reel (9:16)"},
    "tiktok": {"width": 1080, "height": 1920, "description": "TikTok (9:16)"},
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
            # First scale to match target height, then crop width
            scale_height = target_height
            scale_width = int(scale_height * video_aspect)
            crop_x = (scale_width - target_width) // 2
            return f"scale={scale_width}:{scale_height},crop={target_width}:{target_height}:{crop_x}:0"
        else:  # Input is already portrait/vertical or square
            # Scale to match target width, then crop height if needed
            scale_width = target_width
            scale_height = int(scale_width / video_aspect)
            if scale_height < target_height:
                # If scaled height is smaller, scale to target height instead
                scale_height = target_height
                scale_width = int(scale_height * video_aspect)
                crop_x = (scale_width - target_width) // 2
                return f"scale={scale_width}:{scale_height},crop={target_width}:{target_height}:{crop_x}:0"
            else:
                crop_y = (scale_height - target_height) // 2
                return f"scale={scale_width}:{scale_height},crop={target_width}:{target_height}:0:{crop_y}"
    
    # For square videos (Instagram Square)
    else:  # Target is square (1:1)
        if video_aspect > 1:  # Input is landscape
            # Scale to target height, then crop width to make square
            scale_height = target_height
            scale_width = int(scale_height * video_aspect)
            crop_x = (scale_width - target_height) // 2
            return f"scale={scale_width}:{scale_height},crop={target_height}:{target_height}:{crop_x}:0"
        else:  # Input is portrait/vertical
            # Scale to target width, then crop height to make square
            scale_width = target_width
            scale_height = int(scale_width / video_aspect)
            crop_y = (scale_height - target_width) // 2
            return f"scale={scale_width}:{scale_height},crop={target_width}:{target_width}:0:{crop_y}"

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
        return f"scale={zoom_factor}*iw:-1,zoompan=z=1:x='iw*{pan_distance}*(n/{frames})':y=0:fps={fps}:d={frames}"
    elif direction == PanDirection.RIGHT_TO_LEFT:
        return f"scale={zoom_factor}*iw:-1,zoompan=z=1:x='iw*{pan_distance}*(1-(n/{frames}))':y=0:fps={fps}:d={frames}"
    elif direction == PanDirection.TOP_TO_BOTTOM:
        return f"scale={zoom_factor}*iw:-1,zoompan=z=1:x=0:y='ih*{pan_distance}*(n/{frames})':fps={fps}:d={frames}"
    elif direction == PanDirection.BOTTOM_TO_TOP:
        return f"scale={zoom_factor}*iw:-1,zoompan=z=1:x=0:y='ih*{pan_distance}*(1-(n/{frames}))':fps={fps}:d={frames}"
    elif direction == PanDirection.ZOOM_IN:
        return f"scale={zoom_factor}*iw:-1,zoompan=z='1+{pan_distance}*(n/{frames})':x='(iw-iw/z)/2':y='(ih-ih/z)/2':fps={fps}:d={frames}"
    elif direction == PanDirection.ZOOM_OUT:
        return f"scale={zoom_factor}*iw:-1,zoompan=z='1+{pan_distance}*(1-(n/{frames}))':x='(iw-iw/z)/2':y='(ih-ih/z)/2':fps={fps}:d={frames}"
    else:
        return f"scale={zoom_factor}*iw:-1,crop=iw/{zoom_factor}:ih/{zoom_factor}"


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

def extract_interesting_segments(video_path, num_segments=10, min_segment_duration=2):
    """Extract timestamps of potentially interesting segments from a video."""
    duration = get_video_duration(video_path)
    
    # For simplicity, we'll just divide the video into equal parts
    # In a real implementation, you might use scene detection or audio level analysis
    segment_duration = max(min_segment_duration, duration / (num_segments * 2))
    possible_start_times = [i * (duration / num_segments) for i in range(num_segments)]
    
    segments = []
    for start_time in possible_start_times:
        # Ensure we don't go beyond the video duration
        if start_time + segment_duration <= duration:
            segments.append((start_time, segment_duration))
    
    # Shuffle to get a random selection
    random.shuffle(segments)
    return segments

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
    test_duration = 6.0
    test_results = []

    # Test all pan directions with basic parameters
    for direction in list(PanDirection):
        # Try ultra simple version first
        filter_string = generate_ultra_simple_pan_filter(
            direction, test_duration, pan_speed=1.0, pan_distance=0.2)

        success = test_filter_string(filter_string)
        test_results.append({
            'direction': direction.value,
            'filter_string': filter_string,
            'success': success
        })

        if not success:
            # Try even simpler version with corrected parentheses and double quotes
            if direction == PanDirection.LEFT_TO_RIGHT:
                simpler_filter = 'scale=1.2*iw:-1,zoompan=z=1:x="(0.2*iw)*(n/180)":y=0:fps=30:d=181'
            elif direction == PanDirection.RIGHT_TO_LEFT:
                simpler_filter = 'scale=1.2*iw:-1,zoompan=z=1:x="(0.2*iw)*(1-(n/180))":y=0:fps=30:d=181'
            elif direction == PanDirection.TOP_TO_BOTTOM:
                simpler_filter = 'scale=1.2*iw:-1,zoompan=z=1:x=0:y="(0.2*ih)*(n/180)":fps=30:d=181'
            elif direction == PanDirection.BOTTOM_TO_TOP:
                simpler_filter = 'scale=1.2*iw:-1,zoompan=z=1:x=0:y="(0.2*ih)*(1-(n/180))":fps=30:d=181'
            elif direction == PanDirection.ZOOM_IN:
                simpler_filter = 'scale=1.2*iw:-1,zoompan=z="1+0.2*(n/180)":x="(iw-iw/z)/2":y="(ih-ih/z)/2":fps=30:d=181'
            elif direction == PanDirection.ZOOM_OUT:
                simpler_filter = 'scale=1.2*iw:-1,zoompan=z="1+0.2*(1-(n/180))":x="(iw-iw/z)/2":y="(ih-ih/z)/2":fps=30:d=181'
            else:
                simpler_filter = "scale=1.2*iw:-1,crop=iw/1.2:ih/1.2"

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
    and avoids complex expressions that could cause parsing errors.

    Args:
        video_path: Path to the input video
        target_aspect: Target aspect ratio (instagram_reel, tiktok, instagram_square)
        direction: PanDirection enum specifying the panning direction
        duration: Duration of the segment in seconds

    Returns:
        A filter string that can be passed to FFmpeg
    """
    # Get the basic scaling/cropping filter for the target aspect ratio
    basic_scaling = determine_scaling_filter(video_path, target_aspect)

    # For short segments, skip panning to avoid issues
    if duration < 2.0:
        return basic_scaling

    # Calculate frames and basic parameters
    fps = 30
    frames = int(duration * fps)
    pan_distance = 0.2  # Keep this fairly small to avoid extreme panning
    zoom_factor = 1.2   # Fixed zoom factor for simplicity

    # Generate filter based on direction - using extremely simple expressions with double quotes
    if direction == PanDirection.LEFT_TO_RIGHT:
        pan_filter = f"scale={zoom_factor}*iw:-1,zoompan=z=1:x=\"(0.2*iw)*(n/{frames})\":y=0:fps={fps}:d={frames}"
    elif direction == PanDirection.RIGHT_TO_LEFT:
        pan_filter = f"scale={zoom_factor}*iw:-1,zoompan=z=1:x=\"(0.2*iw)*(1-(n/{frames}))\":y=0:fps={fps}:d={frames}"
    elif direction == PanDirection.TOP_TO_BOTTOM:
        pan_filter = f"scale={zoom_factor}*iw:-1,zoompan=z=1:x=0:y=\"(0.2*ih)*(n/{frames})\":fps={fps}:d={frames}"
    elif direction == PanDirection.BOTTOM_TO_TOP:
        pan_filter = f"scale={zoom_factor}*iw:-1,zoompan=z=1:x=0:y=\"(0.2*ih)*(1-(n/{frames}))\":fps={fps}:d={frames}"
    elif direction == PanDirection.ZOOM_IN:
        pan_filter = f"scale={zoom_factor}*iw:-1,zoompan=z=\"1+0.2*(n/{frames})\":x=\"(iw-iw/z)/2\":y=\"(ih-ih/z)/2\":fps={fps}:d={frames}"
    elif direction == PanDirection.ZOOM_OUT:
        pan_filter = f"scale={zoom_factor}*iw:-1,zoompan=z=\"1+0.2*(1-(n/{frames}))\":x=\"(iw-iw/z)/2\":y=\"(ih-ih/z)/2\":fps={fps}:d={frames}"
    else:
        # Default to no panning
        pan_filter = f"scale={zoom_factor}*iw:-1,crop=iw/{zoom_factor}:ih/{zoom_factor}"

    # Add the basic scaling/cropping after the pan effect
    # The comma here chains the filters
    full_filter = pan_filter + "," + basic_scaling.split(',', 1)[1] if ',' in basic_scaling else basic_scaling

    return full_filter

def create_video_montage(video_paths, output_duration, output_path, target_aspect="instagram_reel", 
                         enable_panning=True, pan_strategy="random", pan_speed=1.0, 
                         pan_distance=0.2, easing_type=EasingType.EASE_IN_OUT):
    """
    Create a montage video from input videos with specified duration and aspect ratio.
    
    Args:
        video_paths: List of input video paths
        output_duration: Desired output duration in seconds
        output_path: Path to save the output video
        target_aspect: Target aspect ratio (instagram_reel, tiktok, instagram_square)
        enable_panning: Whether to enable panning effects
        pan_strategy: How to determine pan direction ("random", "sequence", or specific PanDirection)
        pan_speed: Speed factor for panning (higher = faster)
        pan_distance: The percentage of the frame to pan (0.0-1.0)
        easing_type: The easing function to use for the panning
    """
    segments_to_use = []
    
    # Calculate how many segments we need based on desired output duration
    # Let's aim for segments of about 3-5 seconds
    avg_segment_duration = 4
    num_segments_needed = max(3, int(output_duration / avg_segment_duration))
    
    # Extract segments from each video
    for video_path in video_paths:
        duration = get_video_duration(video_path)
        # More segments from longer videos
        num_segments = max(3, int((duration / 60) * 5))
        segments = extract_interesting_segments(video_path, num_segments)
        
        for start_time, segment_duration in segments:
            segments_to_use.append((video_path, start_time, segment_duration))
    
    # Shuffle and limit to what we need
    random.shuffle(segments_to_use)
    if len(segments_to_use) > num_segments_needed:
        segments_to_use = segments_to_use[:num_segments_needed]
    
    # Create temporary directory for segment files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        segment_files = []
        
        # Define pan directions based on strategy
        pan_directions = list(PanDirection)
        if pan_strategy == "sequence" and enable_panning:
            # Use directions in sequence
            current_pan_idx = 0
        
        # Extract segments to temporary files
        for i, (video_path, start_time, segment_duration) in enumerate(segments_to_use):
            segment_file = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
            
            # Determine scaling filter for this video
            basic_scaling_filter = determine_scaling_filter(video_path, target_aspect)
            
            # If panning is enabled, add the pan filter
            if enable_panning:
                if pan_strategy == "random":
                    # Use a random direction
                    pan_direction = random.choice(pan_directions)
                elif pan_strategy == "sequence":
                    # Use directions in sequence
                    pan_direction = pan_directions[current_pan_idx]
                    current_pan_idx = (current_pan_idx + 1) % len(pan_directions)
                elif isinstance(pan_strategy, PanDirection):
                    # Use the specified direction
                    pan_direction = pan_strategy
                else:
                    # Default to random
                    pan_direction = random.choice(pan_directions)
                
                try:
                    # Use our simplified filter to avoid expression issues
                    # pan_filter = generate_ultra_simple_pan_filter(pan_direction, segment_duration, 
                    #                                     pan_speed, pan_distance, easing_type)
                    # filter_string = pan_filter  # Just use the complete pan filter
                    
                        # If panning is enabled, use the reliable filter generator
                    if enable_panning:
                        if pan_strategy == "random":
                            pan_direction = random.choice(pan_directions)
                        elif pan_strategy == "sequence":
                            pan_direction = pan_directions[current_pan_idx]
                            current_pan_idx = (current_pan_idx + 1) % len(pan_directions)
                        elif isinstance(pan_strategy, PanDirection):
                            pan_direction = pan_strategy
                        else:
                            pan_direction = random.choice(pan_directions)
                        
                        # Use the new reliable filter generator
                        filter_string = create_reliable_filter(video_path, target_aspect, pan_direction, segment_duration)
                    else:
                        # No panning, just use the basic scaling
                        filter_string = basic_scaling_filter
                except Exception as e:
                    print(f"Warning: Failed to generate panning filter: {e}")
                    print("Falling back to static scaling")
                    filter_string = basic_scaling_filter
            else:
                # No panning, just use the basic scaling
                filter_string = basic_scaling_filter
            
            # Extract segment using FFmpeg with proper scaling/cropping
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output files
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(segment_duration),
                '-vf', filter_string,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                segment_file
            ]
            print(f"Creating segment {i+1}/{len(segments_to_use)}: {segment_file}")
            print(f"Filter string: {filter_string}")  # Debug output
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            # Check if segment creation was successful
            if result.returncode != 0:
                print(f"Error creating segment from {video_path}:")
                print(result.stderr)
                # Fallback to basic scaling without pan for problematic files
                try:
                    cmd = [
                        'ffmpeg',
                        '-y',
                        '-i', video_path,
                        '-ss', str(start_time),
                        '-t', str(segment_duration),
                        '-vf', basic_scaling_filter,
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        segment_file
                    ]
                    print(f"Retrying with basic scaling: {basic_scaling_filter}")
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                except Exception as fallback_e:
                    print(f"Even fallback failed: {fallback_e}")
                    continue
                
            if os.path.exists(segment_file) and os.path.getsize(segment_file) > 0:
                segment_files.append(segment_file)
            else:
                print(f"Warning: Segment file not created or empty: {segment_file}")
                
        if not segment_files:
            raise Exception("No valid segments were created. Cannot create montage.")
        
        try:
            # Try the concat method first
            temp_output = create_concat_file(segment_files, temp_dir)
            if temp_output:
                # Add text overlay "@Suite.E.Studios"
                create_final_output(temp_output, output_path, output_duration, target_aspect)
            else:
                # If concat fails, fall back to direct encoding
                fallback_create_output(segment_files, output_path, output_duration, target_aspect)
        except Exception as e:
            print(f"Error during montage creation: {e}")
            print("Trying direct encoding fallback method...")
            fallback_create_output(segment_files, output_path, output_duration, target_aspect)
            
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
        '-c', 'copy',
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

def create_final_output(temp_output, output_path, video_duration, target_aspect):
    """Create the final output with text overlay."""
    # Add text overlay "@Suite.E.Studios"
    # We'll add the text for short durations at different intervals
    text_filter = create_text_overlay_filter(video_duration)
    
    # Set target dimensions
    target_width = ASPECT_RATIOS[target_aspect]["width"]
    target_height = ASPECT_RATIOS[target_aspect]["height"]
    
    # Final FFmpeg command to create the output with text overlay
    cmd = [
        'ffmpeg',
        '-y',
        '-i', temp_output,
        '-vf', text_filter,
        '-c:a', 'copy',
        '-s', f"{target_width}x{target_height}",
        output_path
    ]
    print(f"Executing final FFmpeg command to create: {output_path}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    # Check if the command was successful
    if result.returncode != 0:
        print("FFmpeg Error:")
        print(result.stderr)
        raise Exception(f"FFmpeg failed with return code {result.returncode}")
        
    # Verify the file was created
    if not os.path.exists(output_path):
        raise Exception(f"FFmpeg didn't report an error, but the output file wasn't created at: {output_path}")

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

def create_text_overlay_filter(video_duration):
    """Create FFmpeg filter complex string for text overlays."""
    # We'll show text 3-5 times depending on video length
    num_displays = max(3, min(5, int(video_duration / 20)))
    
    # Calculate display intervals and durations
    interval = video_duration / (num_displays + 1)
    display_duration = 3  # 3 seconds per display
    
    # Create the filter complex string
    filter_parts = []
    for i in range(num_displays):
        start_time = (i + 1) * interval
        end_time = start_time + display_duration
        
        # Text appears and fades out
        # For vertical videos, position the text in the lower third
        filter_part = (
            f"drawtext=text='@Suite.E.Studios':fontcolor=white:fontsize=36:"
            f"borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.85:"
            f"enable='between(t,{start_time},{end_time})':alpha='if(lt(t,{start_time+0.5}),(t-{start_time})*2,if(gt(t,{end_time-0.5}),1-(t-{end_time-0.5})*2,1))'"
        )
        filter_parts.append(filter_part)
    
    return ','.join(filter_parts)

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
    
def main():
    parser = argparse.ArgumentParser(description='Create an exciting video montage from input videos for social media.')
    parser.add_argument('--input-string', '-i', help='Input string in format: "output_name, format, video1, video2, ..."')
    parser.add_argument('videos', nargs='*', help='Input video files (if not using --input-string)')
    parser.add_argument('--output', '-o', help='Output video file (if not using --input-string)')
    parser.add_argument('--duration', '-d', type=int, choices=[30, 60, 90], default=60,
                       help='Output video duration in seconds (30, 60, or 90)')
    parser.add_argument('--format', '-f', choices=['instagram_reel', 'tiktok', 'instagram_square'], 
                       help='Output video format/aspect ratio (if not using --input-string)')
    
    # New panning options
    parser.add_argument('--panning', action='store_true', help='Enable panning effects')
    parser.add_argument('--pan-strategy', choices=[d.value for d in PanDirection] + ['random', 'sequence'], default='random',
                       help='Panning strategy: specific direction, random, or sequence')
    parser.add_argument('--pan-speed', type=float, default=1.0, help='Panning speed factor (default: 1.0)')
    parser.add_argument('--pan-distance', type=float, default=0.2, help='Panning distance as percentage of frame (0.0-1.0)')
    parser.add_argument('--easing', choices=[e.value for e in EasingType], default=EasingType.EASE_IN_OUT.value,
                       help='Easing function for smooth panning')
    
    args = parser.parse_args()
    
    if not check_ffmpeg():
        sys.exit(1)
    
    # Determine if we're using the string input mode or traditional args
    if args.input_string:
        output_name, format_name, input_videos = parse_input_string(args.input_string)
        if not output_name or not format_name or not input_videos:
            sys.exit(1)
        
        # Ensure output name has .mp4 extension
        if not output_name.endswith('.mp4'):
            output_name += '.mp4'
            
        output_path = output_name
        video_format = format_name
        videos = input_videos
    else:
        # Traditional argument mode
        if not args.output:
            print("Error: --output is required when not using --input-string")
            sys.exit(1)
        if not args.format:
            print("Error: --format is required when not using --input-string")
            sys.exit(1)
        if not args.videos:
            print("Error: At least one input video is required")
            sys.exit(1)
            
        output_path = args.output
        video_format = args.format
        videos = args.videos
    
    categorized_videos = validate_inputs(videos)
    if not categorized_videos:
        sys.exit(1)
    
    # Flatten the list of videos
    all_videos = []
    for video_list in categorized_videos.values():
        all_videos.extend(video_list)
    
    print(f"Current working directory: {os.path.abspath(os.getcwd())}")
    print(f"Creating a {args.duration}-second {ASPECT_RATIOS[video_format]['description']} montage from {len(all_videos)} video(s)...")
    
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
            output_path, 
            video_format,
            enable_panning=args.panning,
            pan_strategy=pan_strategy,
            pan_speed=args.pan_speed,
            pan_distance=args.pan_distance,
            easing_type=easing_type
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
