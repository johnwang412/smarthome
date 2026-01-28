import time
import ray
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src import config
from src.processors import process_remote_task

class AudioHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            ext = Path(event.src_path).suffix.lower()
            if ext in config.SUPPORTED_EXTENSIONS:
                print(f"New audio file detected: {event.src_path}")
                # Submit Ray task
                process_remote_task.remote(event.src_path)

def main():
    """
    Ad-hoc file watcher entry point.
    """
    # Initialize Ray
    ray.init(ignore_reinit_error=True)

    # Ensure directories exist
    config.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    event_handler = AudioHandler()
    observer = Observer()
    observer.schedule(event_handler, path=str(config.INPUT_DIR), recursive=False)

    print(f"Watching {config.INPUT_DIR} for {config.SUPPORTED_EXTENSIONS} files...")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()
