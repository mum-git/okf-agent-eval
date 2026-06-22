-- PostgreSQL retrieval layer over OKF bundles.
-- One row per Markdown file ("chunk"), keyed to its bundle-relative path so the
-- agent can cite the real source file after a search.

CREATE TABLE IF NOT EXISTS bundle_chunks (
  id               SERIAL PRIMARY KEY,
  bundle_variant   TEXT NOT NULL,
  file_path        TEXT NOT NULL,        -- bundle-relative, begins with /
  is_index         BOOLEAN,
  is_concept       BOOLEAN,
  file_type        TEXT,                 -- frontmatter 'type'
  file_depth       INT,                  -- count of '/' in path
  frontmatter_keys TEXT[],               -- keys present in YAML frontmatter
  frontmatter_text TEXT,                 -- raw YAML block (answer-bearing chunk)
  body_text        TEXT,                 -- markdown body
  search_tsv       tsvector,             -- weighted: frontmatter(A) path(B) body(C)
  UNIQUE (bundle_variant, file_path)
);

CREATE INDEX IF NOT EXISTS idx_chunks_variant ON bundle_chunks(bundle_variant);
CREATE INDEX IF NOT EXISTS idx_chunks_type    ON bundle_chunks(file_type);
CREATE INDEX IF NOT EXISTS idx_chunks_keys    ON bundle_chunks USING GIN(frontmatter_keys);
CREATE INDEX IF NOT EXISTS idx_chunks_tsv     ON bundle_chunks USING GIN(search_tsv);
