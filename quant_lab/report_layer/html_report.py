"""HTML report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Template


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{{ title }}</title>
  <style>
    body { font-family: "Microsoft YaHei", sans-serif; margin: 32px; color: #1f2937; }
    h1, h2 { color: #0f172a; }
    table { border-collapse: collapse; width: 640px; margin-top: 12px; }
    th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }
    th { background: #f3f4f6; }
    img { max-width: 960px; border: 1px solid #e5e7eb; margin-top: 16px; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <p>{{ summary }}</p>
  <h2>绩效指标</h2>
  {{ metrics_table | safe }}
  <h2>NAV 图</h2>
  <img src="{{ nav_figure }}" alt="NAV" />
</body>
</html>
"""


def build_html_report(title: str, summary: str, metrics_table: pd.DataFrame, nav_figure: str, output_path: Path) -> None:
    """Render a minimal HTML report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    template = Template(HTML_TEMPLATE)
    html = template.render(
        title=title,
        summary=summary,
        metrics_table=metrics_table.to_html(index=False),
        nav_figure=nav_figure,
    )
    output_path.write_text(html, encoding="utf-8")
