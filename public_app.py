from flask import Flask, request, jsonify, render_template
import requests as http_requests
import socket
import ipaddress
import re
import time
from urllib.parse import urlparse, unquote

app = Flask(__name__)

# =====================================================================
# תצורת אבטחה - מערכת הגנה רב-שכבתית
# =====================================================================

ALLOWED_SCHEMES = ['http', 'https']

BLOCKED_HOSTNAMES = [
    'localhost', 'internal-app', 'internal', 'admin',
    'metadata', 'metadata.google.internal', 'instance-data',
    '169.254.169.254',
]

ALLOWED_PORTS = [80, 443, 8080, 8443]

ALLOWED_PATH_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')

ALLOWED_CONTENT_TYPES = [
    'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml'
]

MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

# === רשימת טווחי IP פרטיים ===
# חולשה: חסר טווח 172.16.0.0/12 (Private Class B)!
# רשתות Docker משתמשות בדיוק בטווח הזה (172.17.x.x, 172.18.x.x, ...).
# המפתח שכח להוסיף אותו, וזה פותח פרצה לתקיפה דרך רשת ה-Docker.
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('127.0.0.0/8'),       # Loopback
    ipaddress.ip_network('10.0.0.0/8'),         # Private Class A
    ipaddress.ip_network('192.168.0.0/16'),     # Private Class C
    ipaddress.ip_network('169.254.0.0/16'),     # Link-local
    ipaddress.ip_network('0.0.0.0/8'),          # "This" network
]

# Rate Limiting
request_log = {}
RATE_LIMIT = 10
RATE_WINDOW = 60


def is_private_ip(ip_str):
    """בדיקה ידנית של IP מול רשימת טווחים פרטיים."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        return True


def resolve_hostname(hostname):
    """
    רזולוציית DNS באמצעות gethostbyname (IPv4 בלבד).
    חולשה: gethostbyname לא תומך ב-IPv6 או פורמטים מיוחדים של IP.
    אם הפענוח נכשל, הפונקציה מחזירה None במקום לחסום - טעות!
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def check_rate_limit(client_ip):
    """הגבלת קצב בקשות לפי כתובת IP."""
    now = time.time()
    if client_ip not in request_log:
        request_log[client_ip] = []
    request_log[client_ip] = [
        t for t in request_log[client_ip] if now - t < RATE_WINDOW
    ]
    if len(request_log[client_ip]) >= RATE_LIMIT:
        return False
    request_log[client_ip].append(now)
    return True


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/fetch')
def fetch_url():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({"error": "Please provide a 'url' parameter"}), 400

    # === הגנה 1: Rate Limiting ===
    # חולשה: מבוסס על X-Forwarded-For שקל לזייף.
    # תוקף יכול לשלוח header מזויף כדי לעקוף את המגבלה.
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

    parsed_url = urlparse(target_url)

    # === הגנה 2: Scheme Validation ===
    # מונע פרוטוקולים מסוכנים כמו file://, gopher://, dict://
    if parsed_url.scheme not in ALLOWED_SCHEMES:
        return jsonify({
            "error": f"Security Block: Scheme '{parsed_url.scheme}' is not allowed. Only HTTP/HTTPS."
        }), 403

    # === הגנה 3: רשימה שחורה מורחבת של Hostnames ===
    # חולשה: רשימה שחורה היא תמיד חלקית - אי אפשר לחסום את כל השמות.
    # שמות DNS פנימיים שלא ידועים למפתח (כמו aliases של Docker) לא ייחסמו.
    hostname = parsed_url.hostname
    if not hostname:
        return jsonify({"error": "Security Block: Invalid hostname!"}), 403

    hostname_lower = hostname.lower().strip('.')
    for blocked in BLOCKED_HOSTNAMES:
        if hostname_lower == blocked or hostname_lower.endswith('.' + blocked):
            return jsonify({
                "error": f"Security Block: Hostname '{hostname}' is blacklisted!"
            }), 403

    # === הגנה 4: בדיקת IP ישירה ב-Regex ===
    # חולשה: ה-regex מזהה רק פורמט IPv4 סטנדרטי (x.x.x.x).
    # לא מכסה: decimal (2130706433), octal (0177.0.0.1), hex (0x7f000001), IPv6.
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', hostname):
        if is_private_ip(hostname):
            return jsonify({
                "error": f"Security Block: Private IP '{hostname}' detected!"
            }), 403

    # === הגנה 5: רזולוציית DNS + בדיקת IP פנימי ===
    # חולשה כפולה:
    #   (א) אם gethostbyname נכשל (None), הבקשה לא נחסמת!
    #   (ב) is_private_ip חסרה את טווח 172.16.0.0/12 (Docker networks)
    resolved_ip = resolve_hostname(hostname)
    if resolved_ip:
        if is_private_ip(resolved_ip):
            return jsonify({
                "error": f"Security Block: '{hostname}' resolves to private IP ({resolved_ip})!"
            }), 403

    # === הגנה 6: הגבלת פורטים מותרים ===
    # חולשה: 8080 מותר כי זה פורט נפוץ לשירותי API חיצוניים,
    # אבל גם השרת הפנימי רץ על פורט 8080!
    port = parsed_url.port
    if port and port not in ALLOWED_PORTS:
        return jsonify({
            "error": f"Security Block: Port {port} is not allowed!"
        }), 403

    # === הגנה 7: בדיקת סיומת קובץ בנתיב (Path Extension Check) ===
    # שיפור: בדיקה על parsed_url.path במקום URL מלא + URL decoding.
    # עקיפה: תוקף יכול לבנות נתיב עם סיומת תמונה - /admin/secrets/logo.png
    # אם השרת הפנימי מקבל גם נתיבים עם sub-path, ההגנה נעקפת.
    decoded_path = unquote(parsed_url.path).lower()
    if not decoded_path.endswith(ALLOWED_PATH_EXTENSIONS):
        return jsonify({
            "error": "Security Block: URL path must end with a valid image extension!"
        }), 403

    try:
        # === הגנה 8: חסימת הפניות (Redirect Blocking) ===
        response = http_requests.get(
            target_url, timeout=5, allow_redirects=False, stream=True
        )

        if response.status_code in [301, 302, 303, 307, 308]:
            return jsonify({
                "error": "Security Block: HTTP redirects are not allowed!"
            }), 403

        # === הגנה 9: הגבלת גודל תשובה ===
        content_length = response.headers.get('Content-Length', 0)
        if int(content_length or 0) > MAX_RESPONSE_SIZE:
            return jsonify({"error": "Security Block: Response too large!"}), 403

        # === הגנה 10: בדיקת Content-Type של התשובה ===
        # חולשה קריטית: המפתח רק מתעד אזהרה בלוג ולא חוסם!
        # הוא השאיר TODO לעצמו ושכח ליישם את החסימה.
        content_type = response.headers.get('Content-Type', '')
        if not any(t in content_type for t in ALLOWED_CONTENT_TYPES):
            app.logger.warning(
                f"[SECURITY] Non-image Content-Type: {content_type} "
                f"from {target_url}"
            )

        return response.content, response.status_code, {
            'Content-Type': response.headers.get(
                'Content-Type', 'application/octet-stream'
            )
        }

    except http_requests.exceptions.ConnectionError:
        return jsonify({"error": "Connection failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
