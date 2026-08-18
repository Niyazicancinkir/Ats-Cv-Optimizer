import os


def build_run_output_paths(base_pdf_path, timestamp):
    output_dir = os.path.dirname(base_pdf_path) or "output"
    base_name = os.path.splitext(os.path.basename(base_pdf_path))[0]
    run_dir = os.path.join(output_dir, f"{base_name}_{timestamp}")

    return {
        "run_dir": run_dir,
        "tr_pdf": os.path.join(run_dir, f"{base_name}_TR.pdf"),
        "en_pdf": os.path.join(run_dir, f"{base_name}_EN.pdf"),
        "tr_docx": os.path.join(run_dir, f"{base_name}_TR.docx"),
        "en_docx": os.path.join(run_dir, f"{base_name}_EN.docx"),
    }