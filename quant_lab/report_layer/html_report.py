"""HTML report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Template


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{{ title }}</title>
  <style>
    body { font-family: "Microsoft YaHei", sans-serif; margin: 32px; color: #1f2937; background: #f8fafc; }
    h1, h2, h3 { color: #0f172a; }
    .warning { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; padding: 12px 16px; margin-bottom: 20px; border-radius: 8px; }
    .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 18px; min-width: 160px; }
    .card-label { font-size: 12px; color: #6b7280; text-transform: uppercase; }
    .card-value { font-size: 22px; font-weight: 700; margin-top: 4px; }
    .section { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; margin-bottom: 18px; }
    table { border-collapse: collapse; width: 100%; margin-top: 12px; }
    th, td { border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; vertical-align: top; }
    th { background: #f3f4f6; }
    img { max-width: 100%; border: 1px solid #e5e7eb; margin-top: 12px; border-radius: 6px; background: white; }
    ul { margin-top: 8px; }
    .muted { color: #6b7280; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <p class="muted">Generated at {{ generated_at }}</p>

  {% if short_sample_warning %}
  <div class="warning">
    <strong>Short Sample Warning:</strong> {{ warning_message }}
  </div>
  {% endif %}

  <div class="cards">
    {% for card in summary_cards %}
    <div class="card">
      <div class="card-label">{{ card.label }}</div>
      <div class="card-value">{{ card.value }}</div>
    </div>
    {% endfor %}
  </div>

  <div class="section">
    <h2>Run Environment</h2>
    <p>Workspace: {{ run_environment.workspace }}</p>
    <p>Figures: {{ run_environment.figure_dir }}</p>
    <p>Tables: {{ run_environment.table_dir }}</p>
  </div>

  <div class="section">
    <h2>Backtest Convention</h2>
    <ul>
      {% for item in backtest_assumptions %}
      <li>{{ item }}</li>
      {% endfor %}
    </ul>
  </div>

  <div class="section">
    <h2>Sample Summary</h2>
    <p>Sample Start: {{ sample_summary.sample_start }}</p>
    <p>Sample End: {{ sample_summary.sample_end }}</p>
    <p>Trading Days: {{ sample_summary.trading_days }}</p>
  </div>

  <div class="section">
    <h2>Performance Summary</h2>
    {{ performance_table | safe }}
  </div>

  <div class="section">
    <h2>NAV</h2>
    <img src="{{ figures.nav }}" alt="NAV" />
  </div>

  <div class="section">
    <h2>Drawdown</h2>
    <img src="{{ figures.drawdown }}" alt="Drawdown" />
  </div>

  <div class="section">
    <h2>Turnover</h2>
    <img src="{{ figures.turnover }}" alt="Turnover" />
  </div>

  {% if include_strategy_section %}
  <div class="section">
    <h2>Strategy Summary</h2>
    <p>Rebalance Days: {{ strategy_summary.rebalance_days }}</p>
    <p>Average Candidate Count: {{ "%.2f"|format(strategy_summary.avg_candidate_count) }}</p>
    <p>Average Selected Count: {{ "%.2f"|format(strategy_summary.avg_selected_count) }}</p>
    {{ strategy_table | safe }}
  </div>
  {% endif %}

  {% if include_factor_section %}
  <div class="section">
    <h2>Factor Summary</h2>
    <p>Research Rows: {{ factor_summary.research_rows }}</p>
    <p>Screening Rows: {{ factor_summary.screening_rows }}</p>
    <p>Metadata Rows: {{ factor_summary.metadata_rows }}</p>
    {{ factor_table | safe }}
    <img src="{{ figures.screening_distribution }}" alt="Screening Distribution" />
  </div>
  {% endif %}

  {% if figures.correlation_heatmap %}
  <div class="section">
    <h2>Factor Correlation</h2>
    <img src="{{ figures.correlation_heatmap }}" alt="Correlation Heatmap" />
  </div>
  {% endif %}

  {% if include_trade_table %}
  <div class="section">
    <h2>Top Trades</h2>
    {{ top_trades_table | safe }}
  </div>
  {% endif %}

  <div class="section">
    <h2>Latest Positions</h2>
    {{ latest_positions_table | safe }}
  </div>

  <div class="section">
    <h2>Limitations</h2>
    <ul>
      <li>Current report is for research and structure validation only.</li>
      <li>Current execution convention is next_open.</li>
      <li>Current engine does not support suspension, limit-up/down, or complex slippage.</li>
      <li>Current strategy is long-only and equal-weight.</li>
    </ul>
  </div>
</body>
</html>
"""


def build_html_report(context: dict[str, Any], output_path: Path) -> None:
    """Render minimal HTML report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    template = Template(HTML_TEMPLATE)
    html = template.render(**context)
    output_path.write_text(html, encoding="utf-8")
