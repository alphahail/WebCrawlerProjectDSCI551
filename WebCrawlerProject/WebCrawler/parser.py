from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

from config import BASE_URL


THREADMARK_CATEGORIES = {
    "1":  "threadmark",
    "13": "apocrypha",
    "19": "informational",
}


class ThreadPageParser:

    def parse(self, html, url):
        soup = BeautifulSoup(html, "lxml")
        return {
            "title":           self.get_title(soup),
            "author":          self.get_author(soup),
            "tags":            self.get_tags(soup),
            "watchers":        self.get_watchers(soup),
            "threadmark_urls": self.get_threadmark_urls(soup, url),
        }

    def get_title(self, soup):
        tag = soup.select_one("h1.p-title-value")
        return tag.get_text(strip=True) if tag else ""

    def get_author(self, soup):
        tag = soup.select_one(".message-userDetails .username")
        return tag.get_text(strip=True) if tag else ""

    def get_tags(self, soup):
        return [
            t.get_text(strip=True).replace("\n", " ").replace("\r", "").strip()
            for t in soup.select(".tagItem")
            if t.get_text(strip=True)
        ]

    def get_watchers(self, soup):
        for dl in soup.select("dl.pairs--rows"):
            dt = dl.select_one("dt")
            dd = dl.select_one("dd")
            if dt and "Watchers" in dt.get_text():
                try:
                    return int(dd.get_text(strip=True).replace(",", ""))
                except ValueError:
                    return None
        return None

    def get_threadmark_urls(self, soup, thread_url):
        result = {}
        thread_path      = urlparse(thread_url).path.rstrip("/")
        threadmarks_base = f"{BASE_URL}{thread_path}/threadmarks"

        for cat_id, cat_name in THREADMARK_CATEGORIES.items():
            if cat_id != "1":
                continue
            page_url  = threadmarks_base
            fetch_url = self.get_fetch_url(soup, cat_id)
            result[cat_name] = {
                "page_url":  page_url,
                "fetch_url": fetch_url,
            }
        return result

    def get_fetch_url(self, soup, cat_id):
        body = soup.select_one(f".block-body--threadmarkBody.category-{cat_id}")
        if not body:
            return None
        filler = body.select_one(".structItem--threadmark-filler [data-fetchurl]")
        if filler:
            return urljoin(BASE_URL, filler.get("data-fetchurl", ""))
        return None


class ThreadmarkPageParser:

    def parse(self, html, category="threadmark"):
        soup = BeautifulSoup(html, "lxml")
        return self.extract_items(soup, category)

    def parse_load_range(self, html, category="threadmark"):
        soup = BeautifulSoup(html, "lxml")
        return self.extract_items(soup, category)

    def extract_items(self, soup, category):
        items = []
        for item in soup.select(".structItem--threadmark"):
            if "structItem--threadmark-filler" in item.get("class", []):
                continue

            link = item.select_one(".structItem-title a[href]")
            time = item.select_one("time")

            if not link:
                continue

            href     = link.get("href", "")
            post_id  = self.extract_post_id(href)
            post_url = urljoin(BASE_URL, href)

            items.append({
                "post_id":   post_id,
                "post_url":  post_url,
                "title":     link.get_text(strip=True),
                "author":    item.get("data-content-author", ""),
                "timestamp": time.get("datetime") if time else None,
                "likes":     item.get("data-likes", "0"),
                "post_type": category,
            })
        return items

    def extract_post_id(self, href):
        if "#post-" in href:
            return "post-" + href.split("#post-")[-1]
        return ""


class ListingParser:

    BLOCKED_URLS = {
        "https://forums.spacebattles.com/threads/spacebattles-trending-stories-and-quests-updated-weekly.1140820/",
        "https://forums.spacebattles.com/threads/crw-rules-guide-sticky-signpost-05-10-2018.428998/",
    }

    def parse_listing(self, html, url):
        soup = BeautifulSoup(html, "lxml")
        return {
            "threads":  self.get_threads(soup),
            "next_url": self.get_next_page(soup, url),
        }

    def get_threads(self, soup):
        threads = []
        for item in soup.select(".structItem--thread"):
            title_tag = item.select_one(".structItem-title a[href*='/threads/']")
            if not title_tag:
                continue
            if item.select_one(".structItem-status--sticky"):
                continue

            href     = title_tag.get("href", "")
            full_url = urljoin(BASE_URL, href)

            if "/page-" in full_url:
                continue
            if full_url in self.BLOCKED_URLS:
                print(f"[listing] Skipping blocked thread: {full_url}")
                continue

            author = item.get("data-author", "") or ""

            word_count = None
            for a in item.select("a[href*='threadmarks']"):
                text = a.get_text(strip=True)
                if text.startswith("Words:"):
                    word_count = text.replace("Words:", "").strip()
                    break

            replies = None
            views   = None
            for dl in item.select(".structItem-cell--meta dl"):
                dt = dl.select_one("dt")
                dd = dl.select_one("dd")
                if not dt or not dd:
                    continue
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                if label == "replies":
                    replies = value
                elif label == "views":
                    views = value

            threads.append({
                "url":        full_url,
                "author":     author,
                "word_count": word_count,
                "replies":    replies,
                "views":      views,
            })
        return threads

    def get_next_page(self, soup, current_url):
        nav = soup.select_one("a.pageNav-jump--next")
        if not nav or not nav.get("href"):
            return None

        next_url       = urljoin(current_url, nav["href"])
        current_params = parse_qs(urlparse(current_url).query, keep_blank_values=True)
        next_parsed    = urlparse(next_url)
        next_params    = parse_qs(next_parsed.query, keep_blank_values=True)
        merged         = {**current_params, **next_params}

        return urlunparse(next_parsed._replace(query=urlencode(merged, doseq=True)))