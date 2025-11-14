# Fase 1: Homepage Improvements - Implementación Completada

## Resumen de Cambios

Se ha restructurado la página de inicio (index.html) para aumentar la retención de usuarios mediante dos nuevas secciones: **Frases que Inspiran** y **Línea de Tiempo de Documentos Recientes**.

---

## Cambios en Backend (web/app.py)

### Nuevas Funciones

#### 1. `extract_featured_quotes(summaries, limit=8)`
- **Propósito**: Extrae citas destacadas de los últimos documentos publicados
- **Entrada**: Lista de resúmenes (ALL_SUMMARIES)
- **Salida**: Lista de dicts con estructura:
  ```python
  {
      "text": "La inteligencia artificial...",
      "source_doc": "Discurso al Colegio Cardenalicio",
      "doc_slug": "2025-11-03-discurso-...",
      "week_slug": "2025-11-03",
      "week_of": "Semana del 3 de noviembre de 2025"
  }
  ```
- **Lógica**:
  - Busca en los campos `frases_seleccionadas` de los documentos
  - Limita a las últimas 4 semanas de contenido fresco
  - Trunca texto a 150 caracteres

#### 2. `get_recent_documents_timeline(summaries, weeks=2, max_docs=12)`
- **Propósito**: Crea una línea de tiempo con documentos recientes agrupados por semana
- **Entrada**: Lista de resúmenes, número de semanas (default 2), máx documentos por semana (default 6 mostrados)
- **Salida**: Lista de semanas con documentos:
  ```python
  [
      {
          "week_slug": "2025-11-03",
          "week_of": "Semana del 3 de noviembre de 2025",
          "documents": [
              {
                  "title": "Homilía - Solemnidad de Todos los Santos",
                  "excerpt": "En esta homilía...",
                  "doc_slug": "2025-11-03-homilia-...",
                  "tipo": "Homilia"
              },
              ...
          ]
      },
      ...
  ]
  ```

### Actualización de Ruta

#### `/` (index)
**Antes:**
```python
latest_summary_data = ALL_SUMMARIES[0] if ALL_SUMMARIES else None
return render_template("index.html", latest_summary=latest_summary_data)
```

**Después:**
```python
latest_summary_data = ALL_SUMMARIES[0] if ALL_SUMMARIES else None
featured_quotes = extract_featured_quotes(ALL_SUMMARIES, limit=8)
timeline = get_recent_documents_timeline(ALL_SUMMARIES, weeks=2, max_docs=6)

return render_template(
    "index.html",
    latest_summary=latest_summary_data,
    featured_quotes=featured_quotes,
    timeline=timeline
)
```

---

## Cambios en Frontend (web/templates/index.html)

### 1. Nueva Sección: "Frases que Inspiran Esta Semana"
**Posición**: Después de stats, antes del resumen semanal
**Componentes**:
- Carousel rotativo que muestra 1 cita a la vez
- Botones de navegación (anterior/siguiente) con iconos
- Indicadores de puntos (dots) clickeables
- Información de la fuente (documento + semana)
- Enlace a documento completo

**Interactividad**:
- Click en botones anterior/siguiente
- Click en dots para ir a cita específica
- Flechas del teclado (← →)
- Auto-rotación cada 8 segundos (detiene al interactuar)

### 2. Nueva Sección: "Últimos Documentos Publicados"
**Posición**: Después del resumen semanal, antes de "Tu dosis semanal"
**Componentes**:
- Agrupación por semana
- Cards de documentos con:
  - Icono (scroll)
  - Título del documento
  - Tipo de documento (Homilía, Discurso, etc.)
  - Extracto del resumen (120 caracteres)
  - Flecha de "más información"
- Link a archivo completo de resúmenes

**Interactividad**:
- Cards clickeables (enlace a documento)
- Hover effects: color de fondo, borde izquierdo, shadow
- Link "Ver semana completa" para cada semana

---

## Cambios en Estilos CSS (web/static/style.css)

### Sección: Featured Quotes Carousel
- **Background**: Gradiente azul claro (f5f7fa → e8eef5)
- **Card**: Fondo blanco, shadow, border-radius 15px
- **Quote text**: Fuente Merriweather, tamaño 1.4rem, cursiva
- **Navigation**: Botones circulares azules (#003366)
- **Dots**: Indicadores clickeables con transición
- **Responsive**: Ajusta tamaño de fuente y botones en móvil

### Sección: Recent Timeline
- **Background**: Blanco (#ffffff)
- **Doc cards**: Layout flexbox con icono + contenido + flecha
- **Hover**: Transición suave, borde izquierdo coloreado
- **Week headers**: Separador inferior, link a semana completa
- **Responsive**: Oculta extracto en móvil, ajusta espaciado

---

## Archivo JavaScript (web/static/homepage-carousel.js)

### Funcionalidades
1. **Navegación del Carousel**:
   - Botones anterior/siguiente
   - Dots clickeables
   - Teclado (Arrow Left/Right)

2. **Auto-rotación**:
   - Cada 8 segundos cambia a la siguiente cita
   - Se detiene cuando el usuario interactúa
   - Reinicia con cada interacción

3. **Visual Feedback**:
   - Actualiza dot activo
   - Transiciones suaves
   - Solo funciona si carousel está visible

---

## Experiencia del Usuario

### Antes (Problema)
- Usuario llega al homepage
- Ve el hero + suscripción CTAs
- Lee el último resumen
- Se va (una sola visita)

### Después (Solución Fase 1)
- Usuario llega al homepage
- Ve hero + suscripción CTAs
- **VE CITAS DESTACADAS** → puede hojear varias frases inspiracionales
- **VE TIMELINE DE ÚLTIMOS DOCUMENTOS** → descubre contenido nuevo fácilmente
- Lee el último resumen
- **Motivado a volver** porque sabe qué hay de nuevo cada semana

---

## Razones por las que aumenta Retención

### 1. **Razones para Volver**
- Cada lunes hay nuevos documentos visibles
- Las citas cambian semanalmente (visual teaser)
- La timeline muestra claramente "lo nuevo"

### 2. **Razones para Explorar Más**
- Timeline facilita encontrar documentos específicos
- Citas pueden engañar al usuario a leer más
- Cada elemento es clickeable → navegación fácil

### 3. **Engagement Metrics Mejorado**
- Más clics internos (bounce rate ↓)
- Más documentos visitados por sesión (pages/session ↑)
- Más tiempo en página (time on page ↑)
- Mayor probabilidad de suscripción

---

## Testing Checklist

- [ ] Las citas se extraen correctamente sin errores
- [ ] Timeline muestra los últimos 2 semanas
- [ ] Carousel auto-rota cada 8 segundos
- [ ] Botones anterior/siguiente funcionan
- [ ] Dots clickeables navegan correctamente
- [ ] Flechas del teclado funcionan en el carousel
- [ ] Mobile responsive (carousels legibles en móvil)
- [ ] Links llevan a documentos correctos
- [ ] No hay console errors en JS
- [ ] Estilos se cargan correctamente
- [ ] Performance: generación de citas/timeline < 50ms

---

## Próximos Pasos (Fase 2)

- [ ] Agregar sección de Tendencias Temáticas
- [ ] Implementar búsqueda básica
- [ ] Analytics para ver qué elementos generan más clicks
- [ ] A/B testing de textos y diseños
- [ ] Agregar sección de "Temas Recurrentes"
- [ ] Newsletter optimization based on data

---

## Archivos Modificados/Creados

```
✏️  MODIFICADOS:
  - web/app.py (2 nuevas funciones, 1 ruta actualizada)
  - web/templates/index.html (2 nuevas secciones)
  - web/static/style.css (160+ líneas de nuevos estilos)
  - web/templates/base.html (1 new script tag)

✨ CREADOS:
  - web/static/homepage-carousel.js (nuevo archivo JavaScript)
```

---

## Notas Técnicas

- **Compatibilidad**: ES6+ JavaScript (moderno)
- **CSS**: No usa frameworks, estilos puros
- **Accesibilidad**: Buttons con aria-label, navegación por teclado
- **SEO**: Manteiene h2, h3 tags, estructura semántica
- **Performance**: Sin dependencias externas, JS optimizado

