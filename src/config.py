import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
DB_PATH = DATA_DIR / "lancedb"

# Models
HF_TOKEN = os.environ.get("HF_TOKEN") # User needs to set this for PyAnnote
PIPELINE_NAME = "pyannote/speaker-diarization-3.1"

# Ray / Processing
NUM_CPUS = 1
NUM_GPUS = 0 # Set to 1 if GPU available

# Vector DB
VECTOR_DIM = 512 # Depends on embedding model
SIMILARITY_THRESHOLD = 0.5
