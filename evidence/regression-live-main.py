#!/usr/bin/env python3
"""Compare the draft (local) against live GitHub Pages main.

Checks: same features/sections/buttons present, no newly missing labels,
no console errors introduced.
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

LIVE = "https://mrjosueayalaperez-dev.github.io/Community-Bridge-/"
LOCAL = "http://127.0.0.1:8770/index.html"

FEATURES_JS = r"""
() => {
  const ids = [...document.querySelectorAll('[id]')].map(e => e.id).sort();
  const buttons = [...document.querySelectorAll('button, a.btn, a.callbtn, a.textbtn, a.dirbtn')].map(e => ({
    id: e.id || '',
    cls: String(e.className||'').split(/\s+/).filter(Boolean).sort().join(' '),
    text: (e.innerText||'').trim().slice(0,80),
  }));
  const sections = [...document.querySelectorAll('section, main, header, footer')].map(e => ({
    tag: e.tagName, id: e.id||'', aria: e.getAttribute('aria-label')||'', cls: String(e.className||'')
  }));
  const cats = [...document.querySelectorAll('#catGrid .cat')].map(e => (e.innerText||'').split('\n')[0].trim());
  const labels = {};
  document.querySelectorAll('*').forEach(el => {
    for (const a of ['aria-label','title','placeholder','alt']) {
      const v = el.getAttribute(a);
      if (v) {
        const key = (el.id || el.tagName + '.' + (el.className||'') + '.' + a);
        labels[key] = {attr: a, value: v, id: el.id||'', tag: el.tagName};
      }
    }
  });
  return { ids, buttons, sections, cats, labels, title: document.title, lang: document.documentElement.lang };
}
"""

async def snapshot(page, url, consoles, pages_errors):
    consoles.clear(); pages_errors.clear()
    def on_console(msg):
        if msg.type in ("error", "warning"):
            consoles.append({"type": msg.type, "text": msg.text})
    def on_page(err):
        pages_errors.append(str(err))
    page.on("console", on_console)
    page.on("pageerror", on_page)
    resp = await page.goto(url, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(400)
    status = resp.status if resp else None
    snap = await page.evaluate(FEATURES_JS)
    # switch each language and collect labels
    lang_labels = {"en": snap["labels"]}
    for lang in ("es", "ht", "pt"):
        btn = page.locator(f"#btn-{lang}")
        if await btn.count():
            await btn.click()
            await page.wait_for_timeout(250)
            s = await page.evaluate(FEATURES_JS)
            lang_labels[lang] = s["labels"]
    await page.locator("#btn-en").click()
    await page.wait_for_timeout(150)
    return {
        "url": url,
        "status": status,
        "ids": snap["ids"],
        "cats_en": snap["cats"],
        "button_ids": sorted({b["id"] for b in snap["buttons"] if b["id"]}),
        "button_classes": sorted({b["cls"] for b in snap["buttons"] if b["cls"]}),
        "section_ids": [s["id"] for s in snap["sections"] if s["id"]],
        "labels_by_lang": lang_labels,
        "console": list(consoles),
        "pageerrors": list(pages_errors),
        "title": snap["title"],
    }

async def main():
    consoles, errors = [], []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        live = await snapshot(page, LIVE, consoles, errors)
        consoles, errors = [], []
        local = await snapshot(page, LOCAL, consoles, errors)
        await browser.close()

    live_ids = set(live["ids"])
    local_ids = set(local["ids"])
    missing_ids = sorted(live_ids - local_ids)
    new_ids = sorted(local_ids - live_ids)

    live_btns = set(live["button_ids"])
    local_btns = set(local["button_ids"])
    missing_btns = sorted(live_btns - local_btns)

    # Labels: every live element id that had an attribute should still have that attribute locally
    missing_labels = []
    for lang in ("en", "es", "ht", "pt"):
        live_labs = live["labels_by_lang"].get(lang, {})
        local_labs = local["labels_by_lang"].get(lang, {})
        live_by_id_attr = {(v["id"], v["attr"]): v["value"] for v in live_labs.values() if v["id"]}
        local_by_id_attr = {(v["id"], v["attr"]): v["value"] for v in local_labs.values() if v["id"]}
        for key, val in live_by_id_attr.items():
            if key not in local_by_id_attr:
                missing_labels.append({"lang": lang, "id": key[0], "attr": key[1], "live_value": val})

    def interesting_console(entries, url):
        out = []
        for e in entries:
            text = e.get("text") or ""
            # Ignore favicon 404 on live user-site root (known, out of this repo)
            # and font/extension noise.
            if "favicon.ico" in text and "404" in text:
                continue
            if "Failed to load resource" in text and "favicon" in text:
                continue
            out.append(e)
        return out

    live_console = interesting_console(live["console"], LIVE)
    local_console = interesting_console(local["console"], LOCAL)
    new_console = [e for e in local_console if e not in live_console]

    result = {
        "live": {k: live[k] for k in ("url", "status", "cats_en", "button_ids", "section_ids", "console", "pageerrors", "title")},
        "local": {k: local[k] for k in ("url", "status", "cats_en", "button_ids", "section_ids", "console", "pageerrors", "title")},
        "missing_ids": missing_ids,
        "new_ids": new_ids,
        "missing_button_ids": missing_btns,
        "newly_missing_labels": missing_labels,
        "live_console_filtered": live_console,
        "local_console_filtered": local_console,
        "new_console_errors_or_warnings": new_console,
        "live_pageerrors": live["pageerrors"],
        "local_pageerrors": local["pageerrors"],
        "ok": (not missing_ids and not missing_btns and not missing_labels
               and not new_console and not local["pageerrors"]),
    }
    out = Path("/workspace/community-bridge/evidence/regression-live-main.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print("LIVE status", live["status"], "cats", live["cats_en"])
    print("LOCAL status", local["status"], "cats", local["cats_en"])
    print("missing ids:", missing_ids or "none")
    print("new ids:", new_ids)
    print("missing button ids:", missing_btns or "none")
    print("newly missing labels:", missing_labels or "none")
    print("new console:", new_console or "none")
    print("local pageerrors:", local["pageerrors"] or "none")
    print("live pageerrors:", live["pageerrors"] or "none")
    print("REGRESSION", "PASS" if result["ok"] else "REVIEW")
    print("wrote", out)

if __name__ == "__main__":
    asyncio.run(main())
