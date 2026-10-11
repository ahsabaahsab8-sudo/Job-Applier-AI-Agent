from typing import List, Dict, Any
from config import TARGET_KEYWORDS

class JobScorer:
    def __init__(self, target_keywords: List[str] = None):
        self.target_keywords = [k.lower() for k in (target_keywords or TARGET_KEYWORDS)]

    def is_fully_remote(self, job: Dict[str, Any]) -> bool:
        """
        Guarantees the job is 100% remote and NOT on-site, hybrid, or restricted to US citizens/visas.
        """
        location = (job.get("location") or "").lower()
        title = (job.get("title") or "").lower()
        desc = (job.get("descriptionText") or job.get("descriptionHtml") or job.get("description") or "").lower()
        combined = f"{location} {title} {desc}"

        # 1. Strictly reject on-site, in-office, or hybrid requirements
        if any(term in location for term in ["on-site", "onsite", "in-office", "hybrid"]):
            if "remote" not in location:
                return False

        # 2. Reject US citizen or US visa-restricted jobs (incompatible with international remote)
        us_visa_restrictions = [
            "us citizen only", "us citizenship required", "u.s. citizen only",
            "us visa only", "no visa sponsorship", "cannot sponsor",
            "authorized to work in the us only", "must be authorized to work in the united states without sponsorship",
            "must be located in the united states", "must reside in the us", "us only", "usa only"
        ]
        if any(res in combined for res in us_visa_restrictions):
            return False

        # 3. Positively identify remote status
        platform = job.get("source_platform", "")
        if platform in ("WeWorkRemotely", "RemoteOK"):
            # Already remote platforms by design
            return True

        remote_keywords = [
            "remote", "anywhere", "worldwide", "global", "telecommute",
            "work from home", "distributed"
        ]
        return any(kw in location or kw in title or kw in desc for kw in remote_keywords)

    def is_relevant_role(self, job: Dict[str, Any]) -> bool:
        """
        Guarantees we only consider jobs that are:
        1. Fully Remote (no on-site, no US-only visa restrictions)
        2. Match Ahsan's core skills: Flutter, Mobile, Dart, AI, LLM, WebGL, 3D, React, Python.
        """
        if not self.is_fully_remote(job):
            return False

        title = (job.get("title") or "").lower()
        desc = (job.get("descriptionText") or job.get("descriptionHtml") or job.get("description") or "").lower()
        
        # Immediate match if target skill is in title
        for kw in self.target_keywords:
            if kw in title:
                return True

        # Secondary match if multiple target skills exist in job description
        desc_matches = sum(1 for kw in self.target_keywords if kw in desc)
        return desc_matches >= 2

    def score_job(self, job: Dict[str, Any]) -> int:
        title = (job.get("title") or "").lower()
        desc = (job.get("descriptionText") or job.get("descriptionHtml") or job.get("description") or "")
        desc_lower = desc.lower()

        # Reject completely unrelated roles
        if not self.is_relevant_role(job):
            return 0

        score = 0

        # 1. Title direct match boost (+30 pts)
        for kw in ["flutter", "mobile", "ai", "webgl", "threejs", "3d", "react"]:
            if kw in title:
                score += 30
                break

        # 2. Company information availability (+10 pts)
        if job.get("companyName") or job.get("company"):
            score += 10

        # 3. Description completeness (+15 pts)
        if len(desc) > 100:
            score += 15

        # 4. Location availability (+5 pts)
        if job.get("location"):
            score += 5

        # 5. Salary information (+8 pts)
        salary = job.get("salary") or job.get("salaryInfo")
        if salary:
            if isinstance(salary, list) and any(s for s in salary if str(s).strip()):
                score += 8
            elif isinstance(salary, str) and salary.strip():
                score += 8

        # 6. Low applicant count (+10 for < 10, +5 for < 50)
        applicants = job.get("applicantsCount") or job.get("applicants")
        if applicants:
            try:
                count = int(applicants)
                if count < 10:
                    score += 10
                elif count < 50:
                    score += 5
            except (ValueError, TypeError):
                pass

        # 7. Additional keyword density boost (+15 pts max)
        keyword_hits = sum(1 for kw in self.target_keywords if kw in desc_lower)
        score += min(keyword_hits * 3, 15)

        return score

    def rank_and_filter(self, jobs: List[Dict[str, Any]], top_n: int = 100, strict_relevance: bool = True) -> List[Dict[str, Any]]:
        scored = []
        for job in jobs:
            calculated = self.score_job(job)
            if strict_relevance and calculated <= 0:
                continue
            item = dict(job)
            item["calculated_score"] = calculated
            scored.append(item)

        # Sort descending by calculated score
        scored.sort(key=lambda x: x.get("calculated_score", 0), reverse=True)
        return scored[:top_n]

    def rank_jobs(self, jobs: List[Dict[str, Any]], top_n: int = 100, strict_relevance: bool = True) -> List[Dict[str, Any]]:
        return self.rank_and_filter(jobs, top_n=top_n, strict_relevance=strict_relevance)
