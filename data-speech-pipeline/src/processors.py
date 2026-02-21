import ray
import json
from pathlib import Path
from src.pipeline import analyze_file
from src.db.manager import SpeakerDB
from src.config import OUTPUT_DIR, NUM_CPUS


def process_file(file_path: str, output_dir: str = None):
    """
    Core processing logic for a single file.
    Can be called directly (no Ray) or via Ray.
    1. Runs pipeline.
    2. Updates DB.
    3. Saves JSON result.
    """
    path = Path(file_path)
    print(f"Start processing: {path.name}")

    # 1. Pipeline Analysis
    try:
        data = analyze_file(path)
    except Exception as e:
        print(f"Error processing {path.name}: {e}")
        return {"error": str(e), "file": file_path}

    # 2. Database Interaction
    db = SpeakerDB()

    file_results = []

    for local_speaker_id, info in data["speakers"].items():
        embedding = info["embedding"]
        total_time = info["total_time"]

        # Incremental Matching
        global_id, score = db.search_speaker(embedding)

        if global_id:
            # Update existing
            db.update_profile(embedding, global_id, total_time, path.name)
            final_id = global_id
            status = "matched"
        else:
            # Create new
            final_id = db.create_profile(embedding, total_time, path.name)
            status = "created"

        file_results.append({
            "local_id": local_speaker_id,
            "global_id": final_id,
            "status": status,
            "score": score,
            "segments": info["segments"]
        })

    # 3. Save Output
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    output_path = out_dir / f"{path.stem}.json"
    output_data = {
        "file": file_path,
        "results": file_results
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Finished: {path.name} -> {output_path.name}")
    return output_data

@ray.remote(num_cpus=NUM_CPUS)
def process_remote_task(file_path: str, output_dir: str = None):
    """
    Ray task wrapper.
    """
    return process_file(file_path, output_dir)

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Process a single audio file.")
    parser.add_argument("file_path", type=str, help="Path to the audio file")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save output")

    args = parser.parse_args()

    # Direct execution without Ray
    data = analyze_file(args.file_path)

    print(json.dumps(data, indent=2))