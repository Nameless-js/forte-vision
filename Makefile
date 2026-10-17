# Thin wrapper: every target delegates to the cross-platform task runner `scripts/run.py`.
# On Windows (no make) call `python scripts/run.py <target>` directly — see README.md.

PY ?= python

.PHONY: setup test eval robustness timing api-test verify offline-check download-weights clean-cache

setup:
	$(PY) scripts/run.py setup

download-weights:
	$(PY) scripts/run.py download-weights

test:
	$(PY) scripts/run.py test

eval:
	$(PY) scripts/run.py eval

robustness:
	$(PY) scripts/run.py robustness

timing:
	$(PY) scripts/run.py timing

api-test:
	$(PY) scripts/run.py api-test

offline-check:
	$(PY) scripts/run.py offline-check

verify:
	$(PY) scripts/run.py verify

clean-cache:
	$(PY) scripts/run.py clean-cache
