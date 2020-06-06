lint:
	python -m isort -c -rc enochecker_async/
	python -m black --line-length 160 --check enochecker_async/
	python -m flake8 --select F --per-file-ignores="__init__.py:F401" enochecker_async/
	python -m mypy enochecker_async/

format:
	python -m isort -rc enochecker_async/
	python -m black --line-length 160 enochecker_async/

test:
	pip install .
	python -m pytest
