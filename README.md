# NIMOE — Portfolio Automation

Private control repository for auditing repositories owned by Kanak234.

## Setup
1. In **Settings → Secrets and variables → Actions**, create `PORTFOLIO_GH_TOKEN` with read access to the repositories to audit (fine-grained PAT: Metadata read, Contents read; private repos must be selected).
2. The existing secret named `API` is reserved for Neutron 3 Ultra. Never paste its value into source code.
3. Optionally configure repository **Variables** `NEUTRON_API_URL` (full OpenAI-compatible chat-completions URL) and `NEUTRON_MODEL` (provider's exact model ID). Without these, AI analysis is skipped.
4. Enable GitHub Actions if prompted. Run **Portfolio audit → Run workflow** for an immediate scan.

The workflow runs hourly and on manual dispatch. It audits repository metadata, flags missing basic engineering safeguards, and uploads a JSON report. It **does not automatically edit or merge code**, run untrusted repository scripts, guarantee production readiness, or generate GitHub stars. Cross-repository write automation requires separate explicit credentials, tested fix generation, and approval controls.

Note: GitHub-hosted schedules are best-effort and can be delayed or disabled due to platform policies.
