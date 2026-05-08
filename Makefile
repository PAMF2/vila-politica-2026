.PHONY: smoke stats baselines ml cross paper all reproduce verify clean

PYTHON ?= python3
PYTHONPATH := $(PWD)
export PYTHONPATH

# ---------------------------------------------------------------------------
# Headline targets
# ---------------------------------------------------------------------------

smoke:
	$(PYTHON) scripts/smoke_political.py

stats:
	$(PYTHON) scripts/political_stats_rigor.py

baselines:
	$(PYTHON) scripts/baseline_gauntlet.py

ml:
	$(PYTHON) scripts/bench_ml_baselines.py

bart:
	$(PYTHON) scripts/bench_bart.py

stan:
	$(PYTHON) scripts/bench_stan_dlm.py

cross:
	$(PYTHON) scripts/cross_country_validation.py
	$(PYTHON) scripts/cross_country_extended.py
	$(PYTHON) scripts/cross_country_more.py

failure:
	$(PYTHON) scripts/failure_analysis.py

latency:
	$(PYTHON) scripts/bench_latency.py

consolidate:
	$(PYTHON) scripts/bench_all_models.py

predict:
	$(PYTHON) scripts/predict_2026.py

paper:
	$(PYTHON) scripts/build_paper_pdf.py

# ---------------------------------------------------------------------------
# Aggregate targets
# ---------------------------------------------------------------------------

# Full reproduction without BART (fast, <1 min)
reproduce-fast: smoke stats baselines ml stan cross failure latency consolidate predict
	@echo "Fast reproduction complete (no BART). Outputs in data/*.json."

# Full reproduction including BART (~3 min)
reproduce: reproduce-fast bart consolidate
	@echo "Full reproduction complete. Outputs in data/*.json."

# Reproduce + rebuild paper PDF
all: reproduce paper
	@echo "Full pipeline + paper PDF complete -> docs/paper/PAPER.pdf"

# ---------------------------------------------------------------------------
# Verify byte-identical reproduction against shipped JSONs
# ---------------------------------------------------------------------------

verify:
	@echo "Verifying SHA-256 of result JSONs against PAPER.md §8.3 expected hashes..."
	@sha256sum data/political_stats_v2.json data/baseline_gauntlet.json \
		data/cross_country_results.json data/cross_country_extended.json \
		data/cross_country_more.json data/bench_bart.json data/bench_stan_dlm.json \
		data/bench_ml_baselines.json data/failure_analysis.json | \
		awk '{print substr($$1,1,16)"  "$$2}'

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean:
	rm -f data/clients.json
	rm -rf __pycache__ scripts/__pycache__ engine/__pycache__ api/__pycache__
	@echo "Cleaned."
