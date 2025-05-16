import os
import base64
import socket
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict
from typing_extensions import override

import soco
from soco import SoCo

from core.audio.audio_player_base import AudioPlayer
from shared.event_bus import EventBus, EventType
from http.server import HTTPServer, SimpleHTTPRequestHandler

class CustomHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Optional: Route HTTP logs to your logging system instead of stdout
        # import logging
        # logger = logging.getLogger("http_server")
        # logger.debug(format % args)
        pass  # Currently suppressing all HTTP logs

    rbufsize = 64 * 1024

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def guess_type(self, path):
        """Overridden method to provide correct MIME types for audio files."""
        _, ext = os.path.splitext(path)
        if ext.lower() == ".wav":
            return "audio/wav"
        return super().guess_type(path)


class SonosHTTPServer:
    """Simple HTTP server to serve audio files for Sonos."""

    def __init__(self, project_dir=None, port=8000):
        """
        Initialize the HTTP server.
        """
        if project_dir is None:
            # If no project directory is specified,
            # use the parent directory of the current file
            self.project_dir = Path(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )
        else:
            self.project_dir = Path(project_dir)

        self.port = port
        self._server = None
        self._server_thread = None
        self._is_running = False

        # The IP address of the server in the local network
        self.server_ip = self._get_local_ip()

    def _get_local_ip(self):
        """Determine the local IP address of the device in the network."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            print(f"❌ Error determining IP address: {e}")
            return "127.0.0.1"

    def start(self):
        """Start the HTTP server in a separate thread."""
        if self._is_running:
            print(f"ℹ️ HTTP server already running on port {self.port}")
            return self

        os.chdir(self.project_dir)

        try:
            self._server = HTTPServer(("", self.port), CustomHandler)
            self._server_thread = threading.Thread(
                target=self._server.serve_forever, daemon=True
            )
            self._server_thread.start()
            self._is_running = True

            print(f"✅ HTTP server started at http://{self.server_ip}:{self.port}/")
            print(f"   Base directory: {self.project_dir}")

            return self
        except Exception as e:
            print(f"❌ Error starting HTTP server: {e}")
            return self

    def stop(self):
        """Stop the HTTP server."""
        if not self._is_running or self._server is None:
            return False

        try:
            self._server.shutdown()
            self._server.server_close()
            self._is_running = False
            print(f"✅ HTTP server on port {self.port} stopped")
            return True
        except Exception as e:
            print(f"❌ Error stopping HTTP server: {e}")
            return False

    def is_running(self):
        """Check if the server is running."""
        return self._is_running

    def get_url_for_file(self, file_path):
        """
        Create a URL for a file relative to the project directory.
        """
        file_path = Path(file_path)

        # Relative path from project directory to file
        try:
            print("===")
            print("self.project_dir", self.project_dir)
            rel_path = file_path.relative_to(self.project_dir)
        except ValueError:
            print(f"⚠️ Warning: File not in project directory: {file_path}")
            return None

        url_path = str(rel_path).replace("\\", "/")

        # Complete URL
        return f"http://{self.server_ip}:{self.port}/{url_path}"


class SonosPlayer(AudioPlayer):
    """Implementation of AudioPlayer for Sonos speakers"""

    @override
    def __init__(self, project_dir=None, port=8000):
        """
        Initialize the SonosPlayer.
        
        Args:
            project_dir: Base directory for the HTTP server
            port: Port for the HTTP server
        """
        # Basic attributes
        self.is_playing = False
        self.is_busy = False
        self.volume = 1.0
        self.event_bus = EventBus()
        
        # Sonos-specific attributes
        self._sonos_device: Optional[SoCo] = None
        self._sonos_devices: List[SoCo] = []
        self._http_server = SonosHTTPServer(project_dir, port)
        self.project_dir = project_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Temporary file management for audio chunks
        self._temp_dir = tempfile.mkdtemp(prefix="sonos_audio_")
        self._current_file_path: Optional[Path] = None
        self._current_file_url: Optional[str] = None
        self._file_counter = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Queue for audio chunks
        self._audio_queue = []
        self._audio_thread = None

        self.logger.info("SonosPlayer initialized")

    @override
    def start(self):
        """Start the Sonos player and the HTTP server"""
        self.is_playing = True
        
        # Start HTTP server
        self._http_server.start()
        
        # If no Sonos device is connected yet, try to discover
        if not self._sonos_device:
            self._discover_devices()
            if self._sonos_devices:
                self._sonos_device = self._sonos_devices[0]
                self.logger.info("Automatically connected to Sonos: %s", self._sonos_device.player_name)
        
        # Start audio thread
        self._audio_thread = threading.Thread(target=self._audio_processing_loop)
        self._audio_thread.daemon = True
        self._audio_thread.start()
        
        self.logger.info("SonosPlayer started")
        return True

    @override
    def stop(self):
        """Stop the Sonos player and the HTTP server"""
        self.is_playing = False
        
        # Stop audio thread
        if self._audio_thread:
            self._audio_thread.join(timeout=2.0)
        
        # Stop HTTP server
        self._http_server.stop()
        
        # Clean up temp directory
        self._cleanup_temp_files()
        
        self.logger.info("SonosPlayer stopped")
        return True

    @override
    def clear_queue_and_stop(self):
        """Clear the queue and stop current playback"""
        with self._lock:
            self._audio_queue.clear()
            
            if self._sonos_device and self.is_busy:
                try:
                    self._sonos_device.stop()
                except Exception as e:
                    self.logger.error("Error stopping Sonos playback: %s", e)
            
            self.is_busy = False
            self._safely_notify_playback_completed()
            
        self.logger.info("Queue cleared and playback stopped")
        return True

    @override
    def set_volume_level(self, volume: float):
        """Set the volume for Sonos playback"""
        self.volume = max(0.0, min(1.0, volume))
        
        # Also adjust Sonos volume
        if self._sonos_device:
            try:
                # Sonos uses 0-100 as volume range
                sonos_volume = int(self.volume * 100)
                self._sonos_device.volume = sonos_volume
                self.logger.info("Sonos volume set to %d%%", sonos_volume)
            except Exception as e:
                self.logger.error("Error setting Sonos volume: %s", e)
        
        return self.volume

    @override
    def get_volume_level(self) -> float:
        """Return the current volume"""
        # If a Sonos device is connected, get the volume directly from there
        if self._sonos_device:
            try:
                # Conversion from Sonos (0-100) to our scale (0.0-1.0)
                self.volume = self._sonos_device.volume / 100.0
            except Exception as e:
                self.logger.warning("Error retrieving Sonos volume: %s", e)
        
        return self.volume

    @override
    def add_audio_chunk(self, base64_audio):
        """Add a base64-encoded audio chunk for playback"""
        try:
            audio_data = base64.b64decode(base64_audio)
            with self._lock:
                self._audio_queue.append(audio_data)
            self.logger.debug("Audio chunk added to queue (length: %d bytes)", len(audio_data))
        except Exception as e:
            self.logger.error("Error adding audio chunk: %s", e)

    @override
    def play_sound(self, sound_name: str) -> bool:
        """Play a sound file"""
        try:
            # Determine path to sound file
            if not sound_name.endswith('.mp3'):
                sound_name += '.mp3'
            
            # Construct proper absolute path using the project directory
            sound_path = os.path.join(self.project_dir, "resources", "sounds", sound_name)
            
            if not os.path.exists(sound_path):
                self.logger.warning("Sound file not found: %s", sound_path)
                return False
            
            # Create URL for the sound file via the HTTP server
            sound_url = self._http_server.get_url_for_file(sound_path)
            
            if not sound_url:
                self.logger.error("Could not create URL for sound file")
                return False
            
            # Play on Sonos
            if self._sonos_device:
                self._sonos_device.play_uri(sound_url)
                return True
            else:
                self.logger.warning("No Sonos device connected")
                return False
                
        except Exception as e:
            self.logger.error("Error playing sound %s: %s", sound_name, e)
            return False
        
    def connect_to_device(self, device_name=None, ip_address=None) -> bool:
        """
        Connect to a Sonos device by name or IP address
        
        Args:
            device_name: Name of the Sonos device
            ip_address: IP address of the Sonos device
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Connection via IP address
            if ip_address:
                self._sonos_device = SoCo(ip_address)
                self.logger.info("Connected to Sonos device: %s (%s)", self._sonos_device.player_name, ip_address)
                return True
            
            # Connection via name
            if device_name:
                if not self._sonos_devices:
                    self._discover_devices()
                
                for device in self._sonos_devices:
                    if device_name.lower() in device.player_name.lower():
                        self._sonos_device = device
                        self.logger.info("Connected to Sonos device: %s", device.player_name)
                        return True
                
                self.logger.error("No Sonos device with name '%s' found", device_name)
                return False
            
            # Automatic connection to the first device
            if not self._sonos_devices:
                self._discover_devices()
            
            if self._sonos_devices:
                self._sonos_device = self._sonos_devices[0]
                self.logger.info("Automatically connected to Sonos device: %s", self._sonos_device.player_name)
                return True
            else:
                self.logger.error("No Sonos devices found on the network")
                return False
                
        except Exception as e:
            self.logger.error("Error connecting to Sonos: %s", e)
            return False

    def get_available_devices(self) -> List[Dict[str, str]]:
        """
        Return a list of all available Sonos devices
        
        Returns:
            List of dictionaries with 'name' and 'ip' of devices
        """
        self._discover_devices()
        return [{'name': device.player_name, 'ip': device.ip_address} 
                for device in self._sonos_devices]

    def get_current_device(self) -> Optional[Dict[str, str]]:
        """
        Return information about the currently connected Sonos device
        
        Returns:
            Dictionary with 'name' and 'ip' of the device or None
        """
        if self._sonos_device:
            return {
                'name': self._sonos_device.player_name,
                'ip': self._sonos_device.ip_address
            }
        return None

    def _discover_devices(self):
        """Search for Sonos devices on the network"""
        try:
            self._sonos_devices = list(soco.discover())
            self.logger.info("%d Sonos devices found", len(self._sonos_devices))
        except Exception as e:
            self.logger.error("Error searching for Sonos devices: %s", e)
            self._sonos_devices = []

    def _audio_processing_loop(self):
        """Process audio chunks and play them on the Sonos device"""
        while self.is_playing:
            try:
                # Get chunk from queue if available
                audio_chunk = None
                with self._lock:
                    if self._audio_queue:
                        audio_chunk = self._audio_queue.pop(0)
                
                if audio_chunk:
                    self._process_audio_chunk(audio_chunk)
                else:
                    # Short pause if no chunks are available
                    time.sleep(0.1)
                    
                    # Check if playback is complete
                    if self.is_busy and not self._audio_queue:
                        self._check_playback_status()
                        
            except Exception as e:
                self.logger.error("Error in audio processing: %s", e)
                time.sleep(0.5)  # Short pause on errors

    def _process_audio_chunk(self, audio_chunk):
        """Process a single audio chunk for playback on Sonos"""
        if not self._sonos_device:
            self.logger.warning("No Sonos device connected, audio chunk ignored")
            return
        
        was_busy = self.is_busy
        self.is_busy = True
        
        if not was_busy:
            self.event_bus.publish_async_from_thread(EventType.ASSISTANT_STARTED_RESPONDING)
            self.logger.debug("Audio playback started")
        
        try:
            # Create temporary file for the chunk
            self._file_counter += 1
            temp_file = os.path.join(self._temp_dir, f"audio_chunk_{self._file_counter}.mp3")
            
            # Write audio data to file
            with open(temp_file, 'wb') as f:
                f.write(audio_chunk)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written
            
            temp_path = Path(temp_file)
            self._current_file_path = temp_path
            
            # Create URL for the file
            file_url = self._http_server.get_url_for_file(temp_file)
            if not file_url:
                raise Exception("Could not create URL for audio file")
            
            self._current_file_url = file_url
            
            # Play on Sonos
            self._sonos_device.play_uri(file_url)
            
            # Wait briefly to ensure playback has started
            time.sleep(0.1)
            
        except Exception as e:
            self.logger.error("Error processing audio chunk: %s", e)
            self.is_busy = was_busy  # Restore status on error

    def _check_playback_status(self):
        """Check if playback is complete"""
        if not self._sonos_device:
            return
        
        try:
            # For Sonos: Check if playback is still running
            transport_info = self._sonos_device.get_current_transport_info()
            if transport_info['current_transport_state'] != 'PLAYING':
                # Playback is complete
                self.is_busy = False
                self._safely_notify_playback_completed()
                self._cleanup_old_files()
        except Exception as e:
            self.logger.error("Error checking playback status: %s", e)

    def _safely_notify_playback_completed(self):
        """Send 'playback completed' event in a thread-safe way"""
        try:
            self.event_bus.publish_async_from_thread(EventType.ASSISTANT_COMPLETED_RESPONDING)
            self.logger.debug("Audio playback stopped (event sent)")
        except Exception as e:
            self.logger.warning("Error sending event from thread: %s", e)
            try:
                self.event_bus.publish(EventType.ASSISTANT_COMPLETED_RESPONDING)
                self.logger.debug("Audio playback stopped (event sent via fallback)")
            except Exception as e2:
                self.logger.error("Error sending event via fallback: %s", e2)

    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            # Delete all files in temporary directory
            for file in os.listdir(self._temp_dir):
                file_path = os.path.join(self._temp_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            
            # Remove directory
            os.rmdir(self._temp_dir)
            self.logger.debug("Temporary files cleaned up")
        except Exception as e:
            self.logger.warning("Error cleaning up temporary files: %s", e)

    def _cleanup_old_files(self, keep_latest=5):
        """Delete older temporary files, keeping only the most recent ones"""
        try:
            files = [os.path.join(self._temp_dir, f) for f in os.listdir(self._temp_dir)
                    if os.path.isfile(os.path.join(self._temp_dir, f))]
            
            # Sort by creation time
            files.sort(key=lambda x: os.path.getctime(x))
            
            # Delete older files, keep the newest
            for old_file in files[:-keep_latest]:
                os.unlink(old_file)
                
            self.logger.debug("%d old temporary files deleted", len(files) - keep_latest)
        except Exception as e:
            self.logger.warning("Error cleaning up old files: %s", e)