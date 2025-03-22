Async Web Crawler for WordPress Cache Warming
🚀 Overview
This is an asynchronous Python web crawler designed to warm up the QUIC.cloud and LiteSpeed cache for WordPress websites. It ensures your website loads faster by preloading internal pages.

✅ Asynchronous & Fast – Uses asyncio and aiohttp for concurrent requests.
✅ Automatic Cache Warming – Appends ?qc-cache-warm to blog post URLs.
✅ Recursive Crawling – Extracts internal links and follows them up to a specified depth.
✅ Sitemap Support – Fetches URLs from sitemap.xml first.
✅ Desktop & Mobile Simulation – Uses different User-Agent strings to mimic real users.
✅ Logging & Performance Tracking – Logs cache statuses, slow pages, and errors.
✅ Runs via Cron Job – Instead of schedule, you should set a cron job to run every few hours.

🛠️ Installation & Setup
1️⃣ Install Dependencies
Run:

bash
Copy
Edit
pip install aiohttp beautifulsoup4
2️⃣ Clone the Repository
bash
Copy
Edit
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
3️⃣ Modify the Base URL
Edit crawl.py and replace:

python
Copy
Edit
desktop_crawler = AsyncWebCrawler("https://yourwebsite.com", DESKTOP_USER_AGENT)
mobile_crawler = AsyncWebCrawler("https://yourwebsite.com", MOBILE_USER_AGENT)
with your actual domain.

4️⃣ Set Up a Cron Job
Instead of manually running the script, add this line to your cron jobs:

bash
Copy
Edit
0 */3 * * * /usr/bin/python3 /home/mindbody/crawl/crawl.py >> /home/mindbody/crawl/logs.txt 2>&1
This runs the crawler every 3 hours.

📝 How It Works
Step 1: Fetch URLs from Sitemap
Extracts links from sitemap.xml.

If a nested sitemap exists, it follows and fetches additional links.

Step 2: Crawl Internal Links
Extracts and follows internal links up to 5 levels deep.

Step 3: Cache Warming
Requests blog posts (/2023/ and /2024/ URLs) with ?qc-cache-warm for QUIC.cloud.

Step 4: Logging & Debugging
✅ Logs cache status and response times in cache_performance.csv.

✅ Logs slow pages in slow_pages.csv.

✅ Logs errors in error_log.txt.

📂 Logs & Debugging
To monitor logs, use:

bash
Copy
Edit
tail -f /home/mindbody/crawl/debug_log.txt
To check slow pages:

bash
Copy
Edit
cat /home/mindbody/crawl/slow_pages.csv
🛠️ Contributing
If you want to improve this project:

Fork the repository.

Make your changes.

Submit a pull request!

📜 License
This project is licensed under GNU GPL v3.

This README reflects the new version of crawl.py with improved logging and cron support.