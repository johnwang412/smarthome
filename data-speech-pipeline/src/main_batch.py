import ray
import os
from pathlib import Path
from src import config
from src.processors import process_remote_task

def main():
    """
    Batch processing entry point.
    """
    ray.init(ignore_reinit_error=True)

    # Ensure output exists
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. List files (or use Ray Data to read)
    # For massive scale (100k files), using ray.data.from_items is efficient.
    # Alternatively, use ray.data.read_binary_files if you want to read content lazily,
    # but since our pipeline loads the file via path, passing paths is better.

    input_pattern = str(config.INPUT_DIR / "*.wav")
    print(f"Scanning for files in {input_pattern}...")

    # For demo, just listing files in directory using glob
    files = [str(p) for p in config.INPUT_DIR.glob("*.wav")]

    if not files:
        print("No .wav files found in input directory.")
        return

    print(f"Found {len(files)} files. Starting batch processing...")

    # 2. Distribute tasks
    # Option A: Simple list comprehension (good for < 10k files)
    # futures = [process_remote_task.remote(f) for f in files]
    # results = ray.get(futures)

    # Option B: Ray Data (better for 100k+ files)
    ds = ray.data.from_items(files)

    # We use a map function that calls the remote task logic (or just the function directly).
    # Since process_remote_task is an actor/remote function, we can just call the underlying logic
    # or wrap it.

    class FileProcessor:
        def __call__(self, batch):
            # batch is a dict usually if from_items or pandas
            # with from_items(list), it might be a simple item if mapped row-by-row
            pass

    # For now, let's stick to the simplest robust way: parallel iterator
    # We can just map a function that calls the pipeline directly, Ray handles the scheduling.

    ds.map(
        lambda row: process_remote_task.remote(row["item"])
        if isinstance(row, dict) else process_remote_task.remote(row)
    ).take_all() # Force execution

    print("Batch processing complete.")

if __name__ == "__main__":
    main()
