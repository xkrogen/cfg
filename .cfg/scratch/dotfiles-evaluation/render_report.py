#!/usr/bin/env python3
"""Render the report as a standalone, offline HTML file. Needs markdown and bs4."""
from pathlib import Path
import html
import markdown
from bs4 import BeautifulSoup

base = Path(__file__).resolve().parents[2]
source = base/'docs/dotfiles-evaluation-2026-11-06.md'
target = source.with_suffix('.html')
soup = BeautifulSoup(markdown.markdown(source.read_text(), extensions=['tables', 'fenced_code', 'toc']), 'html.parser')
title = soup.find('h1'); title.decompose()
subtitle = soup.find('p'); subtitle.decompose()
nav=[]
for index, section in enumerate(soup.find_all('h2'),1):
    nav.append(f'<a href="#{section["id"]}"><span>{index:02}</span>{html.escape(section.get_text())}</a>')
for table in soup.find_all('table'):
    wrapper=soup.new_tag('div',attrs={'class':'table-wrap','tabindex':'0','role':'region','aria-label':'Comparison table'})
    table.wrap(wrapper)
for p in soup.find_all('p'):
    if p.get_text().startswith(('Status:', 'Limits:', 'Git requirement:')):
        p['class']='callout'
css='''
:root{--ink:#172c40;--muted:#586a79;--teal:#006f68;--paper:#fff;--line:#dce5e8;--bg:#edf2f3;--amber:#9b6315}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--teal);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{color:#003c39}a:focus-visible{outline:3px solid #dfab59;outline-offset:4px}::selection{background:#bee5dd}
.layout{max-width:1510px;margin:auto;display:grid;grid-template-columns:260px minmax(0,1fr);gap:30px;padding:34px 32px 64px}.sidebar{position:sticky;top:30px;align-self:start;max-height:calc(100vh - 60px);overflow:auto}.brand{font-size:13px;font-weight:750;letter-spacing:.16em;text-transform:uppercase;color:var(--teal);margin:4px 0 20px}.nav-title{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--muted);margin:23px 0 12px}nav a{display:flex;gap:11px;align-items:baseline;color:#3f5666;font-size:13px;line-height:1.5;text-decoration:none;padding:8px 9px;border-left:2px solid transparent}nav a span{font-size:10px;color:#829399;font-variant-numeric:tabular-nums}nav a:hover,nav a.active{background:#dcebe7;border-color:var(--teal);color:#004f49}.sidebar-note{font-size:12px;line-height:1.65;border-top:1px solid #ccd9dc;margin-top:22px;padding-top:16px;color:var(--muted)}
main{min-width:0;background:var(--paper);box-shadow:0 6px 40px #172c400a;border:1px solid var(--line);border-radius:16px;overflow:hidden}.hero{background:var(--ink);color:white;padding:50px 54px 35px;position:relative}.eyebrow{font-size:11px;letter-spacing:.17em;text-transform:uppercase;color:#98d6c8;font-weight:700}.hero h1{font-size:clamp(34px,4vw,56px);line-height:1.09;letter-spacing:-.04em;max-width:720px;margin:16px 0 22px;font-weight:750}.hero p{color:#cad8df;font-size:15px;max-width:700px;margin:0}.hero-bottom{display:flex;flex-wrap:wrap;gap:30px;border-top:1px solid #ffffff24;padding-top:23px;margin-top:30px}.hero-bottom div{font-size:12px;color:#bdced4}.hero-bottom strong{display:block;color:white;font-size:23px;line-height:1.25;letter-spacing:-.02em}
.content{padding:8px 54px 52px}.content h2{font-size:27px;line-height:1.27;letter-spacing:-.025em;margin:52px 0 20px;padding-top:22px;border-top:1px solid var(--line);scroll-margin-top:24px}.content h2:first-child{border-top:0;margin-top:24px}.content h3{font-size:19px;line-height:1.45;margin:29px 0 12px;letter-spacing:-.01em}.content p{margin:0 0 18px}.content strong{font-weight:690}.content ol,.content ul{padding-left:24px}.content li{padding-left:5px;margin:0 0 15px}.callout{background:#eff7f4;border-left:4px solid var(--teal);padding:17px 20px;border-radius:0 8px 8px 0;font-size:14px}.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:9px;margin:22px 0 26px}table{border-collapse:collapse;width:100%;font-size:12.5px;line-height:1.55;min-width:590px}th{background:#eaf3f0;color:#154b48;text-align:left;font-weight:700;padding:13px 12px;vertical-align:top;border-bottom:1px solid #cddfd8}td{padding:12px;vertical-align:top;border-bottom:1px solid #e4ebed}tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#f8fafb}td:first-child{font-weight:610;min-width:125px}td:not(:first-child){min-width:110px}pre{background:#142a3b;color:#e1eaf0;font-size:12px;line-height:1.65;padding:21px 24px;border-radius:9px;overflow:auto;margin:22px 0;tab-size:2}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}p code,li code,td code{font-size:.85em;background:#eef2f3;padding:2px 4px;border-radius:4px;overflow-wrap:anywhere}.footer{background:#f5f8f8;border-top:1px solid var(--line);padding:22px 54px;color:var(--muted);font-size:12px}.content>p:has(a){overflow-wrap:anywhere}
@media(min-width:1250px){.content{font-size:16px}.table-wrap{margin-left:-15px;margin-right:-15px}}
@media(max-width:950px){.layout{display:block;padding:15px}.sidebar{position:static;max-height:none;margin-bottom:18px}.brand{margin-bottom:8px}nav{display:none}.nav-title,.sidebar-note{display:none}.hero{padding:32px 26px}.content{padding:5px 26px 35px}.content h2{font-size:24px}.footer{padding:20px 26px}}
@media print{body{background:white;font-size:10pt}.layout{display:block;padding:0}.sidebar{display:none}main{border:0;box-shadow:none}.hero{print-color-adjust:exact;padding:28px}.content{padding:0 10px}.content h2{break-after:avoid;font-size:18pt}.content h3{break-after:avoid}.table-wrap{overflow:visible}table{font-size:8pt;min-width:0}th,td{padding:7px}pre{white-space:pre-wrap;font-size:8pt;break-inside:avoid}.footer{display:none}}
'''
script='''const links=[...document.querySelectorAll('nav a')];const observer=new IntersectionObserver(es=>{for(const e of es){if(e.isIntersecting){links.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id));}}},{rootMargin:'-5% 0px -75% 0px'});document.querySelectorAll('h2').forEach(h=>observer.observe(h));'''
target.write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Dotdrop, GNU Stow, chezmoi, and mise dot evaluated for separate personal/work repositories and Mac/Linux machine profiles."><title>Dotfiles manager evaluation · Erik's cfg</title><style>{css}</style></head>
<body><div class="layout"><aside class="sidebar"><div class="brand">CFG / Field notes</div><div class="nav-title">In this report</div><nav aria-label="Report contents">{''.join(nav)}</nav><div class="sidebar-note">Research snapshot<br><strong>November 6, 2026</strong><br>America/Los_Angeles<br><br>Primary documentation + isolated CLI experiments.<br>No production migration.</div></aside>
<main><header class="hero"><div class="eyebrow">Personal infrastructure / decision report</div><h1>A better home<br>for your dotfiles.</h1><p>Four tools evaluated against your personal base, private work overlay, Mac laptop, and Linux server.</p><div class="hero-bottom"><div><strong>4 tools</strong>dotdrop · Stow · chezmoi · mise</div><div><strong>35 checks</strong>all sandbox assertions passed</div><div><strong>2 repo layers</strong>independent Git ownership</div></div></header><article class="content">{soup}</article><footer class="footer">Prepared for Erik · cfg research · November 6, 2026 · Standalone HTML, with no external assets or network dependencies.</footer></main></div><script>{script}</script></body></html>''')
print(target)
