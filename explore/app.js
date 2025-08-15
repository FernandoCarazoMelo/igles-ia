document.addEventListener('DOMContentLoaded', () => {

    const documentos = [
        { id: 1, titulo: 'Homilía en la Misa de inicio de Pontificado', pontificado: 'Papa Francisco', tipo: 'Homilía', temas: ['inicio', 'servicio', 'fe'] },
        { id: 2, titulo: 'Encíclica Lumen Fidei', pontificado: 'Papa Francisco', tipo: 'Encíclica', temas: ['fe', 'luz', 'razón'] },
        { id: 3, titulo: 'Discurso a los jóvenes en la JMJ', pontificado: 'Papa Francisco', tipo: 'Discurso', temas: ['juventud', 'esperanza', 'fe'] },
        { id: 4, titulo: 'Ángelus del 1 de enero', pontificado: 'Papa Benedicto XVI', tipo: 'Ángelus', temas: ['paz', 'maría', 'año nuevo'] },
        { id: 5, titulo: 'Encíclica Deus Caritas Est', pontificado: 'Papa Benedicto XVI', tipo: 'Encíclica', temas: ['amor', 'caridad', 'dios'] },
        { id: 6, titulo: 'Discurso en la Universidad de Ratisbona', pontificado: 'Papa Benedicto XVI', tipo: 'Discurso', temas: ['fe', 'razón', 'diálogo'] },
        { id: 7, titulo: 'Carta a las Familias', pontificado: 'San Juan Pablo II', tipo: 'Carta Apostólica', temas: ['familia', 'amor', 'vida'] },
        { id: 8, titulo: 'Homilía sobre la Divina Misericordia', pontificado: 'San Juan Pablo II', tipo: 'Homilía', temas: ['misericordia', 'pascua', 'fe'] },
        { id: 9, titulo: 'Encíclica Fides et Ratio', pontificado: 'San Juan Pablo II', tipo: 'Encíclica', temas: ['fe', 'razón', 'filosofía'] },
        { id: 10, titulo: 'Encíclica Rerum Novarum', pontificado: 'León XIII', tipo: 'Encíclica', temas: ['justicia social', 'trabajo'] },
    ];

    // --- ESTADO DE LA APLICACIÓN ---
    let filtrosActivos = {
        pontificado: [],
        tipo: [],
        temas: []
    };
    let busquedaTemas = ''; // NUEVO: Estado para el buscador de temas

    // --- REFERENCIAS AL DOM ---
    const themeSearchInput = document.getElementById('theme-search-input');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const docCountElement = document.getElementById('doc-count');
    const documentList = document.getElementById('document-list');
    const sidebar = document.getElementById('sidebar');

    // --- LÓGICA PRINCIPAL ---
    const aplicarYRenderizar = () => {
        const docsFiltrados = documentos.filter(doc => {
            const pontificadoOk = filtrosActivos.pontificado.length === 0 || filtrosActivos.pontificado.includes(doc.pontificado);
            const tipoOk = filtrosActivos.tipo.length === 0 || filtrosActivos.tipo.includes(doc.tipo);
            const temasOk = filtrosActivos.temas.every(tema => doc.temas.includes(tema));
            return pontificadoOk && tipoOk && temasOk;
        });
        renderizarDocumentos(docsFiltrados);
        renderizarFiltros(docsFiltrados);
    };
    
    // --- FUNCIONES DE RENDERIZADO ---
    const renderizarDocumentos = (docs) => { /* Sin cambios */
        documentList.innerHTML = '';
        docCountElement.textContent = docs.length;
        if (docs.length === 0) { documentList.innerHTML = '<p>No se encontraron documentos.</p>'; return; }
        docs.forEach(doc => {
            const card = document.createElement('div'); card.className = 'doc-card';
            card.innerHTML = `<h2>${doc.titulo}</h2><div class="doc-meta"><span><strong>Pontificado:</strong> ${doc.pontificado}</span> &bull; <span><strong>Tipo:</strong> ${doc.tipo}</span></div><div class="doc-tags">${doc.temas.map(tema => `<span class="doc-tag-item">${tema}</span>`).join('')}</div>`;
            documentList.appendChild(card);
        });
    };

    const renderizarFiltros = (docsFiltrados) => {
        const docsParaPontificado = documentos.filter(d => (filtrosActivos.tipo.length === 0 || filtrosActivos.tipo.includes(d.tipo)) && (filtrosActivos.temas.every(t => d.temas.includes(t))));
        renderizarPillsMultiselect('pontificado', docsParaPontificado);

        const docsParaTipo = documentos.filter(d => (filtrosActivos.pontificado.length === 0 || filtrosActivos.pontificado.includes(d.pontificado)) && (filtrosActivos.temas.every(t => d.temas.includes(t))));
        renderizarPillsMultiselect('tipo', docsParaTipo);
        
        renderizarTemas(docsFiltrados);
    };

    const renderizarPillsMultiselect = (categoria, docs) => { /* Sin cambios */
        const container = document.getElementById(`filtro-${categoria}`);
        const counts = {};
        docs.forEach(doc => counts[doc[categoria]] = (counts[doc[categoria]] || 0) + 1);
        container.innerHTML = '';
        Object.entries(counts).sort((a,b) => b[1] - a[1]).forEach(([valor, count]) => {
            const isSelected = filtrosActivos[categoria].includes(valor);
            const pill = document.createElement('button'); pill.className = `filter-pill ${isSelected ? 'selected' : ''}`;
            pill.dataset.categoria = categoria; pill.dataset.valor = valor;
            pill.innerHTML = `<span>${valor}</span> <span class="item-count">${count}</span>`;
            container.appendChild(pill);
        });
    };
    
    const renderizarTemas = (docsFiltrados) => { // MODIFICADA
        const temasActivosContainer = document.getElementById('temas-activos');
        const temasDisponiblesContainer = document.getElementById('filtro-tematicas');
        const divider = document.getElementById('temas-divider');
        
        temasActivosContainer.innerHTML = '';
        filtrosActivos.temas.forEach(tema => {
            const pill = document.createElement('div'); pill.className = 'filter-pill selected';
            pill.innerHTML = `<span>${tema}</span><button class="remove-btn" data-categoria="temas" data-valor="${tema}">×</button>`;
            temasActivosContainer.appendChild(pill);
        });

        const counts = {};
        docsFiltrados.forEach(doc => {
            doc.temas.forEach(tema => {
                if (!filtrosActivos.temas.includes(tema)) {
                    counts[tema] = (counts[tema] || 0) + 1;
                }
            });
        });

        temasDisponiblesContainer.innerHTML = '';
        
        // Filtra las temáticas según el término de búsqueda ANTES de renderizarlas
        Object.entries(counts)
            .filter(([valor, _]) => valor.toLowerCase().includes(busquedaTemas.toLowerCase()))
            .sort((a,b) => b[1] - a[1])
            .forEach(([valor, count]) => {
                const pill = document.createElement('button'); pill.className = 'filter-pill';
                pill.dataset.categoria = 'temas'; pill.dataset.valor = valor;
                pill.innerHTML = `<span>${valor}</span><span class="item-count">${count}</span>`;
                temasDisponiblesContainer.appendChild(pill);
            });

        divider.classList.toggle('hidden', !(filtrosActivos.temas.length > 0 && Object.keys(counts).length > 0));
    };

    // --- MANEJADORES DE EVENTOS ---
    themeSearchInput.addEventListener('input', e => {
        busquedaTemas = e.target.value;
        aplicarYRenderizar(); // Volvemos a renderizar todo para que la lista de temas se actualice
    });

    clearFiltersBtn.addEventListener('click', () => {
        filtrosActivos = { pontificado: [], tipo: [], temas: [] };
        busquedaTemas = '';
        themeSearchInput.value = '';
        aplicarYRenderizar();
    });

    sidebar.addEventListener('click', e => {
        const targetPill = e.target.closest('button.filter-pill, button.remove-btn');
        if (!targetPill) return;
        const { categoria, valor } = targetPill.dataset;
        e.preventDefault();
        if (categoria === 'pontificado' || categoria === 'tipo') {
            const filtroArray = filtrosActivos[categoria];
            if (filtroArray.includes(valor)) {
                filtrosActivos[categoria] = filtroArray.filter(v => v !== valor);
            } else {
                filtroArray.push(valor);
            }
        } else if (categoria === 'temas') {
            if (filtrosActivos.temas.includes(valor)) {
                filtrosActivos.temas = filtrosActivos.temas.filter(t => t !== valor);
            } else {
                filtrosActivos.temas.push(valor);
            }
        }
        aplicarYRenderizar();
    });

    // --- INICIALIZACIÓN ---
    aplicarYRenderizar();
});