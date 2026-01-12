import os.path
import re
import base64
from io import BytesIO
from pypdf import PdfReader

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dbConnection import connection

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# ---------- PDF helpers ----------

def extract_text_from_pdf_bytes(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_name_email(text):
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    email = email_match.group() if email_match else None

    first_line = text.strip().split("\n")[0][:50] if text else None
    name = first_line

    return name, email


# ---------- DB helpers ----------

def insert_cv_into_hana(conn, mail_id, name, email, attachment_bytes, status="NEW"):
    cursor = conn.cursor()
    sql = """
    INSERT INTO CV_Info (ID, NAME, EMAIL, ATTACHMENT, STATUS)
    VALUES (?, ?, ?, ?, ?)
    """
    cursor.execute(sql, (mail_id, name, email, attachment_bytes, status))
    conn.commit()


# ---------- Attachment processing ----------

def process_and_store_pdf(service, conn, msg_id, payload):
    if "parts" not in payload:
        return

    for part in payload["parts"]:
        filename = part.get("filename")
        body = part.get("body", {})

        if filename and filename.lower().endswith(".pdf") and "attachmentId" in body:
            att_id = body["attachmentId"]

            att = service.users().messages().attachments().get(
                userId="me",
                messageId=msg_id,
                id=att_id
            ).execute()

            pdf_bytes = base64.urlsafe_b64decode(att["data"])
            text = extract_text_from_pdf_bytes(pdf_bytes)
            name, email = extract_name_email(text)

            try:
                insert_cv_into_hana(
                    conn,
                    mail_id=email,
                    name=name,
                    email=email,
                    attachment_bytes=pdf_bytes,
                    status="NEW"
                )
                print(f"Stored CV from mail {msg_id}")

            except Exception as e:
                print(f"Could not insert {msg_id}: {e}")


# ---------- Gmail helpers ----------

def get_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    elif "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""


# ---------- Main ----------

def main():
    creds = None
    conn = connection.get_connection()

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

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
            print("No matching emails found.")
            conn.close()
            return

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

            print(f"\nFrom   : {from_}")
            print(f"Subject: {subject}")

            process_and_store_pdf(service, conn, msg_id, msg_data["payload"])
            print("-" * 60)

    except HttpError as error:
        print(f"An error occurred: {error}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

#nenen