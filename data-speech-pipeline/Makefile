VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install run-batch clean

install: $(VENV)

$(VENV): requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run-batch: install
	PYTHONPATH=. $(PYTHON) src/main_batch.py --input_dir dummy_input --output_dir dummy_output

clean:
	rm -rf $(VENV)
	rm -rf dummy_input dummy_output
	find . -type d -name "__pycache__" -exec rm -rf {} +
