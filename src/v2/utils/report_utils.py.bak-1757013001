# src/v2/utils/report_utils.py

import os

def save_html_report(content: str, filename: str = "daily_report.html", folder: str = "src/v2/data/reports/") -> str:
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path