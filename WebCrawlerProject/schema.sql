CREATE TABLE IF NOT EXISTS stories (
    id             SERIAL PRIMARY KEY,
    url            TEXT UNIQUE NOT NULL,
    title          TEXT,
    author         TEXT,
    tags           JSONB,
    word_count_num INTEGER,
    watchers       INTEGER,
    replies_num    INTEGER,
    views_num      INTEGER,
    fetched_at     TIMESTAMPTZ,
    last_checked   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS posts (
    id         SERIAL PRIMARY KEY,
    story_id   INTEGER REFERENCES stories(id) ON DELETE CASCADE,
    post_id    TEXT UNIQUE,
    author     TEXT,
    timestamp  TIMESTAMPTZ,
    post_url   TEXT,
    post_type  TEXT,
    title      TEXT,
    likes      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_stories_author
    ON stories (author);

CREATE INDEX IF NOT EXISTS idx_stories_last_checked
    ON stories (last_checked DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_stories_watchers
    ON stories (watchers DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_stories_word_count_num
    ON stories (word_count_num DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_stories_replies_num
    ON stories (replies_num DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_stories_views_num
    ON stories (views_num DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_stories_tags
    ON stories USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_posts_story_id
    ON posts (story_id);

CREATE INDEX IF NOT EXISTS idx_posts_story_type
    ON posts (story_id, post_type);

CREATE INDEX IF NOT EXISTS idx_posts_timestamp
    ON posts (timestamp DESC NULLS LAST);