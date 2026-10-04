import requests
import trafilatura
import hashlib
import repository.pages 

pages = repository.pages



def search_searxng(cur, user_query):


    response = requests.get(
        
        "http://localhost:8080/search",
        params={"q": user_query, "format": "json"}
    ) 
    response.raise_for_status()
    
    #Lo convierte en un diccionario
    data = response.json()

    #A los diccionarios se puede acceder directamente
    results = data["results"]

    for resultado in results :
        
        url = resultado["url"]

        page_id = pages.findPageByUrl(cur, url)

        if page_id is None:

            html = trafilatura.fetch_url(url)

            if html is None:
                print(f"No se pudo descargar: {url}")
                continue

            texto = trafilatura.extract(html)

            if texto is None:
                print(f"No se pudo extraer contenido de: {url}")
                continue

            page_id = pages.insert_page(cur, url, resultado["title"], texto, content_hash)

        print(resultado["title"], "----", url, "engine:", resultado["engine"])

#Acordarse de hacer este script mas modular, tiene demasiadas responsabilidades

