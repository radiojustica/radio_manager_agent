import subprocess
import threading
import os
import time
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Queue, Full
from typing import Optional


class NDIRelayServer(BaseHTTPRequestHandler):
    """Icecast-compatible streaming server that reads from a shared broadcast queue."""

    # Suppress default request logging to avoid flooding the console
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path != '/live.mp3':
            self.send_error(404, "Not Found")
            return

        # Create a private queue for this client
        client_queue: Queue = Queue(maxsize=100)
        self.server.add_client(client_queue)

        try:
            self.protocol_version = 'HTTP/1.0'
            self.send_response(200)
            self.send_header('Content-type', 'audio/mpeg')
            self.send_header('icy-name', 'NDI_RADIO_LIVE')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store')
            self.send_header('Connection', 'close')
            self.end_headers()

            # Stream data from the shared broadcaster
            while self.server.running:
                try:
                    chunk = client_queue.get(timeout=2.0)
                    if chunk is None:
                        break  # Sentinel value — broadcaster is shutting down
                    self.wfile.write(chunk)
                except Exception:
                    break  # Connection lost or timeout
        finally:
            self.server.remove_client(client_queue)


class Broadcaster(HTTPServer):
    """HTTP Server that manages multiple audio clients."""

    def __init__(self, server_address, RequestHandlerClass, process, logger):
        super().__init__(server_address, RequestHandlerClass)
        self.ffmpeg_process = process
        self.logger = logger
        self.clients: list = []
        self.running = True
        self.lock = threading.Lock()

    def add_client(self, queue: Queue):
        with self.lock:
            self.clients.append(queue)
        self.logger.info(f"NDI client connected. Total: {len(self.clients)}")

    def remove_client(self, queue: Queue):
        with self.lock:
            if queue in self.clients:
                self.clients.remove(queue)
        self.logger.info(f"NDI client disconnected. Total: {len(self.clients)}")

    def broadcast(self):
        """Dedicated thread to read from FFmpeg stdout and push to all clients."""
        self.logger.info("NDI Broadcaster thread started.")
        try:
            while self.running and self.ffmpeg_process.poll() is None:
                data = self.ffmpeg_process.stdout.read(1024)
                if not data:
                    time.sleep(0.01)
                    continue

                with self.lock:
                    for client_q in list(self.clients):
                        try:
                            client_q.put_nowait(data)
                        except Full:
                            # Drop data for slow clients rather than blocking the broadcaster
                            pass
        except Exception as e:
            self.logger.error(f"NDI Broadcaster error: {e}")
        finally:
            # Send sentinel to all clients so they exit cleanly
            with self.lock:
                for client_q in list(self.clients):
                    try:
                        client_q.put_nowait(None)
                    except Full:
                        pass
            self.logger.info("NDI Broadcaster thread stopped.")

    def shutdown_gracefully(self):
        """Stops the broadcaster and the HTTP server."""
        self.running = False
        self.shutdown()
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self.ffmpeg_process.terminate()
            self.logger.info("FFmpeg process terminated.")


class NDIRelay:
    def __init__(self, ffmpeg_path: str, audio_device: str = "Webcam 1 (NDI Webcam Audio)"):
        self.ffmpeg_path = ffmpeg_path
        self.audio_device = audio_device
        self.logger = logging.getLogger("RadioManagerAgent.NDIRelay")
        self.process: Optional[subprocess.Popen] = None
        self.server: Optional[Broadcaster] = None
        self._log_handle = None

    def start(self, port: int = 8090) -> Optional[str]:
        """Starts FFmpeg and the multi-client broadcast server.

        Returns:
            The stream URL on success, or None on failure.
        """
        log_file = os.path.join("logs", "ffmpeg_relay.log")
        os.makedirs("logs", exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-thread_queue_size", "1024",
            "-f", "dshow",
            "-rtbufsize", "100M",
            "-use_wallclock_as_timestamps", "1",
            "-i", f"audio={self.audio_device}",
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-f", "mp3",
            "-flush_packets", "1",
            "-"
        ]

        try:
            self.logger.info(f"Launching NDI Relay Broadcaster: {self.audio_device}")

            # Open log file — stored as instance attribute so it can be closed on stop()
            self._log_handle = open(log_file, "w", encoding="utf-8")

            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=self._log_handle,
                bufsize=0,  # Unbuffered for low latency
                creationflags=creation_flags
            )

            self.server = Broadcaster(
                ('127.0.0.1', port), NDIRelayServer, self.process, self.logger
            )

            # Start the FFmpeg reader thread
            threading.Thread(target=self.server.broadcast, daemon=True).start()

            # Start the HTTP server thread
            threading.Thread(target=self.server.serve_forever, daemon=True).start()

            stream_url = f"http://localhost:{port}/live.mp3"
            self.logger.info(f"NDI Relay started. Stream URL: {stream_url}")
            return stream_url

        except Exception as e:
            self.logger.error(f"Failed to start NDI relay: {e}")
            self._close_log_handle()
            return None

    def stop(self):
        """Gracefully stops the relay server and FFmpeg process."""
        if self.server:
            self.server.shutdown_gracefully()
            self.server = None
        self._close_log_handle()
        self.logger.info("NDI Relay stopped.")

    def _close_log_handle(self):
        """Closes the FFmpeg log file handle if open."""
        if self._log_handle and not self._log_handle.closed:
            self._log_handle.close()
            self._log_handle = None


