import asyncio
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
import xml.etree.ElementTree as ET
import logging
import os
import csv
from datetime import datetime, timedelta

# 📌 File Paths
BASE_DIR = "/home/mindbody/crawl"
LOG_FILE = os.path.join(BASE_DIR, "cache_performance.csv")
SLOW_PAGES_FILE = os.path.join(BASE_DIR, "slow_pages.csv")
DEBUG_LOG = os.path.join(BASE_DIR, "debug_log.txt")
ERROR_LOG = os.path.join(BASE_DIR, "error_log.txt")

# 📌 User-Agent Strings
DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
MOBILE_USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/537.36'

# 📌 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(DEBUG_LOG),
        logging.StreamHandler()
    ]
)

def write_debug_log(message):
    """Write debug messages to debug_log.txt."""
    with open(DEBUG_LOG, "a") as f:
        f.write(f"{datetime.now()} - {message}\n")

def setup_log_files():
    """Ensure log files exist with headers."""
    for file, headers in [(LOG_FILE, ["Timestamp", "URL", "QUIC Cache", "LiteSpeed Cache", "Response Time (ms)"]),
                          (SLOW_PAGES_FILE, ["Timestamp", "URL", "Response Time (ms)"])]:
        if not os.path.exists(file):
            with open(file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

setup_log_files()
write_debug_log("✅ Log files verified/created.")

class AsyncWebCrawler:
    def __init__(self, base_url, user_agent):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.index_map = {}  # Stores URL -> {last_crawled, cache_status, response_time}
        self.headers = {'User-Agent': user_agent}
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    async def fetch(self, session: ClientSession, url):
        """Fetch and log cache status, handle slow pages, and retry cache misses."""
        async with self.semaphore:
            try:
                retry_count = 0
                cache_status_qc = "UNKNOWN"
                cache_status_ls = "UNKNOWN"

                # ✅ Step 1: Check cache status with HEAD request
                async with session.head(url, timeout=5) as response:
                    cache_status_qc = response.headers.get("X-QC-Cache", "UNKNOWN")
                    cache_status_ls = response.headers.get("X-LiteSpeed-Cache", "UNKNOWN")

                # ✅ Step 2: If QUIC.cloud is "MISS", force cache warming with retries
                while cache_status_qc.lower() == "miss" and retry_count < 3:
                    retry_count += 1
                    logging.warning(f"🚨 Cache MISS detected for {url}. Attempting cache preloading (Retry {retry_count})...")
                    await session.get(url + "?qc-cache-warm", timeout=5)
                    await asyncio.sleep(5 * retry_count)  # Progressive delay

                    # Re-check cache status
                    async with session.head(url, timeout=5) as response:
                        cache_status_qc = response.headers.get("X-QC-Cache", "UNKNOWN")

                    if cache_status_qc.lower() == "hit":
                        logging.info(f"✅ Cache HIT achieved after {retry_count} retries for {url}.")

                # ✅ Step 3: Fetch full page content
                start_time = datetime.now()
                async with session.get(url, timeout=5) as response:
                    duration = (datetime.now() - start_time).total_seconds() * 1000  # Convert to ms

                    # ⚠️ Detect slow pages
                    if duration > 500:
                        logging.warning(f"⚠️ SLOW PAGE: {url} | Response Time: {duration:.2f}ms")
                        with open(SLOW_PAGES_FILE, "a", newline="") as slow_file:
                            slow_writer = csv.writer(slow_file)
                            slow_writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), url, duration])

                    logging.info(f"✅ Visited: {url} | QUIC.cloud: {cache_status_qc} | LiteSpeed: {cache_status_ls} | Time: {duration:.2f}ms")

                    # ✅ Log results
                    with open(LOG_FILE, "a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), url, cache_status_qc, cache_status_ls, duration])

                    if response.status == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                        return await response.text()
            except Exception as e:
                logging.error(f"❌ Error: {url} | {e}")
                with open(ERROR_LOG, "a") as f:
                    f.write(f"{datetime.now()} - {url} | ERROR: {e}\n")
        return None  

    async def fetch_sitemap(self, session, url=None):
        """Fetch and parse the sitemap.xml (or sitemap index) recursively."""
        if url is None:
            url = urljoin(self.base_url, "/sitemap.xml")

        urls = []
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    root = ET.fromstring(xml_content)

                    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
                    for elem in root.findall(f".//{namespace}loc"):
                        sitemap_url = elem.text.strip()
                        if "sitemap" in sitemap_url and sitemap_url.endswith(".xml"):
                            nested_urls = await self.fetch_sitemap(session, sitemap_url)
                            urls.extend(nested_urls)
                        else:
                            urls.append(sitemap_url)
        except Exception as e:
            logging.error(f"Error fetching sitemap: {e}")
        return urls

    async def start_crawl(self):
        """Initialize async crawling session."""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            sitemap_urls = await self.fetch_sitemap(session)
            tasks = [self.fetch(session, url) for url in sitemap_urls] if sitemap_urls else [self.fetch(session, self.base_url)]
            await asyncio.gather(*tasks)

async def run_all_crawlers():
    """Run both desktop and mobile crawlers asynchronously."""
    desktop_crawler = AsyncWebCrawler("https://mindbodybalance.health", DESKTOP_USER_AGENT)
    mobile_crawler = AsyncWebCrawler("https://mindbodybalance.health", MOBILE_USER_AGENT)
    await asyncio.gather(
        desktop_crawler.start_crawl(),
        mobile_crawler.start_crawl()
    )

if __name__ == "__main__":
    logging.info("🚀 Starting cache warming process...")
    
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_all_crawlers())
    except Exception as e:
        logging.error(f"❌ Error running crawlers: {e}")
        with open(ERROR_LOG, "a") as f:
            f.write(f"{datetime.now()} - ERROR: {e}\n")

    logging.info("✅ Cache warming process completed!")