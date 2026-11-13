#!/usr/bin/env python3
"""Sweep Community Bridge listing DATA (not just UI chrome) for leftover English.

For each of es/ht/pt:
  - statically require per-language fields on every listing
  - render every category with every listing expanded, plus searches
    (ged, housing, bus), and collect visible text + aria-label/title/placeholder
  - flag strings identical to the English rendering, or matching an English
    phrase list, after subtracting an explicit allowlist of proper nouns,
    URLs, phones, and official names.

Usage:
  python3 evidence/sweep-listings.py --base http://127.0.0.1:8770 --out evidence/sweep-after.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = Path(__file__).with_name("sweep-allowlist.txt")

LANGS = ("es", "ht", "pt")
SEARCHES = ("ged", "housing", "bus")
ENGLISH_PHRASES = [
    "microphone",
    "free ged & english tutoring",
    "crisis stabilization",
    "coordinated entry",
    "emergency shelter for families",
    "domestic violence emergency shelter",
    "24-hour hotline",
    "public buses",
    "door-to-door rides",
    "housing vouchers",
    "ged preparation",
    "official site",
    "the shelter address is confidential",
    "do not go to an office",
    "rental assistance",
    "free medical equipment",
    "medical equipment bank",
    "free equipment lending",
    "soup kitchen",
    "english tutoring",
    "transportation page",
    "coordinated-entry page",
    "crisis stabilization program pages",
]

PHONE_RE = re.compile(r"""
    (?:
        \(\d{3}\)\s*\d{3}[-.\s]?\d{4}
        |\d{3}[-.\s]\d{3}[-.\s]\d{4}
        |\+\d[\d\-.\s]{6,}\d
        |\b\d{3}[-.\s]\d{4}\b
    )
""", re.X)
URL_RE = re.compile(r"""
    (?:https?://\S+)
    |(?:www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}\S*)
    |(?:[A-Za-z0-9.-]+\.(?:org|com|gov|edu|us|net|fl\.us)\b)
""", re.I | re.X)
# Official US street addresses (kept in English on the card).
ADDRESS_RE = re.compile(r"""
    \b\d{2,6}\s+
    (?:[NSEW]\.?\s+)?
    [A-Za-z0-9.'/-]+
    (?:\s+[A-Za-z0-9.'/-]+){0,6}
    (?:\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Highway|Hwy|Way|Court|Ct|Circle|Cir|Parkway|Pkwy|Building|Bldg|Room|Rm|Suite|Ste|Floor|Fl)\.?)
    (?:[^\n]{0,80}\b(?:FL|Florida)\b[^\n]{0,20}\b\d{5}(?:-\d{4})?)?
""", re.I | re.X)
DATE_RE = re.compile(r"\b(?:20\d{2}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:20)?\d{2})\b")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\s?(?:AM|PM)?\b", re.I)
MONEY_RE = re.compile(r"\$\d+(?:\.\d{2})?")
NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def load_allowlist():
    exact = set()
    for line in ALLOWLIST_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        exact.add(norm(line))
    return exact


def norm(s: str) -> str:
    s = s.replace("\u2014", "—").replace("\u2013", "—")
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def extract_array(html: str, name: str) -> str:
    m = re.search(r"var " + name + r" = \[", html)
    if not m:
        raise SystemExit(f"array {name} not found")
    start = m.end() - 1
    depth = 0
    i = start
    in_str = None
    esc = False
    while i < len(html):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
        else:
            if c in "\"'":
                in_str = c
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return html[start : i + 1]
        i += 1
    raise SystemExit(f"unclosed array {name}")


def split_objs(arr: str):
    body = arr[1:-1]
    objs = []
    depth = 0
    i = 0
    in_str = None
    esc = False
    start = None
    while i < len(body):
        c = body[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
        else:
            if c in "\"'":
                in_str = c
            elif c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    objs.append(body[start : i + 1])
        i += 1
    return objs


def has_field(obj: str, key: str) -> bool:
    return bool(re.search(r"(?:^|[,{\s])" + re.escape(key) + r"\s*:", obj))


def js_str(obj: str, key: str):
    m = re.search(r"\b" + re.escape(key) + r':("((?:\\.|[^"\\])*)")', obj)
    if not m:
        return None
    raw = m.group(2)
    try:
        return bytes(raw, "utf-8").decode("unicode_escape")
    except Exception:
        return raw


def static_check(html: str):
    missing = []
    present = []

    def check_obj(kind, obj, required):
        ident = js_str(obj, "id") or "?"
        miss = [f for f in required if not has_field(obj, f)]
        rec = {"kind": kind, "id": ident, "missing": miss}
        if miss:
            missing.append(rec)
        else:
            present.append(rec)

    for obj in split_objs(extract_array(html, "LISTINGS")):
        # National listings historically used a single `name` string and
        # {en,es,ht,pt} objects for desc/hours/who/cost/langs/coverage/notes.
        req = ["nameEn", "nameEs", "nameHt", "namePt"]
        for group in ("desc", "hours", "who", "cost", "langs", "coverage", "notes"):
            # Either object form with all four keys, or four suffix fields.
            if has_field(obj, group):
                chunk = obj
                # crude: require en/es/ht/pt inside the group object
                gm = re.search(r"\b" + group + r":\{([^{}]*)\}", chunk)
                if gm:
                    body = gm.group(1)
                    for lang in ("en", "es", "ht", "pt"):
                        if not re.search(r"\b" + lang + r"\s*:", body):
                            # record as missing group.lang
                            # (handled below by appending to req check via fake)
                            pass
                # We'll do a more precise check here:
            else:
                req += [group + cap for cap in ("En", "Es", "Ht", "Pt")]
        ident = js_str(obj, "id") or "?"
        miss = [f for f in req if not has_field(obj, f)]
        # object-style multilingual fields
        for group in ("desc", "hours", "who", "cost", "langs", "coverage", "notes"):
            gm = re.search(r"\b" + group + r":\{([^{}]*)\}", obj)
            if gm:
                body = gm.group(1)
                for lang in ("en", "es", "ht", "pt"):
                    if not re.search(r"\b" + lang + r"\s*:", body):
                        miss.append(f"{group}.{lang}")
        rec = {"kind": "national", "id": ident, "missing": miss}
        (missing if miss else present).append(rec)

    for obj in split_objs(extract_array(html, "LOCAL_LISTINGS")):
        ident = js_str(obj, "id") or "?"
        req = []
        for base in ("name", "sourceName", "town", "what", "hours"):
            req += [base + cap for cap in ("En", "Es", "Ht", "Pt")]
        if has_field(obj, "noteEn") or has_field(obj, "note"):
            req += ["noteEn", "noteEs", "noteHt", "notePt"]
        confidential = "confidential:true" in obj.replace(" ", "")
        addr = js_str(obj, "address") or js_str(obj, "addressEn") or ""
        if confidential or "confidential" in addr.lower():
            req += ["addressEn", "addressEs", "addressHt", "addressPt"]
        miss = [f for f in req if not has_field(obj, f)]
        rec = {"kind": "local", "id": ident, "missing": miss}
        (missing if miss else present).append(rec)

    return {
        "listings_checked": len(missing) + len(present),
        "complete": len(present),
        "incomplete": len(missing),
        "missing": missing,
    }


def strip_allowlisted(text: str, exact: set[str]) -> str:
    """Remove allowlisted exact strings, URLs, phones, addresses, dates, money."""
    s = text
    # Remove longest exact allowlist entries first
    for item in sorted(exact, key=len, reverse=True):
        if not item:
            continue
        s = re.sub(re.escape(item), " ", s, flags=re.I)
    s = URL_RE.sub(" ", s)
    s = PHONE_RE.sub(" ", s)
    s = ADDRESS_RE.sub(" ", s)
    s = DATE_RE.sub(" ", s)
    s = TIME_RE.sub(" ", s)
    s = MONEY_RE.sub(" ", s)
    s = NUM_RE.sub(" ", s)
    s = re.sub(r"[•·|,;:/()\[\]{}.+!?¡¿\"'`“”‘’\-—–≈✓⚠🔒📍🕒⚠️🗺️📞💬🔊🎤☀️☀️\s]+", " ", s)
    return norm(s)


_EMOJI_PREFIX = re.compile(r"^[\W_📍🔒🕒⚠️🗺️📞💬🔊🎤☀️✓⚠]+", re.UNICODE)

def looks_like_address(text: str) -> bool:
    s = _EMOJI_PREFIX.sub("", text).strip()
    s = s.lstrip("📍🔒 ")
    if not s:
        return False
    if ADDRESS_RE.fullmatch(s):
        return True
    # Numbered US street + City, ST ZIP (covers Suite/SW/Building variants)
    if re.search(r"^\d{1,6}\s+.+,\s*[A-Za-z .()'/-]+,\s*FL\s+\d{5}(?:-\d{4})?\s*$", s, re.I):
        return True
    return False

def is_allowlisted(text: str, exact: set[str]) -> bool:
    n = norm(text)
    if not n:
        return True
    if n in exact:
        return True
    raw = _EMOJI_PREFIX.sub("", text).strip()
    if URL_RE.fullmatch(raw) or PHONE_RE.fullmatch(raw):
        return True
    if DATE_RE.fullmatch(raw):
        return True
    if looks_like_address(text):
        return True
    residual = strip_allowlisted(text, exact)
    if not residual:
        return True
    leftovers = [tok for tok in residual.split() if tok and tok not in exact]
    return not leftovers


def english_phrase_hits(text: str) -> list[str]:
    n = norm(text)
    hits = []
    for p in ENGLISH_PHRASES:
        if p in n:
            hits.append(p)
    return hits


COLLECT_JS = r"""
() => {
  const out = [];
  const vis = (el) => {
    if (!el) return false;
    if (el.checkVisibility) {
      try { return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }); } catch (e) {}
    }
    let n = el;
    while (n && n.nodeType === 1) {
      const st = window.getComputedStyle(n);
      if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity) === 0) return false;
      n = n.parentElement;
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    return true;
  };
  document.querySelectorAll('*').forEach((el) => {
    for (const a of ['aria-label', 'title', 'placeholder', 'alt']) {
      const v = el.getAttribute(a);
      if (v && v.trim()) {
        const listing = el.closest('[data-listing],[data-local],[data-tcfb]');
        out.push({
          type: a,
          text: v.trim(),
          tag: el.tagName,
          id: el.id || '',
          cls: String(el.className || ''),
          listing: listing ? (listing.getAttribute('data-listing') || listing.getAttribute('data-local') || 'tcfb') : '',
          visible: vis(el)
        });
      }
    }
  });
  const sels = ['.lname','.srcline','.laddr','.ldesc','.lhours','.lstatus','.scope','.fields','h1','h2','h3','h4','.crisis','.cat','.btn','.callbtn','.textbtn','.listenbtn','.dirbtn','.detailsbtn','.backbtn','.langtoggle button','.noacct','.fictional','.chip-sample','.chip-verified','.chip-unverified','.notecard','.greet-card p','.greet-card h2'];
  for (const sel of sels) {
    document.querySelectorAll(sel).forEach((el) => {
      if (!vis(el)) return;
      const t = (el.innerText || '').trim();
      if (!t) return;
      const listing = el.closest('[data-listing],[data-local],[data-tcfb]');
      out.push({
        type: 'text',
        text: t,
        sel,
        id: el.id || '',
        cls: String(el.className || ''),
        listing: listing ? (listing.getAttribute('data-listing') || listing.getAttribute('data-local') || 'tcfb') : '',
        visible: true
      });
    });
  }
  return out;
}
"""


async def click_lang(page, lang):
    await page.locator(f"#btn-{lang}").click()
    await page.wait_for_timeout(120)


async def go_home(page):
    btn = page.locator("#backBtn")
    if await btn.count() and await btn.is_visible():
        await btn.click()
        await page.wait_for_timeout(150)
    # JS fallback if the button is somehow not clickable
    hidden_home = await page.locator("#homeView.hidden").count()
    if hidden_home:
        await page.evaluate("typeof goHome === 'function' && goHome()")
        await page.wait_for_timeout(150)


async def expand_visible_details(page):
    details = page.locator("#resultsView .detailsbtn, #homeView .detailsbtn")
    dcount = await details.count()
    for di in range(dcount):
        btn = details.nth(di)
        if not await btn.is_visible():
            continue
        try:
            await btn.scroll_into_view_if_needed()
            await btn.click()
            await page.wait_for_timeout(60)
        except Exception:
            try:
                await btn.evaluate("el => el.click()")
                await page.wait_for_timeout(60)
            except Exception:
                pass


async def open_categories_and_searches(page, lang):
    collected = []
    await go_home(page)
    await click_lang(page, lang)
    collected.extend(await page.evaluate(COLLECT_JS))
    n = await page.locator("#catGrid .cat").count()
    for i in range(n):
        await go_home(page)
        await click_lang(page, lang)
        buttons = page.locator("#catGrid .cat")
        if i >= await buttons.count():
            break
        await buttons.nth(i).scroll_into_view_if_needed()
        await buttons.nth(i).click()
        await page.wait_for_timeout(200)
        await expand_visible_details(page)
        collected.extend(await page.evaluate(COLLECT_JS))
        await go_home(page)
    # searches use the live search box (listens to input, not Enter)
    for q in SEARCHES:
        await go_home(page)
        await click_lang(page, lang)
        box = page.locator("#searchInput")
        await box.fill(q)
        await box.dispatch_event("input")
        await page.wait_for_timeout(250)
        await expand_visible_details(page)
        collected.extend(await page.evaluate(COLLECT_JS))
        await go_home(page)
    return collected


def dedupe_items(items):
    seen = set()
    out = []
    for it in items:
        key = (it.get("type"), it.get("text"), it.get("listing"), it.get("sel") or it.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def flag_items(items, en_texts: set[str], exact: set[str]):
    flags = []
    for it in items:
        text = it.get("text") or ""
        n = norm(text)
        if not n:
            continue
        if is_allowlisted(text, exact):
            continue
        reasons = []
        if n in en_texts and not is_allowlisted(text, exact):
            reasons.append("identical_to_english")
        hits = english_phrase_hits(text)
        # Don't flag a phrase if the hit is only inside an allowlisted official name
        # that we already failed is_allowlisted (mixed string). Still report it.
        if hits:
            # If after stripping allowlisted chunks the phrase is gone, ignore
            residual = strip_allowlisted(text, exact)
            still = [h for h in hits if h in residual or h in n and h not in exact]
            # More careful: if the full text is mixed (org name + leftover English)
            if still and not is_allowlisted(text, exact):
                reasons.append("english_phrase:" + ",".join(still))
        if reasons:
            flags.append({**it, "reasons": reasons})
    return flags


async def run_browser(base: str, exact: set[str]):
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        await page.goto(base.rstrip("/") + "/index.html", wait_until="networkidle")
        await page.wait_for_timeout(200)
        en_items = dedupe_items(await open_categories_and_searches(page, "en"))
        en_texts = {norm(it["text"]) for it in en_items if it.get("text")}
        by_lang = {}
        for lang in LANGS:
            await page.goto(base.rstrip("/") + "/index.html", wait_until="networkidle")
            await page.wait_for_timeout(200)
            items = dedupe_items(await open_categories_and_searches(page, lang))
            flags = flag_items(items, en_texts, exact)
            attr_flags = [f for f in flags if f.get("type") in ("aria-label", "title", "placeholder", "alt")]
            by_lang[lang] = {
                "strings_collected": len(items),
                "flagged": len(flags),
                "attribute_flagged": len(attr_flags),
                "attribute_flags": attr_flags,
                "flags": flags,
            }
        # In-place runtime switch: open views in English, then click the
        # target language without a reload, and re-collect attributes.
        inplace = {}
        for lang in LANGS:
            await page.goto(base.rstrip("/") + "/index.html", wait_until="networkidle")
            await page.wait_for_timeout(200)
            await click_lang(page, "en")
            # stay on home, then open housing + a search in EN, then switch
            attr_en_home = await page.evaluate(COLLECT_JS)
            await page.evaluate("typeof openCategory === 'function' && openCategory('housing')")
            await page.wait_for_timeout(200)
            await click_lang(page, lang)  # in-place, no reload
            await page.wait_for_timeout(200)
            after_housing = dedupe_items(await page.evaluate(COLLECT_JS))
            await go_home(page)
            await click_lang(page, "en")
            box = page.locator("#searchInput")
            if await box.count():
                await box.fill("ged")
                await box.dispatch_event("input")
                await page.wait_for_timeout(200)
            await click_lang(page, lang)
            await page.wait_for_timeout(200)
            after_search = dedupe_items(await page.evaluate(COLLECT_JS))
            await go_home(page)
            await click_lang(page, lang)
            after_home = dedupe_items(await page.evaluate(COLLECT_JS))
            combined = dedupe_items(after_housing + after_search + after_home)
            attr_items = [it for it in combined if it.get("type") in ("aria-label", "title", "placeholder", "alt")]
            flags = flag_items(attr_items, en_texts, exact)
            # Also flag English chrome labels that should have switched
            required = {
                "es": {"Microphone": "Micrófono", "Welcome": "Bienvenida", "Ask": "Preguntar", "Search": "Buscar",
                       "Moose, your Community Bridge guide": "Moose, su guía de Community Bridge",
                       "Language": "Idioma"},
                "ht": {"Microphone": "Mikwofòn", "Welcome": "Byenveni", "Ask": "Mande", "Search": "Chèche",
                       "Moose, your Community Bridge guide": "Moose, gid Community Bridge ou",
                       "Language": "Lang"},
                "pt": {"Microphone": "Microfone", "Welcome": "Boas-vindas", "Ask": "Perguntar", "Search": "Pesquisar",
                       "Moose, your Community Bridge guide": "Moose, seu guia do Community Bridge",
                       "Language": "Língua"},
            }[lang]
            found_vals = {it["text"] for it in attr_items}
            stuck = []
            missing_expected = []
            for en_lab, expected in required.items():
                if en_lab in found_vals:
                    stuck.append(en_lab)
                if expected not in found_vals:
                    missing_expected.append(expected)
            inplace[lang] = {
                "attributes_collected": len(attr_items),
                "flagged": len(flags),
                "flags": flags,
                "english_labels_still_present_after_switch": stuck,
                "expected_translated_labels_missing": missing_expected,
                "attribute_values": sorted({it["type"]+": "+it["text"] for it in attr_items}),
            }
        await browser.close()
        return {"en_strings_collected": len(en_items), "by_lang": by_lang, "attribute_inplace_switch": inplace}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8770")
    ap.add_argument("--html", default=str(ROOT / "index.html"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--static-only", action="store_true")
    args = ap.parse_args()

    html = Path(args.html).read_text()
    exact = load_allowlist()
    static = static_check(html)
    result = {
        "html": str(Path(args.html).resolve()),
        "allowlist_size": len(exact),
        "allowlist_path": str(ALLOWLIST_PATH),
        "english_phrases": ENGLISH_PHRASES,
        "static": static,
    }
    if not args.static_only:
        import asyncio
        result["runtime"] = asyncio.run(run_browser(args.base, exact))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    # summary to stdout
    print("STATIC listings:", static["listings_checked"], "complete:", static["complete"], "incomplete:", static["incomplete"])
    if static["missing"]:
        for rec in static["missing"]:
            print(f"  missing {rec['kind']} {rec['id']}: {', '.join(rec['missing'][:12])}" + ("..." if len(rec["missing"])>12 else ""))
    if "runtime" in result:
        rt = result["runtime"]
        print("EN strings collected:", rt["en_strings_collected"])
        total = 0
        attr_total = 0
        for lang, data in rt["by_lang"].items():
            print(f"  {lang}: collected={data['strings_collected']} flagged={data['flagged']} attribute_flagged={data.get('attribute_flagged', 0)}")
            total += data["flagged"]
            attr_total += data.get("attribute_flagged", 0)
        print("TOTAL flagged:", total)
        print("TOTAL attribute flagged (full crawl):", attr_total)
        if rt.get("attribute_inplace_switch"):
            print("ATTRIBUTE IN-PLACE SWITCH:")
            for lang, data in rt["attribute_inplace_switch"].items():
                print(f"  {lang}: attrs={data['attributes_collected']} flagged={data['flagged']} stuck_english={data['english_labels_still_present_after_switch']} missing_expected={data['expected_translated_labels_missing']}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
