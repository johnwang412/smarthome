import lancedb
import pyarrow as pa
import numpy as np
from typing import List, Optional, Tuple
from src.config import DB_PATH, VECTOR_DIM, SIMILARITY_THRESHOLD

class SpeakerDB:
    def __init__(self):
        self.db = lancedb.connect(DB_PATH)
        # Define schema
        self.schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
            pa.field("global_speaker_id", pa.string()),
            pa.field("total_speaking_time", pa.float64()),
            pa.field("last_seen", pa.float64()),
            pa.field("files_seen", pa.list_(pa.string()))
        ])

        # Open or create table
        try:
            self.table = self.db.open_table("speakers")
        except FileNotFoundError:
            self.table = self.db.create_table("speakers", schema=self.schema)

    def search_speaker(self, embedding: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Search for a matching speaker in the DB.
        Returns (global_speaker_id, similarity_score) or (None, 0.0) if no match found.
        """
        if self.table.count_rows() == 0:
            return None, 0.0

        results = self.table.search(embedding).limit(1).to_pandas()

        if len(results) > 0:
            # L2 distance is returned by default, lower is better.
            # If using cosine, logic might differ. Assuming L2 for now.
            # We used SIMILARITY_THRESHOLD. Let's assume the user wants typical distance check.
            dist = results.iloc[0]["_distance"]
            if dist < SIMILARITY_THRESHOLD: # Match found
                 return results.iloc[0]["global_speaker_id"], dist

        return None, 0.0

    def update_profile(self, embedding: np.ndarray, global_id: str, duration: float, filename: str):
        """
        Update an existing speaker profile.
        TODO: Implement vector averaging/merging logic.
        For now, we just update metadata.
        """
        # In a real app, we'd fetch the old vector, average it with the new one, and update.
        # LanceDB updates can be tricky, often requiring overwrite or specific query pattern.
        # For simplicity in this scaffold, we'll placeholder the logic.
        print(f"Updating profile for {global_id}")

    def create_profile(self, embedding: np.ndarray, duration: float, filename: str) -> str:
        """
        Create a new speaker profile.
        """
        import uuid
        import time

        new_id = f"SPK_{str(uuid.uuid4())[:8]}"

        data = [{
            "vector": embedding,
            "global_speaker_id": new_id,
            "total_speaking_time": duration,
            "last_seen": time.time(),
            "files_seen": [filename]
        }]

        self.table.add(data)
        return new_id
