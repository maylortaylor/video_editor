#!/usr/bin/env python3
import os
import sys
import random
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Social media aspect ratios
ASPECT_RATIOS = {
    "instagram_reel": {"width": 1080, "height": 1920, "description": "Instagram Reel (9:16)"},
    "tiktok": {"width": 1080, "height": 1920, "description": "TikTok (9:16)"},
    "instagram_square": {"width": 1080, "height": 1080, "description": "Instagram Square (1:1)"},
}

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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dimensions = result.stdout.strip().split('x')
    return int(dimensions[0]), int(dimensions[1])

def categorize_video(video_path):
    """Categorize a video as short, medium, or long based on its duration."""
    duration = get_video_duration(video_path)
    
    if 30 <= duration <= 60:  # 30 seconds to 1 minute
        return "short"
    elif 60 < duration <= 300:  # 1-5 minutes
        return "medium"
    elif 1800 <= duration <= 3600:  # 30 minutes to 1 hour
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
            # Center crop the landscape video to vertical
            return (f"scale={target_width}:-1,crop={target_width}:{target_height}:(iw-{target_width})/2:0")
        else:  # Input is already portrait/vertical or square
            # Scale to fit target width, and either crop height if too tall or pad if too short
            return (f"scale={target_width}:-1,crop={target_width}:{target_height}:0:(ih-{target_height})/2")
    
    # For square videos (Instagram Square)
    else:  # Target is square (1:1)
        if video_aspect > 1:  # Input is landscape
            return (f"scale=-1:{target_height},crop={target_height}:{target_height}:(iw-{target_height})/2:0")
        else:  # Input is portrait/vertical
            return (f"scale={target_width}:-1,crop={target_width}:{target_width}:0:(ih-{target_width})/2")


def validate_inputs(video_paths):
    """Validate that the input videos meet the requirements."""
    categorized_videos = {}
    
    for path in video_paths:
        if not os.path.exists(path):
            print(f"Error: Video file not found: {path}")
            return None
            
        category = categorize_video(path)
        if category not in categorized_videos:
            categorized_videos[category] = []
        categorized_videos[category].append(path)
    
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

def create_video_montage(video_paths, output_duration, output_path, target_aspect="instagram_reel"):
    """Create a montage video from input videos with specified duration and aspect ratio."""
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
        segment_files = []
        
        # Extract segments to temporary files
        for i, (video_path, start_time, segment_duration) in enumerate(segments_to_use):
            segment_file = os.path.join(temp_dir, f"segment_{i:03d}.mp4")
            
            # Determine scaling filter for this video
            scaling_filter = determine_scaling_filter(video_path, target_aspect)
            
            # Extract segment using FFmpeg with proper scaling/cropping
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output files
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(segment_duration),
                '-vf', scaling_filter,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                segment_file
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            segment_files.append(segment_file)
        
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
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Add text overlay "@Suite.E.Studios"
        # We'll add the text for short durations at different intervals
        text_filter = create_text_overlay_filter(output_duration)
        
        # Set target dimensions
        target_width = ASPECT_RATIOS[target_aspect]["width"]
        target_height = ASPECT_RATIOS[target_aspect]["height"]
        
        cmd = [
            'ffmpeg',
            '-y',
            '-i', temp_output,
            '-vf', text_filter,
            '-c:a', 'copy',
            '-s', f"{target_width}x{target_height}",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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

def main():
    parser = argparse.ArgumentParser(description='Create an exciting video montage from input videos for social media.')
    parser.add_argument('--input-string', '-i', help='Input string in format: "output_name, format, video1, video2, ..."')
    parser.add_argument('videos', nargs='*', help='Input video files (if not using --input-string)')
    parser.add_argument('--output', '-o', help='Output video file (if not using --input-string)')
    parser.add_argument('--duration', '-d', type=int, choices=[30, 60, 90], default=60,
                       help='Output video duration in seconds (30, 60, or 90)')
    parser.add_argument('--format', '-f', choices=['instagram_reel', 'tiktok', 'instagram_square'], 
                       help='Output video format/aspect ratio (if not using --input-string)')
    
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
    
    print(f"Creating a {args.duration}-second {ASPECT_RATIOS[video_format]['description']} montage from {len(all_videos)} video(s)...")
    
    try:
        create_video_montage(all_videos, args.duration, output_path, video_format)
        print(f"Success! Video montage saved to: {output_path}")
    except Exception as e:
        print(f"Error creating video montage: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
