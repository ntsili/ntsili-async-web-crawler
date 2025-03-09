# **Async Web Crawler**  
 **A Python-based asynchronous web crawler designed for LiteSpeed Cache and QUIC.cloud cache warming.**  

## **Overview**  
This asynchronous web crawler **warms up your WordPress website’s QUIC.cloud cache** by periodically visiting internal links. This ensures that your website loads quickly by keeping pages preloaded in cache.

It is designed for LiteSpeed Cache and QUIC.cloud, but it can also be adapted for other caching solutions such as WP Rocket, Cloudflare, or FastCGI caching.

## **Features**  

✔️ **Asynchronous & Fast** – Uses `asyncio` and `aiohttp` for concurrent requests.  
✔️ **Automatic Cache Warming** – Appends `?qc-cache-warm` to URLs to **pre-warm QUIC.cloud cache**.  
✔️ **Recursive Crawling** – Extracts **internal links** and follows them up to a specified depth.  
✔️ **Sitemap Support** – **Fetches URLs from `sitemap.xml`** first (if available), ensuring comprehensive crawling.  
✔️ **Desktop & Mobile Simulation** – Uses different **User-Agent strings** to mimic real users.  
✔️ **Logging & Performance Tracking** – Logs **cache statuses** and **response times** in `cache_performance.csv`.  
✔️ **Scheduled Execution** – Runs automatically **every 3 hours** using `schedule`.  

---

## **Installation**  

### **1️. Install Dependencies**  
Ensure Python is installed, then install required libraries:  

pip install aiohttp beautifulsoup4 schedule

markdown
Copy
Edit

### **2️. Clone the Repository**  

git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git cd YOUR_REPO_NAME

markdown
Copy
Edit

### **3️. Modify the Base URL**  

Replace `https://mindbodybalance.health` with your **own website URL** inside the script:  

desktop_crawler = AsyncWebCrawler("https://yourwebsite.com", DESKTOP_USER_AGENT) mobile_crawler = AsyncWebCrawler("https://yourwebsite.com", MOBILE_USER_AGENT)

markdown
Copy
Edit

### **4️. Run the Script**  

python crawler.py

markdown
Copy
Edit

The script will **start crawling immediately** and then run **every 3 hours** in the background.

---

## **How It Works**  

### **⚡ Step 1: Fetch URLs from `sitemap.xml`**  
The crawler first **checks for `sitemap.xml`** and extracts all listed URLs.  

- If the sitemap contains **nested sitemaps**, it recursively fetches them.  
- If no sitemap is found, it **falls back to link extraction** from the base URL.  

### **⚡ Step 2: Extract Internal Links (Fallback Mode)**  
If no sitemap is available, the crawler:  

- Visits the **base URL**.  
- Extracts **internal links** using `BeautifulSoup`.  
- Recursively follows them **up to a specified depth**.  

### **⚡ Step 3: Cache Warming & Logging**  

- Visits each page, checking **QUIC.cloud cache status (`X-QC-Cache` header)**.  
- If a page is a **blog post (`/2023/` or `/2024/` in URL)**, it **forces cache warming**.  
- Logs **response times** and cache status in `cache_performance.csv`.  

### **⚡ Step 4: Automatic Recrawling**  

- Revisits **each URL every 3 hours** to ensure pages remain cached.  

---

## **Configuration**  

You can customize the following parameters inside the **`AsyncWebCrawler`** class:

| Parameter       | Description                         | Default  |
|--------------- |------------------------------------|--------- |
| `max_depth`    | Maximum depth for recursive crawl | `5`      |
| `semaphore`    | Limits concurrent requests       | `10`     |
| `recrawl_interval` | Time before rechecking a page | `3 hours` |

Modify these values **inside the script** as needed.

---

## **Logs & Debugging**  

All logs are recorded in **`cache_performance.csv`**. To **monitor logs in real time**, run:

tail -f cache_performance.csv

yaml
Copy
Edit

If you encounter errors, check the **console output** or logs for debugging.

---

## **License**  
This project is licensed under the **GNU GPL v3**. See the [LICENSE](LICENSE) file for details.

---

## **Contribution**  
**Want to contribute?**  
Fork the repository, make your changes, and **submit a pull request!**  

---