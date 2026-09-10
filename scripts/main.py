import re
import snowballstemmer

# Instantiate the Spanish stemmer (keeps the rules loaded in memory)
_stemmer = snowballstemmer.stemmer("spanish")

# Regex that captures whole words, including Spanish characters (á, é, í, ó, ú, ñ, ü)
WORD_PATTERN = re.compile(r"[a-záéíóúüñ0-9]+")


def tokenize(text: str) -> list[str]:
    """Cleans the text, lowercases it, and extracts only valid tokens."""
    if not text:
        return []
    return WORD_PATTERN.findall(text.lower())


def stem_text(text: str) -> str:
    """Reduces a full text to its lexical roots.
    This is the version stored in the 'pages_fts' virtual table.
    """
    tokens = tokenize(text)
    if not tokens:
        return ""

    # stemWords applies morphological reduction in batch to the token list
    stemmed_words = _stemmer.stemWords(tokens)

    # Join the roots with a single space, for FTS5
    return " ".join(stemmed_words)


def prepare_fts_query(query: str) -> str:
    """Prepares the query entered by the user.
    Both the stored document and the search query must go through the
    exact same algorithm so that the roots match.
    """
    tokens = tokenize(query)
    if not tokens:
        return ""

    stemmed_tokens = _stemmer.stemWords(tokens)
    return " ".join(stemmed_tokens)


# --- Practical demonstration ---
if __name__ == "__main__":
    # 1. Example with noun variations
    sample_text = "La privacidad de los usuarios y las privacidades digitales."
    print("Original text: ", sample_text)
    print("Stemmed text:  ", stem_text(sample_text))
    # Output: 'la privacid de los usuari y las privacid digital'

    # 2. Example with verb variations
    verb_1 = stem_text("correr")
    verb_2 = stem_text("corriendo")
    verb_3 = stem_text("corrieron")
    print(f"\nVerbs ('correr', 'corriendo', 'corrieron') -> ['{verb_1}', '{verb_2}', '{verb_3}']")
    # All return 'corr'

    # 3. How the user would search
    user_query = "¿Cómo proteger mis privacidades?"
    processed_query = prepare_fts_query(user_query)
    print("\nOriginal query:", user_query)
    print("Query for FTS5:", processed_query)
    # MATCH 'com proteg mis privacid' -> Finds 'privacidad'