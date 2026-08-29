# Prompt: Extract casting submissions from a Gmail Takeout `.mbox` into Google Sheets

**What this is.** A single, self-contained prompt to paste into Claude Code (or Claude
Desktop with filesystem access) **running on the MacBook that holds the Takeout folder**.
It parses the `.mbox`, interrogates the prose in each email for the eleven required
fields, saves every genuine photo to a local folder, uploads those to Drive, and writes
one row per applicant into the target Google Sheet.

**Before you run it**
1. Open Terminal, `cd` to any working folder (e.g. `cd ~/Documents`), run `claude`.
2. Paste everything between the `--- BEGIN PROMPT ---` and `--- END PROMPT ---` markers.
3. It will do a 20-email dry run first and show you a table. Check the table, then say
   "go" for the full run. Don't skip the dry run — that's where you catch a bad filter.
4. Expect ~10–25 minutes for 200+ emails, most of it the per-email reading pass.

A runnable implementation of this prompt lives in `tools/casting-extractor/` — run that
directly if you would rather not have Claude write the parser from scratch.

**Edit these two lines in the prompt if anything changed:** the `MBOX` path and the
`SHEET_URL`. Everything else is generic.

---

--- BEGIN PROMPT ---

You are extracting structured casting-submission data from a Gmail Takeout archive on
this Mac. Work carefully and deterministically. Read the whole brief before starting.

## Inputs

```
MBOX      = ~/Downloads/Takeout/Mail/All mail Including Spam and Trash.mbox   (~2.09 GB)
SHEET_URL = https://docs.google.com/spreadsheets/d/12Bsu9ERE7zfMtL2lpHy9xjAyQ8tBz9BUUboi-kuxfBI/edit?gid=0#gid=0
WORKDIR   = ~/Documents/casting-submissions          (create it)
```

The archive is the *whole* mailbox. The emails I care about are the 200-odd submissions
that sit in one Gmail label/folder. Takeout preserves labels in the non-standard
`X-Gmail-Labels:` header on every message — that header is your primary filter. Do not
try to identify submissions by reading all 2 GB.

## Deliverables

1. `WORKDIR/submissions.csv` — one row per applicant, columns exactly as specified below.
2. `WORKDIR/media/` — one sub-folder per applicant containing their photos, plus
   `WORKDIR/media/_all-images/` containing every kept image flat, filename-prefixed with
   the applicant, so I can browse the whole set in one place.
3. A Drive folder `Casting Submissions <YYYY-MM>` holding the images, mirroring the same
   per-applicant sub-folders.
4. The target Google Sheet, tab `gid=0`, populated: headers in row 1, data from row 2.
5. `WORKDIR/audit.csv` — the provenance file (see Stage 7). This is how I check your work.

## Stage 0 — Environment and safety

- Confirm the mbox exists and print its size. If the path is wrong, `find ~/Downloads -name "*.mbox" -maxdepth 4` and ask me which one.
- Python 3 only, standard library where possible (`mailbox`, `email`, `csv`, `hashlib`, `re`). Ask before `pip install` anything.
- **Never load the 2 GB file into memory.** Stream it. Use `mailbox.mbox` with a factory that applies `email.policy.default` so RFC 2047 encoded headers (`=?UTF-8?B?...`) decode to real Unicode:
  ```python
  import mailbox, email
  mb = mailbox.mbox(MBOX, factory=lambda f: email.message_from_binary_file(f, policy=email.policy.default), create=False)
  ```
- Work read-only on the mbox. Never modify, move or delete it.
- Everything you write goes in `WORKDIR`. Nothing in the Downloads folder, nothing in a git repo.
- This is real personal data belonging to real applicants. Keep it local, don't send bodies or attachments to any third-party service, and share the Sheet only with the addresses I name.

## Stage 1 — Index the mailbox

Pass 1, headers only, no body parsing. For every message record: index, `Message-ID`,
`Date`, `From`, `Reply-To`, `Subject`, `X-Gmail-Labels`, `X-Gmail-Thread-Id`, attachment
count, attachment filenames + MIME types. Write `WORKDIR/index.csv`.

Then print me:
- total message count,
- every distinct value of `X-Gmail-Labels` with a count, sorted by count descending.

**Stop and ask me which label is the submissions folder.** Show your best guess first —
the label whose count is nearest 200 and whose name reads like casting/auditions/
submissions/applications. Don't proceed on a guess alone.

## Stage 2 — Select the submission set

Filter to messages carrying the chosen label. Then sanity-check the selection:

- Print the count. If it is wildly off 200, say so and stop.
- Exclude messages I clearly sent (`From:` is my own address) unless they're the only
  copy of a submission — check that before dropping anything.
- Keep every message for now, including duplicates and follow-ups. Grouping happens at
  Stage 6, not here.
- If a plausible submission exists *outside* the label (same subject line, same sender,
  has a headshot attached), list those separately at the end as "possible strays". Don't
  silently fold them in.

## Stage 3 — Extract media

For each selected message, walk all MIME parts (`msg.walk()`), including inline parts
(`Content-Disposition: inline`) and HTML-embedded `cid:` images, not just attachments.

**Keep** — `image/jpeg`, `image/png`, `image/heic`, `image/webp`, `image/tiff`, and any
PDF whose filename suggests a headshot, CV, résumé or spotlight profile.

**Discard** — signature furniture and tracking junk:
- file smaller than 20 KB, **or** shortest side under 300 px (read dimensions from the
  file header; if you can't, fall back to size alone and log it),
- filename matching `logo|icon|banner|signature|footer|spacer|pixel|beacon|social|twitter|facebook|linkedin|instagram|whatsapp|award|badge`,
- anything whose SHA-256 you've already seen **three or more times across different
  senders** — that's a shared template asset, not a headshot.

`image00N.png`-style names from Outlook are ambiguous: judge them on the size test only.

**Naming and layout.** Per applicant slug `Lastname_Firstname` (fall back to the sender's
email local part when the name is unresolved at this stage; rename in Stage 6 once the
name is known):
```
WORKDIR/media/Smith_Jane/Smith_Jane_01.jpg
WORKDIR/media/_all-images/Smith_Jane_01.jpg     (copy, flat, for browsing)
```
Convert HEIC to JPG with `sips -s format jpeg` (built into macOS) and keep the original.
Deduplicate within an applicant by SHA-256. Sanitise filenames: strip path separators and
leading dots from any attachment name before writing it — never trust the filename in the
email.

Log every kept and discarded part with its reason to `WORKDIR/media-log.csv`.

## Stage 4 — Read each email and extract the fields

This is the part that matters. Get the plain-text body (`text/plain` if present, else
strip tags from `text/html` — and pull `href` values out of the HTML *before* stripping,
you'll need them). Strip quoted reply chains and the platform's own footer boilerplate,
but keep signature blocks — that's where the phone number and location usually live.

Then **read the email like a human would** and pull the data out of the sentences.
"I'm Jane, 28, based just outside Manchester, you can see my Spotlight below" is four
fields. Structured forms, free-form pitches, and forwarded platform notifications all
need to yield the same eleven columns.

Two absolute rules:
- **Never invent a value.** If it isn't stated or safely derivable, leave the cell empty.
  An empty cell is a correct answer; a plausible guess is a wrong one.
- **Record where each value came from** — you'll write this to the audit file.

### Field-by-field extraction rules

**Date Received** — from the `Date:` header only, never from body text. Convert to
Europe/London and format `YYYY-MM-DD HH:MM`. On merge, use the *earliest* email from that
applicant (first contact), and note any later ones in the audit.

**First Name / Last Name** — in priority order, stop at the first that yields a confident
name:
1. Explicit self-identification in the body — "My name is…", "Name:", "I'm X and…"
2. The sign-off / signature block
3. `From:` display name, when it reads as a person (not an agency, not a company, not the
   email address repeated)
4. Attachment filenames — `Jane_Smith_Headshot.jpg`, `Jane Smith CV.pdf`
5. Email local part — `jane.smith@` → Jane Smith. Lowest confidence; always flag it.

Handling: `SMITH, Jane` → First `Jane`, Last `Smith`. Strip honorifics (Mr, Ms, Mrs, Dr)
and trailing agency tags (`Jane Smith – Curtis Brown`, `Jane Smith (Independent)`).
Preserve particles and capitalisation exactly: `van der Berg`, `de la Cruz`, `O'Brien`,
`MacLeod`, `Ngũgĩ`. Hyphenated surnames stay whole in Last Name. A single-token name goes
in First Name with Last Name blank — don't split it. Names in non-Latin scripts stay in
their own script; add a transliteration to the audit file only.

**Sender Email Address** — the addr-spec from `From:`, lowercased, display name stripped.

*Except* when the sender is a platform relay — Spotlight, Mandy, Backstage, Casting
Networks, StarNow, a Wix/Squarespace/Google Forms notification, or anything at
`no-reply@`/`notifications@`/`donotreply@`. Then the applicant's real address is, in
order: `Reply-To:` → a labelled "Email:" line in the body → the only non-platform
`mailto:` in the body. Use the relay address only when none of those exist, and flag it in
the audit as `relay-only`.

**Gender / Pronouns** — **only from an explicit statement.** Valid sources: a pronoun
string (`she/her`, `he/him`, `they/them`, `she/they`), a `Pronouns:` line, a `Gender:`
field, a self-description ("as a trans woman", "I'm a male actor"), or the gender line in
a pasted Spotlight/CV block.

**Never infer this from a first name, a headshot, a voice reel, the role applied for, or
anything else.** No exceptions — a wrong guess here is worse than a blank. If only a
gender word is given and no pronouns, record the word as written (`Female`). If both,
record both: `Female — she/her`.

**Age / Playing Age** — in priority order:
1. Stated playing age range → `Playing 25–35`
2. Stated actual age → `28`
3. Date of birth → compute the age *as at the Date Received* → `31 (from DOB)`
4. An age or playing-age line inside a pasted CV/Spotlight block

Normalise dashes to en-dashes, drop "years old"/"yrs"/"y.o.". A graduation year, a
training-course date, or "recent graduate" is **not** an age — leave the cell blank and
note it. Never estimate an age from a photo.

**Phone Number** — pull candidate numbers from the body and signature. Prefer a UK mobile
(`07…`, `+447…`) over a landline, and the applicant's own number over an agent's
switchboard when both appear. Format UK numbers as `+44 7xxx xxxxxx`, international in
E.164 with spacing. Reject anything that is actually a date, a time, a house number, a
postcode, a Companies House or VAT number, a Spotlight PIN, a bank detail, or a number
inside the relay platform's own footer. If two genuine numbers survive, take the one
nearest the sign-off and record the other in the audit.

**Location** — in priority order: an explicit "based in X" / "Location:" / "X-based"
statement → a city in the signature address block → a UK postcode's outward code mapped
to its town (only when unambiguous) → the phone country code, which gives you the country
only and must be flagged. Normalise to `City, Country`: `London, UK`, `Manchester, UK`,
`Dublin, Ireland`. Map London boroughs and areas to `London, UK`. Put qualifiers —
"willing to travel", "self-tape only", "relocating in September" — in the audit notes, not
in the cell.

**Spotlight / Portfolio Link** — collect every URL from both the plain text and the HTML
`href` attributes. Strip tracking parameters (`utm_*`, `fbclid`, `gclid`). Deduplicate.
Discard the platform's own unsubscribe / privacy / marketing / image-CDN links and all
`mailto:` links.

Rank what's left and put the best first, joining the rest with ` | `:
`spotlight.com` → `mandy.com` → `backstage.com` → `castingcallpro` → `starnow` → `imdb.com`
→ a personal domain → Vimeo/YouTube showreel → Instagram → LinkedIn.

Don't expand shortened links (no network calls to third parties); keep them as-is and flag.

**Drive Image Links** — filled in at Stage 8. Leave blank until then.

**Status** — triage value, not free text. Use exactly one of:
- `New` — has a name, an email, and at least one of {phone, location, portfolio link}
- `Needs review` — missing enough that I can't action it
- `No media` — otherwise complete but sent no usable photo
- `Merged duplicate` — folded into another row (these rows are *not* written to the Sheet;
  they appear in the audit only)

## Stage 5 — Dry run, then stop

Run Stages 3–4 on the **first 20 selected emails only**. Print the results as a markdown
table with all eleven columns, plus a second table showing, per field, how many of the 20
were populated and which source rule fired.

**Then stop and wait for me.** I'll tell you to proceed, or correct the rules. Do not
start the full run unprompted.

## Stage 6 — Full run and merge

Run everything. Then group into one row per applicant:

- Primary key: normalised sender email address.
- Also merge when First + Last Name match exactly **and** phone or portfolio link matches
  — that's the same person writing from a second address. Never merge on name alone.
- Merge rules: earliest `Date Received` wins; for every other scalar field, the first
  non-empty value wins, and where two non-empty values genuinely conflict, take the one
  from the most recent email and record both in the audit; links and media are unioned.
- Rename media folders to the resolved `Lastname_Firstname` slug now.

Write `WORKDIR/submissions.csv` with these headers, in this order, spelled exactly:

```
Date Received,First Name,Last Name,Sender Email Address,Gender / Pronouns,Age / Playing Age,Phone Number,Location,Spotlight / Portfolio Link,Drive Image Links,Status
```

## Stage 7 — Audit file

Write `WORKDIR/audit.csv`: one row per *email* (not per applicant), with the applicant
slug, Message-ID, sender, and for each of the eleven fields both the extracted value and
the rule that produced it (`explicit-statement`, `signature-block`, `from-display-name`,
`email-local-part`, `derived-from-dob`, `postcode-lookup`, `not-found`, …). Add columns
for confidence (`high`/`medium`/`low`), merge target, and free-text notes for everything
you deliberately kept out of the Sheet.

Then print a summary: rows written, per-field fill rate, count by Status, every `low`
confidence extraction, and every email you couldn't parse at all.

## Stage 8 — Google Drive

Create a Drive folder `Casting Submissions <YYYY-MM>` with the same per-applicant
sub-folders and upload the kept images. Set each file to "anyone with the link can view"
**only if I confirm** — otherwise leave default permissions and the links will work for
people I share the folder with.

Put each applicant's file `webViewLink`s in **Drive Image Links**, joined with ` | `.

Route, in order of preference:
1. A Google Drive MCP connector, if one is configured in this Claude Code session.
2. `rclone` if it's already set up (`rclone listremotes`).
3. Python with OAuth desktop credentials.
If none is available, tell me which you'd like me to set up rather than picking for me.
If Drive is skipped entirely, put the local absolute paths in the column instead and say so.

## Stage 9 — Write the Google Sheet

Target: `SHEET_URL`, spreadsheet ID `12Bsu9ERE7zfMtL2lpHy9xjAyQ8tBz9BUUboi-kuxfBI`, tab `gid=0`.

- Headers exactly as listed in Stage 6 in row 1; data from row 2.
- **Use `valueInputOption=RAW`.** With `USER_ENTERED`, Sheets mangles `+44…` phone numbers
  into formulas or numbers and reinterprets the dates. RAW keeps every cell as the string
  you extracted.
- Read the sheet first. If it already has data, tell me what's there and ask before
  overwriting — don't clear anything on your own.
- Freeze row 1, bold it, set sensible column widths. Nothing else — no conditional
  formatting, no colour coding.
- Verify by reading the range back and confirming the row count and a sampled row match
  the CSV.

Same route preference as Stage 8 (MCP connector → OAuth). If neither is usable, stop and
tell me — I'll import `submissions.csv` by hand via **File → Import → Upload → Replace
current sheet**, and everything else you've produced still stands.

## Standing rules

- Blank beats guessed. Every time.
- Never infer gender or pronouns from a name, photo, or role.
- Never infer an age from a photo or a graduation year.
- Show me the numbers at each stage — counts, fill rates, exclusions — not just "done".
- Any email you can't parse goes in the audit with the reason. Nothing gets dropped
  silently.
- Stop and ask at the three marked decision points: which label, the dry-run review, and
  the Drive sharing permission.

--- END PROMPT ---

---

## Notes on the choices baked in

**Why `X-Gmail-Labels` is the filter.** Google Takeout flattens every Gmail label into one
mbox, but writes the labels back onto each message as a non-standard header. That turns
"the folder with 200 emails in it" into an exact selector, instead of guessing from
subject lines across a 2 GB file. The prompt makes Claude print the label histogram and
ask, rather than pattern-matching its way to a plausible-looking 200.

**Why the dry run is mandatory.** Extraction rules that look right in the abstract fail on
real submissions — a relay platform you didn't anticipate, a signature format that eats
the phone regex. Twenty rows in a table is the cheapest place to find that out.

**Why gender is explicit-only.** It's the one field where a confident-looking guess causes
real harm and is invisible in the output. Names don't carry gender reliably, and a
misgendered applicant in a casting spreadsheet is a bad, propagating error. Blank is
recoverable; wrong isn't.

**Why RAW on the Sheets write.** `USER_ENTERED` runs every cell through Sheets' parser:
`+44 7700 900123` can become a formula error or a number, and dates get re-localised.
RAW preserves exactly what was extracted.

**Why an audit file.** Eleven columns of clean data with no provenance can't be checked.
The audit file is what lets you see that eight rows got their name from an email local
part, or that three phone numbers came out of a signature that also held an agent's
switchboard.
