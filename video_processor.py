import subprocess
import os

class VideoProcessor:
    @staticmethod
    def create_video_from_images_and_audio(image_paths, audio_path, output_path, bg_music_path=None, description=""):
        """
        Creates a video by combining multiple images, an audio file, and optional background music
        with crossfade transitions and automatic subtitles.
        """
        if not image_paths or not os.path.exists(audio_path):
            raise FileNotFoundError("Image(s) or Audio file not found.")

        # Get audio duration
        duration_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
        ]
        duration = float(subprocess.check_output(duration_cmd).decode().strip())
        
        num_images = len(image_paths)
        img_duration = duration / num_images
        transition_duration = 0.5 if num_images > 1 else 0
        
        # 1. Inputs construction
        inputs = []
        for img in image_paths:
            inputs.extend(['-loop', '1', '-t', str(img_duration + transition_duration), '-i', img])
        
        inputs.extend(['-i', audio_path])
        
        if bg_music_path and os.path.exists(bg_music_path):
            inputs.extend(['-stream_loop', '-1', '-i', bg_music_path])
            has_music = True
        else:
            has_music = False

        # 2. Filter Complex construction
        filter_str = ""
        # Scale and pad all images to 1080x1920
        for i in range(num_images):
            filter_str += f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
        
        # Transitions chain
        last_v = "[v0]"
        offset = img_duration
        if num_images > 1:
            for i in range(1, num_images):
                next_v = f"v{i}"
                out_v = f"xf{i}"
                filter_str += f"{last_v}[{next_v}]xfade=transition=fade:duration={transition_duration}:offset={offset}[{out_v}];"
                last_v = f"[{out_v}]"
                offset += img_duration
        
        # 3. Add Subtitles (Captions) - REMOVED per user request
        # 4. Audio Mixing
        # [num_images:a] is the voiceover, [num_images+1:a] is the background music
        if has_music:
            # Voice at 100%, Music at 15%
            filter_str += f"[{num_images}:a]volume=1.0[a_voice];[{num_images+1}:a]volume=0.15[a_music];[a_voice][a_music]amix=inputs=2:duration=first[outa]"
            audio_map = "[outa]"
        else:
            audio_map = f"{num_images}:a"

        command = [
            'ffmpeg', '-y'
        ]
        command.extend(inputs)
        command.extend([
            '-filter_complex', filter_str.rstrip(';'),
            '-map', last_v,
            '-map', audio_map,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-tune', 'stillimage',
            '-pix_fmt', 'yuv420p',
            '-r', '25',
            '-shortest',
            output_path
        ])

        try:
            # Set encoding to prevent issues with special characters 
            subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr}")
            raise e
