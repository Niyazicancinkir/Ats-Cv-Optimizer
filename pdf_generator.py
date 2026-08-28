import os
from jinja2 import Template
from playwright.sync_api import sync_playwright

def generate_pdf(cv_data, template_path, output_pdf_path):
    print("[*] Optimize edilmiş ATS uyumlu PDF oluşturuluyor (Playwright Headless Engine)...")

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    template = Template(template_content)
    rendered_html = template.render(cv_data)

    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(rendered_html)

            page.wait_for_timeout(500) 

            page.pdf(path=output_pdf_path, format="A4", print_background=True)

        return True
    except Exception as e:
        print(f"[!] PDF oluşturulurken hata: {e}")
        return False