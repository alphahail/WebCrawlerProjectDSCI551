import time
import random
import requests
from urllib.robotparser import RobotFileParser

from config import BASE_URL, CRAWL_DELAY


class Fetcher:
    def __init__(self, delay=CRAWL_DELAY):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WebCrawlerProject"
        })
        self.delay = delay
        self.rp = RobotFileParser()
        self.load_robots()

    def load_robots(self):
        robots_url = f"{BASE_URL}/robots.txt"
        print(f"[robots] Fetching {robots_url} ...")
        try:
            resp = self.session.get(robots_url, timeout=10)
            print(f"[robots] Status: {resp.status_code} | Length: {len(resp.text):,} chars")
            self.rp.set_url(robots_url)
            self.rp.parse(resp.text.splitlines())
            print(f"[robots] Entries parsed: {len(self.rp.entries)}")
            print(f"[robots] disallow_all: {self.rp.disallow_all} | allow_all: {self.rp.allow_all}")
        except Exception as e:
            print(f"[robots] ERROR loading robots.txt: {e}")
            print("[robots] Failing open, will allow all crawling")
            self.rp.allow_all = True

    def can_fetch(self, url):
        ua = self.session.headers["User-Agent"]
        result = self.rp.can_fetch(ua, url)
        print(f"[robots] can_fetch('{ua}', '{url}') -> {result}")
        return result

    def get(self, url):
        if not self.can_fetch(url):
            print(f"[fetch] Blocked by robots.txt: {url}")
            return None
        print(f"[fetch] Sending request to: {url}")
        time.sleep(random.uniform(*self.delay))
        resp = self.session.get(url, timeout=15)
        print(f"[fetch] Status: {resp.status_code} | Length: {len(resp.text):,} chars")
        resp.raise_for_status()
        return resp.text