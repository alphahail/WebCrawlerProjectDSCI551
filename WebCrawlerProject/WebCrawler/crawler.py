from collections import deque

from config import CREATIVE_WRITING_URL
from fetcher import Fetcher
from parser import ThreadPageParser, ThreadmarkPageParser, ListingParser
from storage import Storage


class Crawler:
    def __init__(self, seed_urls=None):
        self.listing_queue   = deque()
        self.thread_queue    = deque()
        self.fetcher         = Fetcher()
        self.thread_parser   = ThreadPageParser()
        self.threadmark_parser = ThreadmarkPageParser()
        self.listing_parser  = ListingParser()
        self.storage         = Storage()

        for url in (seed_urls or [CREATIVE_WRITING_URL]):
            if "/threads/" in url:
                self.thread_queue.append((url, None, None, None, None))
            else:
                self.listing_queue.append(url)

    def run(self, max_threads=50):
        crawled = 0
        try:
            while (self.listing_queue or self.thread_queue) and crawled < max_threads:
                if self.listing_queue:
                    self.process_listing(self.listing_queue.popleft())

                if self.thread_queue:
                    url, word_count, replies, views, author = self.thread_queue.popleft()

                    if not self.storage.word_count_changed(url, word_count):
                        print(f"[crawl] No changes detected, skipping")
                        continue

                    if self.process_thread(url, word_count, replies, views, author):
                        crawled += 1
                        print(f"[crawl] Progress: {crawled} of {max_threads} threads processed")

        finally:
            self.storage.close()

    def process_listing(self, url):
        print(f"\n[crawl] Fetching listing page: {url[:70]}")
        html = self.fetcher.get(url)
        if not html:
            return

        data    = self.listing_parser.parse_listing(html, url)
        queued  = 0
        checked = 0

        for thread in data["threads"]:
            thread_url = thread["url"]
            word_count = thread["word_count"]

            if thread_url in [u for u, *_ in self.thread_queue]:
                continue

            checked += 1
            if self.storage.word_count_changed(thread_url, word_count):
                self.thread_queue.append((
                    thread_url,
                    word_count,
                    thread["replies"],
                    thread["views"],
                    thread["author"],
                ))
                queued += 1

        print(f"[crawl] Checked {checked} threads, queued {queued} for updating")

        if data["next_url"]:
            self.listing_queue.append(data["next_url"])

    def process_thread(self, url, word_count, replies, views, author):
        print(f"\n[crawl] Processing thread: {url[:70]}")

        html = self.fetcher.get(url)
        if not html:
            return False

        page_data = self.thread_parser.parse(html, url)

        if not page_data["title"]:
            print(f"[crawl] Could not parse title, skipping")
            return False

        story_author = author or page_data["author"]

        story_id = self.storage.save_story(
            url,
            page_data["title"],
            story_author,
            page_data["tags"],
            word_count = word_count,
            watchers   = page_data["watchers"],
            replies    = replies,
            views      = views,
        )

        if not story_id:
            print(f"[crawl] Could not save story, skipping")
            return False

        print(f"[crawl] Saved story: {page_data['title'][:50]} (id={story_id})")

        for category, urls in page_data["threadmark_urls"].items():
            posts = self.fetch_threadmarks(urls["page_url"], urls["fetch_url"], category)
            if not posts:
                print(f"[crawl] No {category} entries found")
                continue

            existing  = self.storage.get_post_ids(story_id)
            new_posts = [p for p in posts if p["post_id"] not in existing]

            self.storage.save_posts(story_id, new_posts)
            print(
                f"[crawl] {category}: {len(posts)} total, "
                f"{len(new_posts)} new, "
                f"{len(posts) - len(new_posts)} already stored"
            )

        return True

    def fetch_threadmarks(self, page_url, fetch_url, category):
        all_posts = []

        print(f"[crawl] Fetching threadmarks page: {page_url[:70]}")
        html = self.fetcher.get(page_url)
        if html:
            posts = self.threadmark_parser.parse(html, category)
            all_posts.extend(posts)
            print(f"[crawl] Found {len(posts)} entries on threadmarks page")

        if fetch_url:
            print(f"[crawl] Fetching hidden entries from load-range endpoint")
            html = self.fetcher.get(fetch_url)
            if html:
                posts = self.threadmark_parser.parse_load_range(html, category)
                all_posts.extend(posts)
                print(f"[crawl] Found {len(posts)} additional hidden entries")

        seen   = set()
        unique = []
        for p in all_posts:
            if p["post_id"] not in seen:
                seen.add(p["post_id"])
                unique.append(p)

        return unique