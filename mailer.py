import os
import smtplib
import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional
from pathlib import Path

# Google OAuth imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import (
    GMAIL_SENDER_EMAIL,
    GMAIL_APP_PASSWORD,
    GMAIL_TOKEN_JSON,
    RESUME_PATH,
    DRY_RUN
)

class GmailSender:
    def __init__(
        self,
        sender_email: str = GMAIL_SENDER_EMAIL,
        app_password: str = GMAIL_APP_PASSWORD,
        token_path: Path = GMAIL_TOKEN_JSON,
        resume_path: Path = RESUME_PATH,
        dry_run: bool = DRY_RUN
    ):
        self.sender_email = sender_email
        self.app_password = app_password
        self.token_path = token_path
        self.resume_path = resume_path
        self.dry_run = dry_run
        self._oauth_service = None

    def _get_oauth_service(self):
        """Initializes Gmail API client using gmail_token.json if valid."""
        if self._oauth_service:
            return self._oauth_service

        if not self.token_path.exists():
            return None

        try:
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if scope allows sending
            scopes = data.get("scopes", [])
            has_send_scope = any("gmail.send" in s or "mail.google.com" in s for s in scopes)
            if not has_send_scope:
                return None

            creds = Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
                scopes=scopes
            )

            # Refresh token if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                data["token"] = creds.token
                with open(self.token_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

            self._oauth_service = build("gmail", "v1", credentials=creds)
            return self._oauth_service
        except Exception as e:
            print(f"[-] OAuth initialization failed: {e}")
            return None

    def send_application(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text: Optional[str] = None
    ) -> bool:
        if self.dry_run:
            print("\n" + "="*60)
            print(" [DRY-RUN MODE] Email Prepared (NOT SENT)")
            print(f" To: {to_email}")
            print(f" Subject: {subject}")
            print(f" Attached: {self.resume_path.name if self.resume_path.exists() else 'None'}")
            print(" Body Preview (first 200 chars):")
            print(f" {html_content[:200]}...")
            print("="*60 + "\n")
            return True

        # Build MIME Message
        msg = MIMEMultipart("mixed")
        msg["From"] = f"Ahsan Ali <{self.sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        body_part = MIMEMultipart("alternative")
        if plain_text:
            body_part.attach(MIMEText(plain_text, "plain", "utf-8"))
        body_part.attach(MIMEText(html_content, "html", "utf-8"))
        msg.attach(body_part)

        # Attach Resume PDF
        if self.resume_path.exists():
            try:
                with open(self.resume_path, "rb") as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=self.resume_path.name
                    )
                    msg.attach(pdf_attachment)
            except Exception as e:
                print(f"[-] Failed attaching resume: {e}")

        # Method 1: Try Gmail REST API (OAuth)
        service = self._get_oauth_service()
        if service:
            try:
                raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                service.users().messages().send(
                    userId="me",
                    body={"raw": raw_message}
                ).execute()
                print(f"[+] [Gmail API OAuth] Sent application to: {to_email}")
                return True
            except Exception as e:
                print(f"[-] Gmail API send failed: {e}, attempting SMTP fallback...")

        # Method 2: Try Gmail SMTP SSL (App Password)
        clean_app_password = self.app_password.replace(" ", "").strip() if self.app_password else ""
        if clean_app_password:
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(self.sender_email, clean_app_password)
                    server.send_message(msg)
                print(f"[+] [Gmail SMTP SSL] Sent application to: {to_email}")
                return True
            except Exception as e:
                print(f"[-] SMTP send failed to {to_email}: {e}")
                return False

        print("[!] Cannot send email: No valid Gmail API token with 'gmail.send' scope and no GMAIL_APP_PASSWORD found.")
        return False
