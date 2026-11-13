#!/usr/bin/env python3
"""Verify defect fixes + 390px overflow, 44px targets, translations, favicon, links."""
import json, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8770/index.html"
EVID = Path("/workspace/community-bridge/evidence")
AFTER = EVID / "after"
AFTER.mkdir(parents=True, exist_ok=True)
out = {"passed":0,"failed":0,"tests":[],"links":[],"screenshots":[],"small_targets":[]}

def rec(name, ok, detail):
    out["tests"].append({"name":name,"status":"PASS" if ok else "FAIL","detail":detail})
    out["passed" if ok else "failed"] += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

ENGLISH_UI = re.compile(
    r"\b(Hours|Who it is for|Cost|Languages|Wheelchair access|Coverage|Website|Details|Hide details|Listen|National|Directions|Back to all needs|Verified local|Rechecked local|Not listed|Call 211)\b"
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width":1280,"height":900})

    # Favicon requests
    fav = {"ico": None, "png": None}
    def on_resp(resp):
        u = resp.url
        if u.endswith("favicon.ico") or u.endswith("/favicon.ico"):
            fav["ico"] = resp.status
        if u.endswith("favicon-32.png"):
            fav["png"] = resp.status
    page.on("response", on_resp)
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("#catGrid .cat")
    # also request explicitly
    ico_status = page.evaluate("""async () => { const r = await fetch('favicon.ico'); return r.status; }""")
    png_status = page.evaluate("""async () => { const r = await fetch('favicon-32.png'); return r.status; }""")
    has_link = page.evaluate("""() => !!document.querySelector('link[rel="icon"]')""")
    rec("favicon link present", has_link, "link[rel=icon] in document")
    rec("favicon.ico HTTP", ico_status == 200, f"status={ico_status} (nav={fav.get('ico')})")
    rec("favicon-32.png HTTP", png_status == 200, f"status={png_status}")

    # Listen button text in all 4 languages on home
    listen_ok = True
    listen_detail = []
    for lang in ["en","es","ht","pt"]:
        page.locator(f"#btn-{lang}").click()
        page.wait_for_timeout(150)
        info = page.evaluate("""() => [...document.querySelectorAll('.listenbtn')].map(b => ({text:b.innerText, codes:[...b.innerText].map(c=>c.codePointAt(0).toString(16))}))""")
        bad = [x for x in info if "U0001" in x["text"] or "u0001" in x["text"].lower() or "1f50a" not in x["codes"]]
        expected_word = {"en":"Listen","es":"Escuchar","ht":"Koute","pt":"Ouvir"}[lang]
        word_ok = all(expected_word in x["text"] for x in info) and info
        emoji_ok = all(x["codes"] and x["codes"][0]=="1f50a" for x in info)
        ok = emoji_ok and word_ok and not bad
        listen_ok = listen_ok and ok
        listen_detail.append(f"{lang}: n={len(info)} emoji={emoji_ok} word={word_ok} sample={info[0]['text'] if info else None}")
        # screenshot first listen button + featured card
        if page.locator(".listenbtn").count():
            page.locator("article.card").first.screenshot(path=str(AFTER / f"listen-{lang}.png"))
            out["screenshots"].append(str(AFTER / f"listen-{lang}.png"))
    rec("Listen buttons show speaker emoji + translated label in all 4 languages", listen_ok, "; ".join(listen_detail))

    # HT expanded details on featured 211
    page.locator("#btn-ht").click()
    page.wait_for_timeout(150)
    if page.locator("#featured .detailsbtn").count():
        page.locator("#featured .detailsbtn").first.click()
        page.wait_for_timeout(200)
    h3 = page.evaluate("""() => [...document.querySelectorAll('#featured .fields h3')].map(h=>h.innerText)""")
    rec("HT expanded field labels are Creole, not English",
        bool(h3) and not any(ENGLISH_UI.search(x) for x in h3),
        f"h3={h3}")
    page.locator("article.card").first.scroll_into_view_if_needed()
    page.locator("article.card").first.screenshot(path=str(AFTER / "ht-expanded-211.png"))
    out["screenshots"].append(str(AFTER / "ht-expanded-211.png"))
    page.screenshot(path=str(AFTER / "ht-expanded-211-full.png"), full_page=False)

    # Translation audit for es/ht/pt across home + new sections + all categories (chrome only)
    leftover = []
    for lang in ["es","ht","pt"]:
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_selector("#catGrid .cat")
        page.locator(f"#btn-{lang}").click()
        page.wait_for_timeout(150)
        slugs = page.evaluate("""() => [...document.querySelectorAll('#catGrid [data-cat]')].map(e=>e.getAttribute('data-cat'))""")
        views = [("home", None)] + [(s,s) for s in slugs]
        for name, slug in views:
            if slug:
                if page.locator("#resultsView").is_visible():
                    page.locator("#backBtn").click()
                    page.wait_for_selector("#homeView:not(.hidden)")
                page.locator(f'[data-cat="{slug}"]').click()
                page.wait_for_selector("#resultsView:not(.hidden)")
            vis = page.locator(".detailsbtn").locator("visible=true")
            if vis.count():
                vis.first.click()
                page.wait_for_timeout(80)
            texts = page.evaluate("""() => {
              const sel = 'h2,h3,button,a,.scope,.detailsbtn,.listenbtn,.backbtn,.chip-verified,.chip-unverified';
              return [...document.querySelectorAll(sel)].map(e => (e.innerText||'').trim()).filter(Boolean);
            }""")
            for t in texts:
                if ENGLISH_UI.search(t):
                    leftover.append({"lang":lang,"view":name,"text":t})
    rec("no untranslated English UI chrome in es/ht/pt (all categories, expanded + hidden)",
        not leftover, leftover[:15] if leftover else "none")

    # Overflow at 390 and 375, all 4 langs, home + 3 new sections
    overflow = []
    for width in (390, 375, 1280):
        page.set_viewport_size({"width": width, "height": 844 if width < 800 else 900})
        for lang in ["en","es","ht","pt"]:
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_selector("#catGrid .cat")
            page.locator(f"#btn-{lang}").click()
            page.wait_for_timeout(120)
            def sw():
                return page.evaluate("() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth})")
            m = sw()
            if m["sw"] > m["iw"] + 1:
                overflow.append({"view":"home","lang":lang,"width":width,**m})
            if width in (390,1280) and lang=="en":
                page.screenshot(path=str(AFTER / f"w{width}-home-{lang}.png"), full_page=True)
                out["screenshots"].append(str(AFTER / f"w{width}-home-{lang}.png"))
            for slug in ("education","transit","housing"):
                if page.locator("#resultsView").is_visible():
                    page.locator("#backBtn").click()
                    page.wait_for_selector("#homeView:not(.hidden)")
                page.locator(f'[data-cat="{slug}"]').click()
                page.wait_for_selector("#resultsView:not(.hidden)")
                m = sw()
                if m["sw"] > m["iw"] + 1:
                    overflow.append({"view":slug,"lang":lang,"width":width,**m})
                if width in (390,1280) and lang in ("en","ht"):
                    page.screenshot(path=str(AFTER / f"w{width}-{slug}-{lang}.png"), full_page=True)
                    out["screenshots"].append(str(AFTER / f"w{width}-{slug}-{lang}.png"))
    rec("no horizontal overflow at 390 / 375 / 1280 in 4 languages (home + new sections)",
        not overflow, overflow if overflow else "ok")

    # Tap targets >= 44px at 390px, EN, home + new sections
    page.set_viewport_size({"width":390,"height":844})
    small = []
    def collect_small(ctx):
        data = page.evaluate("""() => {
          const els = [...document.querySelectorAll('a, button')].filter(e => {
            const s = getComputedStyle(e);
            return s.display !== 'none' && s.visibility !== 'hidden' && e.offsetParent !== null;
          });
          const bad = [];
          for (const e of els) {
            const r = e.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            if (r.height < 44 || r.width < 44) {
              bad.push({tag:e.tagName, text:(e.innerText||'').replace(/\\s+/g,' ').slice(0,70),
                        w:Math.round(r.width), h:Math.round(r.height), cls:e.className});
            }
          }
          return bad;
        }""")
        for b in data:
            b["ctx"]=ctx
            small.append(b)
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("#catGrid .cat")
    collect_small("home")
    for slug in ("education","transit","housing"):
        if page.locator("#resultsView").is_visible():
            page.locator("#backBtn").click()
            page.wait_for_selector("#homeView:not(.hidden)")
        page.locator(f'[data-cat="{slug}"]').click()
        page.wait_for_selector("#resultsView:not(.hidden)")
        collect_small(slug)
    out["small_targets"] = small
    rec("tap targets >= 44px at 390px (home + new sections)",
        not small, f"{len(small)} undersized: {small[:8]}")

    # Link crawl
    page.set_viewport_size({"width":1280,"height":900})
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("#catGrid .cat")
    hrefs = set(page.evaluate("""() => {
      const out = [...document.querySelectorAll('a[href]')].map(a => a.href);
      (LOCAL_LISTINGS||[]).forEach(l => { if (l.web) out.push(l.web); if (l.sourceUrl) out.push(l.sourceUrl); });
      (LISTINGS||[]).forEach(l => { if (l.web) out.push(l.web.startsWith('http')?l.web:('https://'+l.web)); });
      return out;
    }"""))
    # also visit categories to collect rendered hrefs
    for slug in page.evaluate("""() => [...document.querySelectorAll('#catGrid [data-cat]')].map(e=>e.getAttribute('data-cat'))"""):
        if page.locator("#resultsView").is_visible():
            page.locator("#backBtn").click()
            page.wait_for_selector("#homeView:not(.hidden)")
        page.locator(f'[data-cat="{slug}"]').click()
        page.wait_for_selector("#resultsView:not(.hidden)")
        for h in page.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a => a.href)"""):
            hrefs.add(h)

    http_links = sorted({h for h in hrefs if h.startswith("http")})
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    rows = []
    for u in http_links:
        status, note = 0, ""
        try:
            req = urllib.request.Request(u, method="GET", headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = resp.status
        except Exception as e:
            status = getattr(e, "code", 0) or 0
            note = str(e)
        rows.append({"url":u,"status":status,"note":note,"date":"2026-11-13"})
        print("LINK", status, u)
    out["links"] = rows
    notfound = [r for r in rows if r["status"]==404]
    rec("external links are non-404", not notfound,
        f"{len(rows)-len(notfound)}/{len(rows)} non-404; 404s={notfound}" if notfound else f"all {len(rows)} non-404")

    browser.close()

(EVID / "verify-results.json").write_text(json.dumps(out, indent=2))
print(f"\n==== SUMMARY passed={out['passed']} failed={out['failed']} ====")
sys.exit(1 if out["failed"] else 0)
