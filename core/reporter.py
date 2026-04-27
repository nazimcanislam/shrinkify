"""
reporter.py — Generates HTML and terminal reports.
"""

from pathlib import Path
from datetime import datetime
from core.scanner import MediaFile
from core.analyzer import AnalysisSummary


def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.2f} GB"


def _fmt_duration(seconds: float) -> str:
    if not seconds:
        return '—'
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def generate_html_report(
    media_files: list[MediaFile],
    summary: AnalysisSummary,
    scan_directory: Path,
    output_path: Path
) -> None:
    conversion_files = [mf for mf in media_files if mf.needs_conversion and not mf.is_duplicate]
    duplicate_files  = [mf for mf in media_files if mf.is_duplicate]
    modern_files     = [mf for mf in media_files if not mf.needs_conversion and not mf.is_duplicate]
    error_files      = [mf for mf in media_files if mf.scan_error]

    now = datetime.now().strftime("%B %d, %Y %H:%M")

    codec_labels = list(summary.video_codec_distribution.keys())
    codec_values = list(summary.video_codec_distribution.values())
    fmt_labels   = list(summary.image_format_distribution.keys())
    fmt_values   = list(summary.image_format_distribution.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shrinkify Report — {scan_directory.name}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');

  :root {{
    --bg: #0c0c0f;
    --surface: #13131a;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --accent: #6ee7b7;
    --accent2: #f59e0b;
    --accent3: #f87171;
    --text: #e2e8f0;
    --text-muted: #64748b;
    --text-dim: #94a3b8;
    --green: #4ade80;
    --yellow: #fbbf24;
    --red: #f87171;
    --blue: #60a5fa;
    --ui-font: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --mono-font: 'Space Mono', 'Courier New', monospace;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--ui-font);
    min-height: 100vh;
    line-height: 1.6;
  }}

  .noise {{
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none; z-index: 0;
  }}

  .container {{ max-width: 1200px; margin: 0 auto; padding: 48px 24px; position: relative; z-index: 1; }}

  .header {{ margin-bottom: 56px; }}
  .header-eyebrow {{ font-family: var(--mono-font); font-size: 11px; color: var(--accent); letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 12px; }}
  .header h1 {{ font-size: clamp(36px, 5vw, 64px); font-weight: 800; line-height: 1; letter-spacing: -0.02em; background: linear-gradient(135deg, #e2e8f0 0%, #6ee7b7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 16px; }}
  .header-meta {{ font-family: var(--mono-font); font-size: 12px; color: var(--text-muted); }}
  .header-meta span {{ color: var(--text-dim); margin: 0 8px; }}

  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 48px; }}
  .stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; position: relative; overflow: hidden; transition: border-color 0.2s; }}
  .stat-card:hover {{ border-color: var(--accent); }}
  .stat-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }}
  .stat-card.green::before {{ background: var(--green); }}
  .stat-card.yellow::before {{ background: var(--yellow); }}
  .stat-card.red::before {{ background: var(--red); }}
  .stat-card.blue::before {{ background: var(--blue); }}
  .stat-card.accent::before {{ background: var(--accent); }}
  .stat-label {{ font-size: 11px; font-family: var(--mono-font); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 8px; }}
  .stat-value {{ font-size: 32px; font-weight: 800; line-height: 1; margin-bottom: 4px; }}
  .stat-card.green .stat-value {{ color: var(--green); }}
  .stat-card.yellow .stat-value {{ color: var(--yellow); }}
  .stat-card.red .stat-value {{ color: var(--red); }}
  .stat-card.blue .stat-value {{ color: var(--blue); }}
  .stat-card.accent .stat-value {{ color: var(--accent); }}
  .stat-sub {{ font-size: 12px; color: var(--text-muted); font-family: var(--mono-font); }}

  .savings-banner {{ background: linear-gradient(135deg, #0d2b1e 0%, #1a1a24 50%, #2b1a0d 100%); border: 1px solid #2a4a3a; border-radius: 20px; padding: 32px 40px; margin-bottom: 48px; display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; align-items: center; gap: 24px; }}
  .savings-item {{ text-align: center; }}
  .savings-item .label {{ font-size: 11px; font-family: var(--mono-font); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 8px; }}
  .savings-item .amount {{ font-size: 28px; font-weight: 800; }}
  .savings-item .amount.current {{ color: var(--text); }}
  .savings-item .amount.saved {{ color: var(--green); }}
  .savings-item .amount.final {{ color: var(--accent); }}
  .savings-item .detail {{ font-size: 12px; color: var(--text-muted); font-family: var(--mono-font); margin-top: 4px; }}
  .savings-arrow {{ font-size: 32px; color: var(--accent); text-align: center; }}

  .section {{ margin-bottom: 48px; }}
  .section-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }}
  .section-title {{ font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }}
  .section-badge {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 20px; padding: 2px 10px; font-size: 12px; font-family: var(--mono-font); color: var(--text-muted); margin-left: auto; }}

  .table-wrap {{ border: 1px solid var(--border); border-radius: 12px; overflow: hidden; max-height: 500px; overflow-y: auto; }}
  .table-wrap::-webkit-scrollbar {{ width: 6px; }}
  .table-wrap::-webkit-scrollbar-track {{ background: var(--surface); }}
  .table-wrap::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead {{ position: sticky; top: 0; z-index: 2; }}
  th {{ background: var(--surface2); padding: 12px 16px; text-align: left; font-family: var(--mono-font); font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.15em; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid rgba(42,42,58,0.5); color: var(--text-dim); font-family: var(--mono-font); font-size: 12px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--surface2); color: var(--text); }}
  .filename-cell {{ color: var(--text); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.05em; }}
  .badge-video  {{ background: rgba(96,165,250,0.15); color: var(--blue);   border: 1px solid rgba(96,165,250,0.3); }}
  .badge-image  {{ background: rgba(110,231,183,0.15); color: var(--accent); border: 1px solid rgba(110,231,183,0.3); }}
  .badge-modern {{ background: rgba(74,222,128,0.15);  color: var(--green);  border: 1px solid rgba(74,222,128,0.3); }}
  .badge-dup    {{ background: rgba(248,113,113,0.15); color: var(--red);    border: 1px solid rgba(248,113,113,0.3); }}
  .badge-error  {{ background: rgba(251,191,36,0.15);  color: var(--yellow); border: 1px solid rgba(251,191,36,0.3); }}
  .savings-cell {{ color: var(--green); font-weight: 700; }}
  .reason-cell  {{ color: var(--accent2); }}
  th.sortable {{ cursor: pointer; user-select: none; }}
  th.sortable:hover {{ color: var(--accent); }}
  th.sortable .sort-icon {{ display: inline-block; margin-left: 5px; opacity: 0.35; font-style: normal; font-size: 9px; }}
  th.sortable.asc .sort-icon::after {{ content: '▲'; opacity: 1; }}
  th.sortable.desc .sort-icon::after {{ content: '▼'; opacity: 1; }}
  th.sortable:not(.asc):not(.desc) .sort-icon::after {{ content: '⇅'; }}
  th.sortable.asc {{ color: var(--accent); }}
  th.sortable.desc {{ color: var(--accent); }}

  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 48px; }}
  .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; }}
  .chart-title {{ font-size: 13px; font-family: var(--mono-font); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 20px; }}
  .bar-item {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }}
  .bar-label {{ font-family: var(--mono-font); font-size: 11px; color: var(--text-dim); width: 80px; flex-shrink: 0; text-align: right; }}
  .bar-track {{ flex: 1; background: var(--surface2); border-radius: 4px; height: 8px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; }}
  .bar-count {{ font-family: var(--mono-font); font-size: 11px; color: var(--text-muted); width: 40px; text-align: right; flex-shrink: 0; }}

  .footer {{ margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; font-family: var(--mono-font); font-size: 11px; color: var(--text-muted); }}

  @media (max-width: 768px) {{
    .savings-banner {{ grid-template-columns: 1fr; }}
    .savings-arrow {{ transform: rotate(90deg); }}
    .charts-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="noise"></div>
<div class="container">

  <div class="header">
    <div class="header-eyebrow">▸ Shrinkify Analysis Report</div>
    <h1>Media Analysis</h1>
    <div class="header-meta">{scan_directory} <span>·</span> {now}</div>
  </div>

  <div class="stats-grid">
    <div class="stat-card blue">
      <div class="stat-label">Total Files</div>
      <div class="stat-value">{summary.total_files:,}</div>
      <div class="stat-sub">{_fmt_size(summary.total_size_bytes)} total</div>
    </div>
    <div class="stat-card yellow">
      <div class="stat-label">Conversion Candidates</div>
      <div class="stat-value">{summary.videos_to_convert + summary.images_to_convert:,}</div>
      <div class="stat-sub">{summary.videos_to_convert} video · {summary.images_to_convert} image</div>
    </div>
    <div class="stat-card red">
      <div class="stat-label">Duplicates</div>
      <div class="stat-value">{summary.duplicate_count:,}</div>
      <div class="stat-sub">{_fmt_size(summary.duplicate_size_bytes)} recoverable</div>
    </div>
    <div class="stat-card green">
      <div class="stat-label">Estimated Total Savings</div>
      <div class="stat-value">{_fmt_size(summary.total_potential_savings_bytes)}</div>
      <div class="stat-sub">{summary.savings_percentage:.1f}% reduction</div>
    </div>
    <div class="stat-card accent">
      <div class="stat-label">Already Modern</div>
      <div class="stat-value">{summary.videos_already_modern + summary.images_already_modern:,}</div>
      <div class="stat-sub">No action needed</div>
    </div>
  </div>

  <div class="savings-banner">
    <div class="savings-item">
      <div class="label">Current Size</div>
      <div class="amount current">{_fmt_size(summary.total_size_bytes)}</div>
      <div class="detail">{summary.total_files:,} files</div>
    </div>
    <div class="savings-arrow">→</div>
    <div class="savings-item">
      <div class="label">Conversion Savings</div>
      <div class="amount saved">−{_fmt_size(summary.estimated_savings_bytes)}</div>
      <div class="detail">{summary.videos_to_convert + summary.images_to_convert:,} files to convert</div>
    </div>
    <div class="savings-arrow">+</div>
    <div class="savings-item">
      <div class="label">Duplicate Savings</div>
      <div class="amount saved">−{_fmt_size(summary.duplicate_savings_bytes)}</div>
      <div class="detail">{summary.duplicate_count:,} duplicates to delete</div>
    </div>
    <div class="savings-arrow">→</div>
    <div class="savings-item">
      <div class="label">Estimated Final Size</div>
      <div class="amount final">{_fmt_size(summary.total_size_bytes - summary.total_potential_savings_bytes)}</div>
      <div class="detail">{summary.savings_percentage:.1f}% smaller</div>
    </div>
  </div>

  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-title">Video Codec Distribution</div>
      {''.join(_bar_item(k, v, max(codec_values) if codec_values else 1, '#60a5fa') for k, v in sorted(summary.video_codec_distribution.items(), key=lambda x: -x[1])) if codec_values else '<div style="color:var(--text-muted);font-size:12px;font-family:var(--mono-font)">No videos found</div>'}
    </div>
    <div class="chart-card">
      <div class="chart-title">Image Format Distribution</div>
      {''.join(_bar_item(k, v, max(fmt_values) if fmt_values else 1, '#6ee7b7') for k, v in sorted(summary.image_format_distribution.items(), key=lambda x: -x[1])) if fmt_values else '<div style="color:var(--text-muted);font-size:12px;font-family:var(--mono-font)">No images found</div>'}
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-title">🔄 Conversion Candidates</div>
      <div class="section-badge">{len(conversion_files)} files</div>
    </div>
    {_conversion_table(conversion_files)}
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-title">🔁 Duplicate Files</div>
      <div class="section-badge">{len(duplicate_files)} files · {_fmt_size(summary.duplicate_size_bytes)}</div>
    </div>
    {_duplicate_table(duplicate_files)}
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-title">✅ Already Modern</div>
      <div class="section-badge">{len(modern_files)} files</div>
    </div>
    {_modern_table(modern_files)}
  </div>

  {_error_section(error_files)}

  <div class="footer">
    <span>Shrinkify — Media Optimization Tool</span>
    <span>Analyzed with ffmpeg + ffprobe</span>
  </div>

</div>
<script>
(function() {{
  function parseBytes(str) {{
    if (!str) return 0;
    str = str.replace(/[−\\-]/g, '').trim();
    // Strip percentage part like "(%70)"
    str = str.replace(/\\s*\\([^)]*\\)\\s*$/, '').trim();
    var units = {{'B':1,'KB':1024,'MB':1024*1024,'GB':1024*1024*1024}};
    var m = str.match(/^([\\d.,]+)\\s*([A-Z]+)$/);
    if (!m) return parseFloat(str.replace(/,/g,'')) || 0;
    return parseFloat(m[1].replace(/,/g,'')) * (units[m[2]] || 1);
  }}

  function cellVal(td) {{
    var raw = td.dataset.sort !== undefined ? td.dataset.sort : td.textContent.trim();
    var n = parseFloat(String(raw).replace(/,/g,''));
    if (!isNaN(n) && String(raw).replace(/,/g,'').match(/^-?[\\d.]+$/)) return n;
    // size strings
    var b = parseBytes(raw);
    if (b > 0) return b;
    return String(raw).toLowerCase();
  }}

  function makeSortable(table) {{
    var ths = table.querySelectorAll('thead th.sortable');
    ths.forEach(function(th, colIdx) {{
      th.addEventListener('click', function() {{
        var asc = th.classList.contains('asc') ? false : true;
        ths.forEach(function(t) {{ t.classList.remove('asc','desc'); }});
        th.classList.add(asc ? 'asc' : 'desc');
        var tbody = table.querySelector('tbody');
        var rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort(function(a, b) {{
          var tdA = a.querySelectorAll('td')[colIdx];
          var tdB = b.querySelectorAll('td')[colIdx];
          var vA = cellVal(tdA), vB = cellVal(tdB);
          if (typeof vA === 'number' && typeof vB === 'number') return asc ? vA - vB : vB - vA;
          return asc ? String(vA).localeCompare(String(vB)) : String(vB).localeCompare(String(vA));
        }});
        rows.forEach(function(r) {{ tbody.appendChild(r); }});
      }});
    }});
  }}

  document.querySelectorAll('table').forEach(makeSortable);
}})();
</script>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')


def _bar_item(label: str, value: int, max_val: int, color: str) -> str:
    pct = (value / max_val * 100) if max_val > 0 else 0
    return f'<div class="bar-item"><div class="bar-label">{label}</div><div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{color};"></div></div><div class="bar-count">{value:,}</div></div>'


def _conversion_table(files: list[MediaFile]) -> str:
    if not files:
        return '<div style="color:var(--text-muted);padding:20px;font-family:var(--mono-font);font-size:12px;">No conversion candidates — great!</div>'
    rows = []
    for mf in files:
        est = mf.estimated_output_size_bytes or 0
        saving = mf.size_bytes - est
        pct = (saving / mf.size_bytes * 100) if mf.size_bytes > 0 else 0
        badge = 'badge-video' if mf.media_type == 'video' else 'badge-image'
        badge_text = 'VIDEO' if mf.media_type == 'video' else 'IMAGE'
        savings_str = f'−{_fmt_size(saving)} ({pct:.1f}%)'
        rows.append(f'<tr>'
                    f'<td class="filename-cell" title="{mf.path}">{mf.filename}</td>'
                    f'<td><span class="badge {badge}">{badge_text}</span></td>'
                    f'<td data-sort="{mf.size_bytes}">{_fmt_size(mf.size_bytes)}</td>'
                    f'<td data-sort="{est}">{_fmt_size(est)}</td>'
                    f'<td class="savings-cell" data-sort="{saving}">{savings_str}</td>'
                    f'<td class="reason-cell">{mf.conversion_reason or "—"}</td>'
                    f'</tr>')
    th = lambda label: f'<th class="sortable">{label}<i class="sort-icon"></i></th>'
    header = (f'<tr>'
              f'{th("Filename")}{th("Type")}{th("Current")}{th("Estimated")}{th("Savings")}{th("Action")}'
              f'</tr>')
    return f'<div class="table-wrap"><table><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def _duplicate_table(files: list[MediaFile]) -> str:
    if not files:
        return '<div style="color:var(--text-muted);padding:20px;font-family:var(--mono-font);font-size:12px;">No duplicates found.</div>'
    rows = []
    for mf in files:
        rows.append(f'<tr>'
                    f'<td class="filename-cell" title="{mf.path}">{mf.filename}</td>'
                    f'<td data-sort="{mf.size_bytes}">{_fmt_size(mf.size_bytes)}</td>'
                    f'<td class="filename-cell" title="{mf.duplicate_of}">{mf.duplicate_of.name if mf.duplicate_of else "—"}</td>'
                    f'<td><span class="badge badge-dup">DUPLICATE</span></td>'
                    f'</tr>')
    th = lambda label: f'<th class="sortable">{label}<i class="sort-icon"></i></th>'
    header = f'<tr>{th("Filename")}{th("Size")}{th("Original")}{th("Status")}</tr>'
    return f'<div class="table-wrap"><table><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def _modern_table(files: list[MediaFile]) -> str:
    if not files:
        return '<div style="color:var(--text-muted);padding:20px;font-family:var(--mono-font);font-size:12px;">—</div>'
    rows = []
    for mf in files:
        codec = mf.video_codec.upper() if mf.video_codec else (mf.image_format or '—')
        badge = 'badge-video' if mf.media_type == 'video' else 'badge-image'
        badge_text = 'VIDEO' if mf.media_type == 'video' else 'IMAGE'
        rows.append(f'<tr>'
                    f'<td class="filename-cell" title="{mf.path}">{mf.filename}</td>'
                    f'<td><span class="badge {badge}">{badge_text}</span></td>'
                    f'<td data-sort="{mf.size_bytes}">{_fmt_size(mf.size_bytes)}</td>'
                    f'<td><span class="badge badge-modern">{codec}</span></td>'
                    f'</tr>')
    th = lambda label: f'<th class="sortable">{label}<i class="sort-icon"></i></th>'
    header = f'<tr>{th("Filename")}{th("Type")}{th("Size")}{th("Format")}</tr>'
    return f'<div class="table-wrap"><table><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def _error_section(files: list[MediaFile]) -> str:
    if not files:
        return ''
    rows = []
    for mf in files:
        rows.append(f'<tr>'
                    f'<td class="filename-cell" title="{mf.path}">{mf.filename}</td>'
                    f'<td data-sort="{mf.size_bytes}">{_fmt_size(mf.size_bytes)}</td>'
                    f'<td><span class="badge badge-error">SCAN ERROR</span></td>'
                    f'<td style="color:var(--yellow);font-size:11px;">{mf.scan_error or "—"}</td>'
                    f'</tr>')
    th = lambda label: f'<th class="sortable">{label}<i class="sort-icon"></i></th>'
    header = f'<tr>{th("Filename")}{th("Size")}{th("Status")}{th("Reason")}</tr>'
    table = f'<div class="table-wrap"><table><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table></div>'
    return f'<div class="section"><div class="section-header"><div class="section-title">⚠️ Scan Errors</div><div class="section-badge">{len(files)} files</div></div>{table}</div>'


def print_summary(summary: AnalysisSummary, scan_dir: Path) -> None:
    SEP = '─' * 52
    print(f"\n{SEP}")
    print(f"  SHRINKIFY — {scan_dir.name}")
    print(SEP)
    print(f"  Total files     : {summary.total_files:,}  ({_fmt_size(summary.total_size_bytes)})")
    print(f"  Videos          : {summary.video_count:,}  ({_fmt_size(summary.video_size_bytes)})")
    print(f"  Images          : {summary.image_count:,}  ({_fmt_size(summary.image_size_bytes)})")
    print(SEP)
    print(f"  Convert         : {summary.videos_to_convert + summary.images_to_convert:,} files  →  −{_fmt_size(summary.estimated_savings_bytes)}")
    print(f"  Duplicates      : {summary.duplicate_count:,} files  →  −{_fmt_size(summary.duplicate_savings_bytes)}")
    print(f"  ── Total savings: −{_fmt_size(summary.total_potential_savings_bytes)}  ({summary.savings_percentage:.1f}%)")
    print(f"  ── Estimated fin: {_fmt_size(summary.total_size_bytes - summary.total_potential_savings_bytes)}")
    print(SEP + "\n")