import json
import os
from pathlib import Path

import streamlit as st

from dashboard_service import list_previous_runs, run_dashboard_pipeline
from file_io import load_json
from path_utils import project_path


def _render_file_links(files_map):
    st.subheader("Cikti Dosyalari")
    for label, relative_path in files_map.items():
        absolute_path = Path(project_path(relative_path)).resolve()
        st.write(f"{label}: {relative_path}")
        st.link_button(f"Dosyayi Ac ({label})", absolute_path.as_uri())


def _render_change_table(title, change_data):
    st.subheader(title)
    summary = change_data.get("summary", {})
    st.write(
        {
            "changed": summary.get("changed_count", 0),
            "added": summary.get("added_count", 0),
            "removed": summary.get("removed_count", 0),
        }
    )

    if change_data.get("changed"):
        st.caption("Degisen Alanlar")
        st.dataframe(change_data["changed"], use_container_width=True)
    if change_data.get("added"):
        st.caption("Eklenen Alanlar")
        st.dataframe(change_data["added"], use_container_width=True)
    if change_data.get("removed"):
        st.caption("Silinen Alanlar")
        st.dataframe(change_data["removed"], use_container_width=True)


def _open_folder_button(relative_run_dir):
    full = project_path(relative_run_dir)
    if st.button("Klasoru Windows Explorer'da Ac"):
        try:
            os.startfile(full)
            st.success("Klasor acildi.")
        except Exception as error:
            st.error(f"Klasor acilamadi: {error}")


def main():
    st.set_page_config(page_title="CV Optimizer Dashboard", layout="wide")
    st.title("CV Optimizer Dashboard")

    try:
        config = load_json("config.json")
    except Exception as error:
        st.error(f"config.json okunamadi: {error}")
        return

    with st.sidebar:
        st.header("Ayarlar")
        api_key = st.text_input("Gemini API Key", value=config.get("GEMINI_API_KEY", ""), type="password")
        st.caption("Bos birakma. Kaydetmek icin asagidaki butonla config guncelle.")
        if st.button("Bu oturumda API key kullan"):
            config["GEMINI_API_KEY"] = api_key
            st.success("Bu oturum icin API key guncellendi.")

        st.divider()
        st.header("Gecmis Calismalar")
        previous_runs = list_previous_runs(config.get("OUTPUT_PDF_PATH", "output/optimized_cv.pdf"))
        if previous_runs:
            selected = st.selectbox(
                "Calisma sec",
                options=range(len(previous_runs)),
                format_func=lambda i: previous_runs[i].get("run_dir", "run"),
            )
            selected_run = previous_runs[selected]
            st.write(selected_run.get("change_summary", {}))
            if st.button("Secili Calismayi Ac"):
                try:
                    os.startfile(project_path(selected_run.get("run_dir", "output")))
                except Exception as error:
                    st.error(str(error))
        else:
            st.caption("Henuz run yok.")

    st.header("Girdi")
    col1, col2 = st.columns(2)

    with col1:
        uploaded_pdf = st.file_uploader("PDF CV Yukle", type=["pdf"])
        uploaded_json = st.file_uploader("JSON CV Yukle", type=["json"])

    with col2:
        job_mode = st.radio("Is Ilani Giris Tipi", ["URL", "Metin"], horizontal=True)
        job_url = ""
        job_text = ""
        if job_mode == "URL":
            job_url = st.text_input("Is Ilani URL")
        else:
            job_text = st.text_area("Is Ilani Metni", height=200)

    run_clicked = st.button("Optimizasyonu Baslat", type="primary", use_container_width=True)

    if run_clicked:
        if not config.get("GEMINI_API_KEY"):
            st.error("GEMINI_API_KEY gerekli.")
            return

        with st.spinner("Calistiriliyor..."):
            uploaded_json_text = ""
            if uploaded_json is not None:
                uploaded_json_text = uploaded_json.read().decode("utf-8", errors="ignore")

            uploaded_pdf_bytes = None
            uploaded_pdf_name = ""
            if uploaded_pdf is not None:
                uploaded_pdf_bytes = uploaded_pdf.getvalue()
                uploaded_pdf_name = uploaded_pdf.name

            result = run_dashboard_pipeline(
                config=config,
                uploaded_json_text=uploaded_json_text,
                uploaded_pdf_bytes=uploaded_pdf_bytes,
                uploaded_pdf_name=uploaded_pdf_name,
                job_url=job_url,
                job_text=job_text,
            )
            st.session_state["last_result"] = result

    result = st.session_state.get("last_result")
    if not result:
        st.info("Bir run baslattiginda sonuc, log ve degisiklikler burada gosterilecek.")
        return

    if not result.get("ok"):
        st.error(result.get("error", "Bilinmeyen hata"))
        st.subheader("Loglar")
        st.code("\n".join(result.get("logs", [])), language="text")
        return

    metadata = result["metadata"]
    files = metadata.get("files", {})

    st.success("Run tamamlandi.")
    st.write({"run_dir": metadata.get("run_dir"), "timestamp": metadata.get("timestamp")})

    tab_result, tab_changes, tab_logs, tab_cv = st.tabs(["Ciktilar", "Degisiklikler", "Loglar", "CV Sonucu"])

    with tab_result:
        _render_file_links(files)
        _open_folder_button(metadata.get("run_dir", "output"))

        for label, relative_path in files.items():
            abs_path = project_path(relative_path)
            if os.path.exists(abs_path):
                with open(abs_path, "rb") as file:
                    st.download_button(
                        label=f"Indir: {label}",
                        data=file.read(),
                        file_name=os.path.basename(abs_path),
                    )

    with tab_changes:
        _render_change_table("TR Degisiklikleri", result["changes"]["tr"])
        _render_change_table("EN Degisiklikleri", result["changes"]["en"])

    with tab_logs:
        st.code("\n".join(result.get("logs", [])), language="text")

    with tab_cv:
        cv_lang = st.radio("Goruntulenecek CV", ["tr", "en"], horizontal=True)
        st.json(result["bilingual_cv"][cv_lang])


if __name__ == "__main__":
    main()
