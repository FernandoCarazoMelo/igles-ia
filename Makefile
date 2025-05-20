run:
	uv run main.py
run-web:
	uv run web/app.py
freeze:
	uv run web/freeze.py
	cp -r web/build docs
