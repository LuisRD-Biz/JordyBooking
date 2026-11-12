import re
import subprocess
import sys

RULES = {
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "github-token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})",
    "meta-token": rb"\bEAA[A-Za-z0-9]{50,}",
    "telegram-token": rb"(?<![0-9])[0-9]{5,16}:[A-Za-z0-9_-]{35,}(?![A-Za-z0-9_-])",
    "sk-api-token": rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}",
    "aws-access-key": rb"\bAKIA[A-Z0-9]{16}\b",
}


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    history = "--history" in sys.argv
    refs = git("rev-list", "--all").decode().splitlines() if history else ["HEAD"]
    seen = set()
    failures = set()
    for ref in refs:
        for entry in git("ls-tree", "-r", "-z", ref).split(b"\0"):
            if not entry:
                continue
            meta, raw_path = entry.split(b"\t", 1)
            _, kind, sha = meta.split()
            if kind != b"blob":
                continue
            path = raw_path.decode("utf-8", errors="replace")
            name = path.rsplit("/", 1)[-1]
            if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
                failures.add((path, "tracked-environment"))
            if name.endswith((".pem", ".p12", ".pfx", ".sqlite", ".sqlite3", ".dump")):
                failures.add((path, "private-artifact"))
            if sha in seen:
                continue
            seen.add(sha)
            content = git("cat-file", "blob", sha.decode())
            for rule, pattern in RULES.items():
                if re.search(pattern, content):
                    failures.add((path, rule))
    for path, rule in sorted(failures):
        print(f"BLOCKED {rule}: {path}")
    print(f"Audited {len(seen)} unique blobs; findings: {len(failures)}")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
