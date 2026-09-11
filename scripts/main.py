import sqlite3
from search.local_search import search
from db.connection import get_connection
from datetime import datetime
from repository.searches import insert_searches


def main():
    try:
        con = get_connection()
        cur = con.cursor()

        print("La Cajita — interactive local search (type 'q' to quit)")
        print("-" * 50)

        while True:
           
            user_query = input("\nSearch query: ").strip()
            query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            #falta colocar que cuando se pulse q, exit, quit o salir se salga del bucle 
            # y no se haga la busqueda ni se inserte en la base de datos
            insert_searches(user_query, cur, con, query_time)
            
            

            if user_query.lower() in ("q", "exit", "quit", "salir"):
                break

            if not user_query:
                continue

            search(cur, user_query)

    except sqlite3.OperationalError as e:
        print(f"Error: Could not connect to the database or the table is missing. Details: {e}")
    finally:
        if 'con' in locals():
            con.close()


if __name__ == "__main__":
    main()