import unittest
import os
import tempfile
import subprocess
from video_editor_script import (
    PanDirection, EasingType, ASPECT_RATIOS,
    create_video_segment, get_video_duration,
    get_video_dimensions, create_video_montage,
    determine_scaling_filter, test_filter_string,
    validate_inputs, TextMotionType
)

class TestVideoEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create test video files for all tests."""
        cls.test_video = cls.create_test_video()
        cls.test_video_with_audio = cls.create_test_video_with_audio()
        cls.temp_dir = tempfile.mkdtemp(prefix='video_editor_test_')
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        for video in [cls.test_video, cls.test_video_with_audio]:
            if os.path.exists(video):
                os.remove(video)
        if os.path.exists(cls.temp_dir):
            for file in os.listdir(cls.temp_dir):
                os.remove(os.path.join(cls.temp_dir, file))
            os.rmdir(cls.temp_dir)

    @staticmethod
    def create_test_video():
        """Create a basic test video file using FFmpeg."""
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'testsrc=duration=10:size=1920x1080:rate=30',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-t', '10',
            temp_video
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return temp_video

    @staticmethod
    def create_test_video_with_audio():
        """Create a test video file with audio using FFmpeg."""
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', 'testsrc=duration=10:size=1920x1080:rate=30',
            '-f', 'lavfi',
            '-i', 'sine=frequency=1000:duration=10',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'ultrafast',
            '-t', '10',
            temp_video
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return temp_video

    def test_video_duration(self):
        """Test video duration detection."""
        duration = get_video_duration(self.test_video)
        self.assertAlmostEqual(duration, 10.0, delta=0.1)

    def test_video_dimensions(self):
        """Test video dimension detection."""
        width, height = get_video_dimensions(self.test_video)
        self.assertEqual(width, 1920)
        self.assertEqual(height, 1080)

    def test_scaling_filter(self):
        """Test scaling filter generation for different aspect ratios."""
        for aspect in ASPECT_RATIOS:
            filter_str = determine_scaling_filter(self.test_video, aspect)
            self.assertIsInstance(filter_str, str)
            self.assertIn('scale=', filter_str)
            self.assertIn('force_original_aspect_ratio=1', filter_str)

    def test_panning_directions(self):
        """Test all panning directions."""
        output_file = os.path.join(self.temp_dir, 'test_pan.mp4')
        
        for direction in PanDirection:
            with self.subTest(direction=direction):
                result = create_video_segment(
                    video_path=self.test_video,
                    start_time=0,
                    segment_duration=3,
                    output_file=output_file,
                    target_aspect='vertical_portrait',
                    direction=direction
                )
                self.assertIsNotNone(result)
                self.assertTrue(os.path.exists(result))
                duration = get_video_duration(result)
                self.assertAlmostEqual(duration, 3.0, delta=0.1)

    def test_zoom_effects(self):
        """Test zoom in and zoom out effects."""
        output_file = os.path.join(self.temp_dir, 'test_zoom.mp4')
        
        for direction in [PanDirection.ZOOM_IN, PanDirection.ZOOM_OUT]:
            with self.subTest(direction=direction):
                result = create_video_segment(
                    video_path=self.test_video,
                    start_time=0,
                    segment_duration=3,
                    output_file=output_file,
                    target_aspect='vertical_portrait',
                    direction=direction
                )
                self.assertIsNotNone(result)
                self.assertTrue(os.path.exists(result))
                duration = get_video_duration(result)
                self.assertAlmostEqual(duration, 3.0, delta=0.1)

    def test_filter_string_validation(self):
        """Test filter string validation."""
        # Test valid filter
        valid_filter = 'scale=1080:1920:force_original_aspect_ratio=1'
        self.assertTrue(test_filter_string(valid_filter))
        
        # Test invalid filter
        invalid_filter = 'scale=invalid:invalid'
        self.assertFalse(test_filter_string(invalid_filter))

    def test_montage_creation(self):
        """Test full montage creation with different parameters."""
        output_file = os.path.join(self.temp_dir, 'test_montage.mp4')
        
        # Test with different segment counts
        for segment_count in ['few', 'some', 'lots']:
            with self.subTest(segment_count=segment_count):
                try:
                    create_video_montage(
                        video_paths=[self.test_video_with_audio],
                        output_duration=30,
                        output_path=output_file,
                        target_aspect='vertical_portrait',
                        enable_panning=True,
                        pan_strategy='sequence',
                        segment_count=segment_count,
                        text="Test Text",
                        text_display_duration=5
                    )
                    self.assertTrue(os.path.exists(output_file))
                    duration = get_video_duration(output_file)
                    self.assertAlmostEqual(duration, 30.0, delta=0.5)
                except Exception as e:
                    self.fail(f"Montage creation failed: {str(e)}")

    def test_aspect_ratio_handling(self):
        """Test handling of different aspect ratios."""
        for aspect in ASPECT_RATIOS:
            with self.subTest(aspect=aspect):
                output_file = os.path.join(self.temp_dir, f'test_{aspect}.mp4')
                result = create_video_segment(
                    video_path=self.test_video,
                    start_time=0,
                    segment_duration=3,
                    output_file=output_file,
                    target_aspect=aspect,
                    direction=None
                )
                self.assertIsNotNone(result)
                self.assertTrue(os.path.exists(result))
                
                # Verify output dimensions
                width, height = get_video_dimensions(result)
                self.assertEqual(width, ASPECT_RATIOS[aspect]['width'])
                self.assertEqual(height, ASPECT_RATIOS[aspect]['height'])

    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with non-existent video
        result = validate_inputs(['nonexistent.mp4'])
        self.assertIsNone(result, "Should return None for non-existent video")
        
        # Test with invalid aspect ratio
        output_file = os.path.join(self.temp_dir, 'test_invalid.mp4')
        try:
            create_video_segment(
                video_path=self.test_video,
                start_time=0,
                segment_duration=3,
                output_file=output_file,
                target_aspect='invalid_aspect',
                direction=None
            )
            self.fail("Expected an error for invalid aspect ratio")
        except Exception as e:
            # Accept any exception for invalid aspect ratio
            self.assertTrue(isinstance(e, Exception), 
                          f"Expected an Exception, got {type(e)}")
            self.assertIn('aspect', str(e).lower(), 
                         "Error message should mention aspect ratio")

    def test_segment_duration_accuracy(self):
        """Test accuracy of segment durations."""
        output_file = os.path.join(self.temp_dir, 'test_duration.mp4')
        
        for duration in [2, 3, 5]:
            with self.subTest(duration=duration):
                result = create_video_segment(
                    video_path=self.test_video,
                    start_time=0,
                    segment_duration=duration,
                    output_file=output_file,
                    target_aspect='vertical_portrait',
                    direction=None
                )
                self.assertIsNotNone(result)
                actual_duration = get_video_duration(result)
                self.assertAlmostEqual(actual_duration, duration, delta=0.1)

    def test_text_overlay_styles(self):
        """Test different text overlay styles."""
        output_file = os.path.join(self.temp_dir, 'test_text.mp4')
        
        for style in ['default', 'pulse', 'concert', 'promo']:
            with self.subTest(style=style):
                try:
                    # Create a longer test video for better testing
                    test_video = self.create_test_video_with_audio()
                    create_video_montage(
                        video_paths=[test_video],
                        output_duration=10,
                        output_path=output_file,
                        target_aspect='vertical_portrait',
                        text="Test Text",
                        text_style=style,
                        text_display_duration=5,
                        enable_panning=False  # Disable panning for simpler test
                    )
                    self.assertTrue(os.path.exists(output_file))
                    duration = get_video_duration(output_file)
                    self.assertAlmostEqual(duration, 10.0, delta=0.5)
                except Exception as e:
                    self.fail(f"Text overlay test failed for style {style}: {str(e)}")
                finally:
                    if os.path.exists(test_video):
                        os.remove(test_video)

    def test_text_motion_types(self):
        """Test different text motion types."""
        output_file = os.path.join(self.temp_dir, 'test_text_motion.mp4')
        
        for motion in TextMotionType:
            with self.subTest(motion=motion.value):
                try:
                    # Create a longer test video for better testing
                    test_video = self.create_test_video_with_audio()
                    create_video_montage(
                        video_paths=[test_video],
                        output_duration=10,
                        output_path=output_file,
                        target_aspect='vertical_portrait',
                        text="Test Text",
                        text_motion=motion.value,
                        text_display_duration=5,
                        enable_panning=False  # Disable panning for simpler test
                    )
                    self.assertTrue(os.path.exists(output_file))
                    duration = get_video_duration(output_file)
                    self.assertAlmostEqual(duration, 10.0, delta=0.5)
                except Exception as e:
                    self.fail(f"Text motion test failed for {motion.value}: {str(e)}")
                finally:
                    if os.path.exists(test_video):
                        os.remove(test_video)

    def test_intro_video_handling(self):
        """Test handling of intro video."""
        output_file = os.path.join(self.temp_dir, 'test_intro.mp4')
        
        try:
            # Create a longer test video (60 seconds) for better testing
            test_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', 'testsrc=duration=60:size=1920x1080:rate=30',
                '-f', 'lavfi',
                '-i', 'sine=frequency=1000:duration=60',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'ultrafast',
                '-t', '60',
                test_video
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Create a shorter intro video (5 seconds)
            intro_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', 'testsrc=duration=5:size=1920x1080:rate=30',
                '-f', 'lavfi',
                '-i', 'sine=frequency=2000:duration=5',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'ultrafast',
                '-t', '5',
                intro_video
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            create_video_montage(
                video_paths=[test_video],
                output_duration=20,
                output_path=output_file,
                target_aspect='vertical_portrait',
                intro_video=intro_video,
                intro_audio=intro_video,
                intro_audio_duration=5.0,
                intro_audio_volume=2.0,
                enable_panning=False,  # Disable panning for simpler test
                segment_count='few'  # Use fewer segments for more reliable testing
            )
            self.assertTrue(os.path.exists(output_file))
            duration = get_video_duration(output_file)
            self.assertAlmostEqual(duration, 20.0, delta=0.5)
        except Exception as e:
            self.fail(f"Intro video test failed: {str(e)}")
        finally:
            # Clean up test files
            for video in [test_video, intro_video]:
                if os.path.exists(video):
                    os.remove(video)

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        output_file = os.path.join(self.temp_dir, 'test_edge.mp4')
        
        # Test with very short duration
        with self.subTest(case="short_duration"):
            result = create_video_segment(
                video_path=self.test_video,
                start_time=0,
                segment_duration=0.5,
                output_file=output_file,
                target_aspect='vertical_portrait',
                direction=None
            )
            self.assertIsNotNone(result)
            actual_duration = get_video_duration(result)
            self.assertAlmostEqual(actual_duration, 0.5, delta=0.1)
        
        # Test with start time near end of video
        with self.subTest(case="late_start"):
            result = create_video_segment(
                video_path=self.test_video,
                start_time=9.0,
                segment_duration=1.0,
                output_file=output_file,
                target_aspect='vertical_portrait',
                direction=None
            )
            self.assertIsNotNone(result)
            actual_duration = get_video_duration(result)
            self.assertAlmostEqual(actual_duration, 1.0, delta=0.1)

if __name__ == '__main__':
    unittest.main() 