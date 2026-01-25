import io
import time
from datetime import datetime
import os
import shutil
import pdb
import argparse
import threading
import subprocess
import wave
import queue

import sounddevice as sd
import numpy as np
from pydub import AudioSegment


class AudioRecorder:
    def __init__(self, device_name, output_dir, threshold_db=-30, sample_rate=44100, channels=1, amplification=1.0):
        """
        :param threshold_db: The threshold in dB for silence detection
        :param sample_rate: The sample rate of the audio
        :param channels: The number of channels
        :param amplification: The amplification factor
        """
        self.device_name = device_name
        self.output_dir = output_dir
        self.threshold_db = threshold_db
        self.sample_rate = sample_rate
        self.channels = channels
        self.amplification = amplification
        self.chunk_duration = 0.1  # seconds
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        self.mp3_buffer = AudioSegment.empty()
        self.current_file = None
        self.recording = False
        self.silence_duration = 0
        self.stream = None
        self.device_id = None
        self.running = False
        self.last_device_name = None
        # Whether we've written audio to the buffer (and not just silence)
        self.wrote_audio = False
        self._reconnect_lock = threading.Lock()
        self._is_reconnecting = False
        self._monitor_thread = None
        self.audio_queue = queue.Queue()
        self._worker_thread = None

    def get_bluetooth_device_id(self):
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            print(f'Device {i}: {device["name"]}')
            if self.device_name == device['name']:
                print(f'found device name: {device["name"]}, id: {i}')
                self.last_device_name = device['name']
                return i
        raise ValueError("No Bluetooth input device found")

    def get_meter_string(self, db):
        meter_width = shutil.get_terminal_size().columns - 10
        min_db = -60
        max_db = 0

        db = max(min_db, min(db, max_db))
        fill_count = int((db - min_db) * meter_width / (max_db - min_db))

        meter = ""
        for i in range(meter_width):
            if i < fill_count:
                if i / meter_width < 0.7:
                    meter += "\033[92m█\033[0m"
                elif i / meter_width < 0.9:
                    meter += "\033[93m█\033[0m"
                else:
                    meter += "\033[91m█\033[0m"
            else:
                meter += "░"

        return f"{meter} {db:>5.1f}dB"

    def audio_callback(self, indata, frames, time, status):
        if status:
            if isinstance(status, sd.CallbackAbort):
                raise Exception(
                    f'Device disconnect detected - used to handle here, ' \
                    f'but now unhandled. Status: {status}')

        # Simply put the audio data into the queue for the worker thread to process
        self.audio_queue.put(indata.copy())

    def _processing_worker(self):
        """Background worker thread to handle audio processing and saving"""
        print("Audio processing worker started.")
        while self.running or not self.audio_queue.empty():
            try:
                # Use a timeout so we can periodically check if self.running is False
                audio_data = self.audio_queue.get(timeout=0.5)
                if audio_data is None:
                    break
            except queue.Empty:
                continue

            if not self.recording:
                self.start_new_recording()

            try:
                # Convert to float32 if not already
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)

                # Calculate volume in dB
                rms = np.sqrt(np.mean(audio_data**2))
                db = 20 * np.log10(rms) if rms > 0 else -100

                # Print the meter
                print("\033[A\033[K" + self.get_meter_string(db))

                # Convert numpy array to wav bytes
                bytes_io = io.BytesIO()
                with wave.open(bytes_io, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes((audio_data * 32767).astype(np.int16))

                # Convert wav bytes to AudioSegment and add to buffer
                bytes_io.seek(0)
                segment = AudioSegment.from_wav(bytes_io)

                if db > self.threshold_db:
                    self.wrote_audio = True
                    # Amplify the audio if there's something to record
                    # Note: amplification should happen before encoding if possible,
                    # but we are using the segment already created.
                    if self.amplification != 1.0:
                        segment = segment + (20 * np.log10(self.amplification))

                    self.silence_duration = 0
                    self.mp3_buffer += segment

                else:
                    self.silence_duration += self.chunk_duration
                    if self.silence_duration > 2.0:
                        if len(self.mp3_buffer.raw_data) >= 135 * 1024 * 1024:
                            self.save_current_file()
                            self.start_new_recording()
                    if self.recording:
                        if self.silence_duration <= 2.0:
                            self.mp3_buffer += segment

            except Exception as e:
                print(f"\nError in processing worker: {e}")
                # We don't reconnect here; the main loop or monitor handles that.

            self.audio_queue.task_done()
        print("Audio processing worker stopped.")

    def handle_disconnect(self):
        """Handle device disconnection and initiate reconnection"""
        with self._reconnect_lock:
            if self._is_reconnecting:
                return
            self._is_reconnecting = True

        if self.stream:
            print(f'\nDevice disconnect detected - closing stream and trying reconnect...')
            self.stream.close()
        self.stream = None

        # Run reconnection in a separate thread so we don't block the callback or main loop
        threading.Thread(target=self.reconnect_device, daemon=True).start()

    def reconnect_device(self):
        """Attempt to reconnect to the Bluetooth device"""
        try:
            while self.running:
                try:
                    # Reset sounddevice because it retains memory of initial device connection
                    sd._terminate()
                    sd._initialize()
                    # Try to find the same device that was previously connected
                    devices = sd.query_devices()
                    found_device = False
                    for i, device in enumerate(devices):
                        if self.last_device_name and self.last_device_name == device['name']:
                            self.device_id = i
                            found_device = True
                            break

                    if found_device:
                        # Test the device by creating a new stream
                        self.create_stream()
                        print(f"\nReconnected to device: {sd.query_devices(self.device_id)['name']}")
                        print()  # Add an extra line for the meter
                        return

                except Exception as e:
                    print(f"\rAttempting to reconnect... ({e})", end="")
                    time.sleep(1)
        finally:
            with self._reconnect_lock:
                self._is_reconnecting = False

    def create_stream(self):
        """Create a new audio input stream"""
        self.stream = sd.InputStream(
            device=self.device_id,
            channels=self.channels,
            samplerate=self.sample_rate,
            callback=self.audio_callback,
            blocksize=self.chunk_samples
        )
        self.stream.start()

    def start_new_recording(self):
        self.wrote_audio = False
        self.recording = True
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.current_file = f"{timestamp}_recording.mp3"
        self.mp3_buffer = AudioSegment.empty()
        print(f"\nStarted new recording: {self.current_file}")
        print()  # Add an extra line for the meter

    def save_current_file(self):
        if not self.wrote_audio:
            return

        if self.mp3_buffer and self.current_file:
            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, self.current_file)
            self.mp3_buffer.export(filepath, format="mp3")
            print(f"\nSaved recording: {filepath}")
            self.mp3_buffer = AudioSegment.empty()

    def start_recording(self):
        try:
            self.running = True
            self.device_id = self.get_bluetooth_device_id()
            print(f"Using device: {sd.query_devices(self.device_id)['name']}")

            # Start worker thread
            self._worker_thread = threading.Thread(target=self._processing_worker, daemon=True)
            self._worker_thread.start()

            self.create_stream()

            # Start monitoring thread once
            if not self._monitor_thread or not self._monitor_thread.is_alive():
                print(f"Starting Bluetooth monitor for: {self.device_name}")
                self._monitor_thread = monitor_bluetooth_device(
                    self.device_name,
                    on_disconnect=self.handle_disconnect,
                    check_interval=1
                )

            while self.running:
                if not self.stream or not self.stream.active:
                    # In case the monitor thread misses it or stream fails for other reasons
                    self.handle_disconnect()
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nRecording stopped.")
            self.running = False
            # Tell worker to finish
            self.audio_queue.put(None)
            if self._worker_thread:
                self._worker_thread.join()

            if self.recording:
                self.save_current_file()
            if self.stream:
                self.stream.close()
        except Exception as e:
            print(f"Error: {e}")
            self.running = False
            self.audio_queue.put(None)
            if self._worker_thread:
                self._worker_thread.join()

            if self.stream:
                self.stream.close()


def detect_bluetooth_disconnection(device_name):
    """
    Detect Bluetooth device disconnection on iOS using system_profiler

    :param device_name: Name of the Bluetooth device to monitor
    :return: Boolean indicating if device is disconnected
    """
    try:
        result = subprocess.run(['ioreg', '-p', 'IOUSB'],
                                capture_output=True, text=True)
        return device_name not in result.stdout
    except Exception as e:
        print(f"Error detecting device: {e}")
        return False


def monitor_bluetooth_device(device_name, on_disconnect, check_interval):
    """
    Monitor a Bluetooth device for disconnection

    :param device_name: Name of the Bluetooth device
    :param on_disconnect: Optional callback when device disconnects
    :param check_interval: Seconds between connection checks
    """
    def monitoring_loop():
        while True:
            if detect_bluetooth_disconnection(device_name):
                print(f"Bluetooth device disconnected: {device_name}")
                if on_disconnect:
                    on_disconnect()
                break
            time.sleep(check_interval)

    # Start monitoring in a separate thread
    thread = threading.Thread(target=monitoring_loop, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Recorder")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save recordings")
    args = parser.parse_args()

    recorder = AudioRecorder(device_name='DJI MIC MINI', output_dir=args.output_dir, threshold_db=-50)
    recorder.start_recording()
