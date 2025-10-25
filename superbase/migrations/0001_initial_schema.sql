-- 1. La "carpeta" de la semana
CREATE TABLE public.semanas (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  fecha_inicio date NOT NULL,
  created_at timestamp WITH time zone NOT NULL DEFAULT now(),
  CONSTRAINT semanas_pkey PRIMARY KEY (id)
);

-- 2. El texto traducido de la semana
CREATE TABLE public.semanas_traducciones (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  semana_id uuid NOT NULL,
  idioma text NOT NULL CHECK (char_length(idioma) = 2),
  resumen_semanal text,
  mensaje_whatsapp text,
  created_at timestamp WITH time zone NOT NULL DEFAULT now(),
  CONSTRAINT semanas_traducciones_pkey PRIMARY KEY (id),
  CONSTRAINT semanas_traducciones_semana_id_fkey FOREIGN KEY (semana_id) REFERENCES public.semanas(id) ON DELETE CASCADE,
  CONSTRAINT semanas_traducciones_semana_id_idioma_key UNIQUE (semana_id, idioma)
);

-- 3. La homilía
CREATE TABLE public.homilias (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  semana_id uuid NOT NULL,
  fecha timestamp WITH time zone NOT NULL,
  -- 'tipo' se ha movido a la tabla de traducciones
  created_at timestamp WITH time zone NOT NULL DEFAULT now(),
  CONSTRAINT homilias_pkey PRIMARY KEY (id),
  CONSTRAINT homilias_semana_id_fkey FOREIGN KEY (semana_id) REFERENCES public.semanas(id) ON DELETE CASCADE
);

-- 4. El contenido traducido de la homilía
CREATE TABLE public.homilias_traducciones (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  homilia_id uuid NOT NULL,
  idioma text NOT NULL CHECK (char_length(idioma) = 2),
  
  tipo text,
  
  -- URLs específicas del idioma
  audio_url text,
  vatican_url text,
  
  -- Títulos
  titulo text NOT NULL,
  titulo_original text,
  titulo_spotify text,
  titulo_youtube text,
  
  -- Contenido de texto
  resumen text,
  descripcion_spotify text,
  texto_completo text,
  
  -- Contenido para redes sociales
  frases_destacadas text[] DEFAULT ARRAY[]::text[],
  mensaje_instagram text,
  
  created_at timestamp WITH time zone NOT NULL DEFAULT now(),
  CONSTRAINT homilias_traducciones_pkey PRIMARY KEY (id),
  CONSTRAINT homilias_traducciones_homilia_id_fkey FOREIGN KEY (homilia_id) REFERENCES public.homilias(id) ON DELETE CASCADE,
  CONSTRAINT homilias_traducciones_homilia_id_idioma_key UNIQUE (homilia_id, idioma)
);