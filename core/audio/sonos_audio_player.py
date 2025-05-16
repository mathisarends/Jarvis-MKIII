import array
import base64
import os
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Optional

import soco
from pydub import AudioSegment
from soco import SoCo
from typing_extensions import override

from core.audio.audio_player_base import AudioPlayer
from shared.event_bus import EventBus, EventType
from shared.singleton_meta_class import SingletonMetaClass


class CustomHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress HTTP request logs for cleaner output
        pass

    rbufsize = 64 * 1024

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        print(f"🔍 HTTP GET Request for: {self.path}")
        return super().do_GET()

    def do_HEAD(self):
        print(f"🔍 HTTP HEAD Request for: {self.path}")
        return super().do_HEAD()

    def guess_type(self, path):
        """Overridden method to provide correct MIME types for audio files."""
        _, ext = os.path.splitext(path)
        if ext.lower() == ".wav":
            return "audio/wav"
        elif ext.lower() == ".mp3":
            return "audio/mpeg"
        return super().guess_type(path)

    def translate_path(self, path):
        """Overridden to ensure proper file serving."""
        translated_path = super().translate_path(path)
        print(f"🔍 Translating path: {path} -> {translated_path}")
        if os.path.exists(translated_path):
            print(f"✅ File exists: {translated_path}")
        else:
            print(f"❌ File NOT found: {translated_path}")
        return translated_path


class SonosHTTPServer(metaclass=SingletonMetaClass):
    """Simple HTTP server to serve audio files for Sonos with singleton pattern."""

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
        self._ref_count = 0  # Reference counter for users

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
        print(f"🔍 HTTP server set working directory to: {self.project_dir}")

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
            print(f"✅ HTTP server on port {self.port} stopped (no more clients)")
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

        # Check if file exists
        if not file_path.exists():
            print(f"❌ File does not exist: {file_path}")
            return None

        # Relative path from project directory to file
        try:
            rel_path = file_path.relative_to(self.project_dir)
            print(f"🔍 Relative path: {rel_path}")
        except ValueError:
            print(f"⚠️ Warning: File not in project directory: {file_path}")
            return None

        url_path = str(rel_path).replace("\\", "/")
        url = f"http://{self.server_ip}:{self.port}/{url_path}"
        
        print(f"🔍 Created URL: {url}")
        return url

class SonosPlayer(AudioPlayer):
    """Implementation of AudioPlayer for Sonos speakers using queue functionality"""

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
        self.volume = 0.5
        self.event_bus = EventBus()

        # Sonos-specific attributes
        self._sonos_device: Optional[SoCo] = None
        self._sonos_devices: List[SoCo] = []

        # Create directories for sounds and temp files within the project structure
        if project_dir:
            self.project_dir = Path(project_dir)
        else:
            # If not specified, use the parent directory of the current file
            self.project_dir = Path(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )

        # Define paths for sounds and temp files
        self.sounds_dir = os.path.join(self.project_dir, "resources", "sounds")

        # Create temp directory for audio chunks within the project's resources directory
        self._temp_dir = os.path.join(self.project_dir, "resources", "sounds", "temp")
        os.makedirs(self._temp_dir, exist_ok=True)

        # Start the HTTP server
        self._http_server = SonosHTTPServer.get_instance(project_dir, port)

        # Queue management
        self._audio_queue = []
        self._lock = threading.Lock()
        self._audio_thread = None

        # Sonos-specific queue management
        self._queue_initialized = False
        self._current_playback_session = None
        self._file_counter = 0

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
                self.logger.info(
                    "Automatically connected to Sonos: %s",
                    self._sonos_device.player_name,
                )

                # Initialize Sonos player settings
                self._initialize_sonos_player()

        # Start audio thread
        self._audio_thread = threading.Thread(target=self._audio_processing_loop)
        self._audio_thread.daemon = True
        self._audio_thread.start()

        self.logger.info("SonosPlayer started")
        return True

    def _initialize_sonos_player(self):
        """Initialize the Sonos player for optimal audio streaming."""
        if not self._sonos_device:
            self.logger.warning("No Sonos device connected, cannot initialize")
            return

        try:
            # Set moderate volume
            self._sonos_device.volume = int(self.volume * 100)
            self.logger.debug("Set Sonos volume to %d%%", int(self.volume * 100))

            # Save the current queue and state for restoration later
            self._current_playback_session = {
                "uri": None,
                "metadata": None,
                "position": None,
                "state": None,
            }

            try:
                info = self._sonos_device.get_current_track_info()
                transport = self._sonos_device.get_current_transport_info()

                self._current_playback_session["uri"] = info.get("uri", "")
                self._current_playback_session["metadata"] = (
                    None  # Metadata is harder to save
                )
                self._current_playback_session["position"] = info.get(
                    "position", "0:00:00"
                )
                self._current_playback_session["state"] = transport.get(
                    "current_transport_state", "STOPPED"
                )

                self.logger.debug(
                    "Saved current playback state: %s", self._current_playback_session
                )
            except Exception as e:
                self.logger.warning("Could not save current playback state: %s", e)

            # Clear the Sonos queue for our use
            # We'll create a new queue for our audio chunks
            try:
                # Prepare device for streaming
                self._sonos_device.stop()
                self._sonos_device.clear_queue()
                self.logger.debug("Cleared Sonos queue")

                # Add a silent placeholder track to initialize queue
                self._queue_initialized = False

            except Exception as e:
                self.logger.warning("Could not clear Sonos queue: %s", e)

        except Exception as e:
            self.logger.error("Error initializing Sonos player: %s", e)

    @override
    def stop(self):
        """Stop the Sonos player and the HTTP server"""
        self.is_playing = False

        # Stop audio thread
        if self._audio_thread:
            self._audio_thread.join(timeout=2.0)

        # Restore previous Sonos state if available
        if self._sonos_device and self._current_playback_session:
            try:
                self._sonos_device.stop()

                if self._current_playback_session["uri"]:
                    self.logger.debug("Restoring previous Sonos state")
                    self._sonos_device.play_uri(
                        self._current_playback_session["uri"],
                        start=self._current_playback_session["position"],
                    )

                    if self._current_playback_session["state"] == "PAUSED_PLAYBACK":
                        self._sonos_device.pause()
                    elif self._current_playback_session["state"] == "STOPPED":
                        self._sonos_device.stop()
            except Exception as e:
                self.logger.warning("Error restoring Sonos state: %s", e)

        # Tempverzeichnis aufräumen
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
                    # Optional: clear Sonos queue
                    # self._sonos_device.clear_queue()
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
            self.logger.debug(
                "Audio chunk added to queue (length: %d bytes)", len(audio_data)
            )
        except Exception as e:
            self.logger.error("Error adding audio chunk: %s", e)

    @override
    def play_sound(self, sound_name: str) -> bool:
        """Play a sound file"""
        try:
            # Determine path to sound file
            if not sound_name.endswith(".mp3"):
                sound_name += ".mp3"

            # Direct path to the sound file using the project directory
            sound_path = os.path.join(
                self.project_dir, "resources", "sounds", sound_name
            )

            self.logger.info("Looking for sound file at: %s", sound_path)

            if not os.path.exists(sound_path):
                self.logger.warning("Sound file not found: %s", sound_path)
                return False

            # Build URL directly to avoid relative path issues
            sound_url = f"http://{self._http_server.server_ip}:{self._http_server.port}/resources/sounds/{sound_name}"

            self.logger.info("Playing sound URL: %s", sound_url)

            # Play on Sonos directly (not using queue for static sounds)
            if self._sonos_device:
                # First stop any current playback
                self._sonos_device.stop()

                # Play directly with transport uri
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
                self.logger.info(
                    "Connected to Sonos device: %s (%s)",
                    self._sonos_device.player_name,
                    ip_address,
                )
                self._initialize_sonos_player()
                return True

            # Connection via name
            if device_name:
                if not self._sonos_devices:
                    self._discover_devices()

                for device in self._sonos_devices:
                    if device_name.lower() in device.player_name.lower():
                        self._sonos_device = device
                        self.logger.info(
                            "Connected to Sonos device: %s", device.player_name
                        )
                        self._initialize_sonos_player()
                        return True

                self.logger.error("No Sonos device with name '%s' found", device_name)
                return False

            # Automatic connection to the first device
            if not self._sonos_devices:
                self._discover_devices()

            if self._sonos_devices:
                self._sonos_device = self._sonos_devices[0]
                self.logger.info(
                    "Automatically connected to Sonos device: %s",
                    self._sonos_device.player_name,
                )
                self._initialize_sonos_player()
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
        return [
            {"name": device.player_name, "ip": device.ip_address}
            for device in self._sonos_devices
        ]

    def get_current_device(self) -> Optional[Dict[str, str]]:
        """
        Return information about the currently connected Sonos device

        Returns:
            Dictionary with 'name' and 'ip' of the device or None
        """
        if self._sonos_device:
            return {
                "name": self._sonos_device.player_name,
                "ip": self._sonos_device.ip_address,
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
        """Process audio chunks and add them to the Sonos queue"""
        while self.is_playing:
            try:
                # Get audio chunk from our queue if available
                audio_chunk = None
                with self._lock:
                    if self._audio_queue:
                        audio_chunk = self._audio_queue.pop(0)

                if audio_chunk:
                    was_busy = self.is_busy
                    self.is_busy = True

                    if not was_busy:
                        self.event_bus.publish_async_from_thread(
                            EventType.ASSISTANT_STARTED_RESPONDING
                        )
                        self.logger.debug("Audio playback started")

                    # Process the audio chunk
                    self._process_and_queue_audio(audio_chunk)

                else:
                    # Check queue status and playback
                    if self.is_busy:
                        self._check_playback_status()

                    # Brief pause if no chunks
                    time.sleep(0.1)
            except Exception as e:
                self.logger.error("Error in audio processing loop: %s", e)
                time.sleep(0.5)

    def _process_and_queue_audio(self, audio_chunk):
        """Process an audio chunk, convert it to MP3, and add it to the Sonos queue."""
        if not self._sonos_device:
            self.logger.warning("No Sonos device connected, audio chunk ignored")
            return

        try:
            # Create a unique filename for this chunk
            self._file_counter += 1
            chunk_filename = f"audio_chunk_{self._file_counter}.mp3"
            temp_file = os.path.join(self._temp_dir, chunk_filename)

            # Convert PCM16 data to MP3 using pydub
            try:


                # Convert the PCM16 data (assuming 24kHz, mono) to MP3
                # First try interpreting as raw PCM16 bytes
                segment = AudioSegment(
                    data=audio_chunk,
                    sample_width=2,  # 16-bit
                    frame_rate=24000,  # Typical rate for OpenAI Audio
                    channels=1  # Mono
                )
                
                self.logger.debug("Successfully created AudioSegment from PCM data")
                    
                # Export as MP3
                segment.export(temp_file, format="mp3", bitrate="128k")
                
                # Log file details
                file_size = os.path.getsize(temp_file)
                self.logger.debug("Created MP3 file from PCM data: %s (size: %d bytes)", 
                                temp_file, file_size)
                
                # Verify the file exists and is not empty
                if not os.path.exists(temp_file) or file_size == 0:
                    self.logger.error("MP3 file creation failed or file is empty: %s", temp_file)
                    return
                    
            except Exception as e:
                self.logger.error("Error converting PCM to MP3: %s", e)
                
                # Fallback: Try with array conversion if direct method fails
                try:
                    # Ensure we have an even number of bytes for 16-bit samples
                    if len(audio_chunk) % 2 != 0:
                        audio_chunk = audio_chunk[:-1]
                    
                    # Convert bytes to array of shorts
                    samples = array.array('h')
                    samples.frombytes(audio_chunk)
                    
                    segment = AudioSegment(
                        data=samples.tobytes(),
                        sample_width=2,
                        frame_rate=24000,
                        channels=1
                    )
                    
                    # Export as MP3
                    segment.export(temp_file, format="mp3", bitrate="128k")
                    self.logger.debug("Successfully created MP3 with array conversion method")
                    
                    # Log file details
                    file_size = os.path.getsize(temp_file)
                    self.logger.debug("Created MP3 file from PCM data: %s (size: %d bytes)", 
                                    temp_file, file_size)
                    
                    # Verify the file exists and is not empty
                    if not os.path.exists(temp_file) or file_size == 0:
                        self.logger.error("MP3 file creation failed or file is empty: %s", temp_file)
                        return
                    
                except Exception as e2:
                    self.logger.error("Failed with array conversion too: %s", e2)
                    # Last resort: just write the raw data and hope Sonos can handle it
                    with open(temp_file, "wb") as f:
                        f.write(audio_chunk)
                        f.flush()
                        os.fsync(f.fileno())
                    self.logger.warning("Wrote raw audio data as last resort: %s", temp_file)

            # Create URL for the file
            file_url = f"http://{self._http_server.server_ip}:{self._http_server.port}/resources/sounds/temp/{chunk_filename}"

            # Initialize queue if needed
            if not self._queue_initialized:
                self._initialize_sonos_queue(file_url)
                return

            # Add to Sonos queue
            position = self._add_to_sonos_queue(file_url)
            self.logger.debug("Added MP3 audio to Sonos queue at position %d: %s", position, file_url)

        except Exception as e:
            self.logger.error("Error processing and queueing audio chunk: %s", e)

    def _initialize_sonos_queue(self, first_audio_url):
        """Initialize the Sonos queue with the first audio file and start playback."""
        try:
            # Clear any existing queue
            self._sonos_device.stop()
            self._sonos_device.clear_queue()

            # Add the first audio file to the queue
            position = self._add_to_sonos_queue(first_audio_url)

            # Start playing the queue
            self._sonos_device.play_from_queue(0)

            self._queue_initialized = True
            self.logger.debug(
                "Initialized Sonos queue with first audio: %s", first_audio_url
            )

        except Exception as e:
            self.logger.error("Error initializing Sonos queue: %s", e)

    def _add_to_sonos_queue(self, audio_url):
        """Add an audio file to the Sonos queue and return its position."""
        try:
            # Add to Sonos queue
            position = self._sonos_device.add_uri_to_queue(audio_url)

            # If this is the first track and we're not playing, start playing
            transport_info = self._sonos_device.get_current_transport_info()
            if transport_info["current_transport_state"] != "PLAYING":
                self._sonos_device.play()

            return position
        except Exception as e:
            self.logger.error("Error adding to Sonos queue: %s", e)
            return -1

    def _check_playback_status(self):
        """Check Sonos playback status and clean up when done."""
        if not self._sonos_device:
            return

        try:
            # Get queue info
            queue_size = len(self._sonos_device.get_queue())

            # Get current track info
            track_info = self._sonos_device.get_current_track_info()
            transport_info = self._sonos_device.get_current_transport_info()

            current_position = int(track_info.get("playlist_position", 0))
            transport_state = transport_info.get("current_transport_state")

            self.logger.debug(
                "Sonos status: %s, Track: %s/%s, Queue size: %s",
                transport_state,
                current_position,
                queue_size,
                queue_size,
            )

            # If we've played all our queued audio and the queue is empty or we're at the end
            # and no more chunks are expected, notify that playback is complete
            if transport_state != "PLAYING" or (
                current_position >= queue_size and len(self._audio_queue) == 0
            ):

                self.is_busy = False
                self._safely_notify_playback_completed()
                self._cleanup_old_files()

        except Exception as e:
            self.logger.error("Error checking playback status: %s", e)

    def _safely_notify_playback_completed(self):
        """Send 'playback completed' event in a thread-safe way"""
        try:
            self.event_bus.publish_async_from_thread(
                EventType.ASSISTANT_COMPLETED_RESPONDING
            )
            self.logger.debug("Audio playback stopped (event sent)")
        except Exception as e:
            self.logger.warning("Error sending event from thread: %s", e)
            try:
                self.event_bus.publish(EventType.ASSISTANT_COMPLETED_RESPONDING)
                self.logger.debug("Audio playback stopped (event sent via fallback)")
            except Exception as e2:
                self.logger.error("Error sending event via fallback: %s", e2)

    def _cleanup_temp_files(self):
        """Clean up temporary files in the temp directory"""
        try:
            # Delete all files in temporary directory
            for file in os.listdir(self._temp_dir):
                file_path = os.path.join(self._temp_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

            self.logger.debug("Temporary files cleaned up")
        except Exception as e:
            self.logger.warning("Error cleaning up temporary files: %s", e)

    def _cleanup_old_files(self, keep_latest=5):
        """Delete older temporary files, keeping only the most recent ones"""
        try:
            files = [
                os.path.join(self._temp_dir, f)
                for f in os.listdir(self._temp_dir)
                if os.path.isfile(os.path.join(self._temp_dir, f))
            ]

            # Sort by creation time
            files.sort(key=lambda x: os.path.getctime(x))

            # Delete older files, keep the newest
            files_to_delete = files[:-keep_latest] if len(files) > keep_latest else []
            for old_file in files_to_delete:
                os.unlink(old_file)

            if files_to_delete:
                self.logger.debug(
                    "%d old temporary files deleted", len(files_to_delete)
                )
        except Exception as e:
            self.logger.warning("Error cleaning up old files: %s", e)
