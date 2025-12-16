"""
Script para generar INSERT statements SQL desde data.json
Crea archivo con datos precargados para init.sql
"""

import json
import os

def generar_inserts_sql():
    """Lee data.json y genera INSERT statements"""
    
    # Leer data.json
    ruta_json = os.path.join(os.path.dirname(__file__), '..', 'data.json')
    with open(ruta_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"[OK] Leidos {len(data)} registros de data.json")
    
    # Generar SQL
    sql_lines = []
    sql_lines.append("-- =====================================================")
    sql_lines.append("-- DATOS PRECARGADOS DESDE data.json")
    sql_lines.append(f"-- Total de registros: {len(data)}")
    sql_lines.append("-- =====================================================\n")
    
    # Extraer contribuyentes unicos
    contribuyentes_unicos = {}
    for hogar in data:
        nombre = hogar.get('propietario', 'Desconocido')
        if nombre not in contribuyentes_unicos:
            contribuyentes_unicos[nombre] = len(contribuyentes_unicos) + 1
    
    # INSERT contribuyentes
    sql_lines.append("-- Insertar contribuyentes")
    for nombre, id_contrib in contribuyentes_unicos.items():
        nombre_escaped = nombre.replace("'", "''")
        sql_lines.append(f"INSERT INTO contribuyentes (id_contribuyente, nombres, dni, telefono) VALUES ({id_contrib}, '{nombre_escaped}', NULL, NULL);")
    
    sql_lines.append(f"\n-- Total contribuyentes insertados: {len(contribuyentes_unicos)}\n")
    
    # INSERT predios y tributos
    sql_lines.append("-- Insertar predios y tributos")
    
    predios_insertados = 0
    tributos_insertados = 0
    
    for idx, hogar in enumerate(data, start=1):
        try:
            # Datos del predio
            codigo_catastral = hogar.get('id_hogar', f'HOG{idx:04d}')
            latitud = hogar.get('latitud')
            longitud = hogar.get('altitud')
            
            if latitud is None or longitud is None:
                continue
            
            sector = 'Jayllihuaya'
            tipo_vivienda = (hogar.get('tipo_vivienda', 'Desconocido') or 'Desconocido').replace("'", "''")
            numero_vivienda = str(hogar.get('numero_vivienda', '') or '')
            
            ingreso_familiar = float(hogar.get('ingreso_familiar', 0))
            autovaluo = ingreso_familiar * 50
            
            # INSERT predio
            sql_lines.append(f"INSERT INTO predios (id_predio, codigo_catastral, geom, sector, tipo_vivienda, autovaluo, numero_vivienda)")
            sql_lines.append(f"  VALUES ({idx}, '{codigo_catastral}', ST_SetSRID(ST_MakePoint({longitud}, {latitud}), 4326), '{sector}', '{tipo_vivienda}', {autovaluo}, '{numero_vivienda}');")
            
            predios_insertados += 1
            
            # Datos tributarios
            propietario = hogar.get('propietario', 'Desconocido')
            id_contribuyente = contribuyentes_unicos.get(propietario)
            
            if id_contribuyente is None:
                continue
            
            monto_impuesto = float(hogar.get('monto_impuesto', 0))
            pago_impuesto = 'TRUE' if hogar.get('pago_impuesto', False) else 'FALSE'
            monto_arbitrios = float(hogar.get('monto_arbitrios', 0))
            pago_arbitrios = 'TRUE' if hogar.get('pago_arbitrios', False) else 'FALSE'
            
            cantidad_personas = hogar.get('cantidad_personas')
            if cantidad_personas is None:
                cantidad_personas = 'NULL'
            
            nivel_educativo = hogar.get('nivel_educativo_jefe')
            if nivel_educativo:
                nivel_educativo = f"'{nivel_educativo.replace(chr(39), chr(39)+chr(39))}'"
            else:
                nivel_educativo = 'NULL'
            
            servicios_basicos = hogar.get('servicios_basicos')
            if servicios_basicos:
                servicios_basicos = f"'{servicios_basicos.replace(chr(39), chr(39)+chr(39))}'"
            else:
                servicios_basicos = 'NULL'
            
            # INSERT tributo
            sql_lines.append(f"INSERT INTO tributos (id_predio, id_contribuyente, monto_impuesto, pago_impuesto, monto_arbitrios, pago_arbitrios, ingreso_familiar, cantidad_personas, nivel_educativo_jefe, servicios_basicos)")
            sql_lines.append(f"  VALUES ({idx}, {id_contribuyente}, {monto_impuesto}, {pago_impuesto}, {monto_arbitrios}, {pago_arbitrios}, {ingreso_familiar}, {cantidad_personas}, {nivel_educativo}, {servicios_basicos});")
            
            tributos_insertados += 1
            
        except Exception as e:
            print(f"[ERROR] Error procesando {hogar.get('id_hogar', idx)}: {e}")
            continue
    
    sql_lines.append(f"\n-- Total predios insertados: {predios_insertados}")
    sql_lines.append(f"-- Total tributos insertados: {tributos_insertados}\n")
    
    # Actualizar secuencias
    sql_lines.append("-- Actualizar secuencias")
    sql_lines.append(f"SELECT setval('contribuyentes_id_contribuyente_seq', {len(contribuyentes_unicos)}, true);")
    sql_lines.append(f"SELECT setval('predios_id_predio_seq', {predios_insertados}, true);")
    sql_lines.append(f"SELECT setval('tributos_id_tributo_seq', {tributos_insertados}, true);")
    
    # Escribir archivo
    ruta_output = os.path.join(os.path.dirname(__file__), 'data_inserts.sql')
    with open(ruta_output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_lines))
    
    print(f"[OK] Generado {ruta_output}")
    print(f"     {len(contribuyentes_unicos)} contribuyentes")
    print(f"     {predios_insertados} predios")
    print(f"     {tributos_insertados} tributos")
    print("\nAhora agrega este contenido al final de init.sql")

if __name__ == '__main__':
    generar_inserts_sql()
