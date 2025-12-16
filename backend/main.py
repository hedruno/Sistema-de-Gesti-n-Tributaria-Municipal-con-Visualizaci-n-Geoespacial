"""
Sistema de Gestión Tributaria Municipal - API Backend
FastAPI + PostGIS
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime

# Configuración
app = FastAPI(
    title="API Tributaria Municipal",
    description="API para gestión de predios y tributos con PostGIS",
    version="1.0.0"
)

# CORS para permitir requests desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgis'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'tributario_db'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123')
}

def get_db_connection():
    """Obtiene conexión a base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión a BD: {str(e)}")

def row_to_geojson_feature(row: Dict) -> Dict:
    """Convierte fila de BD a Feature GeoJSON"""
    properties = dict(row)
    
    # Extraer geometría
    geom_json = properties.pop('geom_json', None)
    properties.pop('longitud', None)
    properties.pop('latitud', None)
    
    # Convertir tipos no serializables
    for key, value in properties.items():
        if isinstance(value, datetime):
            properties[key] = value.isoformat()
        elif value is None:
            properties[key] = None
        elif isinstance(value, (int, float, str, bool)):
            continue
        else:
            properties[key] = str(value)
    
    return {
        "type": "Feature",
        "geometry": geom_json,
        "properties": properties
    }

# =====================================================
# ENDPOINTS
# =====================================================

@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "mensaje": "API Tributaria Municipal - Jayllihuaya",
        "version": "1.0.0",
        "endpoints": {
            "predios": "/api/predios",
            "morosos": "/api/predios/morosos",
            "buscar": "/api/buscar?nombre={nombre}",
            "radio": "/api/predios/radio?lat={lat}&lng={lng}&radius={metros}",
            "estadisticas": "/api/estadisticas",
            "sectores": "/api/sectores"
        }
    }

@app.get("/api/predios")
def get_predios(
    estado: Optional[str] = Query(None, description="Filtrar por estado: AL_DIA, MOROSO, EXONERADO"),
    deuda_min: Optional[float] = Query(None, description="Deuda mínima"),
    deuda_max: Optional[float] = Query(None, description="Deuda máxima"),
    sector: Optional[str] = Query(None, description="Filtrar por sector")
):
    """
    Obtiene todos los predios con información tributaria en formato GeoJSON
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Construir query con filtros dinámicos
    where_clauses = []
    params = []
    
    if estado:
        where_clauses.append("estado_pago = %s")
        params.append(estado.upper())
    
    if deuda_min is not None:
        where_clauses.append("deuda_total >= %s")
        params.append(deuda_min)
    
    if deuda_max is not None:
        where_clauses.append("deuda_total <= %s")
        params.append(deuda_max)
    
    if sector:
        where_clauses.append("sector ILIKE %s")
        params.append(f"%{sector}%")
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    query = f"""
        SELECT * FROM predios_completo
        WHERE {where_sql}
        ORDER BY deuda_total DESC
    """
    
    try:
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Convertir a GeoJSON
        features = [row_to_geojson_feature(dict(row)) for row in rows]
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total": len(features),
                "filtros_aplicados": {
                    "estado": estado,
                    "deuda_min": deuda_min,
                    "deuda_max": deuda_max,
                    "sector": sector
                }
            }
        }
        
        return geojson
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/predios/morosos")
def get_morosos():
    """
    Obtiene solo predios con estado MOROSO
    """
    return get_predios(estado="MOROSO")

@app.get("/api/buscar")
def buscar_contribuyente(
    nombre: str = Query(..., description="Nombre del contribuyente a buscar")
):
    """
    Busca predios por nombre de contribuyente
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT * FROM predios_completo
        WHERE contribuyente_nombre ILIKE %s
        ORDER BY contribuyente_nombre
    """
    
    try:
        cur.execute(query, (f"%{nombre}%",))
        rows = cur.fetchall()
        
        features = [row_to_geojson_feature(dict(row)) for row in rows]
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total": len(features),
                "busqueda": nombre
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/predios/radio")
def buscar_por_radio(
    lat: float = Query(..., description="Latitud del centro"),
    lng: float = Query(..., description="Longitud del centro"),
    radius: float = Query(500, description="Radio en metros")
):
    """
    Busca predios dentro de un radio desde un punto
    Usa ST_DWithin con geography para precisión en metros
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT p.*, 
               ST_Distance(
                   p.geom::geography,
                   ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
               ) AS distancia_metros
        FROM predios_completo p
        WHERE ST_DWithin(
            p.geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
        ORDER BY distancia_metros
    """
    
    try:
        cur.execute(query, (lng, lat, lng, lat, radius))
        rows = cur.fetchall()
        
        features = []
        for row in rows:
            row_dict = dict(row)
            distancia = row_dict.pop('distancia_metros', 0)
            feature = row_to_geojson_feature(row_dict)
            feature['properties']['distancia_metros'] = round(distancia, 2)
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total": len(features),
                "centro": {"lat": lat, "lng": lng},
                "radio_metros": radius
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/estadisticas")
def get_estadisticas():
    """
    Obtiene estadísticas generales del sistema tributario
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Total de predios
        cur.execute("SELECT COUNT(*) FROM predios")
        total_predios = cur.fetchone()[0]
        
        # Distribución por estado
        cur.execute("""
            SELECT estado_pago, COUNT(*) as cantidad, SUM(deuda_total) as deuda
            FROM tributos
            GROUP BY estado_pago
        """)
        distribucion_estado = {row['estado_pago']: {
            'cantidad': row['cantidad'],
            'deuda_total': float(row['deuda'] or 0)
        } for row in cur.fetchall()}
        
        # Deuda total municipal
        cur.execute("SELECT SUM(deuda_total) FROM tributos WHERE estado_pago = 'MOROSO'")
        deuda_total_morosos = float(cur.fetchone()[0] or 0)
        
        # Sector con mayor deuda
        cur.execute("""
            SELECT p.sector, COUNT(*) as cantidad_morosos, SUM(t.deuda_total) as deuda_sector
            FROM predios p
            JOIN tributos t ON p.id_predio = t.id_predio
            WHERE t.estado_pago = 'MOROSO'
            GROUP BY p.sector
            ORDER BY deuda_sector DESC
            LIMIT 1
        """)
        sector_critico = cur.fetchone()
        
        # Promedio de ingreso familiar
        cur.execute("SELECT AVG(ingreso_familiar) FROM tributos WHERE ingreso_familiar IS NOT NULL")
        promedio_ingreso = float(cur.fetchone()[0] or 0)
        
        # Porcentaje de cumplimiento
        morosos = distribucion_estado.get('MOROSO', {}).get('cantidad', 0)
        al_dia = distribucion_estado.get('AL_DIA', {}).get('cantidad', 0)
        exonerados = distribucion_estado.get('EXONERADO', {}).get('cantidad', 0)
        total_contribuyentes = morosos + al_dia + exonerados
        
        porcentaje_cumplimiento = (al_dia / total_contribuyentes * 100) if total_contribuyentes > 0 else 0
        
        return {
            "resumen": {
                "total_predios": total_predios,
                "total_contribuyentes": total_contribuyentes,
                "deuda_total_municipal": round(deuda_total_morosos, 2),
                "promedio_ingreso_familiar": round(promedio_ingreso, 2),
                "porcentaje_cumplimiento": round(porcentaje_cumplimiento, 2)
            },
            "distribucion_estado": distribucion_estado,
            "sector_critico": {
                "nombre": sector_critico['sector'] if sector_critico else None,
                "cantidad_morosos": sector_critico['cantidad_morosos'] if sector_critico else 0,
                "deuda_total": float(sector_critico['deuda_sector'] or 0) if sector_critico else 0
            },
            "indicadores": {
                "morosos": morosos,
                "al_dia": al_dia,
                "exonerados": exonerados
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/sectores")
def get_sectores():
    """
    Obtiene lista de sectores con estadísticas
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT 
            p.sector,
            COUNT(*) as total_predios,
            COUNT(CASE WHEN t.estado_pago = 'MOROSO' THEN 1 END) as morosos,
            COUNT(CASE WHEN t.estado_pago = 'AL_DIA' THEN 1 END) as al_dia,
            SUM(CASE WHEN t.estado_pago = 'MOROSO' THEN t.deuda_total ELSE 0 END) as deuda_total
        FROM predios p
        LEFT JOIN tributos t ON p.id_predio = t.id_predio
        GROUP BY p.sector
        ORDER BY deuda_total DESC
    """
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
        
        sectores = []
        for row in rows:
            sectores.append({
                "sector": row['sector'],
                "total_predios": row['total_predios'],
                "morosos": row['morosos'],
                "al_dia": row['al_dia'],
                "deuda_total": float(row['deuda_total'] or 0),
                "porcentaje_morosidad": round((row['morosos'] / row['total_predios'] * 100) if row['total_predios'] > 0 else 0, 2)
            })
        
        return {"sectores": sectores}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/health")
def health_check():
    """Endpoint de salud para monitoreo"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}

# =====================================================
# ENDPOINTS CRUD
# =====================================================

from pydantic import BaseModel

class PredioCreate(BaseModel):
    """Modelo para crear nuevo predio"""
    latitud: float
    longitud: float
    codigo_catastral: str
    sector: str = "Jayllihuaya"
    tipo_vivienda: str = "Rústica"
    autovaluo: float = 0
    numero_vivienda: str = ""
    contribuyente_nombre: str
    monto_impuesto: float = 0
    pago_impuesto: bool = False
    monto_arbitrios: float = 0
    pago_arbitrios: bool = False
    ingreso_familiar: float = 0
    cantidad_personas: int = 1

class PredioUpdate(BaseModel):
    """Modelo para actualizar predio"""
    codigo_catastral: Optional[str] = None
    sector: Optional[str] = None
    tipo_vivienda: Optional[str] = None
    autovaluo: Optional[float] = None
    numero_vivienda: Optional[str] = None
    contribuyente_nombre: Optional[str] = None
    monto_impuesto: Optional[float] = None
    pago_impuesto: Optional[bool] = None
    monto_arbitrios: Optional[float] = None
    pago_arbitrios: Optional[bool] = None
    ingreso_familiar: Optional[float] = None
    cantidad_personas: Optional[int] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None

@app.post("/api/predios")
def crear_predio(predio: PredioCreate):
    """
    Crea un nuevo predio con su contribuyente y tributo
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Verificar si código catastral ya existe
        cur.execute("SELECT id_predio FROM predios WHERE codigo_catastral = %s", (predio.codigo_catastral,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail=f"Código catastral {predio.codigo_catastral} ya existe")
        
        # 2. Buscar o crear contribuyente
        cur.execute("SELECT id_contribuyente FROM contribuyentes WHERE nombres = %s", (predio.contribuyente_nombre,))
        existing_contrib = cur.fetchone()
        
        if existing_contrib:
            id_contribuyente = existing_contrib['id_contribuyente']
        else:
            cur.execute("""
                INSERT INTO contribuyentes (nombres, dni, telefono)
                VALUES (%s, NULL, NULL)
                RETURNING id_contribuyente
            """, (predio.contribuyente_nombre,))
            id_contribuyente = cur.fetchone()['id_contribuyente']
        
        # 3. Insertar predio
        cur.execute("""
            INSERT INTO predios (codigo_catastral, geom, sector, tipo_vivienda, autovaluo, numero_vivienda)
            VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s)
            RETURNING id_predio
        """, (
            predio.codigo_catastral,
            predio.longitud,
            predio.latitud,
            predio.sector,
            predio.tipo_vivienda,
            predio.autovaluo,
            predio.numero_vivienda
        ))
        id_predio = cur.fetchone()['id_predio']
        
        # 4. Insertar tributo
        cur.execute("""
            INSERT INTO tributos (
                id_predio, id_contribuyente,
                monto_impuesto, pago_impuesto,
                monto_arbitrios, pago_arbitrios,
                ingreso_familiar, cantidad_personas
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_predio, id_contribuyente,
            predio.monto_impuesto, predio.pago_impuesto,
            predio.monto_arbitrios, predio.pago_arbitrios,
            predio.ingreso_familiar, predio.cantidad_personas
        ))
        
        conn.commit()
        
        # 5. Retornar predio creado
        cur.execute("SELECT * FROM predios_completo WHERE id_predio = %s", (id_predio,))
        row = cur.fetchone()
        feature = row_to_geojson_feature(dict(row))
        
        return {
            "success": True,
            "message": "Predio creado exitosamente",
            "predio": feature
        }
    
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando predio: {str(e)}")
    finally:
        cur.close()
        conn.close()

@app.put("/api/predios/{id_predio}")
def actualizar_predio(id_predio: int, predio: PredioUpdate):
    """
    Actualiza información de un predio existente
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Verificar que predio existe
        cur.execute("SELECT id_predio FROM predios WHERE id_predio = %s", (id_predio,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Predio {id_predio} no encontrado")
        
        # 2. Actualizar predio
        predio_updates = []
        predio_params = []
        
        if predio.codigo_catastral is not None:
            predio_updates.append("codigo_catastral = %s")
            predio_params.append(predio.codigo_catastral)
        if predio.sector is not None:
            predio_updates.append("sector = %s")
            predio_params.append(predio.sector)
        if predio.tipo_vivienda is not None:
            predio_updates.append("tipo_vivienda = %s")
            predio_params.append(predio.tipo_vivienda)
        if predio.autovaluo is not None:
            predio_updates.append("autovaluo = %s")
            predio_params.append(predio.autovaluo)
        if predio.numero_vivienda is not None:
            predio_updates.append("numero_vivienda = %s")
            predio_params.append(predio.numero_vivienda)
        if predio.latitud is not None and predio.longitud is not None:
            predio_updates.append("geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)")
            predio_params.extend([predio.longitud, predio.latitud])
        
        if predio_updates:
            predio_params.append(id_predio)
            update_sql = f"UPDATE predios SET {', '.join(predio_updates)} WHERE id_predio = %s"
            cur.execute(update_sql, predio_params)
        
        # 3. Actualizar tributo
        tributo_updates = []
        tributo_params = []
        
        if predio.monto_impuesto is not None:
            tributo_updates.append("monto_impuesto = %s")
            tributo_params.append(predio.monto_impuesto)
        if predio.pago_impuesto is not None:
            tributo_updates.append("pago_impuesto = %s")
            tributo_params.append(predio.pago_impuesto)
        if predio.monto_arbitrios is not None:
            tributo_updates.append("monto_arbitrios = %s")
            tributo_params.append(predio.monto_arbitrios)
        if predio.pago_arbitrios is not None:
            tributo_updates.append("pago_arbitrios = %s")
            tributo_params.append(predio.pago_arbitrios)
        if predio.ingreso_familiar is not None:
            tributo_updates.append("ingreso_familiar = %s")
            tributo_params.append(predio.ingreso_familiar)
        if predio.cantidad_personas is not None:
            tributo_updates.append("cantidad_personas = %s")
            tributo_params.append(predio.cantidad_personas)
        
        if tributo_updates:
            tributo_params.append(id_predio)
            update_sql = f"UPDATE tributos SET {', '.join(tributo_updates)} WHERE id_predio = %s"
            cur.execute(update_sql, tributo_params)
        
        # 4. Actualizar contribuyente si se proporciona nombre
        if predio.contribuyente_nombre is not None:
            cur.execute("""
                UPDATE contribuyentes c
                SET nombres = %s
                FROM tributos t
                WHERE c.id_contribuyente = t.id_contribuyente
                AND t.id_predio = %s
            """, (predio.contribuyente_nombre, id_predio))
        
        conn.commit()
        
        # 5. Retornar predio actualizado
        cur.execute("SELECT * FROM predios_completo WHERE id_predio = %s", (id_predio,))
        row = cur.fetchone()
        feature = row_to_geojson_feature(dict(row))
        
        return {
            "success": True,
            "message": "Predio actualizado exitosamente",
            "predio": feature
        }
    
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando predio: {str(e)}")
    finally:
        cur.close()
        conn.close()

@app.delete("/api/predios/{id_predio}")
def eliminar_predio(id_predio: int):
    """
    Elimina un predio y sus relaciones (tributos)
    El contribuyente NO se elimina por si tiene otros predios
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Verificar que predio existe
        cur.execute("SELECT codigo_catastral FROM predios WHERE id_predio = %s", (id_predio,))
        predio_existente = cur.fetchone()
        
        if not predio_existente:
            raise HTTPException(status_code=404, detail=f"Predio {id_predio} no encontrado")
        
        # 2. Eliminar predio (CASCADE eliminará tributos automáticamente)
        cur.execute("DELETE FROM predios WHERE id_predio = %s", (id_predio,))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Predio {predio_existente['codigo_catastral']} eliminado exitosamente",
            "id_predio": id_predio
        }
    
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando predio: {str(e)}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
