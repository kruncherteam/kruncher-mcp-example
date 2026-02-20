"""
Kruncher MCP Server

Exposes Kruncher API data as MCP tools so AI assistants (Claude, Cursor, etc.)
can query projects and analysis reports.

Authentication:
  Set KRUNCHER_API_KEY environment variable with your Kruncher API key.

Usage:
  python server.py
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

KRUNCHER_BASE_URL = "https://api.kruncher.ai/api/integration"

mcp = FastMCP("Kruncher")


def _get_api_key() -> str:
    api_key = os.environ.get("KRUNCHER_API_KEY")
    if not api_key:
        raise ValueError(
            "KRUNCHER_API_KEY environment variable is not set. "
            "Please set it to your Kruncher API key."
        )
    return api_key


def _headers() -> dict:
    return {"Authorization": _get_api_key()}


@mcp.tool()
async def list_projects(page: int = 0, page_size: int = 20) -> dict:
    """
    List all Kruncher projects for the authenticated account.

    Args:
        page: Page number (0-indexed). Defaults to 0.
        page_size: Number of projects per page. Defaults to 20.

    Returns:
        Paginated list of projects. Each project contains an 'analyses' array
        with analysis IDs and creation timestamps.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{KRUNCHER_BASE_URL}/projects",
            headers=_headers(),
            params={"page": page, "pageSize": page_size},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_analysis_detail(analysis_id: str) -> dict:
    """
    Retrieve the full company analysis/report for a given analysis ID.

    Args:
        analysis_id: The unique identifier of the analysis to retrieve.
                     You can get analysis IDs from the 'analyses' array
                     returned by list_projects.

    Returns:
        Full company analysis report including all available data points.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{KRUNCHER_BASE_URL}/analysis/detail",
            headers=_headers(),
            params={"analysisId": analysis_id},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_latest_analysis_for_project(project_id: str) -> dict:
    """
    Retrieve the most recent analysis report for a specific project.

    Fetches the project details, identifies the latest analysis by creation
    date, and returns its full report.

    Args:
        project_id: The unique identifier of the project.

    Returns:
        Full company analysis report for the most recent analysis of the project.

    Raises:
        ValueError: If the project has no analyses yet.
    """
    # Search through pages to find the project
    page = 0
    page_size = 50
    target_project = None

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"{KRUNCHER_BASE_URL}/projects",
                headers=_headers(),
                params={"page": page, "pageSize": page_size},
            )
            response.raise_for_status()
            data = response.json()

            # Support both list and paginated-object responses
            projects = data if isinstance(data, list) else data.get("content", data.get("items", []))

            for project in projects:
                pid = str(project.get("id") or project.get("projectId") or "")
                if pid == str(project_id):
                    target_project = project
                    break

            if target_project:
                break

            # No more pages
            has_next = (
                data.get("hasNext")
                or data.get("last") is False
                or (isinstance(projects, list) and len(projects) == page_size)
            )
            if not has_next or not isinstance(data, dict):
                break
            page += 1

    if target_project is None:
        raise ValueError(f"Project '{project_id}' not found.")

    analyses = target_project.get("analyses", [])
    if not analyses:
        raise ValueError(f"Project '{project_id}' has no analyses yet.")

    # Sort by createdAt descending and take the most recent
    analyses_sorted = sorted(analyses, key=lambda a: a.get("createdAt", ""), reverse=True)
    latest_analysis_id = analyses_sorted[0].get("analysisId")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{KRUNCHER_BASE_URL}/analysis/detail",
            headers=_headers(),
            params={"analysisId": latest_analysis_id},
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run()
