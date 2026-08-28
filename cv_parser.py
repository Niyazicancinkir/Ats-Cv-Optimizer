import json
import google.generativeai as genai
from pypdf import PdfReader
from path_utils import project_path
from prompt_loader import render_prompt

def parse_pdf_to_json(pdf_path, output_json_path, api_key):
    print(f"[*] '{pdf_path}' taranıyor ve PDF metni çıkarılıyor...")
    full_pdf_path = project_path(pdf_path)
    
    try:
        reader = PdfReader(full_pdf_path)
        raw_cv_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_cv_text += text + "\n"
    except Exception as e:
        print(f"[!] PDF okunurken hata oluştu: {e}")
        return False

    if not raw_cv_text.strip():
        print("[!] PDF içeriği boş veya okunamadı!")
        return False

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.1-flash-lite')
    prompt = render_prompt("parse_pdf", {"RAW_CV_TEXT": raw_cv_text})

    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip()

        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()
        parsed_json = json.loads(cleaned_response)

        full_output_path = project_path(output_json_path)
        with open(full_output_path, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)

        print(f"[✔] Başarılı! PDF parse edildi ve '{output_json_path}' olarak kaydedildi.")
        return True

    except Exception as e:
        print(f"[✘] AI parse işleminde hata oluştu: {e}")
        return False