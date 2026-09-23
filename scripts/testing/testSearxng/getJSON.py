import requests


query = input();

response = requests.get(
    
    "http://localhost:8080/search",
    params={"q": query, "format": "json"}
) 
response.raise_for_status()


#Lo convierte en un diccionario
data = response.json()

#A los diccionarios se puede acceder directamente
results = data["results"]

for resultado in results: 

    print(resultado["title"],resultado["content"],"----",resultado["url"],"engine:",resultado["engine"])


""" 
"query": "privacidad",
    "results": [
        {
            "template": "default.html",
            "title": "Check out the translation for \"privacidad\" on SpanishDictionary.com!",
            "content": "Viviana compart\u00eda habitaci\u00f3n con sus dos hermanitas, as\u00ed que se encerraba en el ba\u00f1o en busca de un poco de privacidad cuando necesitaba hablar por tel\u00e9fono.Viviana used to share a room with her two younger sisters, so she would locked herself in the bathroom looking for some privacy whenever she needed to talk on the phone.Copyright \u00a9 2026 Dictionary Media Group, Inc.",
            "img_src": "",
            "iframe_src": "",
            "audio_src": "",
            "thumbnail": "",
            "publishedDate": null,
            "pubdate": null,
            "length": null,
            "views": "",
            "author": "",
            "metadata": "",
            "priority": "",
            "engines": [
                "brave"
            ],
            "open_group": false,
            "close_group": false,
            "positions": [
                1
"""
   