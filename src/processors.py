import ray
import json
from pathlib import Path
from src.pipeline import analyze_file
from src.db.manager import SpeakerDB
from src.config import OUTPUT_DIR, NUM_CPUS

@ray.remote(num_cpus=NUM_CPUS)
def process_remote_task(file_path: str):
    """
    Ray task wrapper.
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
    # Note: LanceDB connection might need to be handled carefuly in distributed setting.
    # ideally, we might have a centralized actor for DB writes to avoid locking issues,
    # or just rely on LanceDB's concurrency if supported.
    # For now, we instantiate DB here (safe for read/write if locking handled by FS/DB)
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
    output_path = OUTPUT_DIR / f"{path.stem}.json"
    output_data = {
        "file": file_path,
        "results": file_results
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Finished: {path.name} -> {output_path.name}")
    return output_data
