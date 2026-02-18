"""Download GAO cybersecurity report PDFs for the demo corpus.

Usage:
    uv run python scripts/download_corpus.py

Downloads reports listed in CORPUS_MANIFEST to data/corpus/.
Skips files that already exist locally.

GAO.gov requires a browser session (JS challenge) to download PDFs,
so this script uses Playwright with a real browser.

Prerequisites:
    uv pip install playwright
    uv run playwright install chromium
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# GAO Cybersecurity Reports — curated for the Knowledge Base Enrichment demo
# Mix of years (2023-2025), subtopics, and agencies for a realistic corpus
CORPUS_MANIFEST: list[dict[str, str]] = [
    # 2025 reports
    {
        "id": "GAO-25-108436",
        "title": "Cybersecurity Regulations: Industry Perspectives on Harmonization",
        "url": "https://www.gao.gov/assets/gao-25-108436.pdf",
    },
    {
        "id": "GAO-25-108165",
        "title": "Department of Homeland Security: Key Areas for DHS Action",
        "url": "https://www.gao.gov/assets/gao-25-108165.pdf",
    },
    {
        "id": "GAO-25-107852",
        "title": "High-Risk Series: IT Acquisition and Management Challenges",
        "url": "https://www.gao.gov/assets/gao-25-107852.pdf",
    },
    {
        "id": "GAO-25-107649",
        "title": "IT Systems: DOD Needs to Improve Cybersecurity Planning",
        "url": "https://www.gao.gov/assets/gao-25-107649.pdf",
    },
    {
        "id": "GAO-25-107179",
        "title": "Internet of Things: Federal Actions Needed to Address Legislative Requirements",
        "url": "https://www.gao.gov/assets/gao-25-107179.pdf",
    },
    # 2024 reports
    {
        "id": "GAO-24-107231",
        "title": "High-Risk Series: Urgent Action Needed to Address Cybersecurity Challenges",
        "url": "https://www.gao.gov/assets/gao-24-107231.pdf",
    },
    {
        "id": "GAO-24-106916",
        "title": "Cybersecurity: National Cyber Director Needs Additional Actions",
        "url": "https://www.gao.gov/assets/gao-24-106916.pdf",
    },
    {
        "id": "GAO-24-106291",
        "title": "Cybersecurity: OMB Should Improve Information Security Performance Metrics",
        "url": "https://www.gao.gov/assets/gao-24-106291.pdf",
    },
    {
        "id": "GAO-24-106137",
        "title": "Cloud Computing: Agencies Need to Address Key OMB Procurement Requirements",
        "url": "https://www.gao.gov/assets/gao-24-106137.pdf",
    },
    {
        "id": "GAO-24-105658",
        "title": "Critical Infrastructure: Actions Needed to Better Secure Internet-Connected Devices",
        "url": "https://www.gao.gov/assets/gao-24-105658.pdf",
    },
    {
        "id": "GAO-24-106783",
        "title": "Next Generation 911: Federal Agencies Have Begun Planning for Call Center Upgrades",
        "url": "https://www.gao.gov/assets/gao-24-106783.pdf",
    },
    {
        "id": "GAO-24-105451",
        "title": "Bureau of Indian Education: Improved Oversight of COVID-19 Spending Needed",
        "url": "https://www.gao.gov/assets/gao-24-105451.pdf",
    },
    # 2023 reports
    {
        "id": "GAO-23-106428",
        "title": "Cybersecurity High-Risk Series: Challenges in Securing Federal Systems",
        "url": "https://www.gao.gov/assets/gao-23-106428.pdf",
    },
    {
        "id": "GAO-23-105468",
        "title": "Critical Infrastructure Protection: National Cybersecurity Strategy",
        "url": "https://www.gao.gov/assets/gao-23-105468.pdf",
    },
    {
        "id": "GAO-23-106826",
        "title": "Cybersecurity: Launching and Implementing the National Strategy",
        "url": "https://www.gao.gov/assets/gao-23-106826.pdf",
    },
    {
        "id": "GAO-23-106869",
        "title": "Cybersecurity: Interior Needs to Address Threats to Federal Systems",
        "url": "https://www.gao.gov/assets/gao-23-106869.pdf",
    },
    {
        "id": "GAO-23-106443",
        "title": "Cybersecurity High-Risk Series: Challenges in Protecting Critical Infrastructure",
        "url": "https://www.gao.gov/assets/gao-23-106443.pdf",
    },
    {
        "id": "GAO-23-106210",
        "title": "Cybersecurity High-Risk Series: Challenges in Establishing a National Strategy",
        "url": "https://www.gao.gov/assets/gao-23-106210.pdf",
    },
    {
        "id": "GAO-23-105084",
        "title": "DOD Cybersecurity: Enhanced Attention Needed to Ensure Cyber Incidents Are Reported",
        "url": "https://www.gao.gov/assets/gao-23-105084.pdf",
    },
    {
        "id": "GAO-23-106567",
        "title": "Fraud Risk Management: Key Areas for Federal Agency and Congressional Action",
        "url": "https://www.gao.gov/assets/gao-23-106567.pdf",
    },
]


async def download_corpus(output_dir: Path) -> None:
    """Download all reports using a Playwright browser session.

    GAO.gov uses JS-based bot protection that requires cookies set during
    page load. We navigate to the product page first, then use in-page
    fetch() to download the PDF with the session cookies.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Visit GAO.gov once to establish the session
        print("Initializing browser session with GAO.gov...")
        await page.goto("https://www.gao.gov/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        for report in CORPUS_MANIFEST:
            filename = f"{report['id']}.pdf"
            filepath = output_dir / filename

            if filepath.exists():
                print(f"  SKIP  {filename} (already exists)")
                skipped += 1
                continue

            print(f"  GET   {filename} — {report['title']}")
            try:
                # Navigate to the product page to get cookies/JS challenge
                product_url = f"https://www.gao.gov/products/{report['id'].lower()}"
                await page.goto(product_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                # Use in-page fetch to download the PDF (uses session cookies)
                pdf_url = report["url"]
                result = await page.evaluate(
                    """async (url) => {
                        const resp = await fetch(url);
                        if (!resp.ok) return { ok: false, status: resp.status };
                        const buf = await resp.arrayBuffer();
                        const arr = Array.from(new Uint8Array(buf));
                        return { ok: true, data: arr, size: arr.length };
                    }""",
                    pdf_url,
                )

                if result["ok"]:
                    pdf_bytes = bytes(result["data"])
                    filepath.write_bytes(pdf_bytes)
                    size_mb = len(pdf_bytes) / (1024 * 1024)
                    print(f"  OK    {filename} ({size_mb:.1f} MB)")
                    downloaded += 1
                else:
                    print(f"  FAIL  {filename} — HTTP {result['status']}")
                    failed += 1
            except Exception as e:
                print(f"  FAIL  {filename} — {e}")
                failed += 1

        await browser.close()

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    print(f"Total corpus: {len(list(output_dir.glob('*.pdf')))} PDFs in {output_dir}")


if __name__ == "__main__":
    corpus_dir = Path(__file__).parent.parent / "data" / "corpus"
    asyncio.run(download_corpus(corpus_dir))
    if any(True for _ in corpus_dir.glob("*.pdf")):
        sys.exit(0)
    else:
        print("ERROR: No PDFs downloaded!")
        sys.exit(1)
