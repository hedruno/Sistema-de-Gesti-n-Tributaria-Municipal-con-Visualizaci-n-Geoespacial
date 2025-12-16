# 🔍 Guía de Verificación del Sistema

Esta guía te ayudará a verificar que el sistema de gestión tributaria esté funcionando correctamente.

## ✅ Checklist de Archivos

### Archivos Principales
- [x] `README.md` - Documentación principal
- [x] `INFORME_SISTEMA_TRIBUTARIO.md` - Informe técnico completo
- [x] `RESUMEN_EJECUTIVO.md` - Resumen de cumplimiento de rúbrica
- [x] `docker-compose.yml` - Configuración de contenedores
- [x] `nginx.conf` - Configuración del servidor web
- [x] `start.ps1` - Script de inicio rápido
- [x] `.gitignore` - Exclusiones para Git

### Frontend
- [x] `index.html` - Interfaz web principal
- [x] `script.js` - Lógica JavaScript con Leaflet
- [x] `styles.css` - Estilos CSS
- [x] `kd_tree.js` - Estructura de datos espacial
- [x] `data.json` - Datos fuente (343 predios)
- [x] `images/` - Carpeta con imágenes

### Backend
- [x] `backend/main.py` - API FastAPI
- [x] `backend/requirements.txt` - Dependencias Python
- [x] `backend/Dockerfile` - Imagen Docker

### Base de Datos
- [x] `database/init.sql` - Esquema PostGIS
- [x] `database/migrate_data.py` - Script de migración

---

## 🚀 Verificación Paso a Paso

### PASO 1: Verificar Docker

```powershell
# Abrir PowerShell y ejecutar:
docker --version
docker-compose --version
```

**Resultado esperado:**
```
Docker version 24.x.x
Docker Compose version v2.x.x
```

✅ Si ves versiones, Docker está instalado correctamente  
❌ Si hay error, instala Docker Desktop

---

### PASO 2: Iniciar el Sistema

#### Opción A: Script Automático (Recomendado)

```powershell
cd f:\OneDrive\Desktop\jayuhualla
.\start.ps1
```

**Resultado esperado:**
- Mensaje "Docker encontrado" en verde
- Contenedores iniciándose
- PostgreSQL listo
- Migración de datos completada
- URLs de acceso mostradas

#### Opción B: Manual

```powershell
cd f:\OneDrive\Desktop\jayuhualla
docker-compose up -d
```

**Esperar 30-60 segundos** para que los servicios se inicien.

---

### PASO 3: Verificar Estado de Contenedores

```powershell
docker-compose ps
```

**Resultado esperado:**
```
NAME                    STATUS
tributario_postgis      Up (healthy)
tributario_api          Up (healthy)
tributario_frontend     Up
```

✅ Todos los servicios deben mostrar "Up"  
❌ Si alguno dice "Exit" o "Restarting", ver logs: `docker-compose logs [servicio]`

---

### PASO 4: Verificar Base de Datos

```powershell
# Conectar a PostgreSQL
docker exec -it tributario_postgis psql -U admin -d tributario_db

# Dentro de psql, ejecutar:
\dt
```

**Resultado esperado:**
```
              List of relations
 Schema |      Name       | Type  | Owner 
--------+-----------------+-------+-------
 public | contribuyentes  | table | admin
 public | predios         | table | admin
public | tributos        | table | admin
```

```sql
-- Verificar cantidad de predios
SELECT COUNT(*) FROM predios;
```

**Resultado esperado:** `343` (o el número de registros en data.json)

```sql
-- Verificar distribución de estados
SELECT estado_pago, COUNT(*) 
FROM tributos 
GROUP BY estado_pago;
```

**Resultado esperado:**
```
 estado_pago | count 
-------------+-------
 AL_DIA      |   224
 MOROSO      |    85
 EXONERADO   |    34
```

```sql
-- Salir de psql
\q
```

---

### PASO 5: Verificar API Backend

#### 5.1 Endpoint Raíz

```powershell
# Abrir en navegador o ejecutar:
curl http://localhost:8000
```

**Resultado esperado:**
```json
{
  "mensaje": "API Tributaria Municipal - Jayllihuaya",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

#### 5.2 Endpoint Predios

```powershell
curl http://localhost:8000/api/predios | ConvertFrom-Json | Select-Object -First 1
```

**Resultado esperado:** GeoJSON con estructura:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-69.976, -15.8785]
      },
      "properties": {
        "codigo_catastral": "HOG001",
        "contribuyente_nombre": "Propietario_1",
        "estado_pago": "AL_DIA",
        "deuda_total": 0.00
      }
    }
  ]
}
```

#### 5.3 Endpoint Morosos

```powershell
curl http://localhost:8000/api/predios/morosos
```

**Resultado esperado:** Solo predios con `estado_pago = "MOROSO"`

#### 5.4 Endpoint Estadísticas

```powershell
curl http://localhost:8000/api/estadisticas
```

**Resultado esperado:**
```json
{
  "resumen": {
    "total_predios": 343,
    "deuda_total_municipal": 125450.75,
    "porcentaje_cumplimiento": 65.3
  },
  "distribucion_estado": { ... },
  "sector_critico": { ... }
}
```

#### 5.5 Documentación Interactiva

**Abrir en navegador:**
```
http://localhost:8000/docs
```

**Resultado esperado:** Interfaz Swagger UI con todos los endpoints listados y probables

---

### PASO 6: Verificar Frontend

#### 6.1 Acceder a la Aplicación

**Abrir en navegador:**
```
http://localhost
```

**Resultado esperado:**
- Título: "Sistema de Gestión Tributaria Municipal — Jayllihuaya"
- Mapa cargado con OpenStreetMap
- Leyenda visible con colores: Verde (Al Día), Rojo (Moroso), Azul (Exonerado)
- Panel lateral con filtros

#### 6.2 Verificar Carga de Predios

**En el mapa, debes ver:**
- ⭕ Círculos de colores (verde, rojo, azul) representando predios
- Al menos 50-100 círculos visibles en la zona de Jayllihuaya
- Posibilidad de hacer zoom con scroll del mouse

**Si no ves predios:**
1. Abrir consola del navegador (F12)
2. Buscar errores en consola
3. Verificar que el endpoint `/api/predios` responda

#### 6.3 Verificar Filtros

##### Filtro por Estado
1. En panel lateral, seleccionar "Estado de pago" → "Morosos"
2. Clic "Aplicar filtros"
3. **Resultado esperado:** Solo círculos rojos en el mapa

##### Filtro por Deuda
1. Ingresar "Deuda mínima": 100
2. Ingresar "Deuda máxima": 300
3. Clic "Aplicar filtros"
4. **Resultado esperado:** Solo predios con deuda entre S/ 100-300

##### Búsqueda de Contribuyente
1. En buscador, escribir "Propietario_10"
2. Clic "Buscar"
3. **Resultado esperado:**
   - Mapa se centra en ese predio
   - Popup se abre automáticamente
   - Información del contribuyente visible

#### 6.4 Verificar Popup

1. Hacer clic en cualquier círculo del mapa
2. **Resultado esperado:**
   ```
   ┌─────────────────────────────┐
   │ Propietario_1               │
   ├─────────────────────────────┤
   │ Código: HOG001              │
   │ Tipo: Rústica               │
   │ Autovalúo: S/ 59,900.00     │
   ├─────────────────────────────┤
   │ Estado: AL_DIA              │
   │ Deuda Total: S/ 0.00        │
   ├─────────────────────────────┤
   │ Impuesto: ✅ Pagado         │
   │ Arbitrios: ✅ Pagado        │
   ├─────────────────────────────┤
   │ Ingreso Familiar: S/ 1,198  │
   │ Personas: 4                 │
   └─────────────────────────────┘
   ```

#### 6.5 Verificar Resumen de Estadísticas

En panel lateral, arriba de los filtros, debe aparecer recuadro gris con:
- Total predios: 343
- Deuda total: S/ 125,450.75
- Morosos: 85
- Al día: 224
- Ingreso promedio: S/ 1,350.25

#### 6.6 Verificar Gráficos

Scroll down en panel lateral, deben aparecer 2 gráficos:

**Gráfico 1 (Dona):** Distribución por Estado
- Verde: Al Día
- Rojo: Moroso
- Azul: Exonerado

**Gráfico 2 (Barras):** Distribución por Deuda
- Rangos: 0-50, 51-100, 101-200, 201-500, 500+

#### 6.7 Verificar Exportación CSV

1. Aplicar filtro "Morosos"
2. Clic botón "Exportar CSV"
3. **Resultado esperado:**
   - Archivo descargado: `predios_tributarios_2024-12-16.csv`
   - Abrir en Excel/LibreOffice
   - Columnas: Código Catastral, Contribuyente, DNI, Tipo Vivienda, Estado Pago, Deuda Total, etc.
   - Solo registros con estado "MOROSO"

#### 6.8 Verificar Mapa de Calor

1. Activar switch "Mostrar mapa de calor (deuda pendiente)"
2. **Resultado esperado:**
   - Capa semitransparente sobre el mapa
   - Colores: Verde (baja deuda) → Amarillo → Naranja → Rojo (alta deuda)
   - Zonas con concentración de morosos más rojas

---

### PASO 7: Pruebas Avanzadas

#### 7.1 Búsqueda Espacial (API)

```powershell
# Buscar predios en radio de 500m desde coordenada central
curl "http://localhost:8000/api/predios/radio?lat=-15.8785&lng=-69.976&radius=500"
```

**Resultado esperado:** GeoJSON con propiedad `distancia_metros` en cada feature

#### 7.2 Búsqueda por Nombre Parcial

```powershell
curl "http://localhost:8000/api/buscar?nombre=Prop"
```

**Resultado esperado:** Múltiples predios que contengan "Prop" en el nombre

#### 7.3 Endpoint Sectores

```powershell
curl http://localhost:8000/api/sectores
```

**Resultado esperado:**
```json
{
  "sectores": [
    {
      "sector": "Jayllihuaya",
      "total_predios": 343,
      "morosos": 85,
      "al_dia": 224,
      "deuda_total": 125450.75,
      "porcentaje_morosidad": 24.78
    }
  ]
}
```

#### 7.4 Consulta SQL Directa

```powershell
docker exec tributario_postgis psql -U admin -d tributario_db -c "
SELECT 
  p.codigo_catastral,
  c.nombres,
  t.estado_pago,
  t.deuda_total
FROM predios p
JOIN tributos t ON p.id_predio = t.id_predio
JOIN contribuyentes c ON t.id_contribuyente = c.id_contribuyente
WHERE t.estado_pago = 'MOROSO'
ORDER BY t.deuda_total DESC
LIMIT 10;
"
```

**Resultado esperado:** Top 10 morosos con mayor deuda

---

## 🎯 Escenarios de Demostración para Evaluación

### Escenario 1: Gestión de Morosos
**Objetivo:** Identificar y exportar lista de predios morosos

1. Abrir `http://localhost`
2. Filtro "Estado de pago" → "Morosos"
3. Clic "Aplicar filtros"
4. Observar: Solo círculos rojos, resumen muestra 85 morosos, S/ 125,450.75 deuda
5. Clic "Exportar CSV"
6. Abrir CSV, verificar solo registros morosos
7. **Demostrado:** Filtro funcional ✅

### Escenario 2: Búsqueda de Contribuyente
**Objetivo:** Localizar un predio específico

1. En buscador, escribir "Propietario_25"
2. Clic "Buscar"
3. Observar: Mapa centra, popup se abre
4. Leer información: Estado, deuda, pagos
5. **Demostrado:** Búsqueda funcional ✅

### Escenario 3: Análisis Espacial
**Objetivo:** Consultar predios cercanos

1. Abrir Swagger UI: `http://localhost:8000/docs`
2. Endpoint: `/api/predios/radio`
3. Parámetros:
   - lat: -15.8785
   - lng: -69.976
   - radius: 500
4. Clic "Try it out" → "Execute"
5. Observar respuesta: GeoJSON con distancia_metros
6. **Demostrado:** PostGIS ST_DWithin funcional ✅

### Escenario 4: Visualización con Mapa de Calor
**Objetivo:** Identificar zonas críticas

1. Filtro "Morosos"
2. Activar "Mostrar mapa de calor"
3. Observar: Zonas rojas indican alta concentración de deuda
4. **Demostrado:** Heatmap funcional ✅

### Escenario 5: Dashboard de Estadísticas
**Objetivo:** Métricas en tiempo real

1. Abrir `http://localhost:8000/api/estadisticas`
2. Observar JSON con:
   - Total predios: 343
   - Deuda municipal: S/ 125,450.75
   - Sector crítico identificado
   - Porcentaje cumplimiento: 65.3%
3. **Demostrado:** Análisis estadístico funcional ✅

---

## 🐛 Solución de Problemas Comunes

### Problema 1: Contenedores no inician

```powershell
docker-compose down
docker-compose up -d --force-recreate
```

### Problema 2: Base de datos vacía

```powershell
# Ejecutar migración
python database/migrate_data.py

# O manualmente
docker exec -it tributario_postgis psql -U admin -d tributario_db -f /docker-entrypoint-initdb.d/init.sql
```

### Problema 3: No aparecen predios en el mapa

1. Abrir consola del navegador (F12)
2. Ver si hay error en red (Network tab)
3. Verificar que `http://localhost:8000/api/predios` responda

```powershell
# Probar API directamente
curl http://localhost:8000/api/predios
```

### Problema 4: Error CORS

Verificar que nginx.conf tenga configurado el proxy correctamente:
```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;
}
```

### Problema 5: Puerto 80 ocupado

Cambiar puerto en docker-compose.yml:
```yaml
frontend:
  ports:
    - "8080:80"  # Cambiar a 8080
```

Luego acceder a `http://localhost:8080`

---

## ✅ Confirmación Final

Si todos los siguientes puntos funcionan, el sistema está **100% operativo**:

- [ ] Contenedores activos (`docker-compose ps` muestra 3 servicios Up)
- [ ] Base de datos con 343 predios (`SELECT COUNT(*) FROM predios`)
- [ ] API responde en `http://localhost:8000`
- [ ] Documentación visible en `http://localhost:8000/docs`
- [ ] Frontend carga en `http://localhost`
- [ ] Mapa muestra círculos de colores (predios)
- [ ] Filtro de morosos funciona
- [ ] Búsqueda de contribuyente funciona
- [ ] Popup muestra información completa
- [ ] Exportación CSV descarga archivo
- [ ] Mapa de calor se activa correctamente
- [ ] Estadísticas muestran datos correctos

---

**Si todos los checks están completos, el sistema está listo para demostración y evaluación.** 🎉

---

## 📊 Métricas de Validación

### Rendimiento Esperado
- **Carga inicial del mapa**: < 2 segundos
- **Filtro de 85 morosos**: < 500ms
- **Búsqueda de contribuyente**: < 300ms
- **Consulta espacial (500m)**: < 400ms
- **Exportación CSV (85 registros)**: < 1 segundo

### Disponibilidad
- **Uptime esperado**: 99.9% (solo se cae si se apaga Docker)
- **Recovery time**: < 30 segundos (reinicio de contenedores)

---

**Última actualización:** Diciembre 2024  
**Versión:** 1.0.0
