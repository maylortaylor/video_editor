# video_editor
Python video editor made using Claude

## Running the script

### "Old Method"
```
\\ example command to run script with "old method"
python video_editor_script_v1.py --output montage.mp4 --format instagram_reel --duration 60 video1.mp4 video2.mp4 video3.mp4
```


### "New Method"
```
\\ example command to run script with "new method"
python video_editor_script.py --input-string "O:\_Captures\Ajeva 7.27.2024\montage, instagram_reel, O:\_Captures\Ajeva 7.27.2024\GP013015.MP4" --duration 30
```

## NOTES
If you want to save the file in a different location, you have two options:

1. Include the full path in the output name:
```
python video_editor_script.py --input-string "O:\_Captures\Ajeva 7.27.2024\montage, instagram_reel, O:\_Captures\Ajeva 7.27.2024\GP013015.MP4" --duration 30
```

2. Run the script from the directory where you want to save the file:
```
cd C:\Users\Maylor\Videos
python O:\_Dev\video_editor\video_editor_script.py --input-string "montage, instagram_reel, O:\_Captures\Ajeva 7.27.2024\GP013015.MP4" --duration 30
```

The script should also print a success message showing where the file was saved, like:
```
Success! Video montage saved to: montage.mp4
```

3. Or try this?
```
python O:\_Dev\video_editor\video_editor_script.py --input-string "montage, instagram_reel, O:\_Captures\Ajeva 7.27.2024\GP013015.MP4" --duration 30
```