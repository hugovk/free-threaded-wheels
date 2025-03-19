help:
	@echo "make help     -- print this help"
	@echo "make fetch    -- fetch the top PyPI packages data file"
	@echo "make generate -- regenerate the json"

fetch:
	wget https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json -O top-pypi-packages.json

generate: fetch
	python3 generate.py
