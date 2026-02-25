# שימוש בתמונת בסיס קלה של פייתון
FROM python:3.9-slim

# הגדרת תיקיית העבודה בתוך הקונטיינר
WORKDIR /app

# העתקת קובץ הדרישות והתקנת הספריות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת כל שאר הקבצים (קוד המקור) לתוך הקונטיינר
COPY . .