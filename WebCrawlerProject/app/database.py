import psycopg2
import psycopg2.extras
import config


def get_conn():
    print(config.DB_CONFIG)
    conn = psycopg2.connect(**config.DB_CONFIG)
    conn.autocommit = True
    return conn


def fetch_all(conn, query, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params or ())
        return [dict(row) for row in cur.fetchall()]


def fetch_one(conn, query, params=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params or ())
        row = cur.fetchone()
        return dict(row) if row else None


def get_stats(conn):
    return fetch_one(conn, """
        SELECT
            (SELECT COUNT(*) FROM stories)          AS total_stories,
            (SELECT COUNT(*) FROM posts)            AS total_posts,
            (SELECT COUNT(DISTINCT author)
             FROM stories)                          AS total_authors,
            (SELECT MAX(last_checked) FROM stories) AS last_crawled
    """)


def get_stories(conn, search=None, author=None, tag=None,
                sort="last_checked", page=1, per_page=20,
                min_watchers=0, min_word_count=0):
    offset        = (page - 1) * per_page
    where_clauses = []
    params        = []

    if search:
        where_clauses.append("s.title ILIKE %s")
        params.append(f"%{search}%")

    if author:
        where_clauses.append("s.author ILIKE %s")
        params.append(f"%{author}%")

    if tag:
        tags = [tag] if isinstance(tag, str) else list(tag)
        for t in tags:
            where_clauses.append("s.tags @> %s::jsonb")
            params.append(f'["{t}"]')

    if min_watchers and min_watchers > 0:
        where_clauses.append("s.watchers >= %s")
        params.append(min_watchers)

    if min_word_count and min_word_count > 0:
        where_clauses.append("s.word_count_num >= %s")
        params.append(min_word_count)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sort_map = {
        "last_checked":           "s.last_checked DESC NULLS LAST",
        "title":                  "s.title ASC",
        "author":                 "s.author ASC",
        "word_count":             "s.word_count_num DESC NULLS LAST",
        "watchers":               "s.watchers DESC NULLS LAST",
        "replies":                "s.replies_num DESC NULLS LAST",
        "views":                  "s.views_num DESC NULLS LAST",
        "latest_threadmark_date": "p.timestamp DESC NULLS LAST",
    }
    order_sql = sort_map.get(sort, "s.last_checked DESC NULLS LAST")

    index_notes = [f"B-tree on last_checked (sort: {sort})"]
    if tag:
        tag_list = [tag] if isinstance(tag, str) else list(tag)
        index_notes.append(f"GIN on stories.tags ({len(tag_list)} containment check(s): {tag_list})")
    if author:
        index_notes.append("B-tree on stories.author (ILIKE filter)")
    if min_watchers and min_watchers > 0:
        index_notes.append(f"B-tree on stories.watchers (min={min_watchers})")
    if min_word_count and min_word_count > 0:
        index_notes.append(f"B-tree on stories.word_count_num (min={min_word_count})")

    print(f"\n[db] get_stories  page={page}  sort={sort}")
    for note in index_notes:
        print(f"[db]   {note}")
    print(f"[db]   LATERAL JOIN uses idx_posts_story_type per story row")

    count_row = fetch_one(conn,
        f"SELECT COUNT(*) AS total FROM stories s {where_sql}", params
    )
    total = count_row["total"] if count_row else 0
    print(f"[db]   {total} stories match the current filters")

    stories = fetch_all(conn, f"""
        SELECT
            s.id,
            s.url,
            s.title,
            s.author,
            s.tags,
            s.word_count_num,
            s.watchers,
            s.replies_num,
            s.views_num,
            s.last_checked,
            p.title     AS latest_threadmark_title,
            p.post_url  AS latest_threadmark_url,
            p.timestamp AS latest_threadmark_date
        FROM stories s
        LEFT JOIN LATERAL (
            SELECT title, post_url, timestamp
            FROM posts
            WHERE story_id = s.id
              AND post_type = 'threadmark'
            ORDER BY timestamp DESC NULLS LAST
            LIMIT 1
        ) p ON true
        {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])

    print(f"[db]   Returning {len(stories)} stories for this page")

    return {
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, (total + per_page - 1) // per_page),
        "stories":  stories,
    }


def get_story(conn, story_id):
    print(f"\n[db] get_story  id={story_id}")
    print(f"[db]   B-tree index scan on stories.id (primary key)")
    return fetch_one(conn, """
        SELECT
            id, url, title, author, tags,
            word_count_num, watchers,
            replies_num, views_num,
            fetched_at, last_checked
        FROM stories
        WHERE id = %s
    """, (story_id,))


def get_threadmarks(conn, story_id, post_type="threadmark"):
    print(f"\n[db] get_threadmarks  story_id={story_id}  post_type={post_type!r}")
    print(f"[db]   Composite index scan on idx_posts_story_type (story_id, post_type)")

    results = fetch_all(conn, """
        SELECT post_id, post_url, title, author, timestamp, post_type, likes
        FROM posts
        WHERE story_id = %s
          AND post_type = %s
        ORDER BY timestamp ASC NULLS LAST
    """, (story_id, post_type))

    print(f"[db]   Found {len(results)} threadmarks")
    return results


def get_authors(conn):
    return fetch_all(conn, """
        SELECT DISTINCT author
        FROM stories
        WHERE author IS NOT NULL AND author <> ''
        ORDER BY author ASC
    """)


def get_tags(conn):
    print(f"\n[db] get_tags  loading all distinct tag values")
    print(f"[db]   GIN index on stories.tags used to enumerate tag entries")
    return fetch_all(conn, """
        SELECT DISTINCT jsonb_array_elements_text(tags) AS tag
        FROM stories
        WHERE tags IS NOT NULL
        ORDER BY tag ASC
    """)