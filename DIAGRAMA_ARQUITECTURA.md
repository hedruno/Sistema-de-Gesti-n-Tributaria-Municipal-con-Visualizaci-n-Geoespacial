# Arquitectura de Red y Comunicación de Servicios

Este diagrama representa la comunicación entre los contenedores Docker del sistema.

```mermaid
graph TD
    %% Estilos
    classDef container fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000;
    classDef external fill:#fff3e0,stroke:#ff6f00,stroke-width:2px,color:#000;
    classDef database fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000;

    %% Nodos Externos
    User((Usuario / Navegador)):::external

    %% Docker Network
    subgraph "Docker Compose Network (tributario_net)"
        direction TB
        
        %% Frontend Service
        Frontend[Frontend Service<br/>(Nginx Server)]:::container
        
        %% Backend Service
        Backend[Backend Service<br/>(FastAPI - Python)]:::container
        
        %% Database Service
        DB[(Database Service<br/>PostgreSQL + PostGIS)]:::database
    end

    %% Conexiones
    User -- "HTTP Request (Port 80)" --> Frontend
    Frontend -- "Serves Static Files (HTML/JS)" -.-> User
    Frontend -- "Proxy Pass /api (Port 8000)" --> Backend
    Backend -- "SQL Queries (Port 5432)" --> DB
    DB -- "GeoJSON Data" --> Backend
    Backend -- "JSON Response" --> Frontend

    %% Notas
    click Frontend "http://localhost" "Abrir Frontend"
```

## Descripción del Flujo
1. **Usuario:** Accede a `localhost:80` (Mapeado al puerto del host).
2. **Frontend (Nginx):** Sirve los archivos estáticos (`index.html`) y actúa como **Reverse Proxy**. redirigiendo las llamadas que empiezan con `/api` hacia el backend.
3. **Backend (FastAPI):** Recibe las peticiones en el puerto 8000 (interno), procesa la lógica y genera consultas SQL.
4. **Base de Datos (PostGIS):** Recibe comandos en el puerto 5432, ejecuta funciones espaciales (`ST_Distance`, `ST_MakePoint`) y retorna los datos.
