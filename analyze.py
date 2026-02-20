"""
Kruncher Portfolio Analyzer

Fetches the first N portfolio companies, retrieves their latest analysis
report, and uses Claude to generate a 4-bullet investor summary for each.

Usage:
    pip install httpx anthropic
    export KRUNCHER_API_KEY=<your key>
    export ANTHROPIC_API_KEY=<your key>   # get one at console.anthropic.com
    python analyze.py
"""

import asyncio
import json
import os
import sys

import anthropic
import httpx

# ── Config ──────────────────────────────────────────────────────────────────
KRUNCHER_BASE = "https://api.kruncher.ai/api/integration"
N_COMPANIES   = 2   # change to process more companies


# ── Kruncher helpers ─────────────────────────────────────────────────────────
def kruncher_headers() -> dict:
    key = os.environ.get("KRUNCHER_API_KEY", "")
    if not key:
        sys.exit("ERROR: KRUNCHER_API_KEY is not set.")
    return {"Authorization": key}


async def fetch_projects(client: httpx.AsyncClient, n: int) -> list[dict]:
    """Return the first `n` projects."""
    resp = await client.get(
        f"{KRUNCHER_BASE}/projects",
        headers=kruncher_headers(),
        params={"page": 0, "pageSize": n},
    )
    resp.raise_for_status()
    data = resp.json()
    # Handle both plain list and paginated-object responses
    if isinstance(data, list):
        return data[:n]
    return (data.get("content") or data.get("items") or [])[:n]


async def fetch_latest_analysis(client: httpx.AsyncClient, project: dict) -> dict | None:
    """Return the full report for the most recent analysis of a project."""
    analyses = project.get("analyses", [])
    if not analyses:
        return None
    latest = sorted(analyses, key=lambda a: a.get("createdAt", ""), reverse=True)[0]
    analysis_id = latest.get("analysisId")
    if not analysis_id:
        return None
    resp = await client.get(
        f"{KRUNCHER_BASE}/analysis/detail",
        headers=kruncher_headers(),
        params={"analysisId": analysis_id},
    )
    resp.raise_for_status()
    return resp.json()


# ── Claude summarizer ─────────────────────────────────────────────────────────
def summarize_with_claude(company_name: str, report: dict) -> str:
    """Ask Claude to produce a 4-bullet early-stage investor summary."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=anthropic_key)

    prompt = f"""You are an expert early-stage venture capital analyst.

Below is the full Kruncher data report for a portfolio company called "{company_name}".
Analyze it and write exactly 4 concise bullet points for an early-stage investor.
Cover: where the company is today, how it is growing, what looks promising, and what are the key risks or weaknesses.
Be specific — use numbers from the report where available.
Format: return only the 4 bullet points, nothing else.

--- REPORT ---
{json.dumps(report, indent=2)}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print(f"Fetching first {N_COMPANIES} portfolio companies from Kruncher…\n")

    async with httpx.AsyncClient(timeout=30) as client:
        projects = await fetch_projects(client, N_COMPANIES)

        if not projects:
            print("No projects found for this account.")
            return

        print(f"Found {len(projects)} project(s). Fetching analysis reports…\n")

        tasks = [fetch_latest_analysis(client, p) for p in projects]
        reports = await asyncio.gather(*tasks)

    # ── Print summaries ──────────────────────────────────────────────────────
    for project, report in zip(projects, reports):
        name = (
            project.get("name")
            or project.get("companyName")
            or project.get("projectName")
            or f"Project {project.get('id', '?')}"
        )

        print("=" * 60)
        print(f"  {name}")
        print("=" * 60)

        if report is None:
            print("  [No analysis available yet for this company]\n")
            continue

        summary = summarize_with_claude(name, report)
        for line in summary.splitlines():
            print(f"  {line}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
