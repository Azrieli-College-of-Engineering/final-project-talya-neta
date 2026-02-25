import unittest
import requests

class TestEnvironment(unittest.TestCase):
    # הפורט עודכן ל-8000 בגלל שהוספנו את Nginx
    BASE_URL = 'http://localhost:8000' 

    def test_1_public_app_is_reachable(self):
        """מוודא שהשירות הציבורי באוויר ומגיב"""
        try:
            response = requests.get(f"{self.BASE_URL}/")
            self.assertEqual(response.status_code, 200, "השרת הציבורי או ה-Nginx לא מגיבים")
        except requests.exceptions.ConnectionError:
            self.fail("לא ניתן להתחבר לשרת הציבורי. ודא ש-Docker פועל.")

    def test_2_internal_app_is_isolated(self):
        """מוודא שהשירות הפנימי חסום לגישה ישירה מהעולם החיצון"""
        # אנחנו מנסים לגשת אליו ישירות דרך הפורט שלו
        try:
            requests.get("http://localhost:8080/admin/secrets", timeout=2)
            self.fail("אזהרה: השירות הפנימי חשוף לאינטרנט! הוא אמור להיות מבודד.")
        except requests.exceptions.ConnectionError:
            # אם קיבלנו שגיאת חיבור - זה מצוין! הרשת מבודדת נכון
            pass