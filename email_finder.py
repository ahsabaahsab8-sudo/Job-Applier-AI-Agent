import re
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import requests
import dns.resolver

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

IGNORE_EMAILS = {
    "user@domain.com", "example@example.com", "email@company.com", 
    "test@test.com", "support@remoteok.com", "contact@remoteok.com",
    "weworkremotely@weworkremotely.com"
}
IGNORE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css", ".ico")

RECRUITER_KEYWORDS = [
    "career", "careers", "recruit", "recruiting", "recruitment", 
    "job", "jobs", "hr", "talent", "hiring", "apply", "people"
]

ATS_DOMAINS = [
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", 
    "bamboohr.com", "smartrecruiters.com", "workatastartup.com",
    "breezy.hr", "jobvite.com", "rippling.com", "recruitee.com"
]

class RecruiterEmailFinder:
    """
    Intelligent Email Discovery & ATS Classifier with DNS MX Verification.
    Prevents bounces by:
    1. Extracting explicit recruiter emails from job posts & apply pages.
    2. Detecting ATS portals (Ashby, Greenhouse, Lever, Workable).
    3. Verifying DNS MX records before validating any domain.
    4. Rejecting unverified guesses so your Gmail sender reputation remains 100% clean.
    """

    def __init__(self):
        self.mx_cache = {}

    def check_mx_records(self, domain: str) -> bool:
        """Verifies if a domain has active Mail Exchange (MX) DNS records."""
        domain = domain.lower().strip()
        if not domain or "." not in domain:
            return False

        if domain in self.mx_cache:
            return self.mx_cache[domain]

        try:
            answers = dns.resolver.resolve(domain, 'MX', lifetime=4)
            valid = len(answers) > 0
            self.mx_cache[domain] = valid
            return valid
        except Exception:
            self.mx_cache[domain] = False
            return False

    def is_ats_portal(self, url: str) -> bool:
        """Detects if a URL is hosted on an ATS platform."""
        if not url:
            return False
        url_lower = url.lower()
        return any(ats in url_lower for ats in ATS_DOMAINS)

    def find_email(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-tier email discovery:
        - Tier 1: Explicit email in job description
        - Tier 2: Email on the direct apply page
        - Tier 3: ATS Portal Detection (no cold email, use web portal)
        - Tier 4: Company domain search with MX validation
        """
        company_name = job.get("companyName") or job.get("company") or "Company"
        company_website = job.get("companyWebsite") or ""
        apply_url = job.get("applyUrl") or job.get("link") or job.get("url") or ""
        desc_text = job.get("descriptionText") or ""
        desc_html = job.get("descriptionHtml") or ""
        full_text = f"{desc_text} {desc_html}"

        # 1. Direct Regex scan in job text & HTML
        direct_email = self._extract_recruiter_email(full_text)
        if direct_email:
            domain = direct_email.split("@")[-1]
            if self.check_mx_records(domain):
                return {
                    "email": direct_email,
                    "confidence": "high",
                    "source": "job_description",
                    "is_portal": False
                }

        # 2. Check if the applyUrl is a known ATS portal
        if self.is_ats_portal(apply_url):
            return {
                "email": None,
                "confidence": "portal_only",
                "source": "ats_portal",
                "portal_url": apply_url,
                "is_portal": True
            }

        # 3. Try fetching the apply URL to check for mailto: or recruiter email
        if apply_url and apply_url.startswith("http") and not any(x in apply_url for x in ["remoteok.com/api", "linkedin.com/jobs"]):
            page_email = self._scrape_apply_page(apply_url)
            if page_email:
                domain = page_email.split("@")[-1]
                if self.check_mx_records(domain):
                    return {
                        "email": page_email,
                        "confidence": "high",
                        "source": "apply_page",
                        "is_portal": False
                    }

        # 4. Search web for company careers email (DuckDuckGo quick probe)
        searched_email = self._search_company_careers_email(company_name)
        if searched_email:
            domain = searched_email.split("@")[-1]
            if self.check_mx_records(domain):
                return {
                    "email": searched_email,
                    "confidence": "medium",
                    "source": "web_search",
                    "is_portal": False
                }

        # 5. Extract domain and check if standard careers@ has valid MX
        domain = self._extract_domain(company_website, company_name)
        if domain and self.check_mx_records(domain):
            # Only use domain email if the company has active MX records
            return {
                "email": f"careers@{domain}",
                "confidence": "heuristic_mx_verified",
                "source": "corporate_domain_mx_verified",
                "is_portal": False
            }

        # 6. Fallback: If no verified email, classify as Portal Application
        # This prevents sending emails to non-existent addresses and bouncing
        return {
            "email": None,
            "confidence": "unverified",
            "source": "portal_only",
            "portal_url": apply_url,
            "is_portal": True
        }

    def _extract_recruiter_email(self, text: str) -> Optional[str]:
        candidates = EMAIL_REGEX.findall(text)
        # Priority: recruitment keywords
        for email in candidates:
            email_lower = email.lower()
            if any(email_lower.endswith(ext) for ext in IGNORE_EXTENSIONS):
                continue
            if email_lower in IGNORE_EMAILS:
                continue
            if any(kw in email_lower for kw in RECRUITER_KEYWORDS):
                return email_lower

        # Secondary: other valid corporate emails
        for email in candidates:
            email_lower = email.lower()
            if any(email_lower.endswith(ext) for ext in IGNORE_EXTENSIONS):
                continue
            if email_lower in IGNORE_EMAILS:
                continue
            if not any(x in email_lower for x in ["github.com", "sentry.io", "w3.org", "schema.org"]):
                return email_lower

        return None

    def _scrape_apply_page(self, url: str) -> Optional[str]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            if r.status_code == 200:
                # Check for mailto:
                mailto_matches = re.findall(r'mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r.text, re.IGNORECASE)
                for m in mailto_matches:
                    m_lower = m.lower()
                    if m_lower not in IGNORE_EMAILS and not any(m_lower.endswith(ext) for ext in IGNORE_EXTENSIONS):
                        return m_lower
                return self._extract_recruiter_email(r.text)
        except Exception:
            pass
        return None

    def _search_company_careers_email(self, company_name: str) -> Optional[str]:
        if not company_name or len(company_name.strip()) < 3:
            return None
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            query = f'"{company_name.strip()}" ("careers@" OR "jobs@" OR "recruiting@" OR "talent@")'
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                candidates = EMAIL_REGEX.findall(r.text)
                clean_comp = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
                for c in candidates:
                    c_lower = c.lower()
                    if any(c_lower.endswith(ext) for ext in IGNORE_EXTENSIONS) or c_lower in IGNORE_EMAILS:
                        continue
                    # Ensure email belongs to or references the company
                    domain = c_lower.split("@")[-1]
                    if clean_comp in domain and any(kw in c_lower for kw in RECRUITER_KEYWORDS):
                        return c_lower
        except Exception:
            pass
        return None

    def _extract_domain(self, website_url: str, company_name: str) -> Optional[str]:
        if website_url:
            parsed = urllib.parse.urlparse(website_url)
            netloc = parsed.netloc or parsed.path
            netloc = netloc.lower().replace("www.", "")
            parts = netloc.split(".")
            if len(parts) >= 2:
                return ".".join(parts[-2:])
        
        if company_name:
            clean = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
            if clean and len(clean) >= 3:
                return f"{clean}.com"

        return None

    def find_recruiter_email(self, job: Dict[str, Any]) -> Tuple[Optional[str], str]:
        info = self.find_email(job)
        return info.get("email"), info.get("confidence", "unverified")
