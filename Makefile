run:
	uv run main.py
run-web:
	uv run web/app.py
freeze:
	cp data_web/contenido_semanal.html web/data/contenido_semanal_para_web.html	
	cp data_web/contenido_semanal.html web/data/contenido_semanal.html	
	uv run web/freeze.py
	rm -rf docs
	cp -r web/build docs
