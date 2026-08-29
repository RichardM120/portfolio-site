# Casting submission extractor

Pulls eleven fields out of a folder of casting-submission emails in a Gmail
Takeout `.mbox`, saves the photos, and writes a CSV/XLSX ready for Google Sheets.

Standard library only. `--xlsx` additionally needs `openpyxl`.

## Use

```bash
# 1. see which Gmail label holds the submissions
python3 extract_submissions.py --mbox ~/Downloads/Takeout/Mail/"All mail Including Spam and Trash.mbox" --list-labels

# 2. dry run on the first 20 of that label
python3 extract_submissions.py --mbox <path> --label "Casting" --out ~/Documents/casting --limit 20

# 3. full run
python3 extract_submissions.py --mbox <path> --label "Casting" --out ~/Documents/casting --xlsx
```

## Output

```
submissions.csv     one row per applicant, headers in the required order
submissions.xlsx    same, frozen header row + autofilter (--xlsx)
audit.csv           one row per EMAIL: every value, the rule that found it, confidence
media-log.csv       every image part, kept or discarded, with the reason
media/<Last_First>/ that applicant's photos
media/_all-images/  every kept photo, flat, for browsing the whole set
```

Read `audit.csv` before trusting the sheet. Anything marked `/low` was a guess
of last resort — usually a name recovered from an email address.

## What it does with messy input

| Situation | Behaviour |
|---|---|
| Platform relay (Spotlight, Mandy, no-reply@) | Digs past the relay to `Reply-To`, then a labelled `Email:` line, then a body scan |
| Agency submitting a client | Row is the actor, not the agent; the agent's switchboard goes to notes |
| Stub `text/plain` beside a real HTML body | Takes whichever part actually carries the message |
| `SMITH, Jane` / `O'Brien` / `van der Berg` | Split correctly, capitalisation and particles preserved |
| One-word sign-off ("Warmly, Amara") | Tops up the surname from the From display name |
| Same person, two addresses | Merged on name + shared phone or link; earliest date kept |
| DOB instead of an age | Age computed as at the date received |
| Graduation year, headshot | **Never** used to infer an age |
| Name, photo, voice, role | **Never** used to infer gender or pronouns |
| Signature logos, tracking pixels | Discarded under 20 KB or 300 px, or on a junk filename |
| Agent switchboard vs actor mobile | Mobile wins; VAT and company numbers rejected |

Blank beats guessed, everywhere. An empty cell is a correct answer.

## Testing

`make_sample_mbox.py` builds an 18-message fixture (14 submissions + 4 that must
be filtered out) covering every row of the table above. Everything in it is
invented — fictional people, `example.com` addresses, and Ofcom drama-reserved
phone numbers that cannot connect to a real line.

```bash
python3 make_sample_mbox.py sample.mbox
python3 extract_submissions.py --mbox sample.mbox --label "Bluebird Submissions" --out ./run --xlsx
```

Expected: 14 emails in, 12 applicant rows out (two merges), 14 images kept,
4 logos discarded, one row flagged `Needs review` and one `/low` confidence name.

## Getting it into Google Sheets

The CSV imports directly: **File → Import → Upload → Replace current sheet**.
That is the shortest reliable path and needs no API credentials.

To write via the API instead, use `valueInputOption=RAW`. With `USER_ENTERED`,
Sheets reinterprets `+44 7700 900123` as a formula or a number and re-localises
the dates.
