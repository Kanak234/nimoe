"""Read-only GitHub portfolio inventory and optional Neutron analysis."""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.github.com"
OWNER = os.getenv("GH_OWNER", "Kanak234")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", "")
OUT = Path("reports")
OUT.mkdir(exist_ok=True)

def request_json(url, token=TOKEN, method="GET", payload=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "nimoe-auditor/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def repositories():
    repos = []
    for page in range(1, 30):
        params = urllib.parse.urlencode({"per_page": 100, "page": page, "affiliation": "owner"})
        # /user/repos includes private repositories selected by the PAT.
        url = f"{BASE}/user/repos?{params}"
        batch = request_json(url)
        if not isinstance(batch, list):
            raise ValueError("Unexpected GitHub repository response")
        repos.extend(r for r in batch if r.get("owner", {}).get("login", "").lower() == OWNER.lower())
        if len(batch) < 100:
            break
    return repos

def exists(repo, path):
    encoded = urllib.parse.quote(path, safe="/")
    try:
        request_json(f"{BASE}/repos/{repo}/contents/{encoded}")
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise

def audit(repo):
    full = repo["full_name"]
    findings = []
    if repo.get("archived"):
        findings.append("archived")
    if not repo.get("description"):
        findings.append("missing_description")
    if not repo.get("license"):
        findings.append("license_not_detected")
    for path, code in (
        ("README.md", "missing_readme"),
        ("SECURITY.md", "missing_security_policy"),
        ("CONTRIBUTING.md", "missing_contribution_guide"),
    ):
        if not exists(full, path):
            findings.append(code)
    try:
        workflows = request_json(f"{BASE}/repos/{full}/contents/.github/workflows")
        if not isinstance(workflows, list) or not any(x.get("name", "").endswith((".yml", ".yaml")) for x in workflows):
            findings.append("no_workflow_detected")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            findings.append("no_workflow_detected")
        else:
            raise
    return {
        "repository": full, "private": repo.get("private"),
        "default_branch": repo.get("default_branch"), "stars": repo.get("stargazers_count"),
        "findings": findings, "audit_scope": "metadata_and_common_files_only",
    }

def neutron_summary(results):
    url = os.getenv("NEUTRON_API_URL", "").strip()
    model = os.getenv("NEUTRON_MODEL", "").strip()
    key = os.getenv("NEUTRON_API_KEY", "").strip()
    if not all((url, model, key)):
        return {"status": "skipped", "reason": "Configure API secret and NEUTRON_API_URL/NEUTRON_MODEL variables"}
    if not url.startswith("https://"):
        return {"status": "skipped", "reason": "NEUTRON_API_URL must be HTTPS"}
    # Only transmit repository names and high-level findings; never source code or secrets.
    compact = [{"repository": x["repository"], "findings": x["findings"]} for x in results]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Summarize audit findings and suggest prioritized, non-destructive improvements. Do not claim projects are production ready."},
            {"role": "user", "content": json.dumps(compact)[:60000]},
        ],
        "max_tokens": 1200,
    }
    try:
        response = request_json(url, token=key, method="POST", payload=payload)
        return {"status": "ok", "response": response.get("choices", [{}])[0].get("message", {}).get("content", "")}
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        return {"status": "error", "reason": type(exc).__name__}

def main():
    try:
        repos = repositories()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise SystemExit(f"Repository listing failed: {type(exc).__name__}; configure PORTFOLIO_GH_TOKEN for full private-repo access")
    results = []
    for repo in repos:
        if repo["full_name"].lower() == f"{OWNER}/nimoe".lower():
            continue
        try:
            results.append(audit(repo))
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            results.append({"repository": repo["full_name"], "error": type(exc).__name__})
    report = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "owner": OWNER,
              "repository_count": len(results), "repositories": results}
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "neutron.json").write_text(json.dumps(neutron_summary(results), indent=2) + "\n")
    print(f"Audited {len(results)} repositories; reports uploaded as artifacts")

if __name__ == "__main__":
    main()
