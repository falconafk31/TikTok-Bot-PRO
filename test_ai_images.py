import sys
import os
import asyncio
from ai_handler import AIHandler

async def test_gen():
    handler = AIHandler()
    print("Testing Pollinations AI Image Generation...")
    paths = handler.generate_images_from_prompt("Cyberpunk City Sunset", count=2, output_dir="temp/test_images")
    if paths and len(paths) == 2:
        print(f"Success! Generated: {paths}")
    else:
        print("Failed to generate images.")

if __name__ == "__main__":
    asyncio.run(test_gen())
