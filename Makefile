export SUPABASE_URL
export SUPABASE_SERVICE_KEY

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
	uv run generar_rss.py
	uv run web/app.py
	rm -rf docs
	cp -r web/build docs

zip:
	zip deployment_package.zip lambda_function.py welcome.html

create_audio:
	uv run main.py pipeline-date --run-date "2025-10-16"
	uv run main.py generar-audios --run-date "2025-10-16" --only-metadata
	uv run main.py generar-audios --run-date "2025-10-16" --force-create-audio
	make freeze

create_audios_new:
	uv run main.py preparar-datos-audio --run-date="2025-09-30"
	uv run main.py generar-audios 
	uv run generar_rss.py
	make freeze	

update_superbase:
	uv run vatican-archiver/vatican_archiver.py
	uv run superbase/1_seed_database.py
	uv run superbase/2_update_metadata.py
	uv run superbase/3_update_semanas_traducciones.py
	uv run superbase/4_update_all_links_enriched.py
	uv run superbase/5_update_audio_urls.py
