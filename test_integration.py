import os
import numpy as np
import scipy.io.wavfile as wav
import shutil
from pathlib import Path
from src.pipeline import analyze_file
from src.db.manager import SpeakerDB
from src.config import INPUT_DIR, OUTPUT_DIR, DB_PATH

def generate_dummy_wav(path: Path):
    """Generates a valid 2-second silence WAV file."""
    sample_rate = 16000
    duration = 2
    data = np.zeros(int(sample_rate * duration), dtype=np.int16)
    wav.write(path, sample_rate, data)

def test_integration():
    # Setup
    test_file = INPUT_DIR / "test_audio.wav"
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        shutil.rmtree(DB_PATH) # Reset DB for test

    print("Generating test file...")
    generate_dummy_wav(test_file)

    # Run Pipeline directly (unit test style)
    print("Running pipeline...")
    result = analyze_file(test_file)

    print("Pipeline Result Keys:", result.keys())
    assert "speakers" in result

    # Run DB interaction (simulate integration)
    print("Testing DB...")
    db = SpeakerDB()

    # Mocking what the processor does:
    for spk, info in result["speakers"].items():
        embedding = info["embedding"]
        # Force a match check
        gid, score = db.search_speaker(embedding)
        print(f"Search Result: {gid}, {score}")

        # Force create
        new_id = db.create_profile(embedding, 1.0, "test_audio.wav")
        print(f"Created Profile: {new_id}")

        # Verify it exists now
        gid2, _ = db.search_speaker(embedding)
        assert gid2 == new_id
        print("Verification successful: Profile found in DB.")

    print("Integration Test PASSED.")

if __name__ == "__main__":
    test_integration()
