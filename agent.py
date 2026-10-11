import json
import re
import requests
from typing import Dict, Any
from config import (
    KILO_API_KEY,
    KILO_BASE_URL,
    KILO_MODEL,
    CANDIDATE_NAME,
    CANDIDATE_EMAIL,
    CANDIDATE_PHONE,
    CANDIDATE_PORTFOLIO,
    CANDIDATE_GITHUB
)

class AIAgent:
    def __init__(self, api_key: str = KILO_API_KEY, base_url: str = KILO_BASE_URL, model: str = KILO_MODEL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def process_job(self, job: Dict[str, Any], resume_text: str, recruiter_email: str) -> Dict[str, Any]:
        title = job.get("title", "Software Engineer")
        company = job.get("companyName", "Company")
        location = job.get("location", "Remote")
        description = job.get("descriptionText", "") or job.get("descriptionHtml", "")
        description_sample = description[:2500]

        prompt = f"""You are an elite career strategist and executive tech recruiter.
Analyze this job and the candidate's resume, then write a compelling tailored application.

Candidate Information:
- Name: {CANDIDATE_NAME}
- Email: {CANDIDATE_EMAIL}
- Phone: {CANDIDATE_PHONE}
- Portfolio: {CANDIDATE_PORTFOLIO}
- GitHub: {CANDIDATE_GITHUB}

Resume Excerpt:
{resume_text[:2500]}

Target Job:
- Title: {title}
- Company: {company}
- Location: {location}
- Description: {description_sample}

INSTRUCTIONS:
1. Match Analysis: Give a match score (0-100), top 3 strengths, and 2 key gaps.
2. Cover Letter: Write a tailored, persuasive 200-300 word cover letter. Connect candidate's verified background (Flutter, React, 3D WebGL, AI Agents, Python) to the role's needs.
3. HTML Email Body: Create a clean HTML email body for Gmail using simple tags (<p>, <strong>, <ul>, <li>, <br>). No generic placeholders.

OUTPUT PURE JSON ONLY (NO MARKDOWN CODEBLOCKS):
{{
  "match_percentage": 85,
  "strengths": ["...", "...", "..."],
  "gaps": ["...", "..."],
  "subject": "Application for {title} - {CANDIDATE_NAME}",
  "cover_letter": "...",
  "html_email_body": "..."
}}
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional hiring consultant. Respond ONLY with valid, raw JSON."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.4
        }

        try:
            endpoint = f"{self.base_url}/chat/completions"
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=45)
            
            if response.status_code == 200:
                msg = response.json()["choices"][0]["message"]
                raw_text = msg.get("content") or msg.get("reasoning") or ""
                return self._parse_json_response(raw_text, title, company)
            else:
                print(f"[-] Kilo Code API error {response.status_code}: {response.text}")
                return self._fallback_template(title, company, description)
        except Exception as e:
            print(f"[!] Exception calling Kilo Code LLM: {e}")
            return self._fallback_template(title, company, description)

    def _parse_json_response(self, text: str, title: str, company: str) -> Dict[str, Any]:
        clean = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
        clean = re.sub(r"^```\s*$", "", clean, flags=re.MULTILINE).strip()
        try:
            data = json.loads(clean)
            return data
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\})", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return self._fallback_template(title, company, clean)

    def _fallback_template(self, title: str, company: str, details: str) -> Dict[str, Any]:
        subject = f"Application for {title} - {CANDIDATE_NAME}"
        cover_letter = f"""Dear Hiring Team at {company},

I am writing to express my enthusiastic interest in the {title} position. With over 3 years of hands-on experience developing production mobile applications with Flutter, modern web interfaces with React, and architecting intelligent AI agent systems in Python, I am confident in my ability to deliver immediate value to your team.

My background spans delivering full-cycle software solutions, building high-performance cross-platform apps, and engineering agentic workflows. I thrive in fast-paced environments where innovation, code quality, and user experience converge.

I would welcome the opportunity to discuss how my skill set and passion align with {company}'s goals. Thank you for your time and consideration.

Best regards,
{CANDIDATE_NAME}
"""
        html_body = f"""<p>Dear Hiring Team at {company},</p>

<p>I am writing to express my strong interest in the <strong>{title}</strong> position. With 3+ years of production experience shipping <strong>Flutter mobile applications, React/WebGL web systems</strong>, and <strong>AI agent architectures</strong>, I am excited about the opportunity to contribute to your engineering goals.</p>

<p><strong>Key Highlights:</strong></p>
<ul>
  <li><strong>3+ Years Production Experience:</strong> Published apps on Google Play Store & production web platforms.</li>
  <li><strong>Full-Stack & Mobile:</strong> Deep expertise in Flutter, Dart, React, WebGL, and Python backend microservices.</li>
  <li><strong>AI & Agentic Systems:</strong> Proven record designing autonomous LLM workflows and real-time data pipelines.</li>
  <li><strong>Portfolio:</strong> Available at <a href="{CANDIDATE_PORTFOLIO}">{CANDIDATE_PORTFOLIO}</a> | GitHub: <a href="{CANDIDATE_GITHUB}">{CANDIDATE_GITHUB}</a>.</li>
</ul>

<p>My resume is attached to this email. I would love to connect and discuss how my skills align with your open role.</p>

<p>Warm regards,<br>
<strong>{CANDIDATE_NAME}</strong><br>
Mobile: {CANDIDATE_PHONE}<br>
Email: {CANDIDATE_EMAIL}<br>
Portfolio: {CANDIDATE_PORTFOLIO}
</p>
"""
        return {
            "match_percentage": 78,
            "strengths": ["Flutter & Mobile Engineering", "AI Systems Architecture", "Fast Delivery"],
            "gaps": ["Company-specific proprietary stack"],
            "subject": subject,
            "cover_letter": cover_letter,
            "html_email_body": html_body
        }

    def generate_application(self, job: Dict[str, Any], resume_text: str = ""):
        if not resume_text:
            try:
                from resume_parser import ResumeParser
                resume_text = ResumeParser().get_text()
            except Exception:
                resume_text = ""
        analysis = self.process_job(job, resume_text, "")
        return analysis.get("cover_letter", ""), analysis.get("html_email_body", "")
