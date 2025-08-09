PRIMARY = "#5B8DEF"  # Azure
SECONDARY = "#9C27B0"  # Purple
ACCENT = "#00C853"  # Green
DANGER = "#E53935"  # Red
WARNING = "#F59E0B"  # Amber
TEXT = "#1F2937"
MUTED = "#6B7280"
BACKGROUND = "#F8FAFC"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"
DARK_TEXT = "#E5E7EB"
DARK_BG = "#0B1020"
DARK_CARD = "#121931"
DARK_BORDER = "#283149"

CSS = f"""
<style>
:root {{
  --primary: {PRIMARY};
  --secondary: {SECONDARY};
  --accent: {ACCENT};
  --danger: {DANGER};
  --warning: {WARNING};
  --text: {TEXT};
  --muted: {MUTED};
  --bg: {BACKGROUND};
  --card: {CARD_BG};
  --border: {BORDER};
}}

@media (prefers-color-scheme: dark) {{
  :root {{
    --text: {DARK_TEXT};
    --bg: {DARK_BG};
    --card: {DARK_CARD};
    --border: {DARK_BORDER};
  }}
}}

/* Global */
html, body, [class*="css"]  {{
  font-family: Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  color: var(--text);
}}

/* Container */
.block-container {{
  padding-top: 2.2rem; /* increase to avoid header overlap/clipping */
}}

/* Hero */
.hero {{
  background: linear-gradient(135deg, rgba(91,141,239,0.14), rgba(156,39,176,0.10));
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 20px 18px; /* extra top padding prevents text clipping */
  margin: 8px 0 12px; /* small top margin to separate from app toolbar */
  overflow: visible; /* ensure no clipping */
}}
.hero h2 {{
  margin: 0;
  padding-top: 2px; /* guard against font ascender clipping */
  line-height: 1.15;
  color: var(--primary);
}}
.hero .subtitle {{
  color: var(--muted);
  margin-top: 4px;
}}

/* Cards */
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.2rem;
  box-shadow: 0 6px 18px rgba(31,41,55,0.06);
  margin-bottom: 14px;
}}

/* Badges / Chips */
.badge {{
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: var(--primary);
  color: white;
}}
.chip {{
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  margin-right: 6px;
  margin-bottom: 6px;
  border: 1px solid var(--border);
  background: rgba(91,141,239,0.12);
  color: var(--text);
}}
.chip.warn {{ background: rgba(245,158,11,0.14); }}
.chip.ok {{ background: rgba(0,200,83,0.12); }}
.chip.danger {{ background: rgba(229,57,53,0.12); }}

/* Buttons */
.btn-primary {{
  background: linear-gradient(90deg, {PRIMARY}, {SECONDARY});
  color: white;
  border: none;
  padding: 0.6rem 1rem;
  border-radius: 10px;
}}

/* Tables */
.table thead th {{
  background: #EEF2FF;
}}

.muted {{ color: var(--muted); }}
</style>
"""
