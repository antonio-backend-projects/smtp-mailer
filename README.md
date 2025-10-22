# Generic SMTP Email Sender (Yahoo‑ready)

Script CLI in Python per inviare email tramite **qualsiasi SMTP** con supporto a **HTML, allegati, CC/BCC**, cifratura **TLS/SSL**, lettura da **`.env`** e override da **CLI**. Preset per **Yahoo Mail** (App Password), ma funziona anche con Gmail/Outlook e provider custom.

---

## ✨ Caratteristiche

* SMTP generico: host/porta/encryption configurabili
* HTML + testo, **allegati multipli**, CC/BCC, Reply‑To
* STARTTLS (587), SSL (465) o nessuna cifratura (solo reti fidate)
* Config via **`.env`** (caricato con `python-dotenv` se presente)
* **Override da CLI** per tutti i parametri
* Gestione CA bundle: usa **certifi** automaticamente; opzionale `--cafile` o var `MAIL_SSL_CAFILE`

---

## Requisiti

* Python 3.9+
* Dipendenze (vedi `requirements.txt`):

  * `python-dotenv` (opzionale ma consigliato)
  * `certifi` (consigliato; già incluso per Docker)

```bash
pip install -r requirements.txt
```

> Nota: il warning `SyntaxWarning: invalid escape sequence '\p'` è innocuo e deriva dall’esempio di percorso Windows nel docstring.

---

## Configurazione (`.env`)

Esempio **Yahoo** (consigliato SSL 465):

```env
MAIL_PROVIDER=smtp
MAIL_USER=antonio.trento@yahoo.com
MAIL_PASS=<APP-PASSWORD-YAHOO>
MAIL_HOST=smtp.mail.yahoo.com
MAIL_PORT=465
MAIL_ENCRYPTION=ssl
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=antonio.trento@yahoo.com
# Opzionale in ambiente non-Docker (Windows):
# MAIL_SSL_CAFILE=C:\Users\hp\AppData\Roaming\Python\Python313\site-packages\certifi\cacert.pem
```

> **Yahoo richiede App Password** (con 2FA attivo). Usa la app password, **non** la password normale.

**Importante per Docker:** rimuovi/commenta `MAIL_SSL_CAFILE` se punta a un percorso Windows; nel container usiamo automaticamente il CA bundle di **certifi**.

---

## Utilizzo (nativo Python)

Invio semplice:

```bash
python send_email.py \
  --to dest@example.com \
  --subject "Prova" \
  --text "Ciao"
```

HTML + allegati + CC:

```bash
python send_email.py \
  --to a@ex.com --to b@ex.com \
  --cc c@ex.com \
  --subject "Report" \
  --text "Versione testuale" \
  --html "<h1>Report</h1><p>Allegato incluso.</p>" \
  --attach ./report.pdf --attach ./grafico.png
```

**Allegati multipli** (ripeti `--attach`):

```bash
python send_email.py \
  --to dest@example.com \
  --subject "Prova con più allegati" \
  --text "Ciao" \
  --attach ./file1.pdf \
  --attach ./immagini/grafico.png \
  --attach ./dati/export.csv
```

> Su **PowerShell/Windows** niente wildcard (`*.pdf`) a meno di espansioni manuali; su **bash/zsh** le glob vengono espanse dallo shell.

**BCC e BCC multipli** (copie conoscenza nascoste):

```bash
python send_email.py \
  --to primo@esempio.com --to secondo@esempio.com \
  --cc visibile@esempio.com \
  --bcc nascosto1@esempio.com --bcc nascosto2@esempio.com \
  --subject "Prova BCC" \
  --text "Ciao, prova con BCC."
```

> I destinatari in **BCC** ricevono l'email ma **non compaiono** nelle intestazioni visibili.

**Solo BCC** (nessun destinatario visibile):

```bash
python send_email.py \
  --to "undisclosed-recipients:;" \
  --bcc nascosto1@esempio.com --bcc nascosto2@esempio.com \
  --subject "Solo BCC" \
  --text "Lista solo BCC."
```

**Più destinatari (To multipli)**:

```bash
python send_email.py \
  --to a@ex.com --to b@ex.com --to c@ex.com \
  --subject "Invio a più destinatari" \
  --text "Stesso messaggio a più persone."
```

Forza trasporto (es. SSL 465):

```bash
python send_email.py \
  --to you@ex.com --subject "SSL test" --text "Hi" \
  --host smtp.mail.yahoo.com --port 465 --encryption ssl
```

Dry‑run (non invia):

```bash
python send_email.py --to test@ex.com --subject "Check" --text "ping" --dry-run
```

---

## 🚢 Esecuzione con Docker

### `docker-compose.yml` (minimale)

Assicurati che il file nella root sia così:

```yaml
services:
  smtp:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - ./:/app:rw
    env_file:
      - .env
    command: ["python", "send_email.py"]
```

### 1) Installa i requirements **dentro** il container

```bash
docker compose run --rm smtp pip install --no-cache-dir -r requirements.txt
```

### 2) Invia l'email (passando gli argomenti allo script)

Usa `python send_email.py` come comando e poi gli argomenti:

```bash
docker compose run --rm smtp \
  python send_email.py \
  --to a@ex.com --to b@ex.com \
  --cc visibile@esempio.com \
  --bcc nascosto1@esempio.com --bcc nascosto2@esempio.com \
  --subject "Prova Docker + BCC" \
  --text "Ciao" \
  --attach /app/file1.pdf \
  --attach /app/immagini/grafico.png \
  --host smtp.mail.yahoo.com \
  --port 465 \
  --encryption ssl
```

> Nel container, il progetto è montato in **`/app`**, quindi gli allegati vanno referenziati come `/app/<file>`.

**Alternative:**

* Fissa l’entrypoint per non dover scrivere `python send_email.py` e usa `--` per gli argomenti:

  ```yaml
  services:
    smtp:
      image: python:3.12-slim
      working_dir: /app
      volumes: ["./:/app:rw"]
      env_file: [".env"]
      entrypoint: ["python","send_email.py"]
  ```

  E poi:

  ```bash
  docker compose run --rm smtp -- \
    --to dest@example.com \
    --bcc nascosto@esempio.com \
    --subject "Prova" \
    --text "Ciao"
  ```

---

## Ricette provider

Questo script funziona con qualsiasi SMTP standard (auth + TLS/SSL). Di seguito alcune configurazioni pronte.

### Yahoo Mail (consigliato SSL 465)

```env
MAIL_HOST=smtp.mail.yahoo.com
MAIL_PORT=465
MAIL_ENCRYPTION=ssl
MAIL_USER=antonio.trento@yahoo.com
MAIL_PASS=<APP-PASSWORD-YAHOO>
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=antonio.trento@yahoo.com
```

Esempio CLI:

```bash
python send_email.py \
  --to dest@example.com \
  --subject "Prova" \
  --text "Ciao" \
  --host smtp.mail.yahoo.com --port 465 --encryption ssl
```

### Gmail (2FA + App Password)

```env
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_ENCRYPTION=tls
MAIL_USER=tuoaccount@gmail.com
MAIL_PASS=<APP-PASSWORD-GMAIL>
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=tuoaccount@gmail.com
```

Esempio CLI:

```bash
python send_email.py \
  --to dest@example.com \
  --subject "Prova" \
  --text "Ciao" \
  --host smtp.gmail.com --port 587 --encryption tls
```

### Outlook / Office 365

```env
MAIL_HOST=smtp.office365.com
MAIL_PORT=587
MAIL_ENCRYPTION=tls
MAIL_USER=tuoaccount@azienda.com
MAIL_PASS=<PASSWORD-O-APP-PASSWORD>
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=tuoaccount@azienda.com
```

Esempio CLI:

```bash
python send_email.py \
  --to dest@example.com \
  --subject "Prova" \
  --text "Ciao" \
  --host smtp.office365.com --port 587 --encryption tls
```

### SendGrid (SMTP Relay)

> Richiede un dominio/mittente **verificato** e autorizzazioni SPF/DKIM.

```env
MAIL_HOST=smtp.sendgrid.net
MAIL_PORT=587
MAIL_ENCRYPTION=tls
MAIL_USER=apikey               # letteralmente "apikey"
MAIL_PASS=<SENDGRID_API_KEY>   # la tua API key SendGrid
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=tuo@dominio.verificato
```

Esempio CLI:

```bash
python send_email.py \
  --to destinatario@dominio.esempio \
  --subject "Aggiornamenti" \
  --text "Ciao" \
  --host smtp.sendgrid.net --port 587 --encryption tls \
  --from-address tuo@dominio.verificato
```

### Brevo (ex Sendinblue)

> Usa la **SMTP Key** (diversa dalla API Key REST) e un mittente/dominio **verificato**.

```env
MAIL_HOST=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_ENCRYPTION=tls
MAIL_USER=<LA_TUA_EMAIL_O_USERNAME_SMTP>
MAIL_PASS=<BREVO_SMTP_KEY>
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=tuo@dominio.verificato
```

Esempio CLI:

```bash
python send_email.py \
  --to destinatario@dominio.esempio \
  --subject "Newsletter" \
  --text "Ciao" \
  --host smtp-relay.brevo.com --port 587 --encryption tls \
  --from-address tuo@dominio.verificato
```

### Mailgun (facoltativo)

```env
MAIL_HOST=smtp.mailgun.org
MAIL_PORT=587
MAIL_ENCRYPTION=tls
MAIL_USER=postmaster@<tuo-dominio-mailgun>
MAIL_PASS=<PASSWORD_SMTP_MAILGUN>
MAIL_FROM_NAME="Antonio Trento"
MAIL_FROM_ADDRESS=tuo@tuo-dominio.com
```

---

## Troubleshooting

* **CERTIFICATE_VERIFY_FAILED / self-signed in chain**

  * In Docker: di default usiamo `certifi`, quindi dovrebbe andare.
  * Su Windows nativo: imposta `SSL_CERT_FILE` al `cacert.pem` di certifi **oppure** passa `--cafile`.
  * Evita `MAIL_SSL_CAFILE` con percorsi Windows quando usi Docker.
* **550 Mailbox unavailable**

  * Indirizzo destinatario inesistente o rifiutato dal provider.
  * Verifica mittente = utente SMTP (alcuni provider lo richiedono).
* **535/534 Authentication failed**

  * Usa **App Password** (Yahoo/Gmail con 2FA) e controlla `MAIL_USER`/mittente.
* **530 Must issue a STARTTLS first**

  * Usa `MAIL_ENCRYPTION=tls` con `MAIL_PORT=587` o passa `--encryption tls`.

Suggerimenti:

* Prova `--dry-run` per validare intestazioni, corpo e allegati senza inviare.
* Per debug avanzato, puoi aggiungere `server.set_debuglevel(1)` nello script.

---

## Licenza

Aggiungi un file `LICENSE` (es. MIT) se intendi distribuire pubblicamente.

---

## Changelog

* **v1.1.0** – Gestione CA migliorata (certifi, `--cafile`, note Docker), README aggiornato, guida Docker completa.
* **v1.0.0** – Prima versione generica (Yahoo‑ready), CLI + `.env`, allegati, HTML, CC/BCC, TLS/SSL, dry‑run.
