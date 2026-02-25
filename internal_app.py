from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/')
def home():
    return "Internal Service is running."


@app.route('/admin/secrets')
@app.route('/admin/secrets/<path:filename>')
def secrets(filename=None):
    # המידע הרגיש שהתוקף ינסה לשלוף באמצעות ה-SSRF.
    # ה-route מקבל גם sub-paths כמו /admin/secrets/logo.png
    # כדי לאפשר גישה דרך API ידידותי למשתמש.
    return jsonify({
        "status": "success",
        "db_password": "super_secret_database_password_123!",
        "api_key": "AKIA-SECRET-KEY-98765",
        "internal_note": "This endpoint should NEVER be "
                         "accessible from outside!"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
