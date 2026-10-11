import os
import sys
import threading
import sqlite3
from pathlib import Path

# Ensure unbuffered output on Windows
sys.stdout.reconfigure(line_buffering=True)
import telebot
from telebot import types

from config import (
    TELEGRAM_BOT_TOKEN,
    BASE_DIR,
    DB_PATH,
    CSV_PATH,
    RESUME_PATH,
    CANDIDATE_NAME,
    CANDIDATE_EMAIL,
    TARGET_ROLES
)
from scraper import LinkedInScraper
from scorer import JobScorer
from email_finder import RecruiterEmailFinder
from agent import AIAgent
from mailer import GmailSender
from storage import ApplicationStorage
from resume_parser import ResumeParser

if not TELEGRAM_BOT_TOKEN:
    print("[!] TELEGRAM_BOT_TOKEN not found in .env. Exiting.")
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# Lock to avoid concurrent pipeline clashes
pipeline_lock = threading.Lock()

def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🚀 Live Apply: Flutter (3)", callback_data="apply_flutter")
    b2 = types.InlineKeyboardButton("🔍 Preview: Flutter (3)", callback_data="preview_flutter")
    b3 = types.InlineKeyboardButton("🚀 Live Apply: AI Engineer (3)", callback_data="apply_ai")
    b4 = types.InlineKeyboardButton("🔍 Preview: AI Engineer (3)", callback_data="preview_ai")
    b5 = types.InlineKeyboardButton("🚀 Live Apply: Mobile Dev (3)", callback_data="apply_mobile")
    b6 = types.InlineKeyboardButton("🚀 Live Apply: WebGL (3)", callback_data="apply_webgl")
    b7 = types.InlineKeyboardButton("📊 Stats & History", callback_data="cmd_stats")
    b8 = types.InlineKeyboardButton("🏢 Top YC Startups", callback_data="cmd_yc")
    b9 = types.InlineKeyboardButton("📥 Download CSV Tracker", callback_data="cmd_csv")
    b10 = types.InlineKeyboardButton("🧪 Test Gmail Connection", callback_data="cmd_testmail")
    markup.add(b1, b2, b3, b4, b5, b6, b7, b8, b9, b10)
    return markup

@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    welcome_text = (
        f"👋 <b>Welcome {CANDIDATE_NAME}!</b>\n\n"
        "🤖 <b>AI Job Hunting & Auto-Applicant Assistant</b> is ready.\n\n"
        "<b>What I can do for you:</b>\n"
        "• 🔍 Scan LinkedIn, WeWorkRemotely & RemoteOK for fresh 24h jobs\n"
        "• 🎯 Match roles specifically for Flutter, Mobile, AI & WebGL\n"
        "• ✉️ Find recruiter emails & write tailored AI pitches\n"
        "• 🚀 Send cold emails with your PDF resume attached\n"
        "• 🏢 Discover Y Combinator jobs & tailor ATS resumes\n\n"
        "<b>Quick Commands:</b>\n"
        "• <code>/apply &lt;role&gt; [limit]</code> - Run live application\n"
        "• <code>/preview &lt;role&gt; [limit]</code> - Dry-run test\n"
        "• <code>/stats</code> - View applications summary\n"
        "• <code>/yc</code> - Latest Y Combinator roles\n"
        "• <code>/csv</code> - Download application history\n"
        "• <code>/testmail</code> - Verify Gmail delivery\n\n"
        "<i>Or simply tap an action button below:</i>"
    )
    bot.reply_to(message, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=["stats"])
def handle_stats(message):
    send_stats(message.chat.id)

def send_stats(chat_id):
    try:
        storage = ApplicationStorage()
        stats = storage.get_stats()
        text = (
            "📊 <b>Application Tracking Summary:</b>\n\n"
            f"• <b>Total Database Records:</b> {stats.get('total_applications', 0)}\n"
            f"• <b>Live Emails Sent:</b> {stats.get('sent', 0)}\n"
            f"• <b>Dry-Run Previews:</b> {stats.get('dry_run_previews', 0)}\n"
            f"• <b>Failed / Unresolved:</b> {stats.get('failed', 0)}\n\n"
            "Use <code>/csv</code> to download the full detailed spreadsheet."
        )
        bot.send_message(chat_id, text)
    except Exception as e:
        bot.send_message(chat_id, f"[-] Error retrieving stats: {e}")

@bot.message_handler(commands=["csv"])
def handle_csv(message):
    send_csv(message.chat.id)

def send_csv(chat_id):
    if CSV_PATH.exists() and CSV_PATH.stat().st_size > 50:
        with open(CSV_PATH, "rb") as f:
            bot.send_document(chat_id, f, caption="📄 <b>Your Live Job Applications Tracker</b>")
    else:
        bot.send_message(chat_id, "ℹ️ No application history in CSV yet. Run an apply or preview command first!")

@bot.message_handler(commands=["testmail"])
def handle_testmail(message):
    send_testmail(message.chat.id)

def send_testmail(chat_id):
    bot.send_message(chat_id, "⏳ <i>Testing Gmail connection & sending resume to your inbox...</i>")
    sender = GmailSender(dry_run=False)
    success = sender.send_application(
        to_email=CANDIDATE_EMAIL,
        subject="Telegram Bot Test: AI Job Application Connection",
        html_content="<p>Hi Ahsan,</p><p>This test email was triggered directly from your <b>Telegram Bot</b>. Your PDF resume is attached!</p>",
        plain_text="Telegram Bot Gmail Test is working!"
    )
    if success:
        bot.send_message(chat_id, f"✅ <b>Success!</b> Test email and resume delivered to <code>{CANDIDATE_EMAIL}</code>.")
    else:
        bot.send_message(chat_id, "❌ <b>Delivery Failed.</b> Check server logs or app password.")

@bot.message_handler(commands=["yc"])
def handle_yc(message):
    send_yc(message.chat.id)

def send_yc(chat_id):
    yc_file = BASE_DIR / "codebase" / "yc_jobs.txt"
    if not yc_file.exists():
        bot.send_message(chat_id, "⏳ Running YC startup discovery...")
        try:
            import subprocess
            subprocess.run([sys.executable, str(BASE_DIR / "codebase" / "yc_discover.py")], check=True)
        except Exception as e:
            bot.send_message(chat_id, f"[-] YC discovery error: {e}")
            return

    if yc_file.exists():
        with open(yc_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        preview = lines[:8]
        links_text = "\n".join([f"• <code>{l}</code>" for l in preview])
        text = (
            f"🏢 <b>Discovered {len(lines)} Y Combinator Startups:</b>\n\n"
            f"{links_text}\n\n"
            "<i>To tailor an ATS resume for any of these, send:</i>\n"
            "<code>/tailor &lt;URL&gt;</code>"
        )
        bot.send_message(chat_id, text)
    else:
        bot.send_message(chat_id, "[-] Could not retrieve YC jobs.")

@bot.message_handler(commands=["preview"])
def handle_preview_cmd(message):
    args = message.text.split()[1:]
    role = args[0] if len(args) > 0 else "Flutter Developer"
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
    run_pipeline_worker(message.chat.id, role, limit, dry_run=True)

@bot.message_handler(commands=["apply"])
def handle_apply_cmd(message):
    args = message.text.split()[1:]
    role = args[0] if len(args) > 0 else "Flutter Developer"
    limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
    run_pipeline_worker(message.chat.id, role, limit, dry_run=False)

@bot.message_handler(commands=["tailor"])
def handle_tailor(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/tailor &lt;job_url&gt;</code>")
        return
    job_url = args[1].strip()
    threading.Thread(target=tailor_worker, args=(message.chat.id, job_url)).start()

def tailor_worker(chat_id, job_url):
    bot.send_message(chat_id, f"⏳ <b>Analyzing job & generating tailored ATS resume...</b>\n<code>{job_url}</code>")
    try:
        from codebase.tailor import tailor_resume_for_job
        pdf_path, cover_letter, tokens = tailor_resume_for_job(job_url)
        if pdf_path and Path(pdf_path).exists():
            bot.send_message(chat_id, f"✅ <b>ATS Tailoring Complete!</b>\n\n<b>Cover Letter Preview:</b>\n{cover_letter[:400]}...")
            with open(pdf_path, "rb") as f:
                bot.send_document(chat_id, f, caption=f"📄 Tailored Resume for {job_url[:40]}...")
        else:
            bot.send_message(chat_id, "[-] Failed to generate tailored PDF. Check URL accessibility.")
    except Exception as e:
        bot.send_message(chat_id, f"[-] Error in tailor pipeline: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data

    bot.answer_callback_query(call.id)

    if data == "cmd_stats":
        send_stats(chat_id)
    elif data == "cmd_csv":
        send_csv(chat_id)
    elif data == "cmd_yc":
        send_yc(chat_id)
    elif data == "cmd_testmail":
        send_testmail(chat_id)
    elif data == "apply_flutter":
        run_pipeline_worker(chat_id, "Flutter Developer", 3, dry_run=False)
    elif data == "preview_flutter":
        run_pipeline_worker(chat_id, "Flutter Developer", 3, dry_run=True)
    elif data == "apply_ai":
        run_pipeline_worker(chat_id, "AI Engineer", 3, dry_run=False)
    elif data == "preview_ai":
        run_pipeline_worker(chat_id, "AI Engineer", 3, dry_run=True)
    elif data == "apply_mobile":
        run_pipeline_worker(chat_id, "Mobile App Developer", 3, dry_run=False)
    elif data == "apply_webgl":
        run_pipeline_worker(chat_id, "WebGL Developer", 3, dry_run=False)

def run_pipeline_worker(chat_id, role, limit, dry_run):
    def task():
        if not pipeline_lock.acquire(blocking=False):
            bot.send_message(chat_id, "⚠️ <i>A job application task is already running in background. Please wait for it to finish!</i>")
            return

        mode_str = "🔍 [PREVIEW MODE]" if dry_run else "🚀 [LIVE APPLICATION MODE]"
        bot.send_message(chat_id, f"{mode_str}\nSearching <b>{role}</b> openings (Limit: {limit})...\n<i>Please wait 30-60 seconds.</i>")

        try:
            # 1. Scrape
            scraper = LinkedInScraper()
            raw_jobs = scraper.scrape_all_sources(keywords=role, count_per_source=limit)
            if not raw_jobs:
                raw_jobs = scraper.load_cached_or_sample_jobs()

            bot.send_message(chat_id, f"📥 Found <b>{len(raw_jobs)}</b> listings across LinkedIn, WeWorkRemotely & RemoteOK.")

            # 2. Filter & Score
            storage = ApplicationStorage()
            unprocessed = []
            for j in raw_jobs:
                jid = str(j.get("id") or j.get("trackingId") or "")
                title = j.get("title", "")
                company = j.get("companyName", "")
                if not storage.is_applied(jid, title, company):
                    unprocessed.append(j)

            scorer = JobScorer()
            scored_jobs = scorer.rank_jobs(unprocessed)
            top_jobs = scored_jobs[:limit]

            if not top_jobs:
                bot.send_message(chat_id, "ℹ️ No new unapplied jobs matched your target skills right now.")
                return

            bot.send_message(chat_id, f"🎯 <b>{len(top_jobs)}</b> top jobs matched your profile. Generating personalized pitches...")

            # 3. Process
            resume_parser = ResumeParser()
            try:
                resume_text = resume_parser.get_text()
            except Exception:
                resume_text = ""

            email_finder = RecruiterEmailFinder()
            agent = AIAgent()
            mailer = GmailSender(dry_run=dry_run)

            success_count = 0
            for idx, job in enumerate(top_jobs, 1):
                company = job.get("companyName", "Tech Company")
                title = job.get("title", role)
                url = job.get("url") or job.get("job_url", "")
                jid = str(job.get("id") or job.get("trackingId") or "")

                target_email, conf = email_finder.find_recruiter_email(job)

                # LLM pitch
                analysis = agent.process_job(job, resume_text, target_email)
                match_score = analysis.get("match_percentage", 85)
                subject = analysis.get("subject", f"Application for {title} — Ahsan Ali")
                cover_letter = analysis.get("cover_letter", "")
                html_body = analysis.get("html_email_body", "")

                # If legitimate, verified recruiter email exists -> Send email
                if target_email and conf in ("high", "medium", "heuristic_mx_verified"):
                    sent = mailer.send_application(
                        to_email=target_email,
                        subject=subject,
                        html_content=html_body,
                        plain_text=cover_letter
                    )
                    status = "sent" if (sent and not dry_run) else ("dry_run_preview" if dry_run else "failed")
                    if sent:
                        success_count += 1

                    if sent and not dry_run:
                        status_header = f"🚀 <b>SUCCESSFULLY APPLIED VIA EMAIL! ({idx}/{len(top_jobs)})</b>"
                        status_note = f"📨 <i>Cold pitch email + AhsanAli_Resume_v5.pdf delivered to <code>{target_email}</code>!</i>"
                    else:
                        status_header = f"👁️ <b>EMAIL PREVIEW ({idx}/{len(top_jobs)})</b>"
                        status_note = f"📝 <i>Dry-run preview for <code>{target_email}</code> (no email sent).</i>"

                    display_email = f"<code>{target_email}</code> (Verified)"
                else:
                    # ATS Web Portal application (e.g. Ashby, Greenhouse, Workable)
                    sent = False
                    status = "portal_link_ready"
                    status_header = f"📋 <b>ATS WEB PORTAL OPENING ({idx}/{len(top_jobs)})</b>"
                    status_note = (
                        "ℹ️ <i>This company manages hiring exclusively through an ATS web portal (Ashby/Workable/Greenhouse). "
                        "Blind email was safely bypassed to prevent delivery bounces.<br>"
                        "👉 Click the job link below to apply, or use <code>/tailor &lt;URL&gt;</code> for an ATS tailored resume!</i>"
                    )
                    display_email = "<i>Official ATS Portal (Form Submission)</i>"

                storage.record_application({
                    "job_id": jid,
                    "title": title,
                    "company": company,
                    "location": job.get("location", ""),
                    "job_url": url,
                    "target_email": target_email or "ATS Portal",
                    "email_confidence": conf,
                    "match_percentage": match_score,
                    "status": status,
                    "cover_letter": cover_letter
                })

                bot.send_message(
                    chat_id,
                    f"{status_header}\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"💼 <b>Role:</b> {title}\n"
                    f"🎯 <b>Match Score:</b> {match_score}%\n"
                    f"✉️ <b>Destination:</b> {display_email}\n"
                    f"📎 <b>Resume:</b> <code>AhsanAli_Resume_v5.pdf</code>\n"
                    f"🔗 <b>Listing / Portal:</b> <a href='{url}'>Open Job Application</a>\n\n"
                    f"{status_note}"
                )

            final_msg = (
                f"🎉 <b>Batch Complete!</b>\n\n"
                f"• Jobs Scanned & Analyzed: {len(top_jobs)}\n"
                f"• Successfully Applied & Emailed: <b>{success_count}</b>\n"
                f"• Stored in Database & CSV: <b>Yes</b>\n\n"
                f"Use <code>/csv</code> to download your updated tracking spreadsheet, or <code>/stats</code> to see overall progress."
            )
            bot.send_message(chat_id, final_msg)

        except Exception as e:
            bot.send_message(chat_id, f"[-] Error running pipeline: {e}")
        finally:
            pipeline_lock.release()

    threading.Thread(target=task, daemon=True).start()

def main():
    print("=" * 60)
    print("   AI JOB FINDER TELEGRAM BOT SERVICE STARTED")
    print(f"   Candidate: {CANDIDATE_NAME} ({CANDIDATE_EMAIL})")
    print("   Bot Username: @AIJobLeads_bot")
    print("=" * 60)
    print("[+] Polling for Telegram commands... (Press Ctrl+C to stop)")
    
    bot.infinity_polling(timeout=20, long_polling_timeout=20)

if __name__ == "__main__":
    main()
