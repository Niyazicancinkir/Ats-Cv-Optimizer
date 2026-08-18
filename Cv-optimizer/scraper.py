from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrape_job_description(url):
    print(f"[*] URL'den iş ilanı çekiliyor: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )

            page = context.new_page()
            page.goto(url, timeout=2000, wait_until="domcontentloaded")

            print("\n⏳ DİKKAT: Güvenlik duvarı (CAPTCHA) beklemesi.")
            print("⏳ 'Basılı Tut' butonuna tıklamak için 10 saniyeniz var...\n")

            page.wait_for_timeout(2000) 

            html_content = page.content()
            browser.close()

            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            clean_text = ' '.join(text.split())

            if len(clean_text) < 200:
                raise Exception("Kısa metin döndü, muhtemelen süre yetmedi veya yanlış tıklandı.")

            print("[✔] Bot koruması aşıldı! İlan metni başarıyla çekildi.")
            return clean_text[:5000]

    except Exception as e:
        print(f"[!] Bot koruması atlatılamadı veya ağ hatası: {e}")
        return None