from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from collections import Counter
import time
import random
import logging
from googleapiclient.errors import HttpError
import socket
import os

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
def authenticate_gmail():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)
# ...existing code... 

def batch_callback(request_id, response, exception):
    if exception:
        logger.warning(f"Batch error for request {request_id}: {exception}")
    else:
        headers = response.get('payload', {}).get('headers', [])
        for h in headers:
            if h.get('name') == 'From':
                sender_counter[h.get('value')] += 1

CHECKPOINT_FILE = "checkpoint.json"


def _api_call_with_retries(func, max_retries=6, initial_delay=1.0):
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except HttpError as e:
            content = ''
            try:
                if getattr(e, 'content', None):
                    content = e.content.decode('utf-8', errors='ignore')
            except Exception:
                pass
            is_rate_limit = any(x in content for x in ('rateLimitExceeded', 'userRateLimitExceeded', 'quotaExceeded', 'rate limit exceeded'))
            retry_after = None
            if getattr(e, 'resp', None) is not None:
                retry_after = e.resp.get('retry-after')
            if is_rate_limit:
                wait = int(retry_after) if (retry_after and str(retry_after).isdigit()) else delay
                wait = wait + random.random()
                logger.warning("Rate limit hit. Sleeping %.1fs before retry %d/%d", wait, attempt, max_retries)
                if attempt == max_retries:
                    raise
                time.sleep(wait)
                delay *= 2
                continue
            else:
                raise
        except (socket.timeout, socket.error) as e:
            if attempt == max_retries:
                raise
            wait = delay + random.random()
            logger.warning("Socket error: %s. Sleeping %.1fs before retry %d/%d", e, wait, attempt, max_retries)
            time.sleep(wait)
            delay *= 2
    raise RuntimeError("Exceeded retries")


def get_senders_batch(service, max_emails=3000):
    global sender_counter
    sender_counter = Counter()

    page_token = None
    total = 0

    while True:
        # fetch list with retries
        response = _api_call_with_retries(lambda: service.users().messages().list(
            userId='me',
            maxResults=100,
            pageToken=page_token
        ).execute())

        messages = response.get('messages', [])
        if not messages:
            break

        batch = service.new_batch_http_request(callback=batch_callback)

        for msg in messages:
            batch.add(
                service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From']
                )
            )
            total += 1
            if total >= max_emails:
                break

        # execute batch with retries
        _api_call_with_retries(lambda: batch.execute())

        # small pause to avoid rapid queries
        time.sleep(0.25)

        if total >= max_emails:
            break

        page_token = response.get('nextPageToken')
        if not page_token:
            break

    return sender_counter



def save_to_text(counter, filename="gmail_sender_report.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Sender Email ID | Total Emails\n")
        f.write("-" * 40 + "\n")

        for sender, count in counter.most_common():
            f.write(f"{sender} → {count}\n")

def delete_noreply_emails(
    service,
    max_emails=50,
    log_file="deleted_noreply_emails.txt",
    max_retry_per_email=3,
    max_consecutive_failures=5
):
    print("Searching noreply emails...")
    query = 'from:(noreply OR no-reply OR no_reply)'
    page_token = None
    deleted = 0
    consecutive_failures = 0

    with open(log_file, "w", encoding="utf-8") as log:
        log.write("Deleted noreply emails\n")
        log.write("=" * 50 + "\n\n")

        while True:
            try:
                response = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=20,
                    pageToken=page_token
                ).execute()
            except HttpError:
                print("Quota hit while listing. Waiting 30 seconds...")
                time.sleep(30)
                continue

            messages = response.get('messages', [])
            if not messages:
                break

            for msg in messages:
                if deleted >= max_emails:
                    break

                retry_count = 0
                success = False

                while retry_count < max_retry_per_email:
                    try:
                        # Read metadata
                        msg_data = service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='metadata',
                            metadataHeaders=['From', 'Subject']
                        ).execute()

                        headers = msg_data['payload']['headers']
                        sender = subject = "Unknown"

                        for h in headers:
                            if h['name'] == 'From':
                                sender = h['value']
                            elif h['name'] == 'Subject':
                                subject = h['value']

                        print(f"Deleting → {sender} | {subject}")

                        # Delete (move to Trash)
                        service.users().messages().modify(
                            userId='me',
                            id=msg['id'],
                            body={'addLabelIds': ['TRASH']}
                        ).execute()

                        log.write(f"FROM: {sender}\n")
                        log.write(f"SUBJECT: {subject}\n")
                        log.write(f"MESSAGE ID: {msg['id']}\n")
                        log.write("-" * 40 + "\n")

                        success = True
                        deleted += 1
                        consecutive_failures = 0
                        time.sleep(3)  # pacing
                        break

                    except HttpError:
                        retry_count += 1
                        print(f"Retry {retry_count}/{max_retry_per_email} failed. Waiting 15s...")
                        time.sleep(15)

                if not success:
                    consecutive_failures += 1
                    print("Skipping email after retries.")

                # 🔴 HARD BREAK CONDITION
                if consecutive_failures >= max_consecutive_failures:
                    print(
                        f"Stopping: {consecutive_failures} consecutive failures reached."
                    )
                    return

            page_token = response.get('nextPageToken')
            if not page_token:
                break

    print(f"\nMoved {deleted} noreply emails to Trash.")
    print(f"Details saved in: {log_file}")

def main():
    service = authenticate_gmail()

    print("Reading emails efficiently (batch mode)...")
    counter = get_senders_batch(service, max_emails=3000)

    with open("gmail_sender_report.txt", "w", encoding="utf-8") as f:
        for sender, count in counter.most_common():
            f.write(f"{sender} → {count}\n")

    print("Done. Results saved to gmail_sender_report.txt")
    print ("Deleting noreply emails (limited)...")

        # DELETE noreply emails (LIMITED)
    delete_noreply_emails(service, max_emails=10)
    print("Noreply email deletion completed.")

if __name__ == '__main__':
    main()
