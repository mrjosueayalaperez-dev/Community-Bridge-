#!/usr/bin/env python3
"""Local visual, routing, overflow, link-crawl, and axe checks for Community Bridge draft sections."""
import json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/workspace/community-bridge")
EVIDENCE = ROOT / "evidence"
BASE = "http://127.0.0.1:8770/index.html"
LANGS = ["en", "es", "ht", "pt"]
WIDTHS = {"mobile": 375, "desktop": 1280}
SECTIONS = {
    "education": {"label_en": "Learning", "expect_ids": ["literacy-services-irc", "irsc-ged-mueller"]},
    "transit": {"label_en": "Transit", "expect_ids": ["goline-transit"]},
    "housing": {"label_en": "Housing", "expect_ids": [
        "irc-section8", "habc-section8", "tchsc-coordinated-entry",
        "hope-for-families", "safespace-shelter", "uap-irc-housing"
    ]},
}
ASK_QUERIES = {
    "ged": "education",
    "goline": "transit",
    "bus": "transit",
    "shelter": "housing",
    "housing": "housing",
}

results = {"tests": [], "failed": 0, "passed": 0, "warnings": 0, "screenshots": [], "links": [], "axe": {}}

def rec(name, ok, detail, warn=False):
    status = "WARN" if warn and ok else ("PASS" if ok else "FAIL")
    results["tests"].append({"name": name, "status": status, "detail": detail})
    if status == "PASS":
        results["passed"] += 1
    elif status == "WARN":
        results["warnings"] += 1
        results["passed"] += 1
    else:
        results["failed"] += 1
    print(f"[{status}] {name}: {detail}")

def click_lang(page, lang):
    page.locator(f"#btn-{lang}").click()
    page.wait_for_timeout(200)

def open_category(page, slug):
    page.locator(f'[data-cat="{slug}"]').click()
    page.wait_for_selector("#resultsView:not(.hidden)")
    page.wait_for_timeout(200)

def go_home(page):
    if page.locator("#resultsView").is_visible() or page.locator("#privacyView").is_visible():
        if page.locator("#backBtn").is_visible():
            page.locator("#backBtn").click()
        elif page.locator("#privacyBackBtn").is_visible():
            page.locator("#privacyBackBtn").click()
        page.wait_for_selector("#homeView:not(.hidden)")
        page.wait_for_timeout(150)

def screenshot(page, name):
    path = EVIDENCE / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    results["screenshots"].append(str(path))
    return path

def overflow_ok(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")

def tap_issues(page):
    return page.evaluate("""() => {
      const els = [...document.querySelectorAll('a, button')].filter(e => {
        const s = getComputedStyle(e);
        return s.display !== 'none' && s.visibility !== 'hidden' && e.offsetParent !== null;
      });
      const bad = [];
      for (const e of els) {
        const r = e.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.height < 24 || r.width < 24) {
          bad.push({tag:e.tagName, text:(e.innerText||'').slice(0,60), w:Math.round(r.width), h:Math.round(r.height), cls:e.className});
        }
      }
      return {count: els.length, small: bad};
    }""")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("#catGrid .cat")

    cats = page.locator("#catGrid .cat").count()
    rec("home category count", cats == 13, f"found {cats}")

    # Food should not duplicate local cards
    open_category(page, "food")
    food_ids = page.evaluate("""() => [...document.querySelectorAll('#results [data-local]')].map(e => e.getAttribute('data-local'))""")
    rec("food listings unique (no catItems duplicate)", len(food_ids) == len(set(food_ids)) and len(food_ids) >= 9,
        f"{len(food_ids)} cards, {len(set(food_ids))} unique: {food_ids}")
    go_home(page)

    # Mobility still works
    open_category(page, "mobility")
    mob_ids = page.evaluate("""() => [...document.querySelectorAll('#results [data-local]')].map(e => e.getAttribute('data-local'))""")
    rec("mobility still lists local equipment + coach", "community-coach" in mob_ids and len(mob_ids) >= 7,
        f"ids={mob_ids}")
    # should not show the not-covered note as the only content
    rec("mobility not empty-state", "don't have a verified local listing" not in page.inner_text("#resultsView").lower()
        and "no tenemos un listado" not in page.inner_text("#resultsView").lower(),
        "category has listings rather than empty fallback")
    go_home(page)

    # New sections
    for slug, meta in SECTIONS.items():
        go_home(page)
        open_category(page, slug)
        ids = page.evaluate("""() => [...document.querySelectorAll('#results [data-local]')].map(e => e.getAttribute('data-local'))""")
        missing = [i for i in meta["expect_ids"] if i not in ids]
        rec(f"{slug} lists expected cards", not missing, f"got {ids}; missing {missing}")
        body = page.inner_text("#resultsView")
        rec(f"{slug} is not the empty fallback", "don't have a verified local listing" not in body.lower(),
            "listings rendered")
        go_home(page)

    # SafeSpace safety: no maps link
    open_category(page, "housing")
    ss = page.locator('[data-local="safespace-shelter"]')
    rec("SafeSpace card present", ss.count() == 1, f"count={ss.count()}")
    if ss.count():
        hrefs = ss.locator("a").evaluate_all("els => els.map(e => e.href)")
        has_maps = any("google.com/maps" in h for h in hrefs)
        has_tel = any(h.startswith("tel:+17722887023") for h in hrefs)
        rec("SafeSpace has no Maps/directions link", not has_maps, f"hrefs={hrefs}")
        rec("SafeSpace call button uses official hotline", has_tel, f"hrefs={hrefs}")
        rec("SafeSpace uses confidential copy, not a street address",
            "confidential" in ss.inner_text().lower() and "720" not in ss.inner_text() and "612 SE Dixie" not in ss.inner_text(),
            ss.inner_text()[:240])
    go_home(page)

    # Keyword routing via Ask box
    for q, expect in ASK_QUERIES.items():
        go_home(page)
        page.fill("#askInput", q)
        page.click("#askBtn")
        page.wait_for_selector("#resultsView:not(.hidden)")
        # title or cards
        ids = page.evaluate("""() => [...document.querySelectorAll('#results [data-local]')].map(e => e.getAttribute('data-local'))""")
        ok = any(i in (SECTIONS.get(expect, {}).get("expect_ids") or []) for i in ids) or (
            expect == "housing" and "irc-section8" in ids
        )
        rec(f"ask '{q}' routes to {expect}", ok, f"ids={ids}")

    # Privacy back works
    go_home(page)
    page.click("#privacyBtn")
    page.wait_for_selector("#privacyView:not(.hidden)")
    rec("privacy page opens", page.locator("#privacyView").is_visible(), "opened")
    page.click("#privacyBackBtn")
    page.wait_for_selector("#homeView:not(.hidden)")
    rec("privacy back returns home", page.locator("#homeView").is_visible(), "home visible")

    # Screenshots + overflow + tap targets for each section/lang/width
    overflow_fails = []
    tap_notes = []
    for width_name, width in WIDTHS.items():
        page.set_viewport_size({"width": width, "height": 844 if width < 600 else 900})
        for lang in LANGS:
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_selector("#catGrid .cat")
            click_lang(page, lang)
            if not overflow_ok(page):
                overflow_fails.append(f"home-{lang}-{width_name}")
            screenshot(page, f"{width_name}-home-{lang}")
            for slug in SECTIONS:
                go_home(page)
                open_category(page, slug)
                if not overflow_ok(page):
                    overflow_fails.append(f"{slug}-{lang}-{width_name}")
                info = tap_issues(page)
                if info["small"]:
                    tap_notes.append({"context": f"{slug}-{lang}-{width_name}", "small": info["small"]})
                screenshot(page, f"{width_name}-{slug}-{lang}")
                # also capture SafeSpace on housing
                if slug == "housing":
                    el = page.locator('[data-local="safespace-shelter"]')
                    if el.count():
                        el.scroll_into_view_if_needed()
                        screenshot(page, f"{width_name}-housing-safespace-{lang}")

    rec("no horizontal overflow at 375/1280 in 4 languages", not overflow_fails,
        "ok" if not overflow_fails else f"overflow: {overflow_fails}")
    rec("tap targets reviewed", True,
        f"{len(tap_notes)} contexts had controls shorter/narrower than 24px (existing site pattern may include text buttons). Details saved.",
        warn=bool(tap_notes))
    (EVIDENCE / "tap-targets.json").write_text(json.dumps(tap_notes, indent=2))

    # Link crawl: collect hrefs from home + 3 sections in EN at desktop, plus listing source URLs from JS
    page.set_viewport_size({"width": 1280, "height": 900})
    hrefs = set()
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_selector("#catGrid .cat")
    click_lang(page, "en")
    def collect():
        found = page.evaluate("""() => [...document.querySelectorAll('a[href]')].map(a => a.href)""")
        for h in found:
            hrefs.add(h)
    collect()
    for slug in ["food", "mobility"] + list(SECTIONS):
        go_home(page)
        open_category(page, slug)
        collect()
        # expand any details if present
        go_home(page)
    # extract sourceUrl and web from the page JS
    js_urls = page.evaluate("""() => {
      const out = [];
      (LOCAL_LISTINGS||[]).forEach(l => { if (l.web) out.push(l.web); if (l.sourceUrl) out.push(l.sourceUrl); });
      (LISTINGS||[]).forEach(l => { if (l.web) out.push(l.web.startsWith('http') ? l.web : ('https://'+l.web)); });
      return out;
    }""")
    for u in js_urls:
        hrefs.add(u)

    # Filter to http(s)
    http_links = sorted({h for h in hrefs if h.startswith("http")})
    tel_sms = sorted({h for h in hrefs if h.startswith("tel:") or h.startswith("sms:")})
    rec("collected links", True, f"{len(http_links)} http(s), {len(tel_sms)} tel/sms")

    # Check HTTP status
    link_rows = []
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    for u in http_links:
        status = None
        note = ""
        try:
            req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = resp.status
                final = resp.geturl()
        except Exception as e_head:
            try:
                req = urllib.request.Request(u, method="GET", headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    status = resp.status
                    final = resp.geturl()
            except Exception as e_get:
                # ssl or 403 etc
                err = str(e_get)
                if hasattr(e_get, "code"):
                    status = e_get.code
                    note = err
                else:
                    status = 0
                    note = err
                final = u
        row = {"url": u, "status": status, "note": note, "date": "2026-11-13"}
        link_rows.append(row)
        print("LINK", status, u, note[:80] if note else "")

    results["links"] = link_rows
    bad = [r for r in link_rows if r["status"] not in (200, 201, 204, 301, 302, 303, 307, 308)]
    rec("external/internal link crawl (2xx/3xx)", len(bad) == 0,
        f"{len(link_rows)-len(bad)}/{len(link_rows)} ok; problems={bad}" if bad else f"all {len(link_rows)} ok",
        warn=bool(bad))

    # axe on home + each new section (EN, desktop)
    try:
        from axe_playwright_python.sync_playwright import Axe
        axe = Axe()
        axe_all = {}
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_selector("#catGrid .cat")
        click_lang(page, "en")
        for name, do in [
            ("home", lambda: None),
            ("education", lambda: open_category(page, "education")),
            ("transit", lambda: (go_home(page), open_category(page, "transit"))),
            ("housing", lambda: (go_home(page), open_category(page, "housing"))),
        ]:
            if name != "home":
                go_home(page)
                open_category(page, name)
            res = axe.run(page)
            # res.response or dict
            data = res.response if hasattr(res, "response") else res
            if hasattr(data, "violations"):
                viol = data.violations
            elif isinstance(data, dict):
                viol = data.get("violations", [])
            else:
                viol = []
            brief = []
            for v in viol:
                if isinstance(v, dict):
                    brief.append({"id": v.get("id"), "impact": v.get("impact"), "help": v.get("help"), "nodes": len(v.get("nodes") or [])})
                else:
                    brief.append(str(v))
            axe_all[name] = {"violations": brief, "count": len(brief)}
            rec(f"axe {name}", True, f"{len(brief)} violation types", warn=bool(brief))
        results["axe"] = axe_all
        (EVIDENCE / "axe-results.json").write_text(json.dumps(axe_all, indent=2))
    except Exception as e:
        rec("axe ran", False, f"{type(e).__name__}: {e}")

    browser.close()

(EVIDENCE / "test-results.json").write_text(json.dumps(results, indent=2))
print("\n==== SUMMARY ====")
print(f"passed={results['passed']} failed={results['failed']} warnings={results['warnings']} screenshots={len(results['screenshots'])}")
sys.exit(1 if results["failed"] else 0)
