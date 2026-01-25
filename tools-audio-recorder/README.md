# Overview

Script for continuous audio recording:
- auto file saving
- graceful bluetooth device disconnect and reconnect

# Running on a mac
1. Install and source Python virtualenv
2. python samson_audio_recorder.py --output-dir <output-folder-for-file>

Program will run and record, starting new files every X minutes or size. Press
ctrl-c to stop program - whatever is in the audio buffer will write to disk.

# Requirements

brew install ffmpeg
