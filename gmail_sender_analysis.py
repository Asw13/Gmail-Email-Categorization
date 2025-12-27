from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from collections import Counter
import time
from googleapiclient.errors import HttpError
import socket
import os
import base64
import email
import json

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
from collections import Counter
from googleapiclient.errors import HttpError

def batch_callback(request_id, response, exception):
    if exception:
        print(f"Batch error for request {request_id}")
    else:
        headers = response['payload']['headers']
        for h in headers:
            if h['name'] == 'From':
                sender_counter[h['value']] += 1

CHECKPOINT_FILE = "checkpoint.json"

def get_senders_batch(service, max_emails=9500):
    global sender_counter
    sender_counter = Counter()

    page_token = None
    total = 0

    while True:
        response = service.users().messages().list(
            userId='me',
            maxResults=100,
            pageToken=page_token
        ).execute()

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

        batch.execute()

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


def main():
    service = authenticate_gmail()

    print("Reading emails efficiently (batch mode)...")
    counter = get_senders_batch(service, max_emails=9500)

    with open("gmail_sender_report.txt", "w", encoding="utf-8") as f:
        for sender, count in counter.most_common():
            f.write(f"{sender} → {count}\n")

    print("Done. Results saved to gmail_sender_report.txt")

if __name__ == '__main__':
    main()
