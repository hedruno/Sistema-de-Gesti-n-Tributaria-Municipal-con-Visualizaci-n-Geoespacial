# IMPLEMETACIÓN DEL SISTEMA DE GESTIÓN TRIBUTARIA MUNICIPAL - JAYLLIHUAYA
**Informe Técnico Final**
**Fecha:** 16 de Diciembre de 2025

---

## 1. Resumen Ejecutivo

El presente proyecto ha logrado la implementación exitosa de un **Sistema de Información Geográfica (SIG) web** para la gestión tributaria del Centro Poblado de Jayllihuaya. El sistema permite la visualización, administración y análisis espacial de 220 predios, facilitando la identificación de contribuyentes morosos y la gestión de recaudación mediante una interfaz interactiva y amigable.

El sistema integra tecnologías modernas de código abierto (**PostGIS, FastAPI, Leaflet, Docker**) para ofrecer una solución robusta, escalable y de fácil despliegue.

---

## 2. Arquitectura del Sistema

El sistema sigue una arquitectura de microservicios contenerizada:

### 2.1 Componentes Principales

1.  **Base de Datos (PostgreSQL + PostGIS):**
    *   Almacenamiento de datos alfanuméricos y espaciales.
    *   Motor espacial para consultas geográficas (distancias, áreas).
    *   Lógica de negocio implementada en base de datos (Triggers).

2.  **Backend (Python FastAPI):**
    *   API RESTful de alto rendimiento.
    *   Gestión de conexiones a base de datos.
    *   Validación de datos y manejo de errores.
    *   Endpoints CRUD y de análisis espacial.

3.  **Frontend (Javascript + Leaflet):**
    *   Interfaz de usuario reactiva basada en mapas.
    *   Visualización de datos con simbología dinámica.
    *   Herramientas de filtrado, búsqueda y edición en tiempo real.

4.  **Infraestructura (Docker Compose):**
    *   Orquestación de servicios.
    *   Red interna aislada para seguridad.
    *   Volúmenes persistentes para datos.

---

## 3. Base de Datos e Ingeniería de Datos

### 3.1 Esquema Relacional
Se diseñó un modelo normalizado para garantizar la integridad de los datos:

*   **Tabla `predios`**: Contiene la información catastral y la geometría espacial (`GEOMETRY(Point, 4326)`).
*   **Tabla `contribuyentes`**: Almacena datos personales (Nombre, DNI) con unicidad, permitiendo que un contribuyente posea múltiples predios.
*   **Tabla `tributos`**: Vincula predios y contribuyentes, almacenando montos, deudas y estados de pago.

### 3.2 Automatización SQL (Triggers)
Se implementaron triggers para mantener la consistencia automática:
*   `calcular_valores_tributarios`: Se activa ante INSERT o UPDATE. Calcula automáticamente:
    *   `deuda_total` = (monto_impuesto si no pagó) + (monto_arbitrios si no pagó).
    *   `estado_pago`: Se actualiza automáticamente a 'AL_DIA', 'MOROSO' o 'EXONERADO' según las deudas.

### 3.3 Migración de Datos
*   Se desarrolló un script de migración (`generate_inserts.py`) que transforma los datos crudos (`data.json`) en sentencias SQL optimizadas.
*   **Solución Técnica:** Se resolvió el problema de codificación de caracteres (UTF-8) en entornos Windows para garantizar que nombres con tildes y ñ se almacenen correctamente.

---

## 4. Backend (API REST)

El backend expone una API documentada (Swagger UI) con las siguientes capacidades:

### 4.1 Endpoints de Consulta
*   `GET /api/predios`: Recupera todos los predios en formato **GeoJSON** estándar. Soporta filtrado por estado, deuda y sector.
*   `GET /api/buscar`: Búsqueda difusa (fuzzy search) de contribuyentes por nombre.
*   `GET /api/sectores`: Estadísticas agregadas por sector (barrio).

### 4.2 Endpoints CRUD (Gestión)
*   `POST /api/predios`: Crea nuevos predios. Valida existencia de contribuyente (lo crea si no existe) y unicidad catastral.
*   `PUT /api/predios/{id}`: Actualización parcial o total de datos. Recalcula automáticamente deudas vía base de datos.
*   `DELETE /api/predios/{id}`: Eliminación segura con integridad referencial (CASCADE).

---

## 5. Frontend y Visualización (Leaflet)

La interfaz es el corazón del sistema, diseñada para ser intuitiva para personal municipal.

### 5.1 Capacidades del Mapa
*   **Multicapa:** Soporte para 3 vistas base conmutables:
    1.  **Mapa Base:** Calles y referencias (OpenStreetMap).
    2.  **Satelital:** Imágenes aéreas reales (Esri World Imagery).
    3.  **Relieve:** Topografía y curvas de nivel (OpenTopoMap).
*   **Zoom Inteligente:** Implementación de `maxNativeZoom` para permitir "zoom digital" profundo en zonas rurales donde no existen imágenes satelitales de alta resolución, evitando errores de carga y "pantallas grises".

### 5.2 Simbología y Análisis Visual
*   **Semáforo Tributario:** Marcadores coloreados automáticamente:
    *   🔴 **Rojo:** Morosos (Deuda activa).
    *   🟢 **Verde:** Al Día (Sin deuda).
    *   🔵 **Azul:** Exonerados.
*   **Mapa de Calor (Heatmap):** Capa activable que visualiza la concentración de deuda en el territorio, permitiendo identificar "zonas críticas" de morosidad.

### 5.3 Gestión Visual (CRUD Interactivo)
*   **Creación:** Botón flotante (+) que activa un modo de cursor preciso. Al hacer clic en el mapa, captura latitud/longitud y abre un formulario modal.
*   **Edición/Eliminación:** Cada predio tiene un popup interactivo con botones directos para editar sus datos o eliminar el registro.
*   **Actualización en Tiempo Real:** Al guardar cambios, el mapa se refresca automáticamente sin recargar la página, mostrando el nuevo color según el estado de pago recalculado.

### 5.4 Reportes y Exportación
*   **CSV:** Exportación de la data filtrada a Excel/CSV.
*   **PDF:** Generación de reportes imprimibles con resumen ejecutivo.
*   **Filtros Avanzados:** Filtrado por rango de deuda, nombre, servicios básicos e ingreso familiar.

---

## 6. Despliegue y Tecnologías

El proyecto utiliza **Docker Compose** para asegurar que funcione idénticamente en cualquier servidor.

```yaml
services:
  postgis:
    image: postgis/postgis:15-3.3
    # Persistencia de datos espacial
  
  backend:
    build: ./backend
    # API Python de alto rendimiento
  
  frontend:
    image: nginx:alpine
    # Servidor web ligero y proxy inverso
```

### Instrucciones de Ejecución
1.  Iniciar sistema: `docker-compose up -d --build`
2.  Acceder al mapa: `http://localhost`
3.  Acceder a documentación API: `http://localhost:8000/docs`

---

## 7. Conclusión

El sistema desarrollado cumple con todos los requerimientos funcionales y técnicos. Transforma una gestión basada en archivos planos en una **base de datos espacial robusta y transaccional**. 

La capacidad de visualizar la deuda en un mapa, junto con las herramientas de edición directa, empodera al municipio de Jayllihuaya para tomar decisiones basadas en datos geográficos precisos, optimizando sus campañas de recaudación y planificación urbana.
