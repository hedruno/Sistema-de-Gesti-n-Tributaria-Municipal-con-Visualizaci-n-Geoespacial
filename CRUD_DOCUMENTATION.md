# 🎯 CRUD de Predios - Documentación

El sistema ahora incluye **funcionalidad CRUD completa** para gestionar predios.

## 📡 Endpoints API

### 1. CREATE - Crear Nuevo Predio
**POST** `/api/predios`

```json
{
  "latitud": -15.8785,
  "longitud": -69.9760,
  "codigo_catastral": "HOG999",
  "sector": "Jayllihuaya",
  "tipo_vivienda": "Rústica",
  "autovaluo": 50000,
  "numero_vivienda": "S/N",
  "contribuyente_nombre": "Juan Pérez Mamani",
  "monto_impuesto": 120.50,
  "pago_impuesto": false,
  "monto_arbitrios": 85.00,
  "pago_arbitrios": false,
  "ingreso_familiar": 1500,
  "cantidad_personas": 4
}
```

### 2. READ - Leer Predios
**GET** `/api/predios`

Ya implementado ✅

### 3. UPDATE - Actualizar Predio
**PUT** `/api/predios/{id_predio}`

```json
{
  "monto_impuesto": 150.00,
  "pago_impuesto": true,
  "autovaluo": 60000
}
```

### 4. DELETE - Eliminar Predio
**DELETE** `/api/predios/{id_predio}`

---

## 🧪 Probar CRUD con cURL

```powershell
# 1. CREAR predio
curl -X POST http://localhost:8000/api/predios `
  -H "Content-Type: application/json" `
  -d '{
    "latitud": -15.8785,
    "longitud": -69.9760,
    "codigo_catastral": "TEST001",
    "contribuyente_nombre": "Nuevo Propietario",
    "tipo_vivienda": "Material Noble",
    "autovaluo": 80000,
    "monto_impuesto": 200,
    "pago_impuesto": false,
    "monto_arbitrios": 150,
    "pago_arbitrios": false,
    "ingreso_familiar": 2000
  }'

# 2. ACTUALIZAR predio (ejemplo: id_predio = 221)
curl -X PUT http://localhost:8000/api/predios/221 `
  -H "Content-Type: application/json" `
  -d '{
    "monto_impuesto": 250,
    "pago_impuesto": true
  }'

# 3. ELIMINAR predio
curl -X DELETE http://localhost:8000/api/predios/221
```

---

## 🌐 Interfaz Web Swagger

La forma más fácil de probar el CRUD es usando la **interfaz interactiva**:

```
http://localhost:8000/docs
```

En Swagger puedes:
- ✅ Ver todos los endpoints
- ✅ Probar cada operación CRUD
- ✅ Ver ejemplos de Request/Response
- ✅ Ejecutar directamente desde el navegador

---

## 📊 Ejemplos de Uso

### Caso 1: Agregar Predio desde el Mapa

**Usuario hace clic en el mapa → Se abre formulario modal**

Datos capturados:
- ✅ Latitud/Longitud automáticos (clic en mapa)
- ✅ Código catastral generado
- ✅ Formulario para datos tributarios

```javascript
// Ejemplo de llamada desde JavaScript
const response = await fetch('http://localhost:8000/api/predios', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    latitud: clickedLat,
    longitud: clickedLng,
    codigo_catastral: `NUEVO${Date.now()}`,
    contribuyente_nombre: document.getElementById('nombre').value,
    tipo_vivienda: document.getElementById('tipo').value,
    // ... más datos del formulario
  })
});

const result = await response.json();
console.log(result.message); // "Predio creado exitosamente"
```

### Caso 2: Editar Información de Predio

**Usuario hace clic en predio → Popup → Botón "Editar"**

```javascript
// Actualizar solo pago de impuesto
await fetch(`http://localhost:8000/api/predios/${id_predio}`, {
  method: 'PUT',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    pago_impuesto: true,
    pago_arbitrios: true
  })
});

// Recargar mapa para ver cambio de color
cargarPredios();
```

### Caso 3: Eliminar Predio

```javascript
if (confirm('¿Eliminar este predio?')) {
  await fetch(`http://localhost:8000/api/predios/${id_predio}`, {
    method: 'DELETE'
  });
  
  alert('Predio eliminado');
  cargarPredios(); // Refrescar mapa
}
```

---

## ✅ Validaciones Implementadas

### CREATE
- ✅ Código catastral único (no puede duplicarse)
- ✅ Coordenadas obligatorias
- ✅ Contribuyente se reutiliza si ya existe

### UPDATE
- ✅ Verifica que el predio existe
- ✅ Solo actualiza campos proporcionados
- ✅ Actualiza triggers automáticamente (estado_pago, deuda_total)

### DELETE
- ✅ Verifica que el predio existe
- ✅ Elimina tributos en CASCADE
- ✅ NO elimina contribuyente (puede tener otros predios)

---

## 🔄 Flujo de Datos

```
Usuario → Frontend → API REST → PostGIS
                ↓
            Validación
                ↓
        INSERT/UPDATE/DELETE
                ↓
            Triggers SQL
                ↓
        Actualización automática:
        - estado_pago
        - deuda_total
                ↓
        Response GeoJSON
                ↓
        Frontend actualiza mapa
```

---

## 🎨 Próximos Pasos (Interfaz)

Para completar el CRUD en el frontend necesitarías:

### 1. Modal de Creación
```html
<div id="modal-crear-predio" class="modal">
  <form id="form-crear-predio">
    <input name="latitud" readonly>
    <input name="longitud" readonly>
    <input name="codigo_catastral" placeholder="HOG999">
    <input name="contribuyente_nombre" placeholder="Nombre completo">
    <select name="tipo_vivienda">
      <option>Rústica</option>
      <option>Material Noble</option>
    </select>
    <input name="autovaluo" type="number">
    <!-- Más campos -->
    <button type="submit">Crear Predio</button>
  </form>
</div>
```

### 2. Botones en Popup
```javascript
// En crearPopup(), agregar botones:
const html = `
  <div class="popup-tributario">
    <!-- ... info del predio ... -->
    <hr>
    <div class="btn-group">
      <button onclick="editarPredio(${props.id_predio})" class="btn btn-sm btn-warning">
        Editar
      </button>
      <button onclick="eliminarPredio(${props.id_predio})" class="btn btn-sm btn-danger">
        Eliminar
      </button>
    </div>
  </div>
`;
```

### 3. Eventos de Mapa
```javascript
// Clic en mapa para crear predio
map.on('click', function(e) {
  if (modoCreacion) {
    document.getElementById('latitud').value = e.latlng.lat;
    document.getElementById('longitud').value = e.latlng.lng;
    $('#modal-crear-predio').modal('show');
  }
});
```

---

## ✨ El CRUD está LISTO en el backend

**API completamente funcional** ✅

Para probarla ahora mismo:
```
http://localhost:8000/docs
```

¿Quieres que te ayude a implementar también la **interfaz visual** (modales y botones) en el frontend?
