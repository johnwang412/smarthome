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