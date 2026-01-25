VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: install run

install:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

run: install
	$(PYTHON) samson_audio_recorder.py --output-dir "/Users/johnwang/Documents/audio-recorder-data/prod/raw-recordings"
