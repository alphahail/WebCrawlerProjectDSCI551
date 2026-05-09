import json
import datetime
import psycopg2
import psycopg2.extras
import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    id             SERIAL PRIMARY KEY,
    url            TEXT UNIQUE,
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
    story_id   INTEGER REFERENCES stories(id),
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
"""


def parse_count(value):
    if not value:
        return None
    try:
        s = str(value).strip().lower().replace(",", "")
        if s.endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith("k"):
            return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except (ValueError, AttributeError):
        return None


class Storage:
    def __init__(self, **db_config):
        self.conn = psycopg2.connect(**(db_config or config.DB_CONFIG))
        self.conn.autocommit = False
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA)
        self.conn.commit()
        print("[db] Tables and indexes verified")

    def word_count_changed(self, url, new_word_count):
        new_num = parse_count(new_word_count)

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT word_count_num FROM stories WHERE url = %s", (url,)
            )
            row = cur.fetchone()

        if row is None:
            print(f"[db] New story found, will crawl: {url[:70]}")
            return True

        stored = row[0]

        if stored is None and new_num is None:
            return False

        changed = stored != new_num
        if changed:
            print(f"[db] Word count changed ({stored} to {new_num}): {url[:70]}")
        return changed

    def save_story(self, url, title, author, tags, word_count=None,
                   watchers=None, replies=None, views=None):
        now        = datetime.datetime.utcnow()
        words      = parse_count(word_count)
        replies_n  = parse_count(replies)
        views_n    = parse_count(views)

        clean_tags = [
            t.replace("\n", " ").replace("\r", "").strip()
            for t in (tags or [])
        ]

        print(f"[db] INSERT INTO stories ON CONFLICT (url) DO UPDATE")
        print(f"[db] B-tree index on stories.url used for conflict detection")

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO stories (
                    url, title, author, tags,
                    word_count_num, watchers,
                    replies_num, views_num,
                    fetched_at, last_checked
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    title          = EXCLUDED.title,
                    author         = EXCLUDED.author,
                    tags           = EXCLUDED.tags,
                    word_count_num = EXCLUDED.word_count_num,
                    watchers       = EXCLUDED.watchers,
                    replies_num    = EXCLUDED.replies_num,
                    views_num      = EXCLUDED.views_num,
                    last_checked   = EXCLUDED.last_checked
            """, (
                url, title, author, json.dumps(clean_tags),
                words, watchers, replies_n, views_n,
                now, now
            ))
            self.conn.commit()

            cur.execute("SELECT id FROM stories WHERE url = %s", (url,))
            row = cur.fetchone()
            story_id = row[0] if row else None

        print(f"[db] Story saved with id={story_id} (title: {title[:50]})")
        return story_id

    def save_posts(self, story_id, posts):
        if not posts:
            return

        print(f"[db] INSERT INTO posts ({len(posts)} rows) ON CONFLICT (post_id) DO NOTHING")
        print(f"[db] B-tree index on posts.post_id used for duplicate detection")

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, """
                INSERT INTO posts
                    (story_id, post_id, author, timestamp, post_url, post_type, title, likes)
                VALUES %s
                ON CONFLICT (post_id) DO NOTHING
            """, [
                (
                    story_id,
                    p["post_id"],
                    p.get("author", ""),
                    p.get("timestamp") or None,
                    p.get("post_url", ""),
                    p.get("post_type", "threadmark"),
                    p.get("title", ""),
                    int(p.get("likes", 0) or 0),
                )
                for p in posts
            ])
        self.conn.commit()
        print(f"[db] Posts insert complete for story id={story_id}")

    def get_post_ids(self, story_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT post_id FROM posts WHERE story_id = %s", (story_id,))
            return {row[0] for row in cur.fetchall()}

    def close(self):
        self.conn.close()