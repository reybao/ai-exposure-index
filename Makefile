PY := PYTHONPATH=src python

.PHONY: all data index figures private video check

all: data index figures

data:        ## download public inputs and verify checksums
	$(PY) -m ai_exposure.download

index:       ## build occupation and metro exposure tables
	$(PY) -m ai_exposure.build_index

figures:     ## exposure-only public figures
	$(PY) -m ai_exposure.plot

private:     ## real figures from your licensed data in data/private/
	@test -f data/private/ai_postings.csv && $(PY) -m ai_exposure.plot --metric postings || echo "skip: data/private/ai_postings.csv not found"
	@test -f data/private/ai_investment.csv && $(PY) -m ai_exposure.plot --metric investment --per-worker || echo "skip: data/private/ai_investment.csv not found"

video:       ## MP4 animations for social posts, from licensed data (output/private/)
	@test -f data/private/ai_postings.csv && $(PY) -m ai_exposure.plot --metric postings --animate || echo "skip: postings"
	@test -f data/private/ai_investment.csv && $(PY) -m ai_exposure.plot --metric investment --per-worker --animate || echo "skip: investment"

check:       ## scan tracked files for values from your licensed data
	$(PY) scripts/leak_check.py data/private/*.csv
