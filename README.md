# Sistema de Gestión Tributaria Municipal - Jayllihuaya

Sistema de gestión de predios y tributos municipales con visualización geoespacial usando **Leaflet + PostGIS + Docker**.

## 📋 Características

- **Visualización geoespacial** de predios con Leaflet
- **Base de datos PostGIS** con geometría y consultas espaciales
- **API REST** con FastAPI para consultas tributarias
- **Filtros avanzados** por estado de pago, rango de deuda, ubicación
- **Búsqueda** de contribuyentes
- **Mapa de calor** por deuda pendiente
- **Exportación** a CSV y PDF
- **Dashboard** con estadísticas tributarias
- **Arquitectura contenerizada** con Docker Compose

## 🚀 Inicio Rápido

### Requisitos Previos

- Docker Desktop para Windows instalado y ejecutándose
- Git (opcional)
- Navegador web moderno

### Instalación

1. **Abrir PowerShell** en el directorio del proyecto:

```powershell
cd f:\OneDrive\Desktop\jayuhualla
```

2. **Levantar los contenedores** con Docker Compose:

```powershell
docker-compose up -d
```

Este comando creará y ejecutará 3 contenedores:
- `tributario_postgis` - Base de datos PostGIS (puerto 5432)
- `tributario_api` - Backend API FastAPI (puerto 8000)
- `tributario_frontend` - Frontend Nginx (puerto 80)

3. **Esperar** a que los contenedores estén listos (30-60 segundos). Verificar estado:

```powershell
docker-compose ps
```

Todos los servicios deben mostrar estado `Up`.

4. **Migrar datos** a PostgreSQL:

```powershell
# Instalar dependencias Python (solo primera vez)
pip install psycopg2-binary

# Ejecutar migración
python database/migrate_data.py
```

5. **Abrir la aplicación** en el navegador:

```
http://localhost
```

## 🎯 Uso del Sistema

### Panel de Filtros

- **Estado de pago**: Filtra predios por AL_DÍA, MOROSO, o EXONERADO
- **Rango de deuda**: Define monto mínimo y máximo de deuda
- **Búsqueda**: Encuentra contribuyentes por nombre
- **Servicios básicos**: Filtro complementario por servicios
- **Ingreso familiar**: Rango de ingresos

### Visualización del Mapa

- **Colores** indican estado tributario:
  - 🟢 Verde = Al día
  - 🔴 Rojo = Moroso
  - 🔵 Azul = Exonerado

- **Clic en predio** muestra popup con:
  - Información del contribuyente
  - Código catastral
  - Autovalúo
  - Estado de pagos (impuesto predial y arbitrios)
  - Deuda total

### Funcionalidades Especiales

- **Mapa de calor**: Activa con el switch para visualizar concentración de deudas
- **Exportar CSV**: Descarga tabla completa filtrada
- **Exportar PDF**: Genera reporte rápido con estadísticas

## 🏗️ Arquitectura

```
┌─────────────┐
│   Nginx     │ ← Frontend (HTML/JS/CSS + Leaflet)
│  (puerto 80)│
└──────┬──────┘
       │
       ↓ /api/*
┌─────────────┐
│  FastAPI    │ ← Backend REST API
│ (puerto 8000)│
└──────┬──────┘
       │
       ↓ SQL + PostGIS
┌─────────────┐
│  PostgreSQL │ ← Base de datos geoespacial
│   PostGIS   │
│ (puerto 5432)│
└─────────────┘
```

## 📊 Modelo de Datos

### Tablas Principales

- **predios**: Catastro con geometría PostGIS
- **contribuyentes**: Propietarios responsables
- **tributos**: Información tributaria y estados de pago

### Relaciones

```
contribuyentes ←─┬─→ tributos ←─┬─→ predios
                 │               │
            (1:N)│          (N:1)│
                 └───────────────┘
```

## 🔧 Configuración Avanzada

### Variables de Entorno

Editar `docker-compose.yml` para cambiar credenciales:

```yaml
environment:
  POSTGRES_USER: admin
  POSTGRES_PASSWORD: admin123
  POSTGRES_DB: tributario_db
```

### Acceso Directo a PostgreSQL

```powershell
docker exec -it tributario_postgis psql -U admin -d tributario_db
```

Consultas útiles:

```sql
-- Ver total de predios
SELECT COUNT(*) FROM predios;

-- Estadísticas por estado
SELECT estado_pago, COUNT(*), SUM(deuda_total) 
FROM tributos 
GROUP BY estado_pago;

-- Predios morosos con mayor deuda
SELECT p.codigo_catastral, c.nombres, t.deuda_total
FROM predios p
JOIN tributos t ON p.id_predio = t.id_predio
JOIN contribuyentes c ON t.id_contribuyente = c.id_contribuyente
WHERE t.estado_pago = 'MOROSO'
ORDER BY t.deuda_total DESC
LIMIT 10;
```

### API Endpoints

Acceder directamente a la API en `http://localhost:8000`:

- `GET /api/predios` - Todos los predios
- `GET /api/predios/morosos` - Solo morosos
- `GET /api/buscar?nombre={nombre}` - Buscar contribuyente
- `GET /api/predios/radio?lat={lat}&lng={lng}&radius={m}` - Búsqueda espacial
- `GET /api/estadisticas` - Dashboard con métricas
- `GET /api/sectores` - Estadísticas por sector

Documentación interactiva: `http://localhost:8000/docs`

## 🛠️ Mantenimiento

### Ver logs

```powershell
# Todos los servicios
docker-compose logs -f

# Solo backend
docker-compose logs -f backend

# Solo base de datos
docker-compose logs -f postgis
```

### Reiniciar servicios

```powershell
docker-compose restart
```

###  Detener sistema

```powershell
docker-compose down
```

### Limpiar todo (¡cuidado, borra datos!)

```powershell
docker-compose down -v
```

## 🐛 Troubleshooting

### Error "Cannot connect to Docker daemon"

- Verificar que Docker Desktop esté ejecutándose
- Reiniciar Docker Desktop

### Error 500 en API

- Verificar que PostgreSQL esté activo: `docker-compose ps`
- Ver logs: `docker-compose logs backend`
- Verificar migración de datos completada

### No aparecen predios en el mapa

1. Verificar migración: `python database/migrate_data.py`
2. Comprobar datos en BD: `docker exec tributario_postgis psql -U admin -d tributario_db -c "SELECT COUNT(*) FROM predios;"`
3. Revisar consola del navegador (F12) para errores JavaScript

### Puerto 80 ya en uso

Cambiar puerto en `docker-compose.yml`:

```yaml
frontend:
  ports:
    - "8080:80"  # Usar puerto 8080
```

Luego acceder a `http://localhost:8080`

## 📚 Tecnologías Utilizadas

- **Frontend**: Leaflet.js, Bootstrap 5, Chart.js
- **Backend**: Python FastAPI, Uvicorn
- **Base de Datos**: Post greSQL 15 + PostGIS 3.3
- **Contenerización**: Docker + Docker Compose
- **Servidor Web**: Nginx Alpine

## 👥 Créditos

Sistema desarrollado para la Municipalidad del Centro Poblado de Jayllihuaya, Puno, Perú.

## 📄 Licencia

Proyecto académico - Municipalidad de Jayllihuaya © 2024
