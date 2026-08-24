#!/usr/bin/env python3
"""
Lightweight local preview renderer for the KJMD 2026 site.

This is a FALLBACK for machines without a Jekyll-capable Ruby. It renders the
Liquid templates well enough to check layout and styling, but it is NOT Jekyll:
the published site is always built by GitHub Pages. When in doubt, use the
Jekyll path in the launcher.
"""
import os, re, io, glob, sys, shutil
import yaml
from liquid import Environment, FileSystemLoader

# The repo root is the parent of this script's directory (preview/).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "preview", "_site")

# Jekyll's {% include a.html k=v %} isn't standard Liquid. These includes are
# all inside `{% if page.toc %}` (false on every page), so blank them for preview.
def sanitize(s):
    # jekyll-include-cache tag -> plain include
    s = re.sub(r'\{%\s*include_cached\s+', '{% include ', s)
    s = re.sub(r'\{%\s*include\s+toc\.html[^%]*%\}', '', s)
    # python-liquid is stricter than Ruby Liquid about `contains` on a number.
    # overlay_filter is a float in our front matter; the branch is preview-only noise.
    s = s.replace('{% if page.header.overlay_filter contains "gradient" %}', '{% if false %}')
    s = re.sub(r'\{%\s*include\s+([\w./-]+)\s+[^%]*%\}', r'{% include "\1" %}', s)
    s = re.sub(r'\{%\s*include\s+([\w./-]+)\s*%\}', r'{% include "\1" %}', s)
    s = s.replace('{% include "/comments-providers/', '{% include "comments-providers/')
    return s

cfg = yaml.safe_load(io.open(os.path.join(ROOT,'_config.yml'),encoding='utf-8'))
baseurl = cfg.get('baseurl','') or ''

# --- site.data ---
data = {}
for f in glob.glob(os.path.join(ROOT,'_data','*.yml')):
    data[os.path.splitext(os.path.basename(f))[0]] = yaml.safe_load(io.open(f,encoding='utf-8'))

# --- site.static_files (hero images) ---
static_files = []
for f in sorted(glob.glob(os.path.join(ROOT,'assets','images','**','*'), recursive=True)):
    if os.path.isfile(f):
        rel = '/' + os.path.relpath(f, ROOT).replace(os.sep,'/')
        static_files.append({'path': rel, 'name': os.path.basename(f),
                             'extname': os.path.splitext(f)[1],
                             'basename': os.path.splitext(os.path.basename(f))[0]})

site = dict(cfg)
site.update({'data': data, 'static_files': static_files, 'time': '2026-08-24',
             'baseurl': baseurl, 'url': cfg.get('url','')})

# Liquid env: templates live in _includes and _layouts.
# Sanitize at load time so included partials get the same treatment.
os.makedirs(OUT, exist_ok=True)

# Pre-sanitize every include/layout into a temp tree, then load from there.
# Sanitized templates are build scratch; keep them out of the served tree.
TMP = os.path.join(os.path.dirname(OUT), '_templates')
for sub in ('_includes','_layouts'):
    for f in glob.glob(os.path.join(ROOT,sub,'**','*'), recursive=True):
        if not os.path.isfile(f): continue
        rel = os.path.relpath(f, os.path.join(ROOT,sub))
        dst = os.path.join(TMP, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            txt = io.open(f,encoding='utf-8').read()
        except UnicodeDecodeError:
            shutil.copy(f,dst); continue
        io.open(dst,'w',encoding='utf-8').write(sanitize(txt))

# Some partials come from the remote theme and aren't vendored here; stub them.
for missing in ('comments-providers/scripts.html','analytics-providers/custom.html'):
    d = os.path.join(TMP, os.path.dirname(missing))
    os.makedirs(d, exist_ok=True)
    fp = os.path.join(TMP, missing)
    if not os.path.exists(fp):
        io.open(fp,'w',encoding='utf-8').write('')

env = Environment(loader=FileSystemLoader(TMP))

# Jekyll filters we actually use
def relative_url(v, *a):
    v = '' if v is None else str(v)
    if v.startswith('http'): return v
    return baseurl + v if v.startswith('/') else baseurl + '/' + v
def absolute_url(v, *a):
    v = '' if v is None else str(v)
    if v.startswith('http'): return v
    return (site.get('url') or '') + relative_url(v)
def markdownify(v, *a): return v if v is not None else ''
def strip_html(v, *a): return re.sub(r'<[^>]+>','', v or '')
def strip_newlines(v, *a): return (v or '').replace('\n',' ')
def escape_once(v, *a): return v if v is not None else ''
def jsonify(v, *a):
    import json; return json.dumps(v)
def date_to_xmlschema(v, *a): return str(v)
def slugify(v, *a): return re.sub(r'[^a-z0-9]+','-', str(v).lower()).strip('-')
def where_exp(seq, var, expr):
    # only used as: where_exp:"f","f.path contains hero_dir"
    m = re.match(r'\s*\w+\.(\w+)\s+contains\s+(.+)', expr)
    if not m or not seq: return []
    key, needle = m.group(1), m.group(2).strip()
    if needle[:1] in '"\'':
        needle = needle.strip('"\'')
    else:
        # a variable reference; the only one used on this site
        needle = '/assets/images/hero'
    return [x for x in seq if needle in str(x.get(key,''))]

for name, fn in [('relative_url',relative_url),('absolute_url',absolute_url),
                 ('markdownify',markdownify),('strip_html',strip_html),
                 ('strip_newlines',strip_newlines),('escape_once',escape_once),
                 ('jsonify',jsonify),('date_to_xmlschema',date_to_xmlschema),
                 ('slugify',slugify),('where_exp',where_exp)]:
    env.add_filter(name, fn)

def front_matter(path):
    s = io.open(path,encoding='utf-8').read()
    s = sanitize(s)
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', s, re.S)
    if not m: return {}, s
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)

def render_page(page_file):
    page, body = front_matter(page_file)
    # Ruby Liquid coerces for `contains`; python-liquid does not. Jekyll accepts
    # both forms here, so stringify for the preview.
    hdr = page.get('header')
    if isinstance(hdr, dict) and 'overlay_filter' in hdr:
        hdr['overlay_filter'] = str(hdr['overlay_filter'])
    content = body
    layout = page.get('layout')
    seen = 0
    while layout and seen < 10:
        seen += 1
        lp = os.path.join(ROOT,'_layouts',layout+'.html')
        lfm, lbody = front_matter(lp)
        tpl = env.from_string(lbody)
        content = tpl.render(site=site, page=page, content=content,
                             layout=lfm, paginator=None, jekyll={'environment':'production'})
        layout = lfm.get('layout')
    return content

# Pages live under the baseurl so links resolve exactly as they do live.
SITE = os.path.join(OUT, baseurl.strip('/')) if baseurl else OUT
os.makedirs(SITE, exist_ok=True)

# Mirror Jekyll's permalink layout: /venue/ -> venue/index.html, so the
# links in the nav resolve exactly as they do on the published site.
pages = [(os.path.join(ROOT,'index.html'), 'index.html')]
for f in sorted(glob.glob(os.path.join(ROOT,'_pages','*.md'))):
    fm,_ = front_matter(f)
    perm = (fm.get('permalink') or '/').strip('/')
    pages.append((f, os.path.join(perm, 'index.html') if perm else 'index.html'))

for src, dest in pages:
    try:
        html = render_page(src)
        dest_path = os.path.join(SITE, dest)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        io.open(dest_path,'w',encoding='utf-8').write(html)
        print("OK   ", dest)
    except Exception as e:
        print("FAIL ", dest, type(e).__name__, str(e)[:300])


# ---------------------------------------------------------------------------
# Assets: compile the stylesheet and copy everything the pages reference.
# ---------------------------------------------------------------------------

def build_css():
    """Compile assets/css/main.scss the way Jekyll would."""
    src = io.open(os.path.join(ROOT, 'assets/css/main.scss'), encoding='utf-8').read()
    src = re.sub(r'^---.*?---\n', '', src, count=1, flags=re.S)
    skin = cfg.get('minimal_mistakes_skin') or 'default'
    src = src.replace("{{ site.minimal_mistakes_skin | default: 'default' }}", skin)

    tmp_scss = os.path.join(OUT, '_main.scss')
    io.open(tmp_scss, 'w', encoding='utf-8').write(src)

    out_css = os.path.join(SITE, 'assets/css/main.css')
    os.makedirs(os.path.dirname(out_css), exist_ok=True)

    import subprocess
    for cmd in (['sass'], ['npx', '--yes', 'sass@1.77.8']):
        try:
            r = subprocess.run(
                cmd + ['--no-source-map', '--quiet',
                       '--load-path', os.path.join(ROOT, '_sass'),
                       tmp_scss, out_css],
                capture_output=True, text=True)
            if r.returncode == 0:
                return True
            # A real compile error should be shown, not silently retried.
            if 'Error' in (r.stderr or ''):
                print('\nCSS 编译失败:\n' + r.stderr.strip()[:1500])
                return False
        except FileNotFoundError:
            continue
    print('\n找不到 sass 编译器（需要 Node 或 dart-sass），页面将没有样式。')
    return False


def copy_assets():
    for sub in ('images', 'js'):
        srcd = os.path.join(ROOT, 'assets', sub)
        if not os.path.isdir(srcd):
            continue
        dstd = os.path.join(SITE, 'assets', sub)
        if os.path.isdir(dstd):
            shutil.rmtree(dstd)
        shutil.copytree(srcd, dstd)
    fav = os.path.join(ROOT, 'favicon.ico')
    if os.path.exists(fav):
        shutil.copy(fav, os.path.join(SITE, 'favicon.ico'))


copy_assets()
build_css()
print('\n预览已生成: ' + SITE)
