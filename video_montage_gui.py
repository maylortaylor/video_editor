import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import threading

class VideoMontageCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Montage Creator")
        self.root.geometry("900x700")
        self.root.minsize(900, 700)
        
        # Store script path
        self.script_path = "video_editor_script.py"  # Path to your script
        
        # Store form values
        self.input_video = tk.StringVar()
        self.output_file = tk.StringVar()
        self.format = tk.StringVar(value="vertical_portrait")
        self.duration = tk.IntVar(value=30)
        self.segments = tk.StringVar(value="some")
        self.panning = tk.BooleanVar(value=False)
        self.pan_strategy = tk.StringVar(value="sequence")
        self.pan_speed = tk.DoubleVar(value=1.0)
        self.pan_distance = tk.DoubleVar(value=0.2)
        self.easing = tk.StringVar(value="ease_in_out")
        self.text = tk.StringVar()
        self.text_style = tk.StringVar(value="default")
        self.logo_path = tk.StringVar()
        self.intro_video_path = tk.StringVar()
        self.intro_video_length = tk.IntVar(value=5)
        self.intro_audio_path = tk.StringVar()
        
        # Create UI frame
        self.create_ui()
        
        # Status variables
        self.processing = False
        self.command_output = ""

    def create_ui(self):
        # Create notebook for tab organization
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main settings tab
        main_frame = ttk.Frame(notebook, padding=10)
        notebook.add(main_frame, text="Main Settings")
        
        # Advanced settings tab
        advanced_frame = ttk.Frame(notebook, padding=10)
        notebook.add(advanced_frame, text="Advanced Settings")
        
        # Output tab
        output_frame = ttk.Frame(notebook, padding=10)
        notebook.add(output_frame, text="Output")
        
        # Build the main settings tab
        self.build_main_settings(main_frame)
        
        # Build the advanced settings tab
        self.build_advanced_settings(advanced_frame)
        
        # Build the output tab
        self.build_output_tab(output_frame)
        
        # Add run button at the bottom
        run_frame = ttk.Frame(self.root, padding=(0, 10))
        run_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress = ttk.Progressbar(run_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        run_button = ttk.Button(run_frame, text="Generate Video Montage", command=self.run_script)
        run_button.pack(side=tk.RIGHT, padx=5)
        
        preview_button = ttk.Button(run_frame, text="Preview Command", command=self.preview_command)
        preview_button.pack(side=tk.RIGHT, padx=5)

    def build_main_settings(self, parent):
        # Input and output file selection
        file_frame = ttk.LabelFrame(parent, text="Files", padding=10)
        file_frame.pack(fill=tk.X, pady=5)
        
        # Input video
        input_label = ttk.Label(file_frame, text="Input Video:")
        input_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        input_entry = ttk.Entry(file_frame, textvariable=self.input_video, width=50)
        input_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        input_button = ttk.Button(file_frame, text="Browse...", command=self.browse_input)
        input_button.grid(row=0, column=2, pady=5)
        
        # Output file
        output_label = ttk.Label(file_frame, text="Output File:")
        output_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        output_entry = ttk.Entry(file_frame, textvariable=self.output_file, width=50)
        output_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        output_button = ttk.Button(file_frame, text="Browse...", command=self.browse_output)
        output_button.grid(row=1, column=2, pady=5)
        
        # Configure grid columns
        file_frame.columnconfigure(1, weight=1)
        
        # Basic settings
        settings_frame = ttk.LabelFrame(parent, text="Basic Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Format
        format_label = ttk.Label(settings_frame, text="Output Format:")
        format_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        format_combo = ttk.Combobox(settings_frame, textvariable=self.format, width=20)
        format_combo['values'] = ('vertical_portrait', 'instagram_square')
        format_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Duration
        duration_label = ttk.Label(settings_frame, text="Duration (seconds):")
        duration_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        duration_spin = ttk.Spinbox(settings_frame, from_=5, to=90, textvariable=self.duration, width=10)
        duration_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Segments
        segments_label = ttk.Label(settings_frame, text="Segments:")
        segments_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        segments_combo = ttk.Combobox(settings_frame, textvariable=self.segments, width=10)
        segments_combo['values'] = ('few', 'some', 'lots')
        segments_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Text overlay
        text_label = ttk.Label(settings_frame, text="Text Overlay:")
        text_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        text_entry = ttk.Entry(settings_frame, textvariable=self.text, width=30)
        text_entry.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Text style
        text_style_label = ttk.Label(settings_frame, text="Text Style:")
        text_style_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        
        text_style_combo = ttk.Combobox(settings_frame, textvariable=self.text_style, width=10)
        text_style_combo['values'] = ('default', 'pulse', 'pro', 'promo', 'impact')
        text_style_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Logo overlay
        logo_label = ttk.Label(settings_frame, text="Logo Overlay:")
        logo_label.grid(row=5, column=0, sticky=tk.W, pady=5)
        
        logo_entry = ttk.Entry(settings_frame, textvariable=self.logo_path, width=30)
        logo_entry.grid(row=5, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        logo_button = ttk.Button(settings_frame, text="Browse...", command=self.browse_logo)
        logo_button.grid(row=5, column=2, pady=5)
        
        # Configure grid columns
        settings_frame.columnconfigure(1, weight=1)

    def build_advanced_settings(self, parent):
        # Panning settings
        panning_frame = ttk.LabelFrame(parent, text="Panning Effects", padding=10)
        panning_frame.pack(fill=tk.X, pady=5)
        
        # Enable panning
        panning_check = ttk.Checkbutton(panning_frame, text="Enable Panning Effects", variable=self.panning)
        panning_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Pan strategy
        strategy_label = ttk.Label(panning_frame, text="Pan Strategy:")
        strategy_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        strategy_combo = ttk.Combobox(panning_frame, textvariable=self.pan_strategy, width=15)
        strategy_combo['values'] = ('sequence', 'random', 'zoom_in', 'zoom_out')
        strategy_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Pan speed
        speed_label = ttk.Label(panning_frame, text="Pan Speed:")
        speed_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        speed_spin = ttk.Spinbox(panning_frame, from_=0.1, to=3.0, increment=0.1, textvariable=self.pan_speed, width=10)
        speed_spin.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Pan distance
        distance_label = ttk.Label(panning_frame, text="Pan Distance:")
        distance_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        distance_spin = ttk.Spinbox(panning_frame, from_=0.1, to=0.5, increment=0.05, textvariable=self.pan_distance, width=10)
        distance_spin.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Easing
        easing_label = ttk.Label(panning_frame, text="Easing:")
        easing_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        
        easing_combo = ttk.Combobox(panning_frame, textvariable=self.easing, width=15)
        easing_combo['values'] = ('ease_in_out', 'linear', 'ease_in', 'ease_out')
        easing_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Intro settings
        intro_frame = ttk.LabelFrame(parent, text="Intro Settings", padding=10)
        intro_frame.pack(fill=tk.X, pady=5)
        
        # Intro video
        intro_video_label = ttk.Label(intro_frame, text="Intro Video:")
        intro_video_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        intro_video_entry = ttk.Entry(intro_frame, textvariable=self.intro_video_path, width=50)
        intro_video_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        intro_video_button = ttk.Button(intro_frame, text="Browse...", command=self.browse_intro_video)
        intro_video_button.grid(row=0, column=2, pady=5)
        
        # Intro video length
        intro_length_label = ttk.Label(intro_frame, text="Intro Video Length (s):")
        intro_length_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        intro_length_spin = ttk.Spinbox(intro_frame, from_=1, to=30, textvariable=self.intro_video_length, width=10)
        intro_length_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Intro audio
        intro_audio_label = ttk.Label(intro_frame, text="Intro Audio:")
        intro_audio_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        intro_audio_entry = ttk.Entry(intro_frame, textvariable=self.intro_audio_path, width=50)
        intro_audio_entry.grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        intro_audio_button = ttk.Button(intro_frame, text="Browse...", command=self.browse_intro_audio)
        intro_audio_button.grid(row=2, column=2, pady=5)
        
        # Configure grid columns
        panning_frame.columnconfigure(1, weight=1)
        intro_frame.columnconfigure(1, weight=1)

    def build_output_tab(self, parent):
        # Command preview
        preview_label = ttk.Label(parent, text="Command Preview:")
        preview_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.command_preview = tk.Text(parent, height=10, wrap=tk.WORD)
        self.command_preview.pack(fill=tk.X, expand=False)
        
        # Output log
        output_label = ttk.Label(parent, text="Output Log:")
        output_label.pack(anchor=tk.W, pady=(10, 5))
        
        self.output_text = tk.Text(parent, height=15, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar to output text
        output_scrollbar = ttk.Scrollbar(self.output_text, command=self.output_text.yview)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=output_scrollbar.set)

    def browse_input(self):
        filename = filedialog.askopenfilename(filetypes=[
            ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ])
        if filename:
            self.input_video.set(filename)
            # Suggest output filename
            if not self.output_file.get():
                input_path = os.path.dirname(filename)
                input_name = os.path.splitext(os.path.basename(filename))[0]
                output_path = os.path.join(input_path, f"{input_name}_montage.mp4")
                self.output_file.set(output_path)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)

    def browse_logo(self):
        filename = filedialog.askopenfilename(filetypes=[
            ("PNG files", "*.png"),
            ("All files", "*.*")
        ])
        if filename:
            self.logo_path.set(filename)

    def browse_intro_video(self):
        filename = filedialog.askopenfilename(filetypes=[
            ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ])
        if filename:
            self.intro_video_path.set(filename)

    def browse_intro_audio(self):
        filename = filedialog.askopenfilename(filetypes=[
            ("Audio files", "*.mp3 *.wav *.aac *.m4a *.flac"),
            ("All files", "*.*")
        ])
        if filename:
            self.intro_audio_path.set(filename)

    def preview_command(self):
        cmd = self.build_command()
        self.command_preview.delete(1.0, tk.END)
        self.command_preview.insert(tk.END, " ".join(cmd))

    def build_command(self):
        # Start with the basic command
        cmd = [sys.executable, self.script_path]
        
        # Add output file
        if self.output_file.get():
            cmd.extend(["-o", self.output_file.get()])
        
        # Add format
        if self.format.get():
            cmd.extend(["-f", self.format.get()])
        
        # Add duration
        cmd.extend(["-d", str(self.duration.get())])
        
        # Add segments if specified
        if self.segments.get():
            cmd.extend(["--segments", self.segments.get()])
        
        # Add panning settings if enabled
        if self.panning.get():
            cmd.append("--panning")
            cmd.extend(["--pan-strategy", self.pan_strategy.get()])
            cmd.extend(["--pan-speed", str(self.pan_speed.get())])
            cmd.extend(["--pan-distance", str(self.pan_distance.get())])
            cmd.extend(["--easing", self.easing.get()])
        
        # Add text overlay if specified
        if self.text.get():
            cmd.extend(["--text", self.text.get()])
            cmd.extend(["--text-style", self.text_style.get()])
        
        # Add logo if specified
        if self.logo_path.get():
            cmd.extend(["--logo", self.logo_path.get()])
        
        # Add intro video if specified
        if self.intro_video_path.get():
            cmd.extend(["--intro-video", self.intro_video_path.get()])
            cmd.extend(["--intro-video-length", str(self.intro_video_length.get())])
        
        # Add intro audio if specified
        if self.intro_audio_path.get():
            cmd.extend(["--intro-audio", self.intro_audio_path.get()])
        
        # Add input video as the last argument
        if self.input_video.get():
            cmd.append(self.input_video.get())
        
        return cmd

    def run_script(self):
        # Validate required fields
        if not self.input_video.get():
            messagebox.showerror("Error", "Input video is required")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Output file is required")
            return
        
        # Check if output directory exists
        output_dir = os.path.dirname(self.output_file.get())
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory: {str(e)}")
                return
        
        # Build the command
        cmd = self.build_command()
        
        # Show command preview
        self.command_preview.delete(1.0, tk.END)
        self.command_preview.insert(tk.END, " ".join(cmd))
        
        # Clear previous output
        self.output_text.delete(1.0, tk.END)
        
        # Start progress bar
        self.progress.start()
        self.processing = True
        
        # Run the command in a separate thread
        thread = threading.Thread(target=self.run_command, args=(cmd,))
        thread.daemon = True
        thread.start()

    def run_command(self, cmd):
        try:
            # Run the command and capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Read output line by line
            for line in process.stdout:
                self.update_output(line)
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Show completion message
            if return_code == 0:
                self.update_output("\n✅ Video montage created successfully!\n")
                messagebox.showinfo("Success", "Video montage created successfully!")
            else:
                self.update_output(f"\n❌ Error: Process exited with code {return_code}\n")
                messagebox.showerror("Error", f"Process exited with code {return_code}")
        
        except Exception as e:
            self.update_output(f"\n❌ Error: {str(e)}\n")
            messagebox.showerror("Error", str(e))
        
        finally:
            # Stop progress bar
            self.root.after(0, self.stop_progress)

    def update_output(self, text):
        # Update the output text widget from the main thread
        self.root.after(0, lambda: self.append_output(text))

    def append_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)  # Scroll to the end

    def stop_progress(self):
        self.progress.stop()
        self.processing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoMontageCreatorGUI(root)
    
    # Set icon (optional)
    try:
        root.iconbitmap("app_icon.ico")  # Replace with your icon file path
    except:
        pass  # Skip if icon file doesn't exist
    
    root.mainloop()