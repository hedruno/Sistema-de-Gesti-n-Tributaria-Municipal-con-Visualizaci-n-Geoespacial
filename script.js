// =====================================================
// Sistema de Gestión Tributaria Municipal - Frontend
// Leaflet + API Backend PostGIS
// =====================================================

// Configuración
const API_URL = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

// Crear mapa (variable global, inicialización en initMap)
let map = null;

// Configurar capas base (se usarán en initMap)
const capasBaseConfig = {
  osm: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  satelite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  topo: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
};

// Estado global
let prediosLayer = null;
let heatLayer = null;
let chartServicios = null;
let chartDeuda = null;
let currentGeojson = null;

// =====================================================
// FUNCIONES DE ESTILOS Y POPUPS
// =====================================================

function getColorByEstado(estado) {
  switch (estado) {
    case 'AL_DIA': return '#28a745';      // Verde
    case 'MOROSO': return '#dc3545';       // Rojo
    case 'EXONERADO': return '#007bff';    // Azul
    default: return '#6c757d';              // Gris
  }
}

function getBadgeClass(estado) {
  switch (estado) {
    case 'AL_DIA': return 'success';
    case 'MOROSO': return 'danger';
    case 'EXONERADO': return 'info';
    default: return 'secondary';
  }
}

function estiloPredio(feature) {
  const estado = feature.properties.estado_pago;
  const color = getColorByEstado(estado);

  return {
    radius: 8,
    fillColor: color,
    color: '#fff',
    weight: 2,
    opacity: 1,
    fillOpacity: 0.8
  };
}

// =====================================================
// FUNCIONES DE UI Y POPUP
// =====================================================

function crearPopup(feature, layer) {
  const props = feature.properties;

  // Función auxiliar para parsear números
  const parseNum = (val) => {
    const num = parseFloat(val);
    return isNaN(num) ? 0 : num;
  };

  const html = `
    <div class="popup-tributario" style="min-width: 250px;">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="text-primary m-0 text-truncate" style="max-width: 180px;">
          ${props.contribuyente_nombre || 'Sin contribuyente'}
        </h6>
        <span class="badge bg-${getBadgeClass(props.estado_pago)}">
          ${props.estado_pago || 'N/A'}
        </span>
      </div>
      
      <hr class="my-2">
      
      <div class="row g-1 small">
        <div class="col-6 text-muted">Código:</div>
        <div class="col-6 fw-bold text-end">${props.codigo_catastral || 'N/A'}</div>
        
        <div class="col-6 text-muted">Tipo:</div>
        <div class="col-6 text-end">${props.tipo_vivienda || 'N/A'}</div>
        
        <div class="col-6 text-muted">Deuda Total:</div>
        <div class="col-6 text-end text-danger fw-bold">
          S/ ${parseNum(props.deuda_total).toLocaleString('es-PE', { minimumFractionDigits: 2 })}
        </div>
      </div>

      <div class="mt-2 p-2 bg-light rounded small">
        <div class="d-flex justify-content-between mb-1">
          <span>Impuesto:</span>
          ${props.pago_impuesto ?
      '<span class="text-success"><i class="fas fa-check"></i> Pagado</span>' :
      `<span class="text-danger fw-bold">S/ ${parseNum(props.monto_impuesto).toFixed(2)}</span>`
    }
        </div>
        <div class="d-flex justify-content-between">
          <span>Arbitrios:</span>
          ${props.pago_arbitrios ?
      '<span class="text-success"><i class="fas fa-check"></i> Pagado</span>' :
      `<span class="text-danger fw-bold">S/ ${parseNum(props.monto_arbitrios).toFixed(2)}</span>`
    }
        </div>
      </div>
      
      <hr class="my-2">
      
      <div class="d-flex gap-2 justify-content-center">
        <button onclick="editarPredio(${props.id_predio})" class="btn btn-sm btn-outline-primary flex-grow-1">
          <i class="fas fa-edit"></i> Editar
        </button>
        <button onclick="eliminarPredio(${props.id_predio})" class="btn btn-sm btn-outline-danger flex-grow-1">
          <i class="fas fa-trash"></i> Borrar
        </button>
      </div>
    </div>
  `;

  layer.bindPopup(html, { maxWidth: 300 });
}

function getBadgeClass(estado) {
  // Assuming stateColors is defined elsewhere or using a simplified logic
  // For this change, we'll use a direct mapping as provided in the instruction's new code.
  switch (estado) {
    case 'AL_DIA': return 'success';
    case 'MOROSO': return 'danger';
    case 'EXONERADO': return 'info'; // Changed from 'warning' to 'info' as per original code's blue for EXONERADO
    default: return 'secondary';
  }
}

// =====================================================
// INICIALIZACIÓN
// =====================================================

function initMap() {
  map = L.map('map').setView([-15.8785, -69.9760], 16);

  // Capas base
  var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
  }).addTo(map);

  var satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri'
  });

  // Control de capas
  var baseMaps = {
    "Mapa Base": osm,
    "Satelital": satelite
  };

  L.control.layers(baseMaps).addTo(map);

  // Evento CLICK para Crear Predio
  map.on('click', onMapClick);
}

// Búsqueda simple (Helper)
function performSearch() {
  const val = document.getElementById('search-contribuyente').value;
  buscarContribuyente(val);
}


// =====================================================
// CARGAR DATOS DESDE API
// =====================================================

async function cargarPredios(filtros = {}) {
  try {
    showLoading(true);

    // Construir URL con filtros
    const params = new URLSearchParams();
    if (filtros.estado && filtros.estado !== 'all') {
      params.append('estado', filtros.estado);
    }
    if (filtros.deuda_min) {
      params.append('deuda_min', filtros.deuda_min);
    }
    if (filtros.deuda_max) {
      params.append('deuda_max', filtros.deuda_max);
    }

    const url = `${API_URL}/api/predios${params.toString() ? '?' + params.toString() : ''}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error('Error al cargar predios');

    const geojson = await response.json();
    currentGeojson = geojson;

    // Aplicar filtros locales adicionales (servicios básicos, ingreso)
    const filtrosLocales = obtenerFiltrosLocales();
    const featuresFiltradas = filtrarFeaturesLocalmente(geojson.features, filtrosLocales);

    renderizarPredios({ ...geojson, features: featuresFiltradas });
    actualizarEstadisticas(featuresFiltradas);

    showLoading(false);
  } catch (error) {
    console.error('Error cargando predios:', error);
    showLoading(false);

    // Mensaje más específico
    const errorMsg = `Error al cargar datos del servidor.
    
Detalles técnicos:
- URL intentada: ${API_URL}/api/predios
- Error: ${error.message}

Verificaciones:
1. ¿Está Docker corriendo? → docker-compose ps
2. ¿El backend está activo? → http://localhost:8000/api/predios
3. Revisa la consola del navegador (F12) para más detalles`;

    console.error(errorMsg);
    alert('No se pudieron cargar los datos. Verifica que Docker esté ejecutándose.\n\nPresiona F12 para ver detalles en la consola.');
  }
}

function obtenerFiltrosLocales() {
  return {
    servicios: document.getElementById('filtro-servicios')?.value || 'all',
    ingresoMin: parseFloat(document.getElementById('filtro-ingreso-min')?.value) || null,
    ingresoMax: parseFloat(document.getElementById('filtro-ingreso-max')?.value) || null
  };
}

function filtrarFeaturesLocalmente(features, filtros) {
  return features.filter(feature => {
    const props = feature.properties;

    // Filtro servicios básicos
    if (filtros.servicios !== 'all') {
      if (filtros.servicios === 'Completo' && props.servicios_basicos !== 'Completo') return false;
      if (filtros.servicios === 'Incompleto' && props.servicios_basicos === 'Completo') return false;
    }

    // Filtro ingreso
    if (filtros.ingresoMin && props.ingreso_familiar < filtros.ingresoMin) return false;
    if (filtros.ingresoMax && props.ingreso_familiar > filtros.ingresoMax) return false;

    return true;
  });
}

function renderizarPredios(geojson) {
  // Remover capa anterior
  if (prediosLayer) {
    map.removeLayer(prediosLayer);
  }

  // Crear nueva capa
  prediosLayer = L.geoJSON(geojson, {
    pointToLayer: function (feature, latlng) {
      return L.circleMarker(latlng, estiloPredio(feature));
    },
    onEachFeature: crearPopup
  }).addTo(map);

  // Ajustar vista si hay datos
  if (geojson.features.length > 0 && prediosLayer.getBounds().isValid()) {
    map.fitBounds(prediosLayer.getBounds(), { padding: [50, 50], maxZoom: 16 });
  }
}

// =====================================================
// BÚSQUEDA POR CONTRIBUYENTE
// =====================================================

async function buscarContribuyente(nombre) {
  if (!nombre || nombre.trim().length < 3) {
    alert('Ingrese al menos 3 caracteres para buscar');
    return;
  }

  try {
    showLoading(true);
    const url = `${API_URL}/api/buscar?nombre=${encodeURIComponent(nombre)}`;
    const response = await fetch(url);

    if (!response.ok) throw new Error('Error en búsqueda');

    const geojson = await response.json();

    if (geojson.features.length === 0) {
      alert(`No se encontraron predios para "${nombre}"`);
      showLoading(false);
      return;
    }

    renderizarPredios(geojson);

    // Abrir popup del primer resultado
    if (geojson.features.length > 0) {
      const firstFeature = geojson.features[0];
      const coords = firstFeature.geometry.coordinates;
      map.setView([coords[1], coords[0]], 18);

      // Buscar y abrir el popup
      prediosLayer.eachLayer(layer => {
        const layerCoords = layer.getLatLng();
        if (Math.abs(layerCoords.lat - coords[1]) < 0.00001 &&
          Math.abs(layerCoords.lng - coords[0]) < 0.00001) {
          layer.openPopup();
        }
      });
    }

    actualizarEstadisticas(geojson.features);
    showLoading(false);
  } catch (error) {
    console.error('Error en búsqueda:', error);
    showLoading(false);
    alert('Error al buscar contribuyente');
  }
}

// =====================================================
// ESTADÍSTICAS Y GRÁFICOS
// =====================================================

async function cargarEstadisticasGenerales() {
  try {
    const response = await fetch(`${API_URL}/api/estadisticas`);
    if (!response.ok) {
      console.warn('Estadísticas no disponibles');
      return;
    }

    const stats = await response.json();

    // Mostrar en consola para debugging
    console.log('Estadísticas generales:', stats);

    // Actualizar dashboard si existe
    actualizarDashboard(stats);
  } catch (error) {
    console.warn('No se pudieron cargar estadísticas:', error);
    // No mostrar error al usuario, el sistema funciona sin esto
  }
}

function actualizarEstadisticas(features) {
  const total = features.length;

  // Función auxiliar para parsear números
  const parseNum = (val) => {
    const num = parseFloat(val);
    return isNaN(num) ? 0 : num;
  };

  // Calcular promedios
  const deudaTotal = features.reduce((sum, f) => sum + parseNum(f.properties.deuda_total), 0);
  const ingresoTotal = features.reduce((sum, f) => sum + parseNum(f.properties.ingreso_familiar), 0);
  const promedioIngreso = total > 0 ? (ingresoTotal / total) : 0;

  // Distribución por estado
  const distribucionEstado = features.reduce((acc, f) => {
    const estado = f.properties.estado_pago || 'DESCONOCIDO';
    acc[estado] = (acc[estado] || 0) + 1;
    return acc;
  }, {});

  // Actualizar resumen en card
  const cardBody = document.querySelector('#estadisticas .card-body');
  let summaryDiv = cardBody.querySelector('.summary-area');

  if (!summaryDiv) {
    summaryDiv = document.createElement('div');
    summaryDiv.className = 'summary-area mb-3 p-2 bg-light rounded';
    cardBody.insertBefore(summaryDiv, cardBody.firstChild);
  }

  summaryDiv.innerHTML = `
    <h6 class="mb-2">Resumen</h6>
    <div class="row g-2 small">
      <div class="col-6">
        <div class="text-muted">Total predios:</div>
        <strong>${total}</strong>
      </div>
      <div class="col-6">
        <div class="text-muted">Deuda total:</div>
        <strong class="text-danger">S/ ${deudaTotal.toLocaleString('es-PE', { minimumFractionDigits: 2 })}</strong>
      </div>
       <div class="col-6">
        <div class="text-muted">Morosos:</div>
        <strong class="text-danger">${distribucionEstado.MOROSO || 0}</strong>
      </div>
      <div class="col-6">
        <div class="text-muted">Al día:</div>
        <strong class="text-success">${distribucionEstado.AL_DIA || 0}</strong>
      </div>
      <div class="col-12">
        <div class="text-muted">Ingreso promedio:</div>
        <strong>S/ ${promedioIngreso.toLocaleString('es-PE', { minimumFractionDigits: 2 })}</strong>
      </div>
    </div>
  `;

  // Actualizar gráficos
  actualizarGraficoEstado(distribucionEstado);
  actualizarGraficoDeuda(features);
}

function actualizarGraficoEstado(distribucion) {
  const ctx = document.getElementById('chartServicios');
  if (!ctx) return;

  const labels = Object.keys(distribucion);
  const data = Object.values(distribucion);
  const colors = labels.map(label => getColorByEstado(label));

  if (chartServicios) {
    chartServicios.data.labels = labels;
    chartServicios.data.datasets[0].data = data;
    chartServicios.data.datasets[0].backgroundColor = colors;
    chartServicios.update();
  } else {
    chartServicios = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: { boxWidth: 12, padding: 8, font: { size: 11 } }
          },
          title: {
            display: true,
            text: 'Distribución por Estado'
          }
        }
      }
    });
  }
}

function actualizarGraficoDeuda(features) {
  const ctx = document.getElementById('chartIngreso');
  if (!ctx) return;

  // Agrupar por rangos de deuda
  const rangos = [
    { label: '0-50', min: 0, max: 50 },
    { label: '51-100', min: 51, max: 100 },
    { label: '101-200', min: 101, max: 200 },
    { label: '201-500', min: 201, max: 500 },
    { label: '500+', min: 501, max: Infinity }
  ];

  const counts = rangos.map(rango => {
    return features.filter(f => {
      const deuda = f.properties.deuda_total || 0;
      return deuda >= rango.min && deuda < rango.max;
    }).length;
  });

  const labels = rangos.map(r => r.label);

  if (chartDeuda) {
    chartDeuda.data.labels = labels;
    chartDeuda.data.datasets[0].data = counts;
    chartDeuda.update();
  } else {
    chartDeuda = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Predios por rango de deuda (S/)',
          data: counts,
          backgroundColor: '#dc3545'
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: 'Distribución por Deuda'
          }
        },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } }
        }
      }
    });
  }
}

// =====================================================
// MAPA DE CALOR
// =====================================================

function construirHeatmap(features) {
  if (heatLayer) {
    map.removeLayer(heatLayer);
    heatLayer = null;
  }

  const points = [];
  let maxDeuda = 0;

  features.forEach(f => {
    const deuda = parseFloat(f.properties.deuda_total) || 0;
    if (deuda > 0 && f.geometry.coordinates) {
      const coords = f.geometry.coordinates;
      points.push([coords[1], coords[0], deuda]);
      if (deuda > maxDeuda) maxDeuda = deuda;
    }
  });

  if (points.length === 0) return;

  // Normalizar pesos
  const heatPoints = points.map(p => [p[0], p[1], p[2] / (maxDeuda || 1)]);

  heatLayer = L.heatLayer(heatPoints, {
    radius: 25,
    blur: 20,
    maxZoom: 17,
    max: 1.0,
    gradient: {
      0.0: 'green',
      0.5: 'yellow',
      0.7: 'orange',
      1.0: 'red'
    }
  }).addTo(map);
}

// =====================================================
// EXPORTAR DATOS
// =====================================================

function exportarCSV() {
  if (!currentGeojson || currentGeojson.features.length === 0) {
    alert('No hay datos para exportar');
    return;
  }

  const features = currentGeojson.features;
  const headers = [
    'Código Catastral', 'Contribuyente', 'DNI', 'Tipo Vivienda',
    'Estado Pago', 'Deuda Total', 'Monto Impuesto', 'Pago Impuesto',
    'Monto Arbitrios', 'Pago Arbitrios', 'Ingreso Familiar', 'Latitud', 'Longitud'
  ];

  const rows = features.map(f => {
    const p = f.properties;
    const coords = f.geometry.coordinates;
    return [
      p.codigo_catastral || '',
      p.contribuyente_nombre || '',
      p.contribuyente_dni || '',
      p.tipo_vivienda || '',
      p.estado_pago || '',
      (parseFloat(p.deuda_total) || 0).toFixed(2),
      (parseFloat(p.monto_impuesto) || 0).toFixed(2),
      p.pago_impuesto ? 'SI' : 'NO',
      (parseFloat(p.monto_arbitrios) || 0).toFixed(2),
      p.pago_arbitrios ? 'SI' : 'NO',
      (parseFloat(p.ingreso_familiar) || 0).toFixed(2),
      coords[1],
      coords[0]
    ].map(val => `"${String(val).replace(/"/g, '""')}"`);
  });

  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');

  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `predios_tributarios_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportarPDF() {
  if (typeof jsPDF === 'undefined') {
    alert('Librería PDF no disponible');
    return;
  }

  const doc = new jsPDF();
  const features = currentGeojson?.features || [];
  const total = features.length;
  const morosos = features.filter(f => f.properties.estado_pago === 'MOROSO').length;
  const deudaTotal = features.reduce((sum, f) => sum + (f.properties.deuda_total || 0), 0);

  doc.setFontSize(16);
  doc.text('Reporte Tributario Municipal', 14, 20);

  doc.setFontSize(10);
  doc.text(`Fecha: ${new Date().toLocaleDateString('es-PE')}`, 14, 30);
  doc.text(`Total de predios: ${total}`, 14, 40);
  doc.text(`Predios morosos: ${morosos}`, 14, 46);
  doc.text(`Deuda total: S/ ${deudaTotal.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`, 14, 52);

  doc.save(`reporte_tributario_${new Date().toISOString().slice(0, 10)}.pdf`);
}

// =====================================================
// UTILIDADES
// =====================================================

function showLoading(show) {
  const mapEl = document.getElementById('map');
  if (show) {
    mapEl.style.opacity = '0.5';
    mapEl.style.pointerEvents = 'none';
  } else {
    mapEl.style.opacity = '1';
    mapEl.style.pointerEvents = 'auto';
  }
}

function resetearFiltros() {
  document.getElementById('filtro-estado-pago').value = 'all';
  document.getElementById('filtro-deuda-min').value = '';
  document.getElementById('filtro-deuda-max').value = '';
  document.getElementById('filtro-servicios').value = 'all';
  document.getElementById('filtro-ingreso-min').value = '';
  document.getElementById('filtro-ingreso-max').value = '';
  document.getElementById('search-input').value = '';

  if (heatLayer) {
    map.removeLayer(heatLayer);
    heatLayer = null;
    document.getElementById('toggle-heatmap').checked = false;
  }

  cargarPredios();
}

// =====================================================
// INICIALIZACIÓN Y EVENT LISTENERS
// =====================================================

function applyFiltersAndRender() {
  // Leer valores de los inputs
  const estado = document.getElementById('filtro-estado-pago')?.value || 'all';
  const deudaMin = document.getElementById('filtro-deuda-min')?.value;
  const deudaMax = document.getElementById('filtro-deuda-max')?.value;

  // Construir objeto de filtros
  const filtros = {
    estado: estado,
    deuda_min: deudaMin,
    deuda_max: deudaMax
  };

  // Recargar datos
  cargarPredios(filtros);
}

// =====================================================
// VARIABLES GLOBALES (CRUD)
// =====================================================
let modoCreacion = false;
let modalBootstrap = null;
let currentPredioId = null; // null si es nuevo, ID si es edición

// =====================================================
// INICIALIZACIÓN
// =====================================================
document.addEventListener('DOMContentLoaded', () => {
  // Inicializar mapa
  initMap();

  // Inicializar Modal
  const modalEl = document.getElementById('modalPredio');
  if (modalEl) {
    modalBootstrap = new bootstrap.Modal(modalEl);
  } else {
    console.error("No se encontró el elemento modalPredio");
  }

  // Cargar datos datos iniciales
  cargarPredios();
  // cargarEstadisticasGenerales(); // Temporalmente desactivado por bug secundario

  // Botón Nuevo Predio (FAB)
  document.getElementById('btn-nuevo-predio')?.addEventListener('click', toggleModoCreacion);

  // Botón Guardar en Modal
  document.getElementById('btnGuardarPredio')?.addEventListener('click', guardarPredio);

  // Eventos de Filtros
  document.getElementById('applyFilters')?.addEventListener('click', applyFiltersAndRender);
  document.getElementById('btn-search-contribuyente')?.addEventListener('click', buscarContribuyente);
  document.getElementById('search-contribuyente')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') buscarContribuyente();
  });

  // Exportar
  document.getElementById('btn-export-csv')?.addEventListener('click', exportarCSV);
  document.getElementById('btn-export-pdf')?.addEventListener('click', exportarPDF);

  // Mapa de calor
  document.getElementById('toggle-heatmap')?.addEventListener('change', (e) => {
    if (e.target.checked) {
      if (currentGeojson) {
        construirHeatmap(currentGeojson.features);
      }
    } else {
      if (heatLayer) {
        map.removeLayer(heatLayer);
        heatLayer = null;
      }
    }
  });
});

// =====================================================
// BÚSQUEDA Y FILTROS
// =====================================================

// Búsqueda simple
document.getElementById('btn-search-contribuyente')?.addEventListener('click', () => {
  const val = document.getElementById('search-contribuyente').value;
  buscarContribuyente(val);
});

// Asegurar que el mapa registre el click para el modo creación
function initMap() {
  map = L.map('map').setView([-15.8785, -69.9760], 16);

  // 1. Capa Base (OSM)
  var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 20,
    maxNativeZoom: 19,
    attribution: '© OpenStreetMap'
  }).addTo(map);

  // 2. Capa Satelital (Esri)
  // Usamos maxNativeZoom para que escale la imagen si no hay más detalle
  var satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 20,
    maxNativeZoom: 17,
    attribution: 'Tiles &copy; Esri'
  });

  // 3. Capa Relieve (OpenTopoMap)
  var relieve = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 20,
    maxNativeZoom: 16, // OpenTopoMap suele fallar pasados el zoom 16/17
    attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)'
  });

  // Control de capas
  var baseMaps = {
    "Mapa Base": osm,
    "Satelital": satelite,
    "Relieve": relieve
  };

  L.control.layers(baseMaps).addTo(map);

  // Evento CLICK para Crear Predio
  map.on('click', onMapClick);
}


// =====================================================
// LÓGICA CRUD
// =====================================================

function toggleModoCreacion() {
  modoCreacion = !modoCreacion;
  const btn = document.getElementById('btn-nuevo-predio');
  const mapContainer = document.getElementById('map');

  if (modoCreacion) {
    btn.classList.add('active');
    btn.innerHTML = '<i class="fas fa-times"></i>';
    mapContainer.classList.add('cursor-crosshair');
    alert('🎯 MODO CREACIÓN ACTIVADO\nHaz clic en el mapa para ubicar el nuevo predio.');
  } else {
    btn.classList.remove('active');
    btn.innerHTML = '<i class="fas fa-plus"></i> <span class="d-none d-md-inline ms-1">+</span>';
    mapContainer.classList.remove('cursor-crosshair');
  }
}

// Clic en Mapa (Manejo de Creación)
function onMapClick(e) {
  if (!modoCreacion) return;

  abrirModalCreacion(e.latlng.lat, e.latlng.lng);
  toggleModoCreacion(); // Desactivar modo después de clic
}

function abrirModalCreacion(lat, lng) {
  currentPredioId = null; // Nuevo predio
  document.getElementById('modalTitulo').innerText = 'Nuevo Predio';
  document.getElementById('formPredio').reset();

  // Setear coordenadas
  document.getElementById('latitud').value = lat.toFixed(6);
  document.getElementById('longitud').value = lng.toFixed(6);

  // Generar código temporal sugerido
  document.getElementById('codigo_catastral').value = `NUEVO-${Date.now().toString().slice(-4)}`;

  modalBootstrap.show();
}

// Función global para ser llamada desde el popup
window.editarPredio = function (id) {
  currentPredioId = id;
  const feature = currentGeojson.features.find(f => f.properties.id_predio === id);
  if (!feature) return;

  const p = feature.properties;
  const coords = feature.geometry.coordinates;

  document.getElementById('modalTitulo').innerText = `Editar Predio ${p.codigo_catastral}`;

  // Llenar formulario
  document.getElementById('latitud').value = coords[1];
  document.getElementById('longitud').value = coords[0];
  document.getElementById('codigo_catastral').value = p.codigo_catastral;
  document.getElementById('contribuyente_nombre').value = p.contribuyente_nombre || '';
  document.getElementById('tipo_vivienda').value = p.tipo_vivienda || 'Rústica';
  document.getElementById('autovaluo').value = p.autovaluo || 0;
  document.getElementById('ingreso_familiar').value = p.ingreso_familiar || 0;
  document.getElementById('cantidad_personas').value = p.cantidad_personas || 1;

  document.getElementById('monto_impuesto').value = p.monto_impuesto || 0;
  document.getElementById('pago_impuesto').checked = p.pago_impuesto || false;

  document.getElementById('monto_arbitrios').value = p.monto_arbitrios || 0;
  document.getElementById('pago_arbitrios').checked = p.pago_arbitrios || false;

  modalBootstrap.show();
  map.closePopup();
};

// Función global para eliminar desde popup
window.eliminarPredio = async function (id) {
  if (!confirm('¿Estás seguro de ELIMINAR este predio permanentemente?')) return;

  try {
    const response = await fetch(`${API_URL}/api/predios/${id}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error('Error al eliminar');

    const result = await response.json();
    alert('✅ Predio eliminado exitosamente');
    map.closePopup();
    cargarPredios(); // Recargar mapa

  } catch (error) {
    console.error('Error:', error);
    alert('❌ Error al eliminar el predio');
  }
};

async function guardarPredio() {
  // Recolectar datos del formulario
  const data = {
    latitud: parseFloat(document.getElementById('latitud').value),
    longitud: parseFloat(document.getElementById('longitud').value),
    codigo_catastral: document.getElementById('codigo_catastral').value,
    contribuyente_nombre: document.getElementById('contribuyente_nombre').value,
    tipo_vivienda: document.getElementById('tipo_vivienda').value,
    autovaluo: parseFloat(document.getElementById('autovaluo').value) || 0,
    ingreso_familiar: parseFloat(document.getElementById('ingreso_familiar').value) || 0,
    cantidad_personas: parseInt(document.getElementById('cantidad_personas').value) || 1,
    monto_impuesto: parseFloat(document.getElementById('monto_impuesto').value) || 0,
    pago_impuesto: document.getElementById('pago_impuesto').checked,
    monto_arbitrios: parseFloat(document.getElementById('monto_arbitrios').value) || 0,
    pago_arbitrios: document.getElementById('pago_arbitrios').checked,
    // Valores por defecto
    sector: "Jayllihuaya",
    numero_vivienda: "S/N"
  };

  // Validaciones básicas
  if (!data.codigo_catastral || !data.contribuyente_nombre) {
    alert('Por favor complete Código Catastral y Nombre del Contribuyente');
    return;
  }

  const url = currentPredioId
    ? `${API_URL}/api/predios/${currentPredioId}`
    : `${API_URL}/api/predios`;

  const method = currentPredioId ? 'PUT' : 'POST';

  try {
    const response = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Error al guardar');
    }

    const result = await response.json();
    alert(`✅ Predio ${currentPredioId ? 'actualizado' : 'creado'} exitosamente`);
    modalBootstrap.hide();
    cargarPredios(); // Recargar mapa para ver cambios

  } catch (error) {
    console.error('Error guardando:', error);
    alert(`❌ Error: ${error.message}`);
  }
}


