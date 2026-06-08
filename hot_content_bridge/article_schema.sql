-- Article body storage (same SQLite file as trendRadar news DB)

CREATE TABLE IF NOT EXISTS article_contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_item_id INTEGER,
    url_norm TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    title_snapshot TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'success', 'failed')),
    http_status INTEGER,
    markdown TEXT DEFAULT '',
    extracted_title TEXT DEFAULT '',
    error TEXT DEFAULT '',
    content_sha256 TEXT DEFAULT '',
    fetched_at TEXT,
    crawl_config_hash TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_article_url_norm ON article_contents(url_norm);
CREATE INDEX IF NOT EXISTS idx_article_platform ON article_contents(platform_id);
CREATE INDEX IF NOT EXISTS idx_article_fetched ON article_contents(fetched_at);
CREATE INDEX IF NOT EXISTS idx_article_status ON article_contents(status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_article_url_norm_unique ON article_contents(url_norm);
