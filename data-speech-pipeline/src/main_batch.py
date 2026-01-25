import ray
import os
import argparse
from pathlib import Path
from src import config
from src.processors import process_remote_task

def main():
    """
    Batch processing entry point.
    """
    print("Batch processing audio files...")

    parser = argparse.ArgumentParser(description="Batch process audio files.")
    parser.add_argument("--data-root-dir", type=str, help="Root data directory containing 'raw-recordings'")
    args = parser.parse_args()

    if not args.data_root_dir:
        print("Error: --data-root-dir is required.")
        exit(1)

    data_root_dir = Path(args.data_root_dir)
    input_dir = data_root_dir / "raw-recordings"
    output_dir = data_root_dir / "output"

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Folder 'raw-recordings' not found in root directory: {data_root_dir}")
        exit(1)

    print(f'Initializing Ray...')
    ray.init(ignore_reinit_error=True)

    # Ensure output exists
    # 1. List files (or use Ray Data to read)
    # For massive scale (100k files), using ray.data.from_items is efficient.
    # Alternatively, use ray.data.read_binary_files if you want to read content lazily,
    # but since our pipeline loads the file via path, passing paths is better.
    output_dir.mkdir(parents=True, exist_ok=True)

    input_pattern = str(input_dir / "*.wav")
    print(f"Scanning for files in {input_pattern}...")

    # For demo, just listing files in directory using glob
    files = [str(p) for p in input_dir.glob("*.wav")]

    if not files:
        print(f"No .wav files found in input directory: {input_dir}")
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

    # For now, let's stick to the simplest robust way: parallel iterator
    # We can just map a function that calls the pipeline directly, Ray handles the scheduling.

    out_dir_str = str(output_dir)
    ds.map(
        lambda row: process_remote_task.remote(row["item"], output_dir=out_dir_str)
        if isinstance(row, dict) else process_remote_task.remote(row, output_dir=out_dir_str)
    ).take_all() # Force execution

    print("Batch processing complete.")

if __name__ == "__main__":
    main()
