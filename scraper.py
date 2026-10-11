import json
import logging
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import APIFY_API_TOKEN, BASE_DIR, TARGET_ROLES

logger = logging.getLogger(__name__)

class MultiSourceJobScraper:
    """
    Multi-platform Job Scraper:
    - LinkedIn (via Apify with 24h freshness filter)
    - We Work Remotely (Real-time live RSS feed - 100% Free)
    - RemoteOK (Real-time API - 100% Free)
    """

    def __init__(self, apify_token: str = APIFY_API_TOKEN):
        self.apify_token = apify_token
        self.apify_actor_url = (
            f"https://api.apify.com/v2/acts/curious_coder~linkedin-jobs-scraper/run-sync-get-dataset-items"
            f"?token={self.apify_token}"
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def scrape_all_sources(self, keywords: str = "Flutter Developer", count_per_source: int = 50) -> List[Dict[str, Any]]:
        """Scrapes and merges jobs from LinkedIn, We Work Remotely, and RemoteOK."""
        all_jobs = []

        # 1. We Work Remotely (Real-time, Free)
        print("[*] Fetching latest jobs from We Work Remotely...")
        wwr_jobs = self.scrape_weworkremotely()
        all_jobs.extend(wwr_jobs)
        print(f"[+] We Work Remotely: Found {len(wwr_jobs)} fresh remote listings.")

        # 2. RemoteOK (Real-time, Free)
        print("[*] Fetching latest tech jobs from RemoteOK...")
        rok_jobs = self.scrape_remoteok(tags=["flutter", "mobile", "ai", "react"])
        all_jobs.extend(rok_jobs)
        print(f"[+] RemoteOK: Found {len(rok_jobs)} targeted tech listings.")

        # 3. LinkedIn (Apify with latest 24h filter)
        if self.apify_token:
            print(f"[*] Fetching latest 24h LinkedIn jobs via Apify for '{keywords}'...")
            li_jobs = self.scrape_linkedin(keywords=keywords, count=count_per_source)
            all_jobs.extend(li_jobs)
            print(f"[+] LinkedIn: Found {len(li_jobs)} listings.")

        return all_jobs

    def scrape_linkedin(self, keywords: str = "Flutter Developer", location: str = "Remote", count: int = 50) -> List[Dict[str, Any]]:
        """
        Scrapes LinkedIn jobs posted in the LAST 24 HOURS (f_TPR=r86400).
        """
        search_query = f"{keywords} {location}".strip().replace(" ", "%20")
        # f_TPR=r86400 (last 24 hours), f_WT=2 (Remote Only)
        linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={search_query}&f_TPR=r86400&f_WT=2&position=1&pageNum=0"
        
        payload = {
            "count": count,
            "scrapeCompany": True,
            "urls": [linkedin_url]
        }

        try:
            response = requests.post(self.apify_actor_url, json=payload, timeout=300)
            if response.status_code in (200, 201):
                jobs = response.json()
                for j in jobs:
                    j["source_platform"] = "LinkedIn"
                return jobs
            else:
                print(f"[-] Apify responded with code {response.status_code}")
                return []
        except Exception as e:
            print(f"[!] Apify error: {e}")
            return []

    def scrape_weworkremotely(self) -> List[Dict[str, Any]]:
        """Fetches latest remote programming jobs from WeWorkRemotely RSS feed."""
        url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        jobs = []
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item"):
                    raw_title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    desc = item.find("description").text if item.find("description") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""

                    # WWR titles are usually formatted as "CompanyName: Role Title"
                    company = "Unknown"
                    title = raw_title
                    if ":" in raw_title:
                        parts = raw_title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    jobs.append({
                        "id": f"wwr_{abs(hash(link))}",
                        "title": title,
                        "companyName": company,
                        "location": "Remote",
                        "descriptionText": desc,
                        "descriptionHtml": desc,
                        "link": link,
                        "applyUrl": link,
                        "postedAt": pub_date,
                        "source_platform": "WeWorkRemotely"
                    })
        except Exception as e:
            print(f"[-] Failed fetching WeWorkRemotely: {e}")
        return jobs

    def scrape_remoteok(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Fetches targeted jobs from RemoteOK public API."""
        tags = tags or ["flutter", "mobile", "ai", "react"]
        jobs = []
        seen_ids = set()

        for tag in tags:
            url = f"https://remoteok.com/api?tag={tag}"
            try:
                r = requests.get(url, headers=self.headers, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    # First element in RemoteOK API response is legal disclaimer
                    items = data[1:] if isinstance(data, list) and len(data) > 1 else []
                    for item in items:
                        jid = str(item.get("id"))
                        if jid in seen_ids:
                            continue
                        seen_ids.add(jid)

                        jobs.append({
                            "id": f"rok_{jid}",
                            "title": item.get("position", "Software Engineer"),
                            "companyName": item.get("company", "Company"),
                            "location": item.get("location", "Remote"),
                            "descriptionText": item.get("description", ""),
                            "descriptionHtml": item.get("description", ""),
                            "link": item.get("url") or f"https://remoteok.com/l/{jid}",
                            "applyUrl": item.get("apply_url") or item.get("url"),
                            "salary": f"${item.get('salary_min', '')} - ${item.get('salary_max', '')}" if item.get("salary_min") else "",
                            "postedAt": item.get("date", ""),
                            "source_platform": "RemoteOK"
                        })
            except Exception as e:
                print(f"[-] RemoteOK tag '{tag}' failed: {e}")

        return jobs

    def load_cached_or_sample_jobs(self) -> List[Dict[str, Any]]:
        """Loads sample jobs from perplexity ai.json for testing."""
        json_file = BASE_DIR / "perplexity ai.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pinned = data.get("pinData", {}).get("HTTP Request", [])
                    items = [item.get("json", item) for item in pinned if "json" in item or isinstance(item, dict)]
                    for item in items:
                        item["source_platform"] = "LinkedIn (Cached)"
                    return items
            except Exception as e:
                print(f"[-] Failed reading sample jobs: {e}")
        return []

# Backwards compatibility alias
LinkedInScraper = MultiSourceJobScraper
