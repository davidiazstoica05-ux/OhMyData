"""
Ejecuta las 5 consultas clave de FTS5 para el cuaderno de bitácora,
midiendo el tiempo de respuesta promedio y mostrando el recuento real.
"""

import sqlite3
import time
from pathlib import Path

# Misma ruta que en generate_test_data.py
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "MyData.db"

def benchmark_query(cur, sql, params=(), repeats=200):
    # Warm-up para cargar en caché de SQLite
    cur.execute(sql, params).fetchall()

    start = time.perf_counter()
    for _ in range(repeats):
        cur.execute(sql, params).fetchall()
    end = time.perf_counter()

    return (end - start) / repeats * 1000  # milisegundos

def test_consulta(cur, label, sql):
    print(f"\n{label}")
    print(f"SQL: {sql}")
    
    # Obtener resultados reales
    resultados = cur.execute(sql).fetchall()
    
    # Medir tiempo
    tiempo_ms = benchmark_query(cur, sql)
    
    print(f"-> Resultados devueltos: {len(resultados)}")
    print(f"-> Tiempo de ejecución:  {tiempo_ms:.4f} ms")
    
    # Mostrar una muestra si hay resultados para comprobar el BM25
    if resultados:
        print(f"-> Muestra (Top 2): {resultados[:2]}")
    print("-" * 50)

def main():
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        
        print("Iniciando batería de pruebas FTS5 (Promedio de 200 iteraciones)...")
        
        # 1. Búsqueda con muchos resultados
        test_consulta(cur, 
            "1. Búsqueda con muchos resultados", 
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH 'privacidad'")
        
        # 2. Búsqueda con pocos resultados (Usamos 'xilofonomarcador' que es tu término único)
        test_consulta(cur, 
            "2. Búsqueda con pocos resultados", 
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH 'xilofonomarcador'")
        
        # 3. Ranking BM25 en acción
        test_consulta(cur, 
            "3. Ranking BM25 (Ordenado por relevancia)", 
            "SELECT rowid, title, rank FROM pages_fts WHERE pages_fts MATCH 'datos' ORDER BY rank")
        
        # 4. Búsqueda de frase exacta
        test_consulta(cur, 
            "4. Búsqueda de frase exacta (Phrase Query)", 
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH '\"motor de búsqueda\"'")
        
        # 5. Búsqueda con operadores booleanos
        test_consulta(cur, 
            "5. Búsqueda con operadores booleanos (AND, OR)", 
            "SELECT rowid, title FROM pages_fts WHERE pages_fts MATCH 'privacidad AND (datos OR publicidad)'")
            
    except sqlite3.OperationalError as e:
        print(f"Error: No se pudo conectar a la base de datos o falta la tabla. Detalles: {e}")
    finally:
        if 'con' in locals():
            con.close()

if __name__ == "__main__":
    main()