// מאזינים לכפתורי הדוגמאות
document.querySelectorAll('.example-btn').forEach(button => {
    button.addEventListener('click', (event) => {
        const url = event.target.getAttribute('data-url');
        const desc = event.target.getAttribute('data-desc');
        const htmlDesc = event.target.getAttribute('data-html-desc');

        document.getElementById('urlInput').value = url;
        const el = document.getElementById('explanationText');
        if (htmlDesc) {
            el.innerHTML = htmlDesc;
        } else {
            el.textContent = desc;
        }
        
        // מנקים את התוצאה הקודמת
        document.getElementById('resultOutput').textContent ="";
    });
});

// מאזין לכפתור המשיכה המקורי
document.getElementById('fetchBtn').addEventListener('click', async () => {
    const urlInput = document.getElementById('urlInput').value;
    const resultOutput = document.getElementById('resultOutput');

    if (!urlInput) {
        resultOutput.textContent = "שגיאה: נא להזין כתובת URL";
        return;
    }

    resultOutput.textContent ="";

    try {
        const response = await fetch(`/api/fetch?url=${encodeURIComponent(urlInput)}`);
        const data = await response.text();
        resultOutput.textContent = data;
    } catch (error) {
        resultOutput.textContent = "שגיאה בתקשורת מול השרת.";
    }
});