run:
	uv run main.py
run-web:
	uv run web/app.py
freeze_old:
	cp data_web/contenido_semanal.html web/data/contenido_semanal_para_web.html	
	cp data_web/contenido_semanal.html web/data/contenido_semanal.html	
	uv run web/freeze.py
	rm -rf docs
	cp -r web/build docs


freeze:
	uv run web/app.py
	rm -rf docs
	cp -r web/build docs

zip:
	zip deployment_package.zip lambda_function.py welcome.html

create_audio:
	uv run main.py pipeline-date --run-date "2025-08-11"
	uv run main.py generar-audios --run-date "2025-08-25" --only-metadata
	uv run generar_rss.py
	make freeze