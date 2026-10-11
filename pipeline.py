import time
import argparse
from typing import Optional
from config import DAILY_JOB_LIMIT, DRY_RUN, TARGET_ROLES
from resume_parser import ResumeParser
from scraper import LinkedInScraper
from scorer import JobScorer
from email_finder import RecruiterEmailFinder
from agent import AIAgent
from mailer import GmailSender
from storage import ApplicationStorage

def run_pipeline(
    keywords: Optional[str] = None,
    limit: int = DAILY_JOB_LIMIT,
    dry_run: bool = DRY_RUN,
    use_sample_data: bool = False
):
    print("=" * 70)
    print("   AI JOB FINDER & AUTO-APPLICANT (PYTHON CLONE)")
    print(f"   Mode: {'[DRY RUN - PREVIEW ONLY]' if dry_run else '[LIVE APPLICATION]'}")
    print(f"   Target Limit: {limit} jobs")
    print("=" * 70)

    # 1. Load Resume
    print("\n[Step 1/6] Loading Candidate Resume...")
    resume_parser = ResumeParser()
    try:
        resume_text = resume_parser.get_text()
        print(f"[+] Loaded resume: {len(resume_text)} characters.")
    except Exception as e:
        print(f"[!] Error loading resume: {e}")
        return

    # 2. Fetch Jobs via Multi-Source Scraper (or local sample)
    print("\n[Step 2/6] Aggregating Jobs Across Platforms (LinkedIn, WeWorkRemotely, RemoteOK)...")
    scraper = LinkedInScraper()
    query = keywords or TARGET_ROLES[0] if TARGET_ROLES else "Flutter Developer"
    
    if use_sample_data:
        raw_jobs = scraper.load_cached_or_sample_jobs()
    else:
        raw_jobs = scraper.scrape_all_sources(keywords=query, count_per_source=limit)
        if not raw_jobs:
            print("[*] Remote feeds returned 0 items, falling back to local sample jobs...")
            raw_jobs = scraper.load_cached_or_sample_jobs()

    if not raw_jobs:
        print("[-] No jobs found to process. Exiting.")
        return

    print(f"[+] Total listings collected across all platforms: {len(raw_jobs)}")

    # 3. Filter Out Already Applied Jobs & Strict Skill Scoring
    print("\n[Step 3/6] Applying Strict Skill Filter & Scoring (Flutter, Mobile, AI, WebGL, React)...")
    storage = ApplicationStorage()
    unprocessed_jobs = []
    
    for job in raw_jobs:
        job_id = str(job.get("id") or job.get("trackingId") or "")
        title = job.get("title") or "Unknown"
        company = job.get("companyName") or job.get("company") or "Unknown"
        
        if storage.is_already_processed(job_id, title, company):
            continue
        unprocessed_jobs.append(job)

    if not unprocessed_jobs:
        print("[*] All retrieved jobs have already been applied to or processed.")
        return

    scorer = JobScorer()
    top_jobs = scorer.rank_and_filter(unprocessed_jobs, top_n=limit, strict_relevance=True)
    print(f"[+] Selected top {len(top_jobs)} highest-ranking jobs.")

    # 4. Initialize Subsystems
    email_finder = RecruiterEmailFinder()
    agent = AIAgent()
    mailer = GmailSender(dry_run=dry_run)

    # 5. Process & Apply to Each Job
    print("\n[Step 4/6] Processing Each Job with AI Agent & Finding Emails...")
    success_count = 0

    for idx, job in enumerate(top_jobs, 1):
        title = job.get("title", "Position")
        company = job.get("companyName") or job.get("company") or "Company"
        job_url = job.get("link") or job.get("applyUrl") or ""
        job_id = str(job.get("id") or f"job_{idx}")

        platform = job.get("source_platform", "Web")
        print(f"\n--- Job {idx}/{len(top_jobs)}: [{platform}] {title} @ {company} (Score: {job.get('calculated_score', 0)}) ---")

        # Discover recruiter email
        email_info = email_finder.find_email(job)
        target_email = email_info.get("email")
        confidence = email_info.get("confidence", "low")
        print(f"[*] Recruiter Email: {target_email} (Confidence: {confidence})")

        # Generate personalized application via Kilo Code free LLM
        print("[*] Generating tailored cover letter with Kilo Code AI...")
        analysis = agent.process_job(job, resume_text, target_email)

        match_score = analysis.get("match_percentage", 80)
        subject = analysis.get("subject", f"Application for {title} - Ahsan Ali")
        cover_letter = analysis.get("cover_letter", "")
        html_body = analysis.get("html_email_body", "")

        print(f"[+] Match Rating: {match_score}% | Strengths: {', '.join(analysis.get('strengths', [])[:2])}")

        # Send Email only if verified address exists (avoid bounces)
        if target_email and confidence in ("high", "medium", "heuristic_mx_verified"):
            sent = mailer.send_application(
                to_email=target_email,
                subject=subject,
                html_content=html_body,
                plain_text=cover_letter
            )
            status = "sent" if (sent and not dry_run) else ("dry_run_preview" if dry_run else "failed")
            if sent:
                success_count += 1
        else:
            sent = False
            status = "portal_link_ready"
            target_email = "ATS Portal / Form Only"
            print(f"[!] Company uses an ATS portal / web application form. Blind email skipped to protect Gmail sender score.")
            print(f"    Apply directly: {job_url}")

        # Record in SQLite and CSV
        storage.record_application({
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": job.get("location", ""),
            "job_url": job_url,
            "target_email": target_email,
            "email_confidence": confidence,
            "match_percentage": match_score,
            "status": status,
            "cover_letter": cover_letter
        })

        # Gentle throttling between jobs (only sleep if live sending)
        if not dry_run and idx < len(top_jobs):
            print("[*] Throttling for 15 seconds to maintain sender reputation...")
            time.sleep(15)

    print("\n" + "=" * 70)
    print(f"[+] Pipeline complete! Processed: {len(top_jobs)} | Applications Prepared/Sent: {success_count}")
    print(f"[+] Results exported to: applied_jobs.csv and applied_jobs.db")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Job Finder & Auto-Applicant")
    parser.add_argument("--keywords", type=str, default=None, help="Job title / search query (e.g. 'Flutter Developer')")
    parser.add_argument("--limit", type=int, default=5, help="Number of jobs to process (default 5 for quick test)")
    parser.add_argument("--live", action="store_true", help="Enable live sending mode (disables dry-run)")
    parser.add_argument("--sample", action="store_true", help="Use local sample data for testing without Apify credits")
    
    args = parser.parse_args()
    run_pipeline(
        keywords=args.keywords,
        limit=args.limit,
        dry_run=not args.live,
        use_sample_data=args.sample
    )
