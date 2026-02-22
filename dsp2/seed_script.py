import os

import mlx_whisper
from pyannote.audio import Pipeline, Audio
import torch
import chromadb
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding

HF_TOKEN=os.environ.get("HF_TOKEN")

DEVICE = torch.device("mps") # Uses the M4 GPU

# # Initialize Vector DB (Memory for voices)
# DB_PATH = "./speaker_database"
# client = chromadb.PersistentClient(path=DB_PATH)
# collection = client.get_or_create_collection(name="voice_fingerprints")

# Load Diarization Pipeline (Who spoke when)
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1", token=HF_TOKEN
).to(DEVICE)

# Load Embedding Model (Voice characteristic extractor)
# We use the embedding part of pyannote to get the "fingerprint"
from pyannote.audio import Model
embedding_model = Model.from_pretrained("pyannote/embedding", token=HF_TOKEN).to(DEVICE)
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
inference = PretrainedSpeakerEmbedding(embedding_model, device=DEVICE)


def align_text_to_speakers(whisper_results, diarization):
    """
    Refined logic to assign text to speakers based on word-level midpoints.
    """
    aligned_segments = []

    # 1. Flatten all words from all segments into one list
    all_words = []
    for segment in whisper_results['segments']:
        if 'words' in segment:
            all_words.extend(segment['words'])
        else:
            # Fallback if word_timestamps failed
            all_words.append({
                'word': segment['text'],
                'start': segment['start'],
                'end': segment['end']
            })

    # 2. Match each word to a diarization turn
    for word_info in all_words:
        word_text = word_info['word']
        start = word_info['start']
        end = word_info['end']
        midpoint = (start + end) / 2

        assigned_speaker = "Unknown"

        # Find which diarization segment contains the midpoint of this word
        for turn, _, speaker_label in diarization.itertracks(yield_label=True):
            if turn.start <= midpoint <= turn.end:
                assigned_speaker = speaker_label
                break

        aligned_segments.append({
            "speaker": assigned_speaker,
            "text": word_text,
            "start": start,
            "end": end
        })

    return aligned_segments

def process_audio_refined(file_path):
    # A. Transcribe with WORD-LEVEL timestamps (Crucial for M4 speed)
    print("Transcribing...")
    result = mlx_whisper.transcribe(
        file_path,
        path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        word_timestamps=True  # <--- This is the secret sauce
    )

    # B. Run Diarization
    print("Diarizing...")
    diarization = diarization_pipeline(file_path)
    print("Diarization complete")
    breakpoint()

    # C. Align them
    aligned_words = align_text_to_speakers(result, diarization)

    # D. Group words back into readable sentences/turns
    final_transcript = []
    # if not aligned_words:
    #     return ""

    # current_speaker = aligned_words[0]['speaker']
    # current_text = []
    # start_time = aligned_words[0]['start']

    # for word in aligned_words:
    #     if word['speaker'] != current_speaker:
    #         # Speaker changed: get identity from DB and flush the buffer
    #         real_name = get_speaker_name_from_db(file_path, current_speaker, diarization)
    #         final_transcript.append(f"[{start_time:.1f}s] {real_name}: {' '.join(current_text)}")

    #         # Reset for new speaker
    #         current_speaker = word['speaker']
    #         current_text = [word['text']]
    #         start_time = word['start']
    #     else:
    #         current_text.append(word['text'])

    # # Add the last segment
    # real_name = get_speaker_name_from_db(file_path, current_speaker, diarization)
    # final_transcript.append(f"[{start_time:.1f}s] {real_name}: {' '.join(current_text)}")

    return "\n".join(final_transcript)

def get_speaker_name_from_db(file_path, speaker_label, diarization):
    """
    Wraps the Vector DB lookup logic.
    """
    # Use the first available turn for this speaker label to get their fingerprint
    for turn, _, label in diarization.itertracks(yield_label=True):
        if label == speaker_label:
            # (Insert your Vector DB query/add logic here from the previous step)
            # For brevity, returning a placeholder
            return f"Speaker_{speaker_label}"
    return "Unknown"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process a single audio file.")
    parser.add_argument("file_path", type=str, help="Path to the audio file")

    args = parser.parse_args()

    # Direct execution without Ray
    print(f'calling process_audio_refined')
    transcript_str = process_audio_refined(args.file_path)

    print(transcript_str)