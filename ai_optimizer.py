import json
from google import genai
from prompt_loader import render_prompt

class CVOptimizer:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-3.1-flash-lite'

    def optimize_bilingual(self, base_cv_data, job_description):
        print("[*] Gemini AI ile CV iş ilanına göre analiz ediliyor ve çift dilli optimize ediliyor...")
        
        prompt = render_prompt(
            "optimize_bilingual",
            {
                "BASE_CV_JSON": json.dumps(base_cv_data, indent=2, ensure_ascii=False),
                "JOB_DESCRIPTION": job_description,
            },
        )

        print("\n" + "="*50)
        print("🤖 YAPAY ZEKAYA GÖNDERİLEN OPTİMİZASYON PAYLOAD'I:")
        print("="*50)
        print(prompt)
        print("="*50 + "\n")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            result_text = response.text.strip()
            
            if result_text.startswith("```json"): 
                result_text = result_text[7:]
            if result_text.startswith("```"): 
                result_text = result_text[3:]
            if result_text.endswith("```"): 
                result_text = result_text[:-3]
                
            return json.loads(result_text.strip())
            
        except Exception as e:
            print(f"[!] Gemini API hatası: {e}")
            print("[!] Çift dilli optimizasyon başarısız.")
            return None