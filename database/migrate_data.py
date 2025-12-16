"""
Script de migracion de datos JSON a PostGIS
Convierte data.json existente al modelo tributario
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys

# Configuracion de encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuracion de base de datos
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'tributario_db'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123'),
    'client_encoding': 'UTF8'
}

def conectar_db():
    """Establece conexion con PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        print("[OK] Conexion exitosa a PostgreSQL")
        return conn
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Error de conexion: {e}")
        print("\n[AVISO] Verificaciones:")
        print("   1. Esta Docker ejecutandose? -> docker-compose ps")
        print("   2. PostgreSQL esta listo? -> docker-compose logs postgis")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error conectando a BD: {e}")
        sys.exit(1)

def leer_json(archivo='data.json'):
    """Lee el archivo JSON de datos"""
    # Primero intentar en /tmp/ (dentro del contenedor)
    ruta_tmp = f'/tmp/{archivo}'
    if os.path.exists(ruta_tmp):
        ruta = ruta_tmp
    else:
        # Si no, buscar relativamente (ejecucion local)
        ruta = os.path.join(os.path.dirname(__file__), '..', archivo)
    
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[OK] Leidos {len(data)} registros de {archivo}")
        return data
    except Exception as e:
        print(f"[ERROR] Error leyendo {archivo}: {e}")
        print(f"   Ruta intentada: {ruta}")
        sys.exit(1)

def limpiar_tablas(conn):
    """Limpia las tablas antes de migracion"""
    cur = conn.cursor()
    try:
        cur.execute("TRUNCATE TABLE tributos CASCADE;")
        cur.execute("TRUNCATE TABLE predios CASCADE;")
        cur.execute("TRUNCATE TABLE contribuyentes CASCADE;")
        conn.commit()
        print("[OK] Tablas limpiadas")
    except Exception as e:
        conn.rollback()
        print(f"[AVISO] Advertencia limpiando tablas: {e}")
    finally:
        cur.close()

def migrar_contribuyentes(conn, data):
    """Migra contribuyentes unicos"""
    cur = conn.cursor()
    
    # Extraer contribuyentes unicos
    contribuyentes_unicos = {}
    for hogar in data:
        nombre = hogar.get('propietario', 'Desconocido')
        if nombre not in contribuyentes_unicos:
            contribuyentes_unicos[nombre] = {
                'nombres': nombre,
                'dni': None,
                'telefono': None
            }
    
    # Insertar contribuyentes
    mapa_ids = {}
    for nombre, datos in contribuyentes_unicos.items():
        try:
            cur.execute("""
                INSERT INTO contribuyentes (nombres, dni, telefono)
                VALUES (%s, %s, %s)
                RETURNING id_contribuyente
            """, (datos['nombres'], datos['dni'], datos['telefono']))
            id_contrib = cur.fetchone()[0]
            mapa_ids[nombre] = id_contrib
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[AVISO] Error insertando {nombre}: {e}")
    
    cur.close()
    print(f"[OK] Migrados {len(mapa_ids)} contribuyentes")
    return mapa_ids

def migrar_predios_tributos(conn, data, mapa_contribuyentes):
    """Migra predios y tributos"""
    cur = conn.cursor()
    
    predios_insertados = 0
    tributos_insertados = 0
    errores = 0
    
    for idx, hogar in enumerate(data, start=1):
        try:
            # Datos del predio
            codigo_catastral = hogar.get('id_hogar', f'HOG{idx:04d}')
            latitud = hogar.get('latitud')
            longitud = hogar.get('altitud')
            sector = 'Jayllihuaya'
            tipo_vivienda = hogar.get('tipo_vivienda', 'Desconocido')
            numero_vivienda = str(hogar.get('numero_vivienda', ''))
            
            # Calcular autovaluo estimado
            ingreso_familiar = float(hogar.get('ingreso_familiar', 0))
            autovaluo = ingreso_familiar * 50
            
            if latitud is None or longitud is None:
                if idx <= 5:  # Solo mostrar primeros 5
                    print(f"[AVISO] Hogar {codigo_catastral} sin coordenadas")
                errores += 1
                continue
            
            # Insertar predio
            try:
                cur.execute("""
                    INSERT INTO predios (codigo_catastral, geom, sector, tipo_vivienda, autovaluo, numero_vivienda)
                    VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s)
                    RETURNING id_predio
                """, (codigo_catastral, float(longitud), float(latitud), sector, autovaluo, numero_vivienda))
                
                conn.commit()  # Commit inmediato para obtener el ID
                result = cur.fetchone()
                
                if result is None or len(result) == 0:
                    if idx <= 5:
                        print(f"[ERROR] No se pudo obtener id_predio para {codigo_catastral}")
                    errores += 1
                    continue
                    
                id_predio = result[0]
                predios_insertados += 1
                
            except Exception as e_predio:
                if idx <= 5:
                    print(f"[ERROR] Fallo insercion predio {codigo_catastral}: {e_predio}")
                errores += 1
                conn.rollback()
                continue
            
            # Datos tributarios
            propietario = hogar.get('propietario', 'Desconocido')
            id_contribuyente = mapa_contribuyentes.get(propietario)
            
            if id_contribuyente is None:
                if idx <= 5:
                    print(f"[AVISO] Contribuyente no encontrado para {codigo_catastral}")
                errores += 1
                continue
            
            monto_impuesto = float(hogar.get('monto_impuesto', 0))
            pago_impuesto = bool(hogar.get('pago_impuesto', False))
            monto_arbitrios = float(hogar.get('monto_arbitrios', 0))
            pago_arbitrios = bool(hogar.get('pago_arbitrios', False))
            
            cantidad_personas = hogar.get('cantidad_personas')
            nivel_educativo = hogar.get('nivel_educativo_jefe')
            servicios_basicos = hogar.get('servicios_basicos')
            
            # Insertar tributo
            try:
                cur.execute("""
                    INSERT INTO tributos (
                        id_predio, id_contribuyente, 
                        monto_impuesto, pago_impuesto,
                        monto_arbitrios, pago_arbitrios,
                        ingreso_familiar, cantidad_personas,
                        nivel_educativo_jefe, servicios_basicos
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_predio, id_contribuyente,
                    monto_impuesto, pago_impuesto,
                    monto_arbitrios, pago_arbitrios,
                    ingreso_familiar, cantidad_personas,
                    nivel_educativo, servicios_basicos
                ))
                
                tributos_insertados += 1
                
            except Exception as e_tributo:
                if idx <= 5:
                    print(f"[ERROR] Fallo insercion tributo para {codigo_catastral}: {e_tributo}")
                errores += 1
                conn.rollback()
                continue
            
            # Commit cada 25 registros
            if idx % 25 == 0:
                conn.commit()
                print(f"  Procesados {idx}/{len(data)} registros ({predios_insertados} predios, {errores} errores)")
        
        except Exception as e:
            if idx <= 10:
                print(f"[ERROR] Error general procesando {hogar.get('id_hogar', idx)}: {type(e).__name__}: {e}")
            errores += 1
            conn.rollback()
            continue
    
    # Commit final
    try:
        conn.commit()
    except:
        conn.rollback()
    
    cur.close()
    
    print(f"\n[OK] Migrados {predios_insertados} predios y {tributos_insertados} tributos")
    if errores > 0:
        print(f"[AVISO] {errores} registros con errores fueron omitidos")
    return predios_insertados, tributos_insertados

def verificar_migracion(conn):
    """Verifica estadisticas de la migracion"""
    cur = conn.cursor()
    
    print("\n" + "="*50)
    print("ESTADISTICAS DE MIGRACION")
    print("="*50)
    
    cur.execute("SELECT COUNT(*) FROM contribuyentes")
    print(f"Contribuyentes: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM predios")
    print(f"Predios: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(*) FROM tributos")
    print(f"Tributos: {cur.fetchone()[0]}")
    
    cur.execute("""
        SELECT estado_pago, COUNT(*) 
        FROM tributos 
        GROUP BY estado_pago
        ORDER BY estado_pago
    """)
    print("\nDistribucion por estado de pago:")
    for estado, cantidad in cur.fetchall():
        print(f"  {estado}: {cantidad}")
    
    cur.execute("SELECT SUM(deuda_total) FROM tributos WHERE estado_pago = 'MOROSO'")
    deuda_morosos = cur.fetchone()[0] or 0
    print(f"\nDeuda total de morosos: S/ {deuda_morosos:,.2f}")
    
    cur.close()
    print("="*50 + "\n")

def main():
    """Funcion principal de migracion"""
    print("\n" + "="*50)
    print("MIGRACION DE DATOS A POSTGIS")
    print("="*50 + "\n")
    
    # 1. Leer JSON
    data = leer_json()
    
    # 2. Conectar a BD
    conn = conectar_db()
    
    # 3. Limpiar tablas
    limpiar_tablas(conn)
    
    # 4. Migrar contribuyentes
    mapa_contribuyentes = migrar_contribuyentes(conn, data)
    
    # 5. Migrar predios y tributos
    migrar_predios_tributos(conn, data, mapa_contribuyentes)
    
    # 6. Verificar migracion
    verificar_migracion(conn)
    
    # 7. Cerrar conexion
    conn.close()
    print("[OK] Migracion completada exitosamente\n")

if __name__ == '__main__':
    main()
