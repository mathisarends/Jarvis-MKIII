import os
import subprocess
import sys
from pathlib import Path


def analyze_audio_file(file_path):
    """Analyze an audio file to determine its actual format and properties."""
    print(f"\n--- Analyzing file: {file_path} ---")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ File does not exist: {file_path}")
        return
    
    # Get file size
    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size} bytes")
    
    # Try to use 'file' command for basic format detection
    try:
        result = subprocess.run(['file', file_path], capture_output=True, text=True)
        print(f"File command result: {result.stdout.strip()}")
    except Exception as e:
        print(f"Error running 'file' command: {e}")
    
    # Try to read first few bytes directly
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            hex_header = ' '.join([f'{b:02x}' for b in header])
            print(f"First 16 bytes: {hex_header}")
            
            # Check for MP3 header - simpler version
            if header.startswith(b'ID3'):
                print("✅ File has ID3 header (likely MP3)")
            # Check for WAV header
            elif header.startswith(b'RIFF') and header[8:12] == b'WAVE':
                print("File appears to be WAV format")
            # Check for Ogg/Vorbis
            elif header.startswith(b'OggS'):
                print("File appears to be Ogg format")
            else:
                print("❓ No standard audio header detected - might be raw audio data or corrupted")
    except Exception as e:
        print(f"Error reading file header: {e}")

def find_and_analyze_audio_files():
    """Find and analyze audio files in the temp directory."""
    # Base project directory (assuming script is run from project root)
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Just check the temp directory
    temp_dir = os.path.join(project_dir, "resources", "sounds", "temp")
    
    if not os.path.exists(temp_dir):
        print(f"❌ Temp directory not found: {temp_dir}")
        return
    
    # Find audio files
    found_files = []
    print(f"Searching in: {temp_dir}")
    for file in os.listdir(temp_dir):
        if file.endswith(".mp3") or "audio_chunk" in file:
            found_files.append(os.path.join(temp_dir, file))
    
    if not found_files:
        print("No audio files found in the temp directory.")
        return
    
    print(f"Found {len(found_files)} audio files")
    
    # Analyze each file
    for file_path in found_files:
        analyze_audio_file(file_path)

if __name__ == "__main__":
    print("🔍 Audio File Format Analyzer 🔍")
    find_and_analyze_audio_files()