
from steming import stem_text

from db.connection import get_connection

from datetime import datetime



def insert_searches(query, cur, con, query_time = None):
    """Inserts a search query into the 'searches' table, storing both the
    original query and its stemmed version for later analysis.
    """
    
    if query_time is None:
        query_time = datetime.now().isoformat(sep=" ", timespec="seconds")   
    
    if cur is None or con is None:
        raise ValueError("Both 'cur' and 'con' must be provided.")

    stemmed_query = stem_text(query)

    cur.execute(
        """INSERT INTO searches (query, timestamp)
           VALUES (?, ?)""",
        (query, query_time),
    )
    con.commit()
    
    print(f"Inserted search query: '{query}' (stemmed: '{stemmed_query}') at {query_time}")
    
    search_id = cur.lastrowid
    return search_id
    