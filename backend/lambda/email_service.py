import os
import json
import base64
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'nsinghrajput30@gmail.com')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'dahiyamohit764@gmail.com')
SENDER_NAME = os.environ.get('SENDER_NAME', 'Cloud Attendance')
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')


def send_email(to_email, subject, body, attachment=None, filename=None):
    """Send email via Brevo API (HTTPS — works on Render; send to any address)."""
    api_key = BREVO_API_KEY
    if not api_key:
        print('❌ Email error: BREVO_API_KEY is not set', flush=True)
        return False

    payload = {
        'sender': {'name': SENDER_NAME, 'email': SENDER_EMAIL},
        'to': [{'email': to_email}],
        'subject': subject,
        'htmlContent': body,
    }

    if attachment is not None and filename:
        if isinstance(attachment, str):
            content = base64.b64encode(attachment.encode('utf-8')).decode('ascii')
        else:
            content = base64.b64encode(attachment).decode('ascii')
        payload['attachment'] = [{'content': content, 'name': filename}]

    try:
        req = urllib.request.Request(
            'https://api.brevo.com/v3/smtp/email',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'accept': 'application/json',
                'api-key': api_key,
                'Content-Type': 'application/json',
                'User-Agent': 'CloudAttendance/1.0',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201, 202):
                print(f'❌ Email error: Brevo returned status {resp.status}', flush=True)
                return False
        print(f'✅ Email sent to {to_email}', flush=True)
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        print(f'❌ Email error ({e.code}): {error_body}', flush=True)
        return False
    except Exception as e:
        print(f'❌ Email error: {e}', flush=True)
        return False
