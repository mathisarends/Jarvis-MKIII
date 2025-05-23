import array
import asyncio
import base64
import os
import re
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import List, Optional

import soco
from pydub import AudioSegment
from soco import SoCo
from typing_extensions import override

from core.audio.audio_player_base import AudioPlayer
from resources.config import RATE
from shared.event_bus import EventBus, EventType
from shared.singleton_meta_class import SingletonMetaClass


class CustomHandler(SimpleHTTPRequestHandler):
    """HTTP-Handler für das Sonos-System - ohne Deduplizierung"""

    def log_message(self, format, *args):
        # Suppress HTTP request logs for cleaner output
        pass

    rbufsize = 64 * 1024

    # Cache für Anfragen-Logging (nur für Logging, nicht für Deduplizierung)
    _request_cache = {}

    # Audio-Chunk-Pattern für Erkennung (nur für Logging-Zwecke)
    _audio_chunk_pattern = re.compile(r"/resources/sounds/temp/audio_chunk_\d+\.mp3$")

    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def is_audio_chunk(self, path):
        """Prüft, ob der Pfad einem Audio-Chunk entspricht"""
        return bool(self._audio_chunk_pattern.match(path))

    def do_GET(self):
        """Handle GET requests without deduplication"""
        # Standardmäßiges Logging
        path_key = f"get_{self.path}"
        last_time = self._request_cache.get(path_key, 0)
        current_time = time.time()

        if (
            current_time - last_time < 5
        ):  # Wiederholte Anfrage in den letzten 5 Sekunden
            print(f"↩️ Repeat GET request for: {self.path}")
        else:
            print(f"🔍 HTTP GET Request for: {self.path}")
            self._request_cache[path_key] = current_time

        return super().do_GET()

    def do_HEAD(self):
        """Handle HEAD requests without deduplication"""
        path_key = f"head_{self.path}"
        last_time = self._request_cache.get(path_key, 0)
        current_time = time.time()

        if current_time - last_time < 5:
            print(f"↩️ Repeat HEAD request for: {self.path}")
        else:
            print(f"🔍 HTTP HEAD Request for: {self.path}")
            self._request_cache[path_key] = current_time

        return super().do_HEAD()

    def end_headers(self):
        """Add optimized caching headers"""
        if self.is_audio_chunk(self.path):
            self.send_header("Cache-Control", "public, max-age=60")
        else:
            self.send_header("Cache-Control", "public, max-age=300")

        # ETag für effizientes Caching
        file_path = self.translate_path(self.path)
        if os.path.exists(file_path):
            stat_result = os.stat(file_path)
            etag = f'"{stat_result.st_mtime}_{stat_result.st_size}"'
            self.send_header("ETag", etag)

            # Last-Modified für HTTP-Caching
            last_modified = self.date_time_string(int(stat_result.st_mtime))
            self.send_header("Last-Modified", last_modified)

        # Wichtige Header für Audio-Streaming
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Connection", "keep-alive")

        super().end_headers()

    def guess_type(self, path):
        """Overridden method to provide correct MIME types for audio files."""
        _, ext = os.path.splitext(path)
        if ext.lower() == ".wav":
            return "audio/wav"
        if ext.lower() == ".mp3":
            return "audio/mpeg"
        return super().guess_type(path)

    def translate_path(self, path):
        """Overridden to ensure proper file serving with optimized logging."""
        translated_path = super().translate_path(path)

        path_key = f"path_{path}"
        last_time = self._request_cache.get(path_key, 0)
        current_time = time.time()

        if current_time - last_time < 5:
            if not os.path.exists(translated_path):
                print(f"❌ File still NOT found: {translated_path}")
            return translated_path

        self._request_cache[path_key] = current_time

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
    def __init__(self, project_dir=None, port=8010):
        """
        Initialize the SonosPlayer.

        Args:
            project_dir: Base directory for the HTTP server
            port: Port for the HTTP server
        """
        # Basic attributes
        self.is_playing = False
        self.is_busy = False
        self.volume = 0.25
        self.event_bus = EventBus()
        self.last_state_change = time.time()
        self.min_state_change_interval = 0.5

        # Sonos-specific attributes
        self._sonos_device: Optional[SoCo] = None
        self._sonos_devices: List[SoCo] = []
        self._queued_urls = set()  # Set to track URLs already in the queue
        self._needs_queue_reset = False  # Flag zur Steuerung von Queue-Resets

        # Neue Attribute für sequentielle Wiedergabe
        self._expected_next_position = (
            1  # Position, die als nächstes gespielt werden sollte
        )
        self._queue_management_lock = (
            threading.Lock()
        )
        self._playback_sequence = []
        self._playing_position = 0

        if project_dir:
            self.project_dir = Path(project_dir)
        else:
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
        self._state_lock = threading.Lock()
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
            try:
                # Prepare device for streaming
                self._sonos_device.stop()
                self._sonos_device.clear_queue()
                self.logger.debug("Cleared Sonos queue")

                # Reset queue tracking
                self._queued_urls.clear()
                self._needs_queue_reset = False
                self._queue_initialized = False

                # Reset sequence tracking
                self._playback_sequence = []
                self._playing_position = 0
                self._expected_next_position = 1

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
        self._cleanup_all_temp_files()

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
                    # Sonos-Queue leeren
                    self._sonos_device.clear_queue()
                    # URL-Tracking zurücksetzen
                    self._queued_urls.clear()
                    # Sequenz-Tracking zurücksetzen
                    self._playback_sequence = []
                    self._playing_position = 0
                    self._expected_next_position = 1
                    # Queue-Reset für die nächste Antwort aktivieren
                    self._needs_queue_reset = True
                except Exception as e:
                    self.logger.error("Error stopping Sonos playback: %s", e)

            # Status zurücksetzen mit Mutex-Schutz
            with self._state_lock:
                if self.is_busy:
                    self.is_busy = False
                    self.last_state_change = time.time()
                    threading.Thread(target=self._send_complete_event).start()

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
                try:
                    self._sonos_device.stop()
                    self._sonos_device.play_uri(sound_url)
                    return True
                except Exception as e:
                    self.logger.error("Error playing sound on Sonos: %s", e)
                    return False
            else:
                self.logger.warning("No Sonos device connected")
                return False

        except Exception as e:
            self.logger.error("Error playing sound %s: %s", sound_name, e)
            return False
    
    @override
    def stop_sound(self):
        """Stop the currently playing sound"""
        try:
            if self._sonos_device:
                self._sonos_device.stop()
                self.logger.debug("Stopped current sound playback")
                return True
            else:
                self.logger.warning("No Sonos device connected, cannot stop sound")
                return False
        except Exception as e:
            self.logger.error("Error stopping sound: %s", e)
            return False

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
        """Process an audio chunk, convert it to MP3, and add it to the Sonos queue with sequence control."""
        if not self._sonos_device:
            self.logger.warning("No Sonos device connected, audio chunk ignored")
            return

        try:
            # Zustandsänderung mit Lock schützen
            with self._state_lock:
                current_time = time.time()
                was_busy = self.is_busy
                self.is_busy = True

                # Nur ein Event senden, wenn wir gerade erst angefangen haben zu spielen
                # UND eine Mindestzeit seit dem letzten Event vergangen ist
                if (
                    not was_busy
                    and (current_time - self.last_state_change)
                    >= self.min_state_change_interval
                ):
                    self.last_state_change = current_time
                    # Event in einem separaten Thread senden
                    threading.Thread(target=self._send_start_event).start()

                    # Wenn wir wieder anfangen zu sprechen und ein Reset benötigt wird, setze dies zurück
                    if self._needs_queue_reset:
                        self._sonos_device.stop()
                        self._sonos_device.clear_queue()
                        self._queued_urls.clear()
                        self._needs_queue_reset = False
                        self._queue_initialized = False

                        # Sequenzierung zurücksetzen
                        self._playback_sequence = []
                        self._playing_position = 0
                        self._expected_next_position = 1

                        self.logger.debug("Queue reset at start of new response")

            # Create a unique filename for this chunk
            self._file_counter += 1
            chunk_filename = f"audio_chunk_{self._file_counter}.mp3"
            temp_file = os.path.join(self._temp_dir, chunk_filename)

            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                self.logger.debug(f"Using existing file: {temp_file}")
            else:
                try:
                    segment = AudioSegment(
                        data=audio_chunk,
                        sample_width=2,
                        frame_rate=RATE,
                        channels=1,
                    )

                    self.logger.debug("Successfully created AudioSegment from PCM data")

                    # Export as MP3
                    segment.export(temp_file, format="mp3", bitrate="128k")

                    # Log file details
                    file_size = os.path.getsize(temp_file)
                    self.logger.debug(
                        "Created MP3 file from PCM data: %s (size: %d bytes)",
                        temp_file,
                        file_size,
                    )

                    # Verify the file exists and is not empty
                    if not os.path.exists(temp_file) or file_size == 0:
                        self.logger.error(
                            "MP3 file creation failed or file is empty: %s", temp_file
                        )
                        return

                except Exception as e:
                    self.logger.error("Error converting PCM to MP3: %s", e)

                    # Fallback: Try with array conversion if direct method fails
                    try:
                        # Ensure we have an even number of bytes for 16-bit samples
                        if len(audio_chunk) % 2 != 0:
                            audio_chunk = audio_chunk[:-1]

                        # Convert bytes to array of shorts
                        samples = array.array("h")
                        samples.frombytes(audio_chunk)

                        segment = AudioSegment(
                            data=samples.tobytes(),
                            sample_width=2,
                            frame_rate=RATE,
                            channels=1,
                        )

                        # Export as MP3
                        segment.export(temp_file, format="mp3", bitrate="128k")
                        self.logger.debug(
                            "Successfully created MP3 with array conversion method"
                        )

                        # Log file details
                        file_size = os.path.getsize(temp_file)
                        self.logger.debug(
                            "Created MP3 file from PCM data: %s (size: %d bytes)",
                            temp_file,
                            file_size,
                        )

                        # Verify the file exists and is not empty
                        if not os.path.exists(temp_file) or file_size == 0:
                            self.logger.error(
                                "MP3 file creation failed or file is empty: %s",
                                temp_file,
                            )
                            return

                    except Exception as e2:
                        self.logger.error("Failed with array conversion too: %s", e2)
                        # Last resort: just write the raw data and hope Sonos can handle it
                        with open(temp_file, "wb") as f:
                            f.write(audio_chunk)
                            f.flush()
                            os.fsync(f.fileno())
                        self.logger.warning(
                            "Wrote raw audio data as last resort: %s", temp_file
                        )

            # Create URL for the file
            file_url = f"http://{self._http_server.server_ip}:{self._http_server.port}/resources/sounds/temp/{chunk_filename}"

            # Initialize queue if needed
            if not self._queue_initialized:
                self._initialize_sonos_queue(file_url)
                # Sequenzierung initialisieren
                with self._queue_management_lock:
                    self._playback_sequence = [file_url]
                    self._playing_position = 0
                return

            # Add to Sonos queue with sequence control
            with self._queue_management_lock:
                position = self._add_to_sonos_queue_in_sequence(file_url)

            if position > 0:
                self.logger.debug(
                    "Added MP3 audio to Sonos queue at position %d: %s",
                    position,
                    file_url,
                )
            else:
                self.logger.debug("Skipped duplicate addition to queue: %s", file_url)

        except Exception as e:
            self.logger.error("Error processing and queueing audio chunk: %s", e)

    def _initialize_sonos_queue(self, first_audio_url):
        """Initialize the Sonos queue with the first audio file and start playback."""
        try:
            # Clear any existing queue
            self._sonos_device.stop()
            self._sonos_device.clear_queue()
            self._queued_urls.clear()

            # Add the first audio file to the queue
            self._add_to_sonos_queue_in_sequence(first_audio_url)

            # Kurze Verzögerung einbauen, um sicherzustellen, dass der erste Chunk vollständig geladen ist
            self.logger.debug("Waiting for first audio chunk to be fully indexed...")

            # Start playing the queue
            self._sonos_device.play_from_queue(0)

            self._queue_initialized = True
            self.logger.debug(
                "Initialized Sonos queue with first audio: %s", first_audio_url
            )

        except Exception as e:
            self.logger.error("Error initializing Sonos queue: %s", e)

    def _add_to_sonos_queue_in_sequence(self, audio_url):
        """Add an audio file to the Sonos queue in the correct sequence."""
        try:
            # Überprüfen, ob diese URL bereits in der Queue ist
            if audio_url in self._queued_urls:
                self.logger.debug(f"Skipping duplicate URL in queue: {audio_url}")
                return -1  # Skip duplicates

            # Sequenznummer aus der URL extrahieren
            try:
                # Extrahiere Nummer aus "audio_chunk_X.mp3"
                file_name = audio_url.split("/")[-1]
                chunk_num = int(file_name.split("_")[2].split(".")[0])

                # In chronologischer Reihenfolge zur Sequenz hinzufügen
                self._playback_sequence.append(audio_url)

                # Sortieren der _playback_sequence nach Chunk-Nummer
                self._playback_sequence.sort(
                    key=lambda url: int(url.split("/")[-1].split("_")[2].split(".")[0])
                )

                self.logger.debug(
                    f"Current sequence: {[url.split('/')[-1] for url in self._playback_sequence]}"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to extract sequence number: {e}, adding to end"
                )
                self._playback_sequence.append(audio_url)

            # Bei einer neuen Gesprächsrunde die Queue komplett leeren
            if self._needs_queue_reset:
                self._sonos_device.stop()
                self._sonos_device.clear_queue()
                self._queued_urls.clear()
                self._needs_queue_reset = False
                self.logger.debug("Queue reset for new conversation")

            # Sonos-Warteschlange neu aufbauen um richtige Reihenfolge zu garantieren
            if len(self._playback_sequence) > 1:
                position_in_list = self._playback_sequence.index(audio_url)

                # Wenn dieses Audio-Chunk nicht das nächste in der Sequenz ist,
                # organisieren wir die gesamte Queue neu um die korrekte Reihenfolge wiederherzustellen
                if position_in_list != len(self._playback_sequence) - 1:
                    # Warte kurz mit dem Hinzufügen, bis die Datei vollständig geschrieben ist
                    time.sleep(0.1)

                    # Aktuelle Wiedergabeposition merken
                    try:
                        current_position = (
                            int(
                                self._sonos_device.get_current_track_info().get(
                                    "playlist_position", 1
                                )
                            )
                            - 1
                        )
                        if current_position < 0:
                            current_position = 0
                    except:
                        current_position = 0

                    # Leere die bestehende Queue
                    self._sonos_device.stop()
                    self._sonos_device.clear_queue()
                    self._queued_urls.clear()

                    # Füge alle Dateien in der sortierten Reihenfolge hinzu
                    for idx, url in enumerate(self._playback_sequence):
                        pos = self._sonos_device.add_uri_to_queue(url)
                        self._queued_urls.add(url)
                        self.logger.debug(
                            f"Re-added {url.split('/')[-1]} at position {pos}"
                        )

                    # Wiedergabe fortsetzen, wenn wir unterbrochen haben (TODO: Ich glaube hierhin sollte man noch schauen)
                    if current_position < len(self._playback_sequence):
                        self._sonos_device.play_from_queue(current_position)
                        self.logger.debug(
                            f"Resumed playback from position {current_position}"
                        )
                    else:
                        self._sonos_device.play_from_queue(0)

                    return len(self._playback_sequence)
                else:
                    # Normaler Ablauf: Einfach das Element ans Ende der Queue anhängen
                    position = self._sonos_device.add_uri_to_queue(audio_url)
                    # URL tracken
                    self._queued_urls.add(audio_url)
            else:
                # Erster Eintrag in der Liste
                position = self._sonos_device.add_uri_to_queue(audio_url)
                self._queued_urls.add(audio_url)

            # Starte Wiedergabe, wenn wir noch nicht spielen
            transport_info = self._sonos_device.get_current_transport_info()
            if transport_info["current_transport_state"] != "PLAYING":
                self._sonos_device.play()

            return position
        except Exception as e:
            self.logger.error(f"Error adding to Sonos queue in sequence: {e}")
            return -1

    def _check_playback_status(self):
        """Check Sonos playback status and ensure sequential playback."""
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

            # Überprüfung, ob Sonos den aktuellen Track übersprungen hat
            with self._queue_management_lock:
                if current_position > 0 and self._playing_position > 0:
                    expected_next = self._playing_position + 1
                    if (
                        current_position != expected_next
                        and current_position != self._playing_position
                    ):
                        self.logger.warning(
                            f"Detected out-of-sequence playback: expected={expected_next}, actual={current_position}"
                        )
                        # Versuche, zur richtigen Position zu springen
                        if expected_next <= queue_size:
                            self._sonos_device.play_from_queue(
                                expected_next - 1
                            )  # Sonos verwendet 0-indexiert für play_from_queue
                            self.logger.debug(
                                f"Corrected playback position to {expected_next}"
                            )

                # Aktuelle Position aktualisieren
                if current_position > 0:
                    self._playing_position = current_position

            # If we've played all our queued audio and the queue is empty or we're at the end
            # and no more chunks are expected, notify that playback is complete
            if transport_state != "PLAYING" or (
                current_position >= queue_size and len(self._audio_queue) == 0
            ):
                # Zustandsänderung mit Lock schützen
                with self._state_lock:
                    current_time = time.time()

                    # Prüfen, ob genug Zeit seit dem letzten Event vergangen ist
                    if (
                        self.is_busy
                        and (current_time - self.last_state_change)
                        >= self.min_state_change_interval
                    ):
                        self.is_busy = False
                        self.last_state_change = current_time
                        # Event in einem separaten Thread senden
                        threading.Thread(target=self._send_complete_event).start()
                        # Nächste Antwort sollte mit frischer Queue beginnen
                        self._needs_queue_reset = True

        except Exception as e:
            self.logger.error("Error checking playback status: %s", e)

    def _send_start_event(self):
        """Sendet das Start-Event in einem eigenen Thread"""
        try:
            self.logger.debug("Audio playback started - sending event")
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Fire the event synchronously to avoid event loop issues
            self.event_bus.publish(EventType.ASSISTANT_STARTED_RESPONDING)

            # Close the loop
            loop.close()
        except Exception as e:
            self.logger.error(f"Failed to send start event: {e}")

    def _send_complete_event(self):
        """Sendet das Complete-Event in einem eigenen Thread und räumt alle temporären Dateien auf"""
        try:
            self.logger.debug("Audio playback complete - sending event")

            self.event_bus.publish(EventType.ASSISTANT_COMPLETED_RESPONDING)

            self.logger.debug("Waiting 1 second before cleaning up files...")
            time.sleep(1)

            self._cleanup_all_temp_files()

            self._file_counter = 0
            self.logger.debug("File counter reset to 0 for next response")

        except Exception as e:
            self.logger.error(f"Failed to send complete event: {e}")

    def _cleanup_all_temp_files(self):
        """Alle temporären Dateien im Temp-Verzeichnis aufräumen"""
        try:
            # Alle Dateien im Temp-Verzeichnis auflisten
            files = [
                os.path.join(self._temp_dir, f)
                for f in os.listdir(self._temp_dir)
                if os.path.isfile(os.path.join(self._temp_dir, f))
            ]

            # Alle Dateien löschen
            for file_path in files:
                try:
                    os.unlink(file_path)
                    chunk_name = os.path.basename(file_path)
                    file_url = f"http://{self._http_server.server_ip}:{self._http_server.port}/resources/sounds/temp/{chunk_name}"
                    if file_url in self._queued_urls:
                        self._queued_urls.remove(file_url)
                    self.logger.debug(f"Deleted temporary file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Could not delete file {file_path}: {e}")

            # URL-Tracking zurücksetzen
            self._queued_urls.clear()

            # Sequenzierung zurücksetzen
            self._playback_sequence = []
            self._playing_position = 0
            self._expected_next_position = 1

            self.logger.debug("All temporary files cleaned up and tracking reset")
        except Exception as e:
            self.logger.warning(f"Error cleaning up all temporary files: {e}")
