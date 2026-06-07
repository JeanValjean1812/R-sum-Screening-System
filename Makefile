.PHONY: install install-dev run web test clean

install:           ## Install runtime dependencies
	pip install -r requirements.txt

install-dev:       ## Install runtime + development dependencies
	pip install -r requirements-dev.txt

run:               ## Screen the sample résumés from the command line
	python main.py

web:               ## Launch the Streamlit web interface
	streamlit run app.py

test:              ## Run the test suite
	pytest -q

clean:             ## Remove caches and generated output
	rm -rf .pytest_cache __pycache__ */__pycache__ output/*.csv
