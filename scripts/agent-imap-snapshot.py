#!/usr/bin/env python3
"""Read a bounded university inbox snapshot; credentials arrive only via env."""
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
import imaplib
import json
import os
import re
import ssl
import sys


def collect():
    with imaplib.IMAP4_SSL("unimail.tu-dortmund.de", 993, ssl_context=ssl.create_default_context(), timeout=25) as client:
        client.login(os.environ["IMAP_USER"], os.environ["IMAP_PASSWORD"])
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("Inbox selection failed")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%d-%b-%Y")
        status, data = client.uid("search", None, "SINCE", cutoff)
        if status != "OK":
            raise RuntimeError("Message search failed")
        uids = data[0].split()
        status, unseen = client.uid("search", None, "UNSEEN")
        unread = len(unseen[0].split()) if status == "OK" else None
        messages = []
        for uid in reversed(uids[-40:]):
            status, fetched = client.uid("fetch", uid, "(BODY.PEEK[HEADER] RFC822.SIZE)")
            chunks = [part for part in fetched if isinstance(part, tuple)]
            if status != "OK" or not chunks:
                raise RuntimeError("Header fetch failed")
            header = BytesParser(policy=policy.default).parsebytes(chunks[0][1])
            message = {"uid": uid.decode(), "subject": str(header.get("Subject", "")),
                       "from": str(header.get("From", "")), "date": str(header.get("Date", "")),
                       "messageId": str(header.get("Message-ID", "")), "body": None}
            # Fetch bounded messages without setting Seen; omit large attachments.
            size = re.search(rb"RFC822.SIZE (\d+)", chunks[0][0])
            authentication = re.search(r"pass(?:word|wort)|verif(?:y|ying|ication|iz)|login|sign.?in|anmeld.*code|one.time|einmal|passcode|\botp\b|security code|sicherheitscode|two.factor", message['subject'], re.I)
            if size and int(size.group(1)) <= 262144 and not authentication:
                status, fetched = client.uid("fetch", uid, "(BODY.PEEK[])")
                chunks = [part for part in fetched if isinstance(part, tuple)]
                if status != "OK" or not chunks:
                    raise RuntimeError("Body fetch failed")
                full = BytesParser(policy=policy.default).parsebytes(chunks[0][1])
                body = full.get_body(preferencelist=("plain",))
                if body is not None:
                    message["body"] = body.get_content()[:12000]
            messages.append(message)
        return {"state": "ok", "collectedAt": datetime.now(timezone.utc).isoformat(),
                "source": "TU Dortmund UniMail", "link": "https://unimail.tu-dortmund.de/",
                "scope": "INBOX, last 14 days, newest 40; plain bodies up to 256 KiB",
                "totalInScope": len(uids), "truncated": len(uids) > 40,
                "unreadCount": unread, "messages": messages}


if __name__ == "__main__":
    try:
        print(json.dumps(collect(), ensure_ascii=False))
    except Exception:
        print("UniMail snapshot failed; check central vault access and university IMAP authentication.", file=sys.stderr)
        sys.exit(1)
