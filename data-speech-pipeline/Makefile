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
	@if [ -z "$(FILE)" ]; then echo "Error: FILE is required. Usage: make process-file FILE=path/to/file.wav [OUT_DIR=output/]"; exit 1; fi
	PYTHONPATH=. $(PYTHON) src/processors.py "$(FILE)" $(if $(OUT_DIR),--output-dir "$(OUT_DIR)",)