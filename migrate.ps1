# =====================================================
# Script de Migracion Alternativo (usa Docker Exec)
# Evita problemas de encoding en Windows
# =====================================================

Write-Host "`n==============================================`n" -ForegroundColor Cyan
Write-Host "MIGRACION DE DATOS A POSTGIS" -ForegroundColor Green
Write-Host "==============================================`n" -ForegroundColor Cyan

# Verificar que Docker este corriendo
try {
    docker ps | Out-Null
} catch {
    Write-Host "[ERROR] Docker no esta ejecutandose" -ForegroundColor Red
    exit 1
}

# Copiar archivos al contenedor
Write-Host "[1/4] Copiando archivos al contenedor..." -ForegroundColor Yellow
docker cp ./data.json tributario_postgis:/tmp/data.json
docker cp ./database/migrate_data.py tributario_postgis:/tmp/migrate_data.py

# Instalar dependencias en el contenedor
Write-Host "[2/4] Instalando dependencias (psycopg2)..." -ForegroundColor Yellow
docker exec tributario_postgis bash -c "apt-get update -qq && apt-get install -y -qq python3-psycopg2 > /dev/null 2>&1"

# Ejecutar migracion dentro del contenedor
Write-Host "[3/4] Ejecutando migracion..." -ForegroundColor Yellow
docker exec -e PYTHONIOENCODING=utf-8 tributario_postgis python3 /tmp/migrate_data.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Migracion completada exitosamente!" -ForegroundColor Green
    
    # Verificar datos
    Write-Host "`n[4/4] Verificando datos..." -ForegroundColor Yellow
    docker exec tributario_postgis psql -U admin -d tributario_db -c "SELECT COUNT(*) as total_predios FROM predios;"
    docker exec tributario_postgis psql -U admin -d tributario_db -c "SELECT estado_pago, COUNT(*) FROM tributos GROUP BY estado_pago;"
} else {
    Write-Host "`n[ERROR] Fallo la migracion" -ForegroundColor Red
    Write-Host "Ver logs arriba para mas detalles" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n==============================================`n" -ForegroundColor Cyan
