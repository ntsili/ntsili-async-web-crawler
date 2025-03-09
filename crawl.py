import asyncio
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
import xml.etree.ElementTree as ET
import logging
import schedule
import time
import csv
from datetime import datetime, timedelta

# Logging setup (console)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Log file for cache performance
LOG_FILE = "cache_performance.csv"

# User-Agent Strings
DESKTOP_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
MOBILE_USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/537.36'


class AsyncWebCrawler:
    def __init__(self, base_url, user_agent):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.index_map = {}  # Stores URL -> {last_crawled, cache_status, response_time}
        self.headers = {'User-Agent': user_agent}
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        self.recrawl_interval = timedelta(hours=3)  # Re-crawl pages every 3 hours

    def normalize_url(self, url):
        """Normalize URL (remove query params and fragments)."""
        parsed_url = urlparse(url)
        normalized_url = parsed_url._replace(query='', fragment='')
        return urlunparse(normalized_url)

    def should_crawl(self, url):
        """Determine if a URL should be crawled based on last crawl time."""
        if url not in self.index_map:
            return True  # New URL, must be crawled
        last_crawled = self.index_map[url]['last_crawled']
        return datetime.now() - last_crawled > self.recrawl_interval

    async def fetch(self, session: ClientSession, url):
        """Fetch and log cache status, prioritizing blog posts."""
        async with self.semaphore:
            try:
                if not self.should_crawl(url):
                    logging.info(f"Skipping recently crawled: {url}")
                    return None  # Skip if recently crawled
                
                if "/2023/" in url or "/2024/" in url:  # Prioritize blog posts
                    cache_warm_url = url + "?qc-cache-warm"
                    await session.get(cache_warm_url, timeout=10)

                start_time = time.time()
                async with session.get(url, timeout=10) as response:
                    duration = round((time.time() - start_time) * 1000, 2)
                    cache_status = response.headers.get("X-QC-Cache", "UNKNOWN")

                    logging.info(f"Visited: {url} | QUIC.cloud Cache: {cache_status} | Response Time: {duration}ms")

                    # Update index map
                    self.index_map[url] = {
                        'last_crawled': datetime.now(),
                        'cache_status': cache_status,
                        'response_time': duration
                    }

                    with open(LOG_FILE, "a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), url, cache_status, duration])

                    if response.status == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                        return await response.text()
            except Exception as e:
                logging.error(f"Request failed: {url} | Error: {e}")
        return None   

    async def fetch_sitemap(self, session, url=None):
        """Fetch and parse the sitemap.xml (or sitemap index) recursively."""
        if url is None:
            url = urljoin(self.base_url, "/sitemap.xml")  # Default to base sitemap

        urls = []
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    root = ET.fromstring(xml_content)

                    # Extract URLs from the sitemap
                    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
                    for elem in root.findall(f".//{namespace}loc"):
                        sitemap_url = elem.text.strip()

                        # Check if it's another sitemap index (nested sitemap)
                        if "sitemap" in sitemap_url and sitemap_url.endswith(".xml"):
                            logging.info(f"Found nested sitemap: {sitemap_url}")
                            nested_urls = await self.fetch_sitemap(session, sitemap_url)  # Recursively fetch
                            urls.extend(nested_urls)
                        else:
                            urls.append(sitemap_url)

                    return urls
                else:
                    logging.warning(f"Could not fetch sitemap: {url}")
        except Exception as e:
            logging.error(f"Error fetching sitemap: {e}")

        return urls

    def parse_links(self, html_content, base_url):
        """Extract internal links from page."""
        soup = BeautifulSoup(html_content, 'html.parser')
        for link in soup.find_all('a', href=True):
            url = link['href']
            if not urlparse(url).netloc:  # Relative URL
                url = urljoin(base_url, url)
            if urlparse(url).netloc == self.base_domain:  # Internal links only
                yield self.normalize_url(url)

    async def crawl(self, url, session, depth=0, max_depth=5):
        """Recursively crawl pages up to max depth."""
        normalized_url = self.normalize_url(url)
        if depth > max_depth:
            return
        
        html_content = await self.fetch(session, url)
        if html_content:
            tasks = [self.crawl(link, session, depth + 1, max_depth) for link in self.parse_links(html_content, url)]
            await asyncio.gather(*tasks)

    async def start_crawl(self, max_depth=5):
        """Initialize async crawling session, prioritizing sitemap URLs first."""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            sitemap_urls = await self.fetch_sitemap(session)

            if sitemap_urls:
                logging.info(f"Discovered {len(sitemap_urls)} URLs from sitemap.xml")
                tasks = [self.crawl(url, session, max_depth=max_depth) for url in sitemap_urls]
            else:
                logging.info("No sitemap.xml found, falling back to normal crawling.")
                tasks = [self.crawl(self.base_url, session, max_depth=max_depth)]

            await asyncio.gather(*tasks)


async def run_all_crawlers():
    """Run both desktop and mobile crawlers asynchronously."""
    desktop_crawler = AsyncWebCrawler("https://mindbodybalance.health", DESKTOP_USER_AGENT)
    mobile_crawler = AsyncWebCrawler("https://mindbodybalance.health", MOBILE_USER_AGENT)

    await asyncio.gather(
        desktop_crawler.start_crawl(max_depth=5),
        mobile_crawler.start_crawl(max_depth=5)
    )

def setup_log_file():
    """Create log file with headers if it doesn't exist."""
    try:
        with open(LOG_FILE, "x", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "URL", "Cache Status", "Response Time (ms)"])
    except FileExistsError:
        pass  # File already exists

def run_crawlers():
    """Runs the crawlers using asyncio.run() properly."""
    logging.info("Starting WordPress cache warming process...")
    setup_log_file()  # Ensure log file exists
    
    try:
        asyncio.run(run_all_crawlers())  # Ensures correct async execution
    except Exception as e:
        logging.error(f"Error running async tasks: {e}")
    
    logging.info("Cache warming process completed!")

# Schedule to run every 3 hours
schedule.every(3).hours.do(run_crawlers)

if __name__ == "__main__":
    run_crawlers()  # Run immediately on startup
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if it's time to run
