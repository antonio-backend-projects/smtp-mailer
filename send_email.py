#!/usr/bin/env python3
"""
Generic SMTP Email Sender (Yahoo-ready) — with attachments, HTML, CC/BCC.

- Reads config from environment (.env supported) using keys:

  MAIL_PROVIDER=smtp
  MAIL_USER=antonio.trento@yahoo.com
  MAIL_PASS=your-app-password-or-smtp-pass
  MAIL_HOST=smtp.mail.yahoo.com
  MAIL_PORT=587
  MAIL_ENCRYPTION=tls   # one of: tls | ssl | none
  MAIL_FROM_NAME="Antonio Trento"
  MAIL_FROM_ADDRESS=antonio.trento@yahoo.com
  # optional TLS CA bundle
  MAIL_SSL_CAFILE=C:\path\to\cacert.pem

- CLI flags let you override both message fields (to/subject/body/attachments)
  and transport settings (host/port/encryption/user/pass/from...).

Yahoo note:
  * Server: smtp.mail.yahoo.com
  * SSL: 465  (MAIL_ENCRYPTION=ssl)
  * STARTTLS: 587 (MAIL_ENCRYPTION=tls) — consigliato
  * Necessaria una App Password (non la password normale) se usi 2FA.

Examples
--------
# Basic (env-driven)
python send_email.py \
  --to someone@example.com \
  --subject "Prova invio" \
  --text "Ciao, funziona!"

# With HTML and attachments
python send_email.py \
  --to a@ex.com --to b@ex.com \
  --cc c@ex.com \
  --subject "Report" \
  --text "Versione testuale" \
  --html "<h1>Report</h1><p>Allegato incluso.</p>" \
  --attach ./report.pdf --attach ./grafico.png

# Override transport on CLI (e.g., SSL on 465)
python send_email.py \
  --to you@ex.com --subject "SSL test" --text "Hi" \
  --host smtp.mail.yahoo.com --port 465 --encryption ssl
"""

from __future__ import annotations
import argparse
import getpass
import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Iterable, List, Tuple

# --- optional .env loader ---
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# --- prefer Mozilla CA bundle (certifi) or env-provided cafile ---
try:
    import certifi  # type: ignore
    _CAFILE_DEFAULT = certifi.where()
except Exception:
    _CAFILE_DEFAULT = None

def _build_ssl_context(cafile: str | None = None, insecure: bool = False) -> ssl.SSLContext:
    """
    Build an SSLContext using priority:
    CLI --cafile -> ENV MAIL_SSL_CAFILE -> ENV SSL_CERT_FILE -> certifi -> system default.
    If 'insecure' is True, disable verification (ONLY for testing).
    """
    cafile = cafile or os.getenv("MAIL_SSL_CAFILE") or os.getenv("SSL_CERT_FILE") or _CAFILE_DEFAULT
    if cafile:
        ctx = ssl.create_default_context(cafile=cafile)
    else:
        ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

# --- Defaults tailored for Yahoo, but fully overridable ---
YAHOO_DEFAULTS = {
    "MAIL_PROVIDER": "smtp",
    "MAIL_USER": os.getenv("YAHOO_EMAIL", "antonio.trento@yahoo.com"),
    "MAIL_PASS": os.getenv("YAHOO_APP_PASSWORD", ""),
    "MAIL_HOST": "smtp.mail.yahoo.com",
    "MAIL_PORT": "587",
    "MAIL_ENCRYPTION": "tls",  # or "ssl" (465) per SSL diretto
    "MAIL_FROM_NAME": "",
    "MAIL_FROM_ADDRESS": os.getenv("YAHOO_EMAIL", "antonio.trento@yahoo.com"),
}

def env_get(key: str, fallback: str | None = None) -> str | None:
    val = os.getenv(key)
    if val is None or val == "":
        return fallback
    return val

def load_transport_from_env() -> dict:
    # Se non è configurato MAIL_HOST, cade su Yahoo defaults
    cfg = {
        "provider": env_get("MAIL_PROVIDER", YAHOO_DEFAULTS["MAIL_PROVIDER"]) or "smtp",
        "user": env_get("MAIL_USER", YAHOO_DEFAULTS["MAIL_USER"]) or "",
        "password": env_get("MAIL_PASS", YAHOO_DEFAULTS["MAIL_PASS"]) or "",
        "host": env_get("MAIL_HOST", YAHOO_DEFAULTS["MAIL_HOST"]) or "",
        "port": int(env_get("MAIL_PORT", YAHOO_DEFAULTS["MAIL_PORT"]) or 587),
        "encryption": (env_get("MAIL_ENCRYPTION", YAHOO_DEFAULTS["MAIL_ENCRYPTION"]) or "tls").lower(),
        "from_name": env_get("MAIL_FROM_NAME", YAHOO_DEFAULTS["MAIL_FROM_NAME"]) or "",
        "from_address": env_get("MAIL_FROM_ADDRESS", YAHOO_DEFAULTS["MAIL_FROM_ADDRESS"]) or "",
    }
    if cfg["encryption"] not in {"tls", "ssl", "none"}:
        cfg["encryption"] = "tls"
    return cfg

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Invia email via SMTP generico (Yahoo-ready) con allegati, HTML, CC/BCC.")

    # Message fields
    p.add_argument("--to", dest="to", action="append", required=True, help="Destinatario. Ripeti per più indirizzi.")
    p.add_argument("--cc", dest="cc", action="append", help="CC. Ripeti per più indirizzi.")
    p.add_argument("--bcc", dest="bcc", action="append", help="BCC. Ripeti per più indirizzi.")
    p.add_argument("--subject", required=True, help="Oggetto dell'email.")
    p.add_argument("--text", default="", help="Corpo testuale (plain text).")
    p.add_argument("--html", default=None, help="Corpo in HTML (opzionale).")
    p.add_argument("--attach", dest="attachments", action="append", help="Percorso file da allegare. Ripeti per più allegati.")
    p.add_argument("--reply-to", dest="reply_to", default=None, help="Indirizzo Reply-To (opzionale).")

    # Transport overrides (optional; otherwise pulled from env/.env)
    p.add_argument("--from-address", dest="from_address", default=None, help="Mittente: email.")
    p.add_argument("--from-name", dest="from_name", default=None, help="Mittente: nome visualizzato.")
    p.add_argument("--user", dest="user", default=None, help="SMTP username.")
    p.add_argument("--password", dest="password", default=None, help="SMTP password / app password.")
    p.add_argument("--host", dest="host", default=None, help="SMTP host.")
    p.add_argument("--port", dest="port", type=int, default=None, help="SMTP port.")
    p.add_argument("--encryption", choices=["tls", "ssl", "none"], default=None, help="Cifratura: tls | ssl | none.")

    # TLS controls
    p.add_argument("--cafile", dest="cafile", default=None, help="Percorso CA bundle personalizzato (opzionale).")
    p.add_argument("--insecure", action="store_true", help="DISABILITA la verifica TLS (SOLO TEST).")

    # Utility
    p.add_argument("--dry-run", action="store_true", help="Costruisce il messaggio ma non invia.")

    return p.parse_args()

def guess_mime_type(path: Path) -> Tuple[str, str]:
    ctype, _ = mimetypes.guess_type(str(path))
    if ctype is None:
        return ("application", "octet-stream")
    maintype, subtype = ctype.split("/", 1)
    return maintype, subtype

def build_message(
    from_address: str,
    from_name: str,
    to: Iterable[str],
    subject: str,
    text: str = "",
    html: str | None = None,
    cc: Iterable[str] | None = None,
    bcc: Iterable[str] | None = None,
    reply_to: str | None = None,
    attachments: Iterable[str] | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    display_from = formataddr((from_name, from_address)) if from_name else from_address
    msg["From"] = display_from
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Body
    if html:
        msg.set_content(text or "")
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(text or "")

    # Attachments
    for f in attachments or []:
        path = Path(f)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Allegato non trovato: {path}")
        maintype, subtype = guess_mime_type(path)
        with path.open("rb") as fp:
            data = fp.read()
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)

    # Store recipients for sending
    all_rcpts = list({*(to or []), *(cc or []), *(bcc or [])})
    msg.__all_recipients__ = all_rcpts  # type: ignore[attr-defined]
    return msg

def send_smtp(
    msg: EmailMessage,
    user: str,
    password: str,
    host: str,
    port: int,
    encryption: str = "tls",
    cafile: str | None = None,
    insecure: bool = False,
) -> None:
    recipients: List[str] = getattr(msg, "__all_recipients__", [])  # type: ignore[assignment]
    if not recipients:
        raise ValueError("Nessun destinatario (To/Cc/Bcc) indicato.")

    encryption = (encryption or "tls").lower()
    if encryption == "ssl":
        context = _build_ssl_context(cafile=cafile, insecure=insecure)
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            if user:
                server.login(user, password)
            server.send_message(msg, to_addrs=recipients)
    else:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            if encryption == "tls":
                context = _build_ssl_context(cafile=cafile, insecure=insecure)
                server.starttls(context=context)
                server.ehlo()
            if user:
                server.login(user, password)
            server.send_message(msg, to_addrs=recipients)

def resolve_config(args: argparse.Namespace) -> tuple[dict, dict]:
    env_cfg = load_transport_from_env()

    # CLI overrides (only if provided)
    tr = {
        "user": args.user if args.user is not None else env_cfg["user"],
        "password": args.password if args.password is not None else env_cfg["password"],
        "host": args.host if args.host is not None else env_cfg["host"],
        "port": args.port if args.port is not None else env_cfg["port"],
        "encryption": args.encryption if args.encryption is not None else env_cfg["encryption"],
        "from_name": args.from_name if args.from_name is not None else env_cfg["from_name"],
        "from_address": args.from_address if args.from_address is not None else env_cfg["from_address"],
        "cafile": args.cafile if hasattr(args, "cafile") else None,
        "insecure": bool(getattr(args, "insecure", False)),
    }

    # Validation + sensible Yahoo fallbacks
    if not tr["from_address"]:
        tr["from_address"] = tr["user"]
    if not tr["host"]:
        tr["host"] = YAHOO_DEFAULTS["MAIL_HOST"]
    if not tr["port"]:
        tr["port"] = int(YAHOO_DEFAULTS["MAIL_PORT"])  # 587
    if tr["encryption"] not in {"tls", "ssl", "none"}:
        tr["encryption"] = "tls"

    msg_cfg = {
        "from_address": tr["from_address"],
        "from_name": tr["from_name"],
    }
    return tr, msg_cfg

def main():
    args = parse_args()

    # Resolve transport and message config
    transport, msg_cfg = resolve_config(args)

    # Ask for password if missing and login is expected
    if transport["user"] and not transport["password"]:
        transport["password"] = getpass.getpass("Inserisci la password/app password SMTP: ")

    # Build message
    msg = build_message(
        from_address=msg_cfg["from_address"],
        from_name=msg_cfg["from_name"],
        to=args.to,
        subject=args.subject,
        text=args.text,
        html=args.html,
        cc=args.cc,
        bcc=args.bcc,
        reply_to=args.reply_to,
        attachments=args.attachments,
    )

    if args.dry_run:
        print("[DRY-RUN] Messaggio costruito. Intestazioni principali:\n")
        for k in ("From", "To", "Cc", "Subject", "Reply-To"):
            if msg.get(k):
                print(f"{k}: {msg[k]}")
        print("\nTrasporto:")
        print(f"Host: {transport['host']}  Port: {transport['port']}  Enc: {transport['encryption']}  User: {transport['user']}")
        print(f"CAFile: {transport.get('cafile') or os.getenv('MAIL_SSL_CAFILE') or os.getenv('SSL_CERT_FILE') or _CAFILE_DEFAULT}")
        print("Corpo generato e allegati conteggiati con successo.")
        return

    # Send
    send_smtp(
        msg=msg,
        user=transport["user"],
        password=transport["password"],
        host=transport["host"],
        port=int(transport["port"]),
        encryption=transport["encryption"],
        cafile=transport.get("cafile"),
        insecure=transport.get("insecure", False),
    )

    print("✅ Email inviata correttamente a:", ", ".join(getattr(msg, "__all_recipients__", [])))

if __name__ == "__main__":
    main()
