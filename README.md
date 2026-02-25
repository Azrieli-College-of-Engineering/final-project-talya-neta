# SSRF Attack Lab — Multi-Layer Bypass Demonstration

> A hands-on security research environment demonstrating **Server-Side Request Forgery (SSRF)** — from basic exploitation to bypassing 10 layers of defense.

---

## What is SSRF?

**Server-Side Request Forgery** is a vulnerability where an attacker tricks a server into making HTTP requests on their behalf. Instead of the attacker connecting to an internal service directly (which is blocked by firewalls), they *weaponize the server itself* as a proxy to reach internal resources.

```
Attacker  ──►  Public Server  ──►  Internal Service
              (the proxy)          (normally unreachable)
```

---

## Architecture

The lab runs two isolated services inside a Docker network:

```
┌─────────────────────────────────────────────────────┐
│                   Docker Network                     │
│                                                      │
│  ┌──────────────────┐       ┌────────────────────┐  │
│  │   public-app     │       │   internal-app     │  │
│  │   (Flask :5000)  │──────►│   (Flask :8080)    │  │
│  │                  │       │                    │  │
│  │  10 security     │       │  /admin/secrets    │  │
│  │  layers          │       │  db_password       │  │
│  │                  │       │  api_key           │  │
│  └──────────────────┘       └────────────────────┘  │
│           ▲                         ✗                │
│           │                  not exposed             │
└───────────┼─────────────────────────────────────────┘
            │
         Attacker
    (http://localhost:5000)
```

- **`public-app`** — Exposed to the internet. Has a `/api/fetch` endpoint that fetches URLs on behalf of the user. Protected by 10 security layers.
- **`internal-app`** — Hidden inside the Docker network. Not exposed externally. Holds sensitive credentials at `/admin/secrets`.

---

## The 10 Security Layers (and their flaws)

The public server implements a progressively hardened defense system. Every layer has a deliberate, realistic weakness — the kind of mistake developers actually make.

| # | Defense | What It Does | The Flaw |
|---|---------|--------------|----------|
| 1 | **Rate Limiting** | Max 10 requests/min per IP | Based on `X-Forwarded-For` — trivially spoofable |
| 2 | **Scheme Validation** | Blocks `file://`, `gopher://`, `dict://` | Correct — but only one layer |
| 3 | **Hostname Blacklist** | Blocks known internal names (`localhost`, `internal-app`, ...) | Blacklists are always incomplete — unknown aliases bypass it |
| 4 | **IP Regex Check** | Detects direct IPv4 addresses (`x.x.x.x`) | Misses octal, hex, decimal, and IPv6 representations |
| 5 | **DNS Resolution** | Resolves hostname and checks if it's a private IP | Missing `172.16.0.0/12` — the entire Docker network range |
| 6 | **Port Restriction** | Only allows ports 80, 443, 8080, 8443 | Port 8080 is allowed (needed for "external APIs") — and the internal service runs on 8080 |
| 7 | **Path Extension Check** | URL path must end with `.png`, `.jpg`, etc. | Attacker can craft `/admin/secrets/logo.png` — a valid-looking path that the internal server accepts |
| 8 | **Redirect Blocking** | Blocks HTTP 301/302/307 responses | Correctly implemented |
| 9 | **Response Size Limit** | Blocks responses over 10MB | Secrets are small — passes trivially |
| 10 | **Content-Type Check** | Checks if response is actually an image | **Never enforced** — developer 

---

## Project Structure

```
SSRF_Attack/
├── public_app.py          # Vulnerable public server (10 defense layers)
├── internal_app.py        # Internal service with sensitive credentials
├── docker-compose.yml     # Network isolation setup
├── Dockerfile
├── requirements.txt
├── templates/
│   └── index.html         # Interactive demo UI
├── static/
│   ├── app.js
│   └── style.css
└── tests/
    └── test_ssrf_exploit.py  # Automated proof-of-concept tests
```

---

## Running the Lab

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) · Python 3.9+

---

**Step 1 — Build and start both containers**
bash:
docker compose up --build

**Step 2 — Open the demo UI**
http://localhost:5000

Click the scenario buttons to walk through a legitimate request, three blocked attacks, and the full bypass POC.

**Step 3 — Run the automated tests** (in a separate terminal)
bash:
pip install requests pytest
python -m pytest tests/test_ssrf_exploit.py -v

**Step 4 — Tear down**
bash:
docker compose down

---

## Technologies

`Python` `Flask` `Docker` `Docker Compose` `unittest` `ipaddress` `socket`


