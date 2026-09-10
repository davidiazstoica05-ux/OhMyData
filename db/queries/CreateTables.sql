-- Table of searches performed by the user
CREATE TABLE searches (
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table of saved pages (memory + anti-404 cache)
CREATE TABLE pages (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    extracted_content TEXT,
    content_hash TEXT,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_changed_at DATETIME
);

-- N:M junction table between searches and pages
CREATE TABLE search_page (
    search_id INTEGER NOT NULL,
    page_id INTEGER NOT NULL,
    result_position INTEGER,
    PRIMARY KEY (search_id, page_id),
    FOREIGN KEY (search_id) REFERENCES searches(id),
    FOREIGN KEY (page_id) REFERENCES pages(id)
);

-- FTS5 virtual table for full-text search over page content
-- Populated manually by the ingestion script (stemmed content only)
CREATE VIRTUAL TABLE pages_fts USING fts5(
    title,
    extracted_content,
    content='pages',
    content_rowid='id'
);