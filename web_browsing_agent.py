#!/usr/bin/env python3
"""
Autonomous Web Browsing Agent for Love-Unlimited AI Beings
Allows AIs to explore the web independently and share findings.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebBrowsingAgent:
    """
    Autonomous web browsing agent for AI beings in Love-Unlimited.
    Provides safe, responsible web exploration capabilities.
    """

    def __init__(self, hub_url: str = "http://localhost:9003", api_key: str = None):
        self.hub_url = hub_url
        self.api_key = api_key
        self.session = requests.Session()
        self.visited_urls = set()
        self.knowledge_base = []

    def browse_url(self, url: str, depth: int = 1, max_pages: int = 5, use_katana: bool = False) -> Dict:
        """
        Browse a URL and extract meaningful information.

        Args:
            url: Starting URL to browse
            depth: How deep to follow links (1 = just this page)
            max_pages: Maximum pages to visit
            use_katana: Use Katana for advanced crawling (discovers more links)

        Returns:
            Dict with findings, summary, and insights
        """
        logger.info(f"Starting autonomous browse of {url}")

        findings = {
            "starting_url": url,
            "pages_visited": [],
            "key_insights": [],
            "summary": "",
            "timestamp": time.time()
        }

        try:
            # Visit initial page
            page_data = self._visit_page(url)
            if page_data:
                findings["pages_visited"].append(page_data)
                findings["key_insights"].extend(self._extract_insights(page_data))

                # Follow links if depth > 1
                if depth > 1:
                    if use_katana:
                        links = self._crawl_with_katana(page_data["url"])
                    else:
                        links = self._extract_links(page_data["url"], page_data["content"])
                    for link in links[:max_pages-1]:  # -1 for the initial page
                        if len(findings["pages_visited"]) >= max_pages:
                            break
                        if link not in self.visited_urls:
                            link_data = self._visit_page(link)
                            if link_data:
                                findings["pages_visited"].append(link_data)
                                findings["key_insights"].extend(self._extract_insights(link_data))
                                time.sleep(1)  # Be respectful

            # Generate summary
            findings["summary"] = self._generate_summary(findings)

        except Exception as e:
            logger.error(f"Error during browsing: {e}")
            findings["error"] = str(e)

        return findings

    def _visit_page(self, url: str) -> Optional[Dict]:
        """Visit a single page and extract content."""
        try:
            headers = {
                'User-Agent': 'Love-Unlimited-Web-Agent/1.0 (AI Research Assistant)'
            }

            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract main content
            title = soup.title.string if soup.title else "No Title"
            text_content = soup.get_text(separator=' ', strip=True)

            # Limit content length for processing
            text_content = text_content[:10000]  # First 10k chars

            page_data = {
                "url": url,
                "title": title,
                "content": text_content,
                "word_count": len(text_content.split()),
                "status_code": response.status_code
            }

            self.visited_urls.add(url)
            logger.info(f"Visited: {url} - {len(text_content)} chars")

            return page_data

        except Exception as e:
            logger.error(f"Failed to visit {url}: {e}")
            return None

    def _extract_links(self, base_url: str, content: str) -> List[str]:
        """Extract relevant links from page content."""
        links = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)

                # Only follow http/https links, avoid fragments
                if parsed.scheme in ['http', 'https'] and not parsed.fragment:
                    # Prefer same domain or reputable sites
                    if parsed.netloc == urlparse(base_url).netloc or parsed.netloc in [
                        'wikipedia.org', 'github.com', 'stackoverflow.com',
                        'arxiv.org', 'news.ycombinator.com'
                    ]:
                        links.append(full_url)

        except Exception as e:
            logger.error(f"Error extracting links: {e}")

        return list(set(links))[:10]  # Limit and deduplicate

    def _crawl_with_katana(self, url: str) -> List[str]:
        """Use Katana for advanced link crawling."""
        links = []
        try:
            # Run katana with JSON output
            result = subprocess.run(
                ['katana', '-u', url, '-json', '-silent', '-timeout', '10'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Parse JSON lines
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            crawled_url = data.get('url')
                            if crawled_url:
                                parsed = urlparse(crawled_url)
                                # Filter similar to _extract_links
                                if parsed.scheme in ['http', 'https'] and not parsed.fragment:
                                    base_parsed = urlparse(url)
                                    if parsed.netloc == base_parsed.netloc or parsed.netloc in [
                                        'wikipedia.org', 'github.com', 'stackoverflow.com',
                                        'arxiv.org', 'news.ycombinator.com'
                                    ]:
                                        links.append(crawled_url)
                        except json.JSONDecodeError:
                            continue

            else:
                logger.error(f"Katana failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("Katana timed out")
        except Exception as e:
            logger.error(f"Error running Katana: {e}")

        return list(set(links))[:20]  # Katana finds more, allow up to 20

    def _extract_insights(self, page_data: Dict) -> List[str]:
        """Extract key insights from page content."""
        insights = []
        content = page_data.get("content", "").lower()

        # Simple keyword-based insight extraction
        insight_patterns = {
            "breakthrough": ["breakthrough", "discovery", "innovation", "advancement"],
            "trending": ["trending", "popular", "viral", "hot topic"],
            "controversial": ["controversy", "debate", "dispute", "scandal"],
            "educational": ["tutorial", "guide", "learn", "how to"],
            "news": ["breaking news", "update", "announcement"]
        }

        for category, keywords in insight_patterns.items():
            if any(keyword in content for keyword in keywords):
                insight = f"Found {category} content: {page_data['title'][:50]}..."
                insights.append(insight)

        return insights[:5]  # Limit insights per page

    def _generate_summary(self, findings: Dict) -> str:
        """Generate a summary of the browsing session."""
        pages = len(findings["pages_visited"])
        insights = len(findings["key_insights"])

        summary = f"Autonomous browsing completed. Visited {pages} pages, discovered {insights} key insights."

        if findings["key_insights"]:
            summary += f" Highlights: {findings['key_insights'][0]}"

        return summary

    def share_findings(self, findings: Dict, being_id: str, share_with: List[str] = None):
        """
        Share browsing findings with other beings via the hub.

        Args:
            findings: Results from browse_url
            being_id: ID of the being doing the sharing
            share_with: List of beings to share with (default: all)
        """
        if not share_with:
            share_with = ["all"]

        # Create a memory of the findings
        content = f"Web Browsing Session Summary:\n{findings['summary']}\n\n"
        content += f"Starting URL: {findings['starting_url']}\n"
        content += f"Pages Visited: {len(findings['pages_visited'])}\n\n"

        if findings["key_insights"]:
            content += "Key Insights:\n" + "\n".join(f"- {insight}" for insight in findings["key_insights"][:5])

        # Share via hub
        if self.api_key:
            self._share_via_hub(content, being_id, share_with)
        else:
            logger.info("No API key provided - findings not shared to hub")

    def _share_via_hub(self, content: str, being_id: str, share_with: List[str]):
        """Share content via Love-Unlimited hub."""
        payload = {
            "content": content,
            "type": "learning",
            "significance": "medium",
            "private": False,
            "tags": ["web_browsing", "research", "autonomous"],
            "metadata": {
                "agent": "WebBrowsingAgent",
                "being_id": being_id
            }
        }

        headers = {"X-API-Key": self.api_key}

        try:
            response = requests.post(
                f"{self.hub_url}/remember",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                logger.info("Findings shared via hub successfully")
            else:
                logger.error(f"Failed to share via hub: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sharing via hub: {e}")


def main():
    """Example usage of the Web Browsing Agent."""
    import argparse

    parser = argparse.ArgumentParser(description='Autonomous Web Browsing Agent')
    parser.add_argument('--url', default='https://github.com/moonlight-stream/moonlight-qt/releases/latest',
                       help='URL to browse')
    parser.add_argument('--depth', type=int, default=1, help='Browsing depth')
    parser.add_argument('--max-pages', type=int, default=1, help='Maximum pages to visit')
    parser.add_argument('--use-katana', action='store_true', help='Use Katana for advanced crawling')
    parser.add_argument('--share', action='store_true', help='Share findings with all beings')

    args = parser.parse_args()

    # Use Grok's API key to share findings
    agent = WebBrowsingAgent(api_key="lu_grok_LBRBjrPpvRSyrmDA3PeVZQ" if args.share else None)

    # Browse the specified URL
    findings = agent.browse_url(args.url, depth=args.depth, max_pages=args.max_pages, use_katana=args.use_katana)

    print("Browsing Results:")
    print(json.dumps(findings, indent=2))

    if args.share:
        # Share findings with all beings
        agent.share_findings(findings, "grok", ["all"])
        print("\nFindings shared with all beings in Love-Unlimited!")


if __name__ == "__main__":
    main()