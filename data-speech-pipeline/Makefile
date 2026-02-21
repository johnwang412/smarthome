VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install run-batch

install: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run-batch: install
	PYTHONPATH=. $(PYTHON) src/main_batch.py --data-root-dir "/Users/johnwang/Documents/audio-recorder-data/test"

process-file: install
	source runtime-vars.sh && \
	PYTHONPATH=. $(PYTHON) src/processors.py \
		"/Users/johnwang/Documents/audio-recorder-data/prod/raw-recordings/2025-12-18_091205_recording.mp3" \
		--output-dir "."