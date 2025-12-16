# =====================================================
# Script de Inicio Rápido
# Sistema de Gestión Tributaria Municipal
# =====================================================

Write-Host "`n==============================================...`n" -ForegroundColor Cyan
Write-Host "Sistema de Gestión Tributaria Municipal" -ForegroundColor Green
Write-Host "Centro Poblado de Jayllihuaya" -ForegroundColor Yellow
Write-Host "`n==============================================" -ForegroundColor Cyan

# Verificar Docker
Write-Host "`n[1/5] Verificando Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker encontrado: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker no está instalado o no está en ejecución" -ForegroundColor Red
    Write-Host "   Por favor, instale Docker Desktop para Windows" -ForegroundColor Red
    Read-Host "Presione Enter para salir"
    exit 1
}

# Verificar Docker Compose
try {
    $composeVersion = docker-compose --version
    Write-Host "✓ Docker Compose encontrado: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose no está instalado" -ForegroundColor Red
    Read-Host "Presione Enter para salir"
    exit 1
}

# Detener contenedores existentes si los hay
Write-Host "`n[2/5] Preparando contenedores..." -ForegroundColor Yellow
docker-compose down 2>$null

# Levantar servicios
Write-Host "`n[3/5] Iniciando servicios Docker (esto puede tomar 1-2 minutos)..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Contenedores iniciados correctamente" -ForegroundColor Green
} else {
    Write-Host "✗ Error al iniciar contenedores" -ForegroundColor Red
    Read-Host "Presione Enter para salir"
    exit 1
}

# Esperar a que PostgreSQL esté listo
Write-Host "`n[4/5] Esperando a que PostgreSQL esté listo..." -ForegroundColor Yellow
$maxRetries = 30
$retry = 0
$ready = $false

while ($retry -lt $maxRetries -and -not $ready) {
    Start-Sleep -Seconds 2
    $retry++
    
    $healthCheck = docker exec tributario_postgis pg_isready -U admin -d tributario_db 2>$null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        Write-Host "✓ PostgreSQL está listo" -ForegroundColor Green
    } else {
        Write-Host "  Esperando... ($retry/$maxRetries)" -ForegroundColor Gray
    }
}

if (-not $ready) {
    Write-Host "✗ PostgreSQL no respondió a tiempo" -ForegroundColor Red
    Write-Host "  Ejecute: docker-compose logs postgis" -ForegroundColor Yellow
    Read-Host "Presione Enter para salir"
    exit 1
}

# Verificar si hay datos en la BD
Write-Host "`n[5/5] Verificando datos en base de datos..." -ForegroundColor Yellow
$prediosCount = docker exec tributario_postgis psql -U admin -d tributario_db -tAc "SELECT COUNT(*) FROM predios;" 2>$null

if ($LASTEXITCODE -eq 0 -and $prediosCount -gt 0) {
    Write-Host "✓ Base de datos con $prediosCount predios registrados" -ForegroundColor Green
} else {
    Write-Host "⚠ Base de datos vacía. Ejecutando migración..." -ForegroundColor Yellow
    
    # Verificar si Python está instalado
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "  Python encontrado: $pythonVersion" -ForegroundColor Gray
        
        # Instalar dependencias si es necesario
        Write-Host "  Instalando dependencias Python..." -ForegroundColor Gray
        pip install -q psycopg2-binary 2>$null
        
        # Ejecutar migración
        Write-Host "  Migrando datos a PostgreSQL..." -ForegroundColor Gray
        python database/migrate_data.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Migración completada correctamente" -ForegroundColor Green
        } else {
            Write-Host "✗ Error en migración. Puede ejecutarla manualmente:" -ForegroundColor Red
            Write-Host "   python database/migrate_data.py" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠ Python no encontrado. Migración manual requerida:" -ForegroundColor Yellow
        Write-Host "   1. Instale Python 3.x" -ForegroundColor Gray
        Write-Host "   2. Ejecute: pip install psycopg2-binary" -ForegroundColor Gray
        Write-Host "   3. Ejecute: python database/migrate_data.py" -ForegroundColor Gray
    }
}

# Verificar servicios
Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host "Estado de Servicios:" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan

docker-compose ps

# Información de acceso
Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host "Sistema Listo!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan

Write-Host "`nAcceda al sistema en:" -ForegroundColor Yellow
Write-Host "  → Frontend:  " -NoNewline
Write-Host "http://localhost" -ForegroundColor Cyan
Write-Host "  → API Docs:  " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  → PostgreSQL:" -NoNewline
Write-Host " localhost:5432 (admin/admin123)" -ForegroundColor Cyan

Write-Host "`nComandos útiles:" -ForegroundColor Yellow
Write-Host "  Ver logs:       docker-compose logs -f" -ForegroundColor Gray
Write-Host "  Detener:        docker-compose down" -ForegroundColor Gray
Write-Host "  Reiniciar:      docker-compose restart" -ForegroundColor Gray
Write-Host "  Backup BD:      docker exec tributario_postgis pg_dump -U admin tributario_db > backup.sql" -ForegroundColor Gray

Write-Host "`n==============================================`n" -ForegroundColor Cyan

# Abrir navegador automáticamente
$openBrowser = Read-Host "¿Desea abrir el navegador ahora? (S/N)"
if ($openBrowser -ieq "S" -or $openBrowser -ieq "Y") {
    Start-Process "http://localhost"
}

Write-Host "Presione Ctrl+C para detener el script (los servicios seguirán activos)" -ForegroundColor Gray
Write-Host "Para detener los servicios, ejecute: docker-compose down`n" -ForegroundColor Gray
