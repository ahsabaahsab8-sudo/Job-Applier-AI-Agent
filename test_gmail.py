from mailer import GmailSender
from config import GMAIL_SENDER_EMAIL

def test_gmail():
    print("=" * 60)
    print("          GMAIL DIRECT SENDER TEST (OAUTH & SMTP)")
    print("=" * 60)
    print(f"Sender Target: {GMAIL_SENDER_EMAIL}")

    sender = GmailSender(dry_run=False)
    
    success = sender.send_application(
        to_email=GMAIL_SENDER_EMAIL,
        subject="Test: AI Job Finder Direct Gmail Delivery",
        html_content="<p>Hi Ahsan,</p><p>Your Gmail connection is working! Your PDF resume is attached.</p>",
        plain_text="Your Gmail connection is working!"
    )

    if success:
        print(f"\n[+] SUCCESS! Check your inbox ({GMAIL_SENDER_EMAIL}) for the test email with your resume.")
    else:
        print("\n[-] Could not send. See instructions above.")
    print("=" * 60)

if __name__ == "__main__":
    test_gmail()
