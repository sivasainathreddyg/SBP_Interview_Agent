import os.path
import base64
from pypdf import PdfReader
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    elif "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""

def save_attachments(service, msg_id, payload, save_dir="attachments"):
    import os

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    if "parts" not in payload:
        return

    for part in payload["parts"]:
        filename = part.get("filename")
        body = part.get("body", {})

        if filename and "attachmentId" in body:
            att_id = body["attachmentId"]

            att = service.users().messages().attachments().get(
                userId="me",
                messageId=msg_id,
                id=att_id
            ).execute()

            data = att["data"]
            file_data = base64.urlsafe_b64decode(data)

            path = os.path.join(save_dir, filename)
            with open(path, "wb") as f:
                f.write(file_data)

            print(f"Saved attachment: {path}")

            # If it's a PDF, extract text
            # if filename.lower().endswith(".pdf"):
            #     text = extract_text_from_pdf(path)
            #     print(f"Extracted text from {filename}:\n{text[:1000]}")




def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def main():
    creds = None

    # Load token if exists
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Login if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)

        results = service.users().messages().list(
            userId="me",
            labelIds=["INBOX"],
            q='subject:"Job Application"',
            maxResults=5
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            print("No messages found in INBOX.")
            return

        print("\nLatest emails in INBOX:\n")

        for msg in messages:
            msg_id = msg["id"]
            msg_data = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()

            headers = msg_data["payload"]["headers"]
            subject = from_ = None

            for h in headers:
                if h["name"] == "Subject":
                    subject = h["value"]
                if h["name"] == "From":
                    from_ = h["value"]

            snippet = msg_data.get("snippet", "")
            body = get_body(msg_data["payload"])

            print(f"From   : {from_}")
            print(f"Subject: {subject}")
            print(f"Snippet: {snippet}")

            save_attachments(service, msg_id, msg_data["payload"])

            print("-" * 60)


    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()

    # new
