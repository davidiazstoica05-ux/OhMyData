import re
import snowballstemmer

# Instanciamos el stemmer en español (mantiene las reglas en memoria)
_stemmer = snowballstemmer.stemmer("spanish")

# Expresión regular que captura palabras completas incluyendo caracteres en español (á, é, í, ó, ú, ñ, ü)
WORD_PATTERN = re.compile(r"[a-záéíóúüñ0-9]+")


def tokenize(text: str) -> list[str]:
    """Limpia el texto, lo pasa a minúsculas y extrae únicamente los tokens válidos."""
    if not text:
        return []
    return WORD_PATTERN.findall(text.lower())


def stem_text(text: str) -> str:
    """Reduce un texto completo a sus raíces léxicas.
    Este resultado es el que se almacena en la tabla virtual 'pages_fts'.
    """
    tokens = tokenize(text)
    if not tokens:
        return ""

    # stemWords aplica la reducción morfológica por lotes a la lista
    stemmed_words = _stemmer.stemWords(tokens)

    # Devolvemos las raíces unidas por un espacio simple para FTS5
    return " ".join(stemmed_words)


def prepare_fts_query(query: str) -> str:
    """Prepara la consulta introducida por el usuario.
    Tanto el documento guardado como la búsqueda deben pasar por el
    mismo algoritmo exacto para que las raíces coincidan.
    """
    tokens = tokenize(query)
    if not tokens:
        return ""

    stemmed_tokens = _stemmer.stemWords(tokens)
    return " ".join(stemmed_tokens)


# --- Demostración práctica de funcionamiento ---
if __name__ == "__main__":
    # 1. Ejemplo con variaciones de sustantivos
    texto_ejemplo = "La privacidad de los usuarios y las privacidades digitales."
    print("Texto original:  ", texto_ejemplo)
    print("Texto stemizado: ", stem_text(texto_ejemplo))
    # Salida: 'la privacid de los usuari y las privacid digital'

    # 2. Ejemplo con variaciones verbales
    verbo_1 = stem_text("correr")
    verbo_2 = stem_text("corriendo")
    verbo_3 = stem_text("corrieron")
    print(f"\nVerbos ('correr', 'corriendo', 'corrieron') -> ['{verbo_1}', '{verbo_2}', '{verbo_3}']")
    # Todas devuelven 'corr'

    # 3. Cómo buscaría el usuario
    busqueda_usuario = "¿Cómo proteger mis privacidades?"
    query_procesada = prepare_fts_query(busqueda_usuario)
    print("\nBúsqueda original:", busqueda_usuario)
    print("Query para FTS5:  ", query_procesada)
    # MATCH 'com proteg mis privacid' -> Encuentra 'privacidad'