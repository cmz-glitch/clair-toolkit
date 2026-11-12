"""Cold-outreach dedupe against a contacted-email list, by address and domain."""

from __future__ import annotations

from pathlib import Path

from clair_toolkit.util import domain_of, emails_in, is_freemail


def load_contacts(path: Path) -> list[str]:
    found: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        emails = emails_in(line)
        if emails:
            found.append(emails[0])
        elif "@" in line:
            found.append(line.casefold())
    return found


def dedupe(contacts: list[str], candidates: list[str]) -> dict:
    by_address = set(contacts)
    by_domain: dict[str, str] = {}
    for email in contacts:
        domain = domain_of(email)
        if domain and not is_freemail(domain):
            by_domain.setdefault(domain, email)
    new: list[str] = []
    skip: list[dict] = []
    for candidate in candidates:
        email = (emails_in(candidate) or [candidate.strip().casefold()])[0]
        domain = domain_of(email)
        if email in by_address:
            skip.append({"email": email, "via": "address", "matched": email})
            continue
        if domain and not is_freemail(domain) and domain in by_domain:
            skip.append({"email": email, "via": "domain", "matched": by_domain[domain]})
            continue
        new.append(email)
    return {"hit": bool(skip), "new": new, "skip": skip}
