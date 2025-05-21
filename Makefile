run:
	uv run main.py
run-web:
	uv run web/app.py
freeze:
	uv run web/freeze.py
	rm -rf docs
	cp -r web/build docs