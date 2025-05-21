run:
	uv run main.py
run-web:
	uv run web/app.py
freeze:
	echo "Freezing web app..."
	uv run web/freeze.py
	echo "Freezing web app done."
	echo "Copying frozen web app to docs..."
	cp -r web/build docs
	echo "Copying frozen web app done."