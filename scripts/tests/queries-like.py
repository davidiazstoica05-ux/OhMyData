"""
Ejecuta las mismas 5 consultas lógicas utilizando LIKE (Escaneo Secuencial).
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "MyData.db"

def benchmark_query(cur, sql, params=(), repeats=200):
    cur.execute(sql, params).fetchall() # Warm-up

    start = time.perf_counter()
    for _ in range(repeats):
        cur.execute(sql, params).fetchall()
    end = time.perf_counter()

    return (end - start) / repeats * 1000

def test_consulta(cur, label, sql, params=()):
    print(f"\n{label}")
    print(f"SQL: {sql}")
    
    resultados = cur.execute(sql, params).fetchall()
    tiempo_ms = benchmark_query(cur, sql, params)
    
    print(f"-> Resultados devueltos: {len(resultados)}")
    print(f"-> Tiempo de ejecución:  {tiempo_ms:.4f} ms")
    print("-" * 50)

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    print("Iniciando batería de pruebas LIKE (Promedio de 200 iteraciones)...")
    
    # 1. Búsqueda con muchos resultados
    test_consulta(cur, 
        "1. Búsqueda con muchos resultados", 
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%privacidad%'")
    
    # 2. Búsqueda con pocos resultados
    test_consulta(cur, 
        "2. Búsqueda con pocos resultados", 
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%xilofonomarcador%'")
    
    # 3. Equivalente a BM25 (Solo búsqueda, LIKE no puede ordenar por relevancia)
    test_consulta(cur, 
        "3. Equivalente a ranking (Búsqueda masiva sin ordenación matemática)", 
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%datos%'")
    
    # 4. Búsqueda de frase exacta (Corregido a plural según tu dataset)
    test_consulta(cur, 
        "4. Búsqueda de frase exacta (Phrase Query)", 
        "SELECT rowid, title FROM pages WHERE extracted_content LIKE '%motores de búsqueda%'")
    
    # 5. Búsqueda con operadores booleanos (Demuestra la ineficiencia de LIKE)
    test_consulta(cur, 
        "5. Búsqueda con operadores booleanos (AND, OR)", 
        """SELECT rowid, title FROM pages 
           WHERE extracted_content LIKE '%privacidad%' 
           AND (extracted_content LIKE '%datos%' OR extracted_content LIKE '%publicidad%')""")
        
    con.close()

if __name__ == "__main__":
    main()