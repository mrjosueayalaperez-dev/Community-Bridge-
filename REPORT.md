# Community Bridge draft PR report — GED, Transportation, Housing, and live-test defect fixes

**Date:** Friday, Nov 13, 2026, America/New_York (ET)  
**Repo:** https://github.com/mrjosueayalaperez-dev/Community-Bridge-  
**Live site (unchanged by this work):** https://mrjosueayalaperez-dev.github.io/Community-Bridge-/  
**Limits honored:** draft PR only; no merge, no push to main, no deploy, no secrets, no PR closed.

The site already had categories named **Learning** (description mentions GED), **Transit**, and **Housing**. This work fills those existing categories rather than inventing a new layout. Learning and Transit were empty (they showed the “call 211” fallback). Housing already had two Section 8 listings; those were kept and four verified listings were added.

Region assumed (existing site): **Indian River County, Florida** — Fellsmere, Sebastian, and Vero Beach — with a few nearby Brevard listings already in the directory. New listings follow that same focus.

---

## Overall

### (1) What changed
- Added verified local listings to Learning (GED / adult education), Transit (GoLine), and Housing (coordinated entry, family shelter, domestic-violence shelter, crisis stabilization).
- Wired `catItems` / uncovered-place routing so education and transit locals actually appear (previously only housing and mobility locals were included). Food locals are still assembled separately so they are not duplicated.
- Updated the outdated “verified local listings cover food only” notice in all four languages.
- Confidential-shelter cards (SafeSpace) do not show a map or a street address.
- Live-test defect fixes in the same PR: Listen control glyph, favicon, 44px tap targets, 390px overflow, retarget of a dead 211 PDF source link.
- Leftover `\U0001f50a` Listen escapes were removed from preview candidate HTML files. Favicon links were added on every HTML page in the repo.

### (2) Where
- **Branch:** `draft/ged-transit-housing-sections`
- **PR:** see the GitHub draft PR created with this report (linked in the handoff).
- **Base:** `main` at `0f38789b56a5d806f7da6da97d478d2b932e7e06`
- **Commit SHAs:** recorded in the PR after push (this file is included in the branch).

### (3) Tests run
- `node --check` on the page script.
- Playwright (Chromium) against a local static server on port 8770: category routing, Ask-box keywords (`ged`, `goline`, `bus`, `shelter`, `housing`), food-listing de-duplication, mobility regression, SafeSpace no-maps rule, language toggles, expanded/hidden details in en/es/ht/pt, horizontal overflow at 375 / 390 / 1280, tap targets at 390px, favicon HTTP, Listen button code points, full-site link crawl.
- axe-core on home + new sections (pre-existing `region` landmark warning only).
- First-party HTTP checks of every new resource URL on Nov 13, 2026 (ET).

### (4) Results with counts
- Learning: 2 new local cards. Transit: 1 new local card. Housing: 4 new local cards + 2 existing Section 8 cards = 6.
- Ask routing: 5/5 test queries landed in the expected category.
- Overflow: none at 375, 390, or 1280 in four languages after the language-toggle padding tweak.
- Tap targets: 0 controls under 44×44 px at 390px on home and the three new sections, after source-line links were given a 44px min-height.
- Favicon: `favicon.ico` and `favicon-32.png` return 200 from the local server; `link rel="icon"` is present.
- Listen buttons: U+1F50A speaker emoji + translated label (Listen / Escuchar / Koute / Ouvir) in all four languages. Code point confirmed in Playwright.
- HT expanded labels on a featured national card: ORÈ, POU KI MOUN LI YE, PRI, LANG, AKSÈ POU CHÈZ WOULAN, ZÒN LI KOUVRI, SIT ENTÈNÈT — no English chrome labels.
- Translation audit of visible UI chrome (buttons, headings, field labels) across all 13 categories in es/ht/pt: no leftover English UI strings. Organization names (proper nouns) remain in English.
- Link crawl of the live page plus all listing `web` / `sourceUrl` values: **0 of 65 HTTP(S) links returned 404**. Status of every URL is in `evidence/verify-results.json` and summarized below. Some pre-existing hosts returned 403, 500, 202, or a client timeout (0); those are not 404 and are flagged NEEDS VERIFICATION.

### (5) Status label
**IMPLEMENTED** and **TESTED** on a local static server. **Not deployed.** GitHub Pages still serves current `main` until a founder merge.

### (6) Sources used and how verified
Every new phone, address, hour, fee, and program fact was read from a first-party official or recognized-nonprofit page on Nov 13, 2026 (ET). URLs were opened with WebFetch and/or curl. Conflicting official pages are described on the card and the reader is told to call and confirm. Hours were omitted when the official site did not list them.

### (7) Risks
- Official pages disagree on some GoLine Saturday hours and UAP’s street address; cards disclose the conflict, but a caller may still get a stale detail if the agency’s site is wrong.
- IRSC’s GED page lists an enrollment end date that appears inconsistent; the card tells people to call the Mueller Campus.
- Florida DOE’s GED page returned 403 to curl (bot block) but was readable via WebFetch; the “online testing suspended in Florida” note is marked NEEDS VERIFICATION.
- SafeSpace’s shelter address is intentionally withheld; a directions button is not rendered.
- Spanish, Haitian Creole, and Portuguese strings were written to match the site’s existing tone but have **not** had a native-speaker review.
- The greeting and on-page copy still say “Moose.” This PR does not rename the Community Bridge guide.

### (8) What was not done and why
- No merge, no deploy, no change to `main`.
- Community Coach remains under Mobility Equipment (already approved there); Transit mentions it rather than duplicating the card.
- No new national GED-testing card (www.ged.com has no public phone on the homepage we opened). Scheduling is described on the IRSC card.
- The Source was not added as a housing listing; its official site did not document a specific, verifiable housing program this session (it is already listed under Food).
- Cold-weather shelter details from a third-party directory were not used.
- Pre-existing hosts that return 403/500 (Childhelp, Salvation Army HTTP URL, HRSA, Our Father’s Table, `http://seniorresourceassociation.org/` without www) were not rewritten except the 404 PDF cited below.

### (9) Decisions needed from Josue
- Native-speaker review of all new es / ht / pt strings (listings + the updated `nonFoodLocal` / `confidentialLocation` phrases).
- Whether Community Coach should also appear as a Transit card, or stay only under Mobility Equipment.
- Whether to keep the honest conflict notes (GoLine hours, UAP address, IRSC dates) or shorten the cards.
- Approval to merge this draft PR (Pages will only change after a merge you approve).
- Whether the on-page guide name “Moose” should later become “MNQ Professor” (out of scope here).

### (10) Rollback steps
Do not merge the PR. The live site stays on `main` (`0f38789`). To drop the branch later: delete `draft/ged-transit-housing-sections` (do not close the PR unless you ask). No production files were changed on GitHub Pages.

**Evidence:** `evidence/before/`, `evidence/after/`, `evidence/verify-results.json`.

---

## GED / Learning

### (1) What changed
Two local listings under the existing **Learning** category:
1. **Literacy Services of Indian River County** — free GED, English, and diploma tutoring for county residents only. Main office at the county Main Library; additional offices in Fellsmere, Sebastian, and the IRSC Brackett Library. Hours are not on their site, so the card says to call.
2. **Indian River State College — GED Preparation (Mueller Campus, Vero Beach)** — $30/semester, $20 one-time application fee, SSN or ITIN required on the application, CASAS placement exam. Other Treasure Coast campuses exist and are mentioned, but the card is anchored in Vero Beach (the site’s coverage area).

Ask-box keywords such as “ged prep” / “high school equivalency” now route here.

### (2) Where
Same branch / PR. New ids: `literacy-services-irc`, `irsc-ged-mueller`.

### (3)–(4) Tests and results
Opening **Learning** shows both cards and is no longer the 211-only empty state. Query `ged` routes to these two cards. Screenshots: `evidence/after/w390-education-en.png`, `w390-education-ht.png`.

### (5) Status
**IMPLEMENTED** / **TESTED** locally. Translations: **NEEDS VERIFICATION** (native review). Florida DOE testing-rule sentence: **NEEDS VERIFICATION** (403 to curl).

### (6) Sources
| Resource | URL | HTTP | Date checked (ET) |
|---|---|---|---|
| Literacy Services — Become a Student | https://www.literacyservicesirc.org/students/become-a-student/ | 200 | Nov 13, 2026 |
| Literacy Services home | https://www.literacyservicesirc.org/ | 200 | Nov 13, 2026 |
| IRSC GED Preparation | https://irsc.edu/program/ged-preparation/ | 200 | Nov 13, 2026 |
| IRSC Adult Education | https://irsc.edu/adult-education/ | 200 | Nov 13, 2026 |
| GED Testing Service | https://www.ged.com/ | 200 (www.ged.com; ged.com SSL failed in curl) | Nov 13, 2026 |
| Florida DOE HSE / GED | https://www.fldoe.org/academics/career-adult-edu/hse/ | 403 to curl; body read via WebFetch | Nov 13, 2026 |

Facts used: LSIRC phone (772) 778-2223 and four office addresses from their Become-a-Student page; “all services are free”; “only serve Indian River County residents.” IRSC Mueller address 6155 College Lane, Building A Room 130, Vero Beach; phone (772) 226-2507; $30 / $20 fees; SSN or ITIN; CASAS; morning/evening classes 2 days/week plus online; Spring 2027 dates as listed, with a call-to-confirm note on the inconsistent end date.

### (7)–(10)
Risks, omissions, decisions, and rollback are in the overall section. Coordinates: LSIRC and IRSC via OpenStreetMap Nominatim this session.

---

## Transportation / Transit

### (1) What changed
One local listing under the existing **Transit** category:
- **GoLine — Indian River County Public Buses**, operated by Senior Resource Association. 14 fixed routes, described as zero-fare / no charge (donation encouraged on GoLine’s Riding page), wheelchair accessible, riders under 12 with an adult. Door-to-bus-stop connector: call to ask. Door-to-door Community Coach is pointed to under Mobility Equipment (same agency, already listed).

The official site disagrees with itself on Saturday hours and on the information-line hours; the card states both published versions and tells people to call (772) 569-0903.

### (2) Where
New id: `goline-transit`. Address 694 14th Street, Vero Beach (same SRA address already used for Community Coach); coordinates reused from that existing card.

### (3)–(4) Tests
Opening **Transit** shows the GoLine card instead of the empty 211 fallback. Queries `goline` and `bus` route here. Screenshots: `evidence/after/w390-transit-en.png`, `w390-transit-ht.png`.

### (5) Status
**IMPLEMENTED** / **TESTED** locally. Saturday-hour conflict: disclosed, still **NEEDS VERIFICATION** by calling the agency. Translations: **NEEDS VERIFICATION**.

### (6) Sources
| Resource | URL | HTTP | Date checked (ET) |
|---|---|---|---|
| GoLine home | https://www.golineirt.com/ | 200 | Nov 13, 2026 |
| Riding GoLine | https://www.golineirt.com/info.html | 200 | Nov 13, 2026 |
| SRA Transportation | https://www.seniorresourceassociation.org/services/transportation/ | 200 | Nov 13, 2026 |
| SRA Community Coach | https://www.seniorresourceassociation.org/services/community-coach/ | 200 | Nov 13, 2026 |

Home (Nov 13): weekdays 6:00 AM–9:00 PM; Saturday 7:00 AM–7:00 PM on most routes; no service Thanksgiving, Christmas, New Year’s Day; info line (772) 569-0903, listed 6:00 AM–7:00 PM weekdays; footer office (772) 569-0760 at 694 14th Street. Riding page: Saturday 8:00 AM–5:00 PM in one section and 7:00 AM–7:00 PM in another; info line 7:00 AM–6:00 PM; no fare, donation encouraged; all vehicles wheelchair accessible; under 12 with an adult; door-to-bus-stop connector. SRA describes GoLine as zero-fare and Community Coach fares as $0 to a maximum of $2.

### (7)–(10)
See overall. Community Coach was not moved out of Mobility Equipment.

---

## Housing

### (1) What changed
Kept the two existing Section 8 cards. Added:
1. **Treasure Coast Homeless Services Council — Coordinated Entry** (CoC FL-509), 2525 St Lucie Avenue, Vero Beach, (772) 213-9040, Mon–Fri 8:30 AM–5:00 PM. Their site says prevention services are not being provided at this time.
2. **Hope for Families Center** — family emergency shelter, 720 4th Street, Vero Beach, (772) 567-5537. Intake hours cited from TCHSC (not listed on Hope for Families’ own site). Program requirements and a waiting list are summarized from the organization’s site.
3. **SafeSpace** — state-certified domestic-violence shelter and 24-hour hotline (772) 288-7023 for Indian River, Martin, and St. Lucie. Address confidential; no map button; all services free per their site.
4. **United Against Poverty — Crisis Stabilization (Indian River)**, 1400 27th Street, (772) 564-9365, hours from UAP’s own campus page. Housing/shelter assistance is listed as a possible care-plan step, not as an overnight shelter. TCHSC lists a different address and slightly different hours; the card uses UAP’s own page and says to confirm.

### (2) Where
New ids: `tchsc-coordinated-entry`, `hope-for-families`, `safespace-shelter`, `uap-irc-housing`. Existing: `irc-section8`, `habc-section8`.

### (3)–(4) Tests
Housing shows all six cards. `shelter` and `housing` route here. SafeSpace has a tel: link to the official hotline and **no** Google Maps link. Screenshots: `evidence/after/w390-housing-en.png`, `w390-housing-ht.png`.

### (5) Status
**IMPLEMENTED** / **TESTED** locally. Address/hours conflicts and HFC intake hours (TCHSC vs org site): disclosed, **NEEDS VERIFICATION** by calling. Translations: **NEEDS VERIFICATION**. Hope for Families coordinates: US Census Geocoder match for `720 4TH ST, VERO BEACH, FL, 32962` (Nominatim had no hit).

### (6) Sources
| Resource | URL | HTTP | Date checked (ET) |
|---|---|---|---|
| TCHSC Coordinated Entry | https://tchelpspot.org/coordinated-entry-homeless-assistance/ | 200 | Nov 13, 2026 |
| Hope for Families | https://hopeforfamiliescenter.org/ | 200 | Nov 13, 2026 |
| SafeSpace intervention services | https://safespacefl.org/overview-intervention-services/ | 200 | Nov 13, 2026 |
| SafeSpace contact | https://safespacefl.org/contact/ | 200 | Nov 13, 2026 |
| UAP Indian River campus | https://unitedagainstpoverty.org/campus/indian-river/ | 200 | Nov 13, 2026 |
| UAP Crisis Stabilization | https://unitedagainstpoverty.org/crisis-stabilization-program/ | 200 | Nov 13, 2026 |
| IRC Housing Services (existing card) | https://indianriver.gov/services/community_services/housing_services/index.php | 200 | Nov 13, 2026 |
| HABC (existing card) | https://habc.us/abouthcv/ | 200 | Nov 13, 2026 |

### (7)–(10)
See overall. Did not invent shelter street addresses. Did not add House of Hope (Stuart) or UAP St. Lucie as primary IRC listings.

---

## Live-test defect fixes (same PR)

Before images are the live-test captures from `/workspace/community-bridge-test-2026-11-13/` (copied to `evidence/before/`). After images are Playwright captures of this branch.

### 1. Haitian Creole expanded listing — untranslated English label
- **Finding:** On the live-test screenshot, the only English-looking string on the expanded HT card was the broken Listen control (`U0001f50a Koute`). All field labels (ORÈ, POU KI MOUN LI YE, etc.) were already in Creole on current `main`. A full pass of every category in es/ht/pt, expanded and collapsed, found no remaining English UI chrome labels.
- **Fix:** None required for the field labels themselves; the Listen glyph fix (below) removes the English-looking `U0001f50a` text. Verified after: `evidence/after/ht-expanded-211.png`.
- **Status:** **TESTED**. Translations of *new* listing prose still **NEEDS VERIFICATION** by a native speaker.

### 2. Listen buttons showed literal `U0001f50a Listen`
- **Cause:** A Python-style `\U0001f50a` escape is not valid JavaScript, so the browser painted the letters `U0001f50a`. `index.html` on `main` (`0f38789`, already equal to the live GitHub Pages HTML at check time) already contains the literal 🔊 character (U+1F50A). Three preview candidate files still had `\U0001f50a`.
- **Fix:** Left the working literal 🔊 in `index.html`. Replaced leftover `\U0001f50a` in `index-p1-candidate.html`, `index-p1-promo-candidate.html`, `index-pilot-candidate.html`, `index-section8-candidate.html`, and `phase2-candidate.html`. Confirmed in Playwright for en/es/ht/pt: first code point is `1f50a`, label is Listen / Escuchar / Koute / Ouvir. After: `evidence/after/listen-en.png` (and `listen-es.png`, `listen-ht.png`, `listen-pt.png`). Before: `evidence/before/desktop-listen-label.webp`.
- **Status:** **IMPLEMENTED** / **TESTED**.

### 3. Favicon 404
- **Cause:** The live page had no `<link rel="icon">`, so the browser requested `https://mrjosueayalaperez-dev.github.io/favicon.ico` (user-site root, not this project). That path is outside this repo.
- **Fix:** Added `favicon.ico` and `favicon-32.png` (teal “bridge” mark in the site’s existing teal) and a relative `<link rel="icon">` on **every HTML page** in the repo, so the browser requests `.../Community-Bridge-/favicon.ico`. Local fetch: both files 200. Will only appear on the live host after a merge you approve.
- **Status:** **IMPLEMENTED** / **TESTED** locally. **Not deployed.**

### Layout checks requested before report
- **390px overflow:** none, four languages, home + three new sections. **TESTED.**
- **Tap targets ≥ 44px:** after CSS min-height on buttons, language toggle, details/back, and source links, 0 undersized controls at 390px on home + new sections. **IMPLEMENTED** / **TESTED.**
- **External links non-404:** 65/65 non-404 on the crawl of this branch. A previously 404 source PDF (`https://211palmbeach.org/wp-content/uploads/2021/12/Food-Reference-Guide-IRC.pdf`) used on two existing food listings was retargeted to the official 211 Palm Beach homepage (`https://211palmbeach.org/`, 200). Other non-404 anomalies (pre-existing, **NEEDS VERIFICATION**): `https://www.childhelp.org` 500; `http://www.salvationarmyflorida.org/verobeach/` 500; `http://seniorresourceassociation.org/` 500 (the `https://www.` SRA URL is 200); `https://mchb.hrsa.gov` 403; `https://ourfatherstablesoupkitchen.org/` 403; `https://brevardalz.org` 202; occasional client timeout (0) on `https://operationhopefl.org/` and `https://brevardalz.org/` that returned 200 earlier the same day.

---

## Full link-status table (this branch, Nov 13, 2026, ET)

See `evidence/verify-results.json` for the machine-readable list (url, status, note, date). New-resource rows used in the three sections are all 200 except as noted in the source tables above.
