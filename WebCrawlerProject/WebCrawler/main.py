import sys
import config
from crawler import Crawler

if __name__ == "__main__":
    args   = sys.argv[1:]
    offline = "--offline" in args
    nums   = [a for a in args if a.isdigit()]
    limit  = int(nums[0]) if nums else 50

    if offline:
        config.DB_CONFIG = config.LOCAL_CONFIG
        print("Running in offline mode, connecting to local PostgreSQL")
        print(config.DB_CONFIG)
    else:
        print("Connecting to Supabase")

    print(f"Starting crawler, max threads: {limit}")
    crawler = Crawler(seed_urls=[config.CREATIVE_WRITING_URL])
    crawler.run(max_threads=limit)