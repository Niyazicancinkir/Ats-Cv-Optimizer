import io
import json
import os
import traceback
from contextlib import redirect_stdout
from datetime import datetime

from ai_optimizer import CVOptimizer
from cv_change_tracker import build_cv_change_report
from cv_parser import parse_pdf_to_json
from docx_generator import generate_docx
from file_io import load_json, load_text
from output_paths import build_run_output_paths
from path_utils import project_path
from pdf_generator import generate_pdf
from scraper import scrape_job_description


def _capture_logs(func, *args, **kwargs):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


def _write_bytes(relative_path, content):
    full_path = project_path(relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as file:
        file.write(content)


def _write_json(relative_path, payload):
    full_path = project_path(relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _write_text(relative_path, text):
    full_path = project_path(relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as file:
        file.write(text)


def _resolve_job_description(job_url, manual_job_text, logs):
    if manual_job_text and manual_job_text.strip():
        logs.append("[*] Is ilani metni manuel alandan kullanildi.")
        return manual_job_text.strip()

    if job_url and job_url.strip():
        logs.append(f"[*] Is ilani URL uzerinden cekiliyor: {job_url}")
        text, scrape_logs = _capture_logs(scrape_job_description, job_url.strip())
        if scrape_logs.strip():
            logs.extend(scrape_logs.strip().splitlines())
        if text and len(text.strip()) >= 50:
            return text

    try:
        fallback_text = load_text("ilan.txt")
        logs.append("[*] URL/metin uygun degildi. ilan.txt fallback kullanildi.")
        return fallback_text
    except Exception:
        logs.append("[!] Is ilani metni bulunamadi. URL, metin veya ilan.txt gerekli.")
        return ""


def _resolve_base_cv_data(config, uploaded_json_text, uploaded_pdf_bytes, uploaded_pdf_name, logs, timestamp):
    if uploaded_json_text and uploaded_json_text.strip():
        logs.append("[*] Base CV JSON yuklemesi kullaniliyor.")
        return json.loads(uploaded_json_text)

    if uploaded_pdf_bytes:
        safe_name = uploaded_pdf_name or f"uploaded_{timestamp}.pdf"
        pdf_relative = f"data/uploads/{timestamp}_{safe_name}"
        parsed_relative = f"data/uploads/parsed_cv_{timestamp}.json"
        _write_bytes(pdf_relative, uploaded_pdf_bytes)
        logs.append(f"[*] PDF kaydedildi: {pdf_relative}")

        ok, parser_logs = _capture_logs(
            parse_pdf_to_json,
            pdf_path=pdf_relative,
            output_json_path=parsed_relative,
            api_key=config["GEMINI_API_KEY"],
        )
        if parser_logs.strip():
            logs.extend(parser_logs.strip().splitlines())
        if not ok:
            raise RuntimeError("PDF parse islemi basarisiz.")

        return load_json(parsed_relative)

    logs.append("[*] Yukleme yok. Config icindeki BASE_CV_PATH kullaniliyor.")
    return load_json(config["BASE_CV_PATH"])


def run_dashboard_pipeline(config, uploaded_json_text, uploaded_pdf_bytes, uploaded_pdf_name, job_url, job_text):
    logs = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        base_cv = _resolve_base_cv_data(
            config,
            uploaded_json_text,
            uploaded_pdf_bytes,
            uploaded_pdf_name,
            logs,
            timestamp,
        )

        job_description = _resolve_job_description(job_url, job_text, logs)
        if not job_description or len(job_description.strip()) < 50:
            raise RuntimeError("Is ilani metni cok kisa veya bos.")

        logs.append("[*] AI optimizasyon baslatildi.")
        optimizer = CVOptimizer(api_key=config["GEMINI_API_KEY"])
        bilingual_cv, optimize_logs = _capture_logs(optimizer.optimize_bilingual, base_cv, job_description)
        if optimize_logs.strip():
            logs.extend(optimize_logs.strip().splitlines())

        if not bilingual_cv or "tr" not in bilingual_cv or "en" not in bilingual_cv:
            raise RuntimeError("Bilingual optimizasyon sonucu gecersiz.")

        bilingual_cv["tr"]["title"] = base_cv.get("title", "Software Engineer")
        bilingual_cv["en"]["title"] = base_cv.get("title", "Software Engineer")

        output_paths = build_run_output_paths(config["OUTPUT_PDF_PATH"], timestamp)

        tr_pdf_ok, tr_pdf_logs = _capture_logs(generate_pdf, bilingual_cv["tr"], config["TEMPLATE_PATH"], output_paths["tr_pdf"])
        en_pdf_ok, en_pdf_logs = _capture_logs(generate_pdf, bilingual_cv["en"], config["TEMPLATE_PATH"], output_paths["en_pdf"])
        tr_docx_ok, tr_docx_logs = _capture_logs(generate_docx, bilingual_cv["tr"], output_paths["tr_docx"])
        en_docx_ok, en_docx_logs = _capture_logs(generate_docx, bilingual_cv["en"], output_paths["en_docx"])

        for chunk in [tr_pdf_logs, en_pdf_logs, tr_docx_logs, en_docx_logs]:
            if chunk.strip():
                logs.extend(chunk.strip().splitlines())

        if not (tr_pdf_ok and en_pdf_ok and tr_docx_ok and en_docx_ok):
            raise RuntimeError("Cikti dosyalarinin bir kismi olusturulamadi.")

        tr_change = build_cv_change_report(base_cv, bilingual_cv["tr"])
        en_change = build_cv_change_report(base_cv, bilingual_cv["en"])

        run_dir = output_paths["run_dir"]
        _write_json(os.path.join(run_dir, "base_cv.json"), base_cv)
        _write_json(os.path.join(run_dir, "optimized_cv_tr.json"), bilingual_cv["tr"])
        _write_json(os.path.join(run_dir, "optimized_cv_en.json"), bilingual_cv["en"])
        _write_json(os.path.join(run_dir, "changes_tr.json"), tr_change)
        _write_json(os.path.join(run_dir, "changes_en.json"), en_change)

        metadata = {
            "timestamp": timestamp,
            "run_dir": run_dir,
            "job_url": job_url,
            "job_text_used": bool(job_text and job_text.strip()),
            "files": {
                "tr_pdf": output_paths["tr_pdf"],
                "en_pdf": output_paths["en_pdf"],
                "tr_docx": output_paths["tr_docx"],
                "en_docx": output_paths["en_docx"],
            },
            "change_summary": {
                "tr": tr_change["summary"],
                "en": en_change["summary"],
            },
        }

        _write_json(os.path.join(run_dir, "run_metadata.json"), metadata)
        _write_text(os.path.join(run_dir, "process.log"), "\n".join(logs))

        return {
            "ok": True,
            "metadata": metadata,
            "base_cv": base_cv,
            "bilingual_cv": bilingual_cv,
            "changes": {"tr": tr_change, "en": en_change},
            "logs": logs,
        }
    except Exception as error:
        logs.append(f"[!] Hata: {error}")
        logs.extend(traceback.format_exc().splitlines())
        return {
            "ok": False,
            "error": str(error),
            "logs": logs,
        }


def list_previous_runs(base_output_path):
    output_root = os.path.dirname(base_output_path) or "output"
    full_root = project_path(output_root)
    if not os.path.exists(full_root):
        return []

    runs = []
    for name in sorted(os.listdir(full_root), reverse=True):
        run_dir_relative = os.path.join(output_root, name)
        metadata_relative = os.path.join(run_dir_relative, "run_metadata.json")
        metadata_full = project_path(metadata_relative)
        if not os.path.isdir(project_path(run_dir_relative)):
            continue
        if not os.path.exists(metadata_full):
            continue

        try:
            with open(metadata_full, "r", encoding="utf-8") as file:
                data = json.load(file)
            runs.append(data)
        except Exception:
            continue

    return runs
