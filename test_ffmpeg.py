from video_processor import VideoProcessor
import os

def test_ffmpeg():
    # Create a dummy image if not exists
    image_path = "test_image.jpg"
    audio_path = "test_audio.mp3" # Run test_groq.py first to get this
    output_path = "test_video.mp4"

    if not os.path.exists(image_path):
        print(f"Please provide an image named {image_path} to test video creation.")
        return

    if not os.path.exists(audio_path):
        print(f"Please run test_groq.py first to generate {audio_path}.")
        return

    print("Testing FFmpeg Video Creation...")
    try:
        vp = VideoProcessor()
        vp.create_video_from_image_and_audio(image_path, audio_path, output_path)
        print(f"Success! Video created at {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ffmpeg()
