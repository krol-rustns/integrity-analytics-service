.PHONY: install proto test run

install:
	python -m pip install -e '.[test]'

proto:
	python tools/generate_protos.py

test:
	python -m pytest -q

run:
	python -m integrity_analytics.main
