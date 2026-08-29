#!/usr/bin/env python3
"""Build a synthetic Gmail-Takeout-shaped .mbox for testing the extractor.

Everything here is invented: fictional people, example.com addresses, and
Ofcom drama-reserved phone numbers (07700 900xxx / 020 7946 0xxx) that can
never connect to a real line. Nothing in this file is real personal data.
"""
import datetime as dt
import email.utils
import mailbox
import struct
import sys
import zlib
from email.message import EmailMessage
from pathlib import Path

LABEL = "Casting/Bluebird Submissions"


def png(w, h, pad=30000, seed=0):
    tone = (150 + seed * 7 % 90, 130 + seed * 13 % 90, 110 + seed * 29 % 90)
    raw = b"".join(b"\x00" + bytes(tone) * w for _ in range(h))

    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    if pad:
        out += chunk(b"tEXt", b"Comment\x00" + f"sample-{seed}-".encode() + b"x" * pad)
    return out + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")


LOGO = png(120, 40, pad=0)
_seen = {}


def headshot(filename):
    """A distinct image per attachment, so dedupe-by-hash is actually exercised."""
    if filename not in _seen:
        _seen[filename] = png(800, 1000, seed=len(_seen) + 1)
    return _seen[filename]

BASE = dt.datetime(2026, 7, 6, 9, 15, tzinfo=dt.timezone.utc)
_n = [0]


def build(frm, subject, body, *, html=False, reply_to=None, label=LABEL,
          images=(), logo=False, hours=None):
    _n[0] += 1
    m = EmailMessage()
    m["From"] = frm
    m["To"] = "Richard Morland <richardmorland@example.com>"
    m["Subject"] = subject
    when = BASE + dt.timedelta(hours=hours if hours is not None else _n[0] * 7)
    m["Date"] = email.utils.format_datetime(when)
    m["Message-ID"] = f"<sample-{_n[0]:03d}@example.com>"
    m["X-Gmail-Labels"] = label
    if reply_to:
        m["Reply-To"] = reply_to
    if html:
        m.set_content("Please view this message in HTML.")
        m.add_alternative(body, subtype="html")
    else:
        m.set_content(body)
    for fn in images:
        m.add_attachment(headshot(fn), maintype="image", subtype="png", filename=fn)
    if logo:
        m.add_attachment(LOGO, maintype="image", subtype="png", filename="email-logo.png")
    return m


MESSAGES = []
A = MESSAGES.append

# 1 — clean submission, everything present and clearly stated
A(build("Jade Whitfield <jade.whitfield@example.com>", "Submission - Bluebird (Role: Nell)", """Hi Richard,

Please find my submission for Nell attached. Pronouns she/her. My playing age is 25-35,
though I'm 31.

Spotlight: https://www.spotlight.com/interactive/cv/1234-5678-9012?utm_source=email
Showreel: https://vimeo.com/987654321

I'm based in Hackney and happy to travel for filming.

Kind regards,
Jade Whitfield
07700 900123
""", images=("Jade_Whitfield_Headshot.png", "Jade_Whitfield_Full.png"), logo=True))

# 2 — platform relay: real applicant is in Reply-To, not From
A(build("Spotlight <notifications@spotlight.com>", "New submission received for Bluebird",
        """You have received a submission via Spotlight.

Name: Marcus Ade-Fowler
Gender: Male
Playing Age: 30 - 42
Location: Birmingham
Email: marcus.adefowler@example.org
Mobile: 07700 900456
Profile: https://www.spotlight.com/interactive/cv/2222-3333-4444

Do not reply to this email. Manage your preferences at https://www.spotlight.com/preferences
Unsubscribe: https://www.spotlight.com/unsubscribe?id=abc123
""", reply_to="Marcus Ade-Fowler <marcus.adefowler@example.org>", logo=True))

# 3 — HTML only, name only in the signature, DOB rather than an age
A(build("info@example.net", "Casting submission",
        """<html><body><p>Dear Richard,</p>
<p>I would love to be considered. My DOB is 14/03/1995 and I am a woman.</p>
<p>My profile is here:
<a href="https://www.mandy.com/uk/actor/profile/sophie-arden">Mandy profile</a>
and my site is <a href="https://sophiearden.example.co.uk">sophiearden.example.co.uk</a>.</p>
<p>I live in Leeds.</p>
<p>Best wishes,<br>Sophie Arden<br>Tel: 07700 900789</p>
<p style="font-size:9px">
<a href="https://example.net/unsubscribe">Unsubscribe</a> |
<a href="https://example.net/privacy">Privacy</a></p>
</body></html>""", html=True, images=("sophie_arden_headshot.png",)))

# 4 — surname-first with an apostrophe, he/him, Irish number
A(build("\"O'BRIEN, Declan\" <declan.obrien@example.ie>", "RE: Bluebird casting call", """Hello,

Declan here. I am 27 years old, he/him.

Based in Dublin but I can self-tape at short notice.
https://www.starnow.com/declanobrien

Cheers,
Declan O'Brien
+353 1 234 5678
""", images=("headshot-final.png",)))

# 5 — almost nothing: name has to come from the address, one photo
A(build("harriet.blakemore@example.com", "(no subject)",
        "Please see attached.\n", images=("IMG_4471.png",)))

# 6 — follow-up from #1: merges, adds a photo, keeps the earliest date
A(build("Jade Whitfield <jade.whitfield@example.com>", "Re: Submission - Bluebird (Role: Nell)",
        """Sorry - forgot to attach the profile shot. Also my new number is 07700 900321.

Jade
""", images=("Jade_Whitfield_Profile.png",), hours=96))

# 7 — agent submitting: switchboard and the actor's mobile both present
A(build("Kestrel Talent Management <submissions@example-agency.co.uk>",
        "Submitting Nia Camara for Bluebird", """Dear Richard,

We would like to submit Nia Camara for the role of Nell.

Playing age 22-30. Nia is based in Bristol. Pronouns: she/they.
Spotlight: https://www.spotlight.com/interactive/cv/5555-6666-7777

Nia's mobile is 07700 900654 if you would like to contact her directly.

Kind regards,
Priya Raman
Kestrel Talent Management
Office: 020 7946 0555
Company number 08123456 | VAT 123 4567 89
""", images=("Nia_Camara_Headshot.png",), logo=True))

# 8 — non-Latin name, they/them, location only via postcode
A(build("Оксана Демченко <o.demchenko@example.com>", "Submission for Bluebird", """Hi Richard,

Pronouns they/them. Playing age 20-28.

My address is 14 Wilbraham Road, M14 6JT.

Portfolio: https://www.instagram.com/o.demchenko.acts

Many thanks,
Оксана Демченко
07700 900222
""", images=("demchenko_headshot.png",)))

# 9 — a graduation year is NOT an age; the cell must stay empty
A(build("Tomasz Wisniewski <tomasz.w@example.com>", "Bluebird - submission", """Hello Richard,

I graduated from LAMDA in 2019 and have been working in theatre since.

I'm based in Glasgow. https://www.backstage.com/u/tomasz-wisniewski/

Thanks,
Tomasz Wisniewski
07700 900888
""", images=("tomasz_headshot.png",)))

# 10 — real submission but the only image is a signature logo -> "No media"
A(build("Rowan Ellis-Hart <rowan.ellishart@example.com>", "Interested in Bluebird", """Hi,

I'm interested in Nell. I'm 34, she/her, based in Cardiff.

https://www.spotlight.com/interactive/cv/9999-0000-1111

Best,
Rowan Ellis-Hart
07700 900444
""", logo=True))

# 11 — second address for #4: same name + same phone, must merge
A(build("Declan O'Brien <dec.obrien.actor@example.com>", "Additional material - Declan O'Brien",
        """Hi again, sending an extra shot from my personal address.

+353 1 234 5678
""", images=("declan_extra.png",), hours=150))

# 12 — everything buried in prose, actual age AND playing range in one sentence
A(build("Amara Osei <amara.osei@example.com>", "Nell // submission", """Hey Richard,

I'm Amara, 24, though I usually play 18-25, and I'm based just outside Bristol
so getting to set is easy. She/her. You can see my reel at
https://www.youtube.com/watch?v=abcdefghij and my Spotlight is
https://www.spotlight.com/interactive/cv/3141-5926-5358

Give me a shout on 07700 900777.

Warmly,
Amara
""", images=("amara_osei_1.png", "amara_osei_2.png")))

# 13 — Mandy relay, applicant address only as a mailto in the body
A(build("Mandy Casting <no-reply@mandy.com>", "Application: Bluebird - Nell", """An applicant has responded to your listing.

Applicant: Ben Larkham
Playing age: 40-52
Contact: ben.larkham@example.com
Based in Newcastle upon Tyne.

View the application: https://www.mandy.com/uk/applications/8891234
Unsubscribe from these alerts: https://www.mandy.com/unsubscribe/xyz
""", images=("ben_larkham.png",)))

# 14 — single-token name: First Name only, Last Name must stay empty
A(build("Solenne <solenne@example.fr>", "Bluebird submission", """Bonjour Richard,

My name is Solenne. I am 29, she/her, currently based in Paris but relocating
to London in September. Willing to travel.

https://www.spotlight.com/interactive/cv/7777-8888-9999

Solenne
+33 6 12 34 56 78
""", images=("solenne_headshot.png",)))

# --- noise: correct label absent, must be filtered out ------------------
A(build("newsletter@example-theatre.com", "This week at the Playhouse",
        "Our autumn season is now on sale. Book at https://example-theatre.com/whatson\n",
        label="Inbox,Newsletters", logo=True))
A(build("hmrc@example.gov.uk", "Your Self Assessment", "Nothing to see here.\n",
        label="Inbox"))
A(build("Mum <mum@example.com>", "Sunday?", "Are you coming for lunch? Call me on 07700 900999.\n",
        label="Inbox,Family"))
A(build("Jade Whitfield <jade.whitfield@example.com>", "Unrelated chat",
        "Different thread entirely, wrong label.\n", label="Inbox"))


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "sample.mbox")
    if out.exists():
        out.unlink()
    mb = mailbox.mbox(str(out))
    mb.lock()
    for m in MESSAGES:
        mb.add(m)
    mb.flush()
    mb.unlock()
    labelled = sum(1 for m in MESSAGES if m["X-Gmail-Labels"] == LABEL)
    print(f"wrote {out} - {len(MESSAGES)} messages, {labelled} labelled '{LABEL}'")


if __name__ == "__main__":
    main()
