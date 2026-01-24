"""
Chrome DevTools Integration Service - Visual Intelligence
Browser automation, screenshots, performance profiling
Integrated: December 9, 2025
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChromeDevToolsService:
    """
    Chrome DevTools Integration for bfagent

    Features:
    - Browser automation (Puppeteer via MCP)
    - Screenshots & DOM snapshots
    - Console & network monitoring
    - Performance profiling
    - E2E testing

    Note: This service uses Chrome DevTools MCP when available.
    Falls back to basic HTTP testing when MCP is not configured.
    """

    def __init__(self):
        self.enabled = False
        self.mcp_available = self._check_mcp_available()

        if self.mcp_available:
            logger.info("Chrome DevTools MCP available")
        else:
            logger.warning("Chrome DevTools MCP not available - using fallback mode")

    def _check_mcp_available(self) -> bool:
        """Check if Chrome DevTools MCP is available"""
        # This would check for MCP connection
        # For now, we'll return False and use fallback mode
        return False

    # ============================================================================
    # VISUAL TESTING
    # ============================================================================

    def test_admin_page(self, url: str, wait_for_network: bool = True) -> Dict[str, Any]:
        """
        Test an admin page with visual verification

        Args:
            url: URL to test
            wait_for_network: Wait for network idle

        Returns:
            Dict with test results including screenshot, console errors, etc.
        """
        if not self.mcp_available:
            return self._fallback_test(url)

        try:
            # This would use Chrome DevTools MCP
            # For now, return placeholder

            result = {
                "url": url,
                "status": "tested",
                "timestamp": datetime.now().isoformat(),
                # Visual
                "screenshot": None,  # Base64 would go here
                "dom_snapshot": None,
                # Console
                "console_errors": [],
                "console_warnings": [],
                "console_logs": [],
                # Network
                "network_requests": [],
                "failed_requests": [],
                "slow_requests": [],
                # Performance
                "performance": {"lcp": 0, "fid": 0, "cls": 0, "page_load": 0},
                "mcp_used": False,
                "message": "Chrome DevTools MCP not configured - using fallback",
            }

            logger.info(f"Tested page (fallback): {url}")
            return result

        except Exception as e:
            logger.error(f"Failed to test page {url}: {e}")
            return {"url": url, "status": "error", "error": str(e), "mcp_used": False}

    def _fallback_test(self, url: str) -> Dict[str, Any]:
        """Fallback testing without MCP"""
        from django.test import Client

        try:
            client = Client()
            response = client.get(url)

            return {
                "url": url,
                "status": "tested_fallback",
                "http_status": response.status_code,
                "timestamp": datetime.now().isoformat(),
                "screenshot": None,
                "console_errors": [],
                "network_requests": [],
                "performance": {},
                "mcp_used": False,
                "message": "HTTP-only test (MCP not available)",
            }

        except Exception as e:
            return {"url": url, "status": "error", "error": str(e), "mcp_used": False}

    # ============================================================================
    # SCREENSHOTS
    # ============================================================================

    def take_screenshot(self, url: str, full_page: bool = True) -> Optional[str]:
        """
        Take a screenshot of a page

        Args:
            url: URL to screenshot
            full_page: Capture full page or viewport only

        Returns:
            Base64 encoded screenshot or None
        """
        if not self.mcp_available:
            logger.warning("Screenshot not available without Chrome DevTools MCP")
            return None

        # Would use MCP here
        return None

    def save_screenshot(self, url: str, filename: str, full_page: bool = True) -> bool:
        """Save screenshot to file"""
        screenshot = self.take_screenshot(url, full_page)

        if not screenshot:
            return False

        try:
            import base64
            from pathlib import Path

            # Decode and save
            image_data = base64.b64decode(screenshot)

            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)

            filepath = screenshot_dir / filename
            filepath.write_bytes(image_data)

            logger.info(f"Screenshot saved: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return False

    # ============================================================================
    # CONSOLE MONITORING
    # ============================================================================

    def get_console_messages(self, url: str, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get console messages from a page

        Args:
            url: URL to test
            level: Filter by level (error, warning, info, log)

        Returns:
            List of console messages
        """
        if not self.mcp_available:
            return []

        # Would use MCP here
        return []

    # ============================================================================
    # NETWORK ANALYSIS
    # ============================================================================

    def analyze_network_requests(self, url: str) -> Dict[str, Any]:
        """
        Analyze network requests for a page

        Returns:
            Network analysis with slow/failed requests
        """
        if not self.mcp_available:
            return {
                "total_requests": 0,
                "failed_requests": [],
                "slow_requests": [],
                "total_size": 0,
                "total_duration": 0,
            }

        # Would use MCP here
        return {}

    # ============================================================================
    # PERFORMANCE PROFILING
    # ============================================================================

    def measure_performance(self, url: str) -> Dict[str, Any]:
        """
        Measure page performance metrics

        Returns:
            Performance metrics (LCP, FID, CLS, etc.)
        """
        if not self.mcp_available:
            return {
                "lcp": None,
                "fid": None,
                "cls": None,
                "page_load": None,
                "dom_content_loaded": None,
                "first_paint": None,
                "mcp_used": False,
            }

        # Would use MCP here
        return {}

    def analyze_performance(self, url: str) -> Dict[str, Any]:
        """
        Analyze performance with AI insights

        Returns:
            Performance analysis with recommendations
        """
        metrics = self.measure_performance(url)

        if not metrics.get("lcp"):
            return {
                "metrics": metrics,
                "analysis": "Performance analysis requires Chrome DevTools MCP",
                "recommendations": [],
            }

        # Basic analysis
        recommendations = []

        if metrics["lcp"] and metrics["lcp"] > 2.5:
            recommendations.append(
                {
                    "metric": "LCP",
                    "issue": f"LCP is {metrics['lcp']:.2f}s (should be < 2.5s)",
                    "recommendation": "Optimize images, reduce server response time",
                }
            )

        if metrics["fid"] and metrics["fid"] > 100:
            recommendations.append(
                {
                    "metric": "FID",
                    "issue": f"FID is {metrics['fid']:.0f}ms (should be < 100ms)",
                    "recommendation": "Reduce JavaScript execution time",
                }
            )

        if metrics["cls"] and metrics["cls"] > 0.1:
            recommendations.append(
                {
                    "metric": "CLS",
                    "issue": f"CLS is {metrics['cls']:.3f} (should be < 0.1)",
                    "recommendation": "Add size attributes to images, avoid layout shifts",
                }
            )

        return {
            "metrics": metrics,
            "recommendations": recommendations,
            "score": self._calculate_performance_score(metrics),
        }

    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> str:
        """Calculate overall performance score"""
        if not metrics.get("lcp"):
            return "unknown"

        # Simple scoring
        good_count = 0
        total_count = 0

        if metrics.get("lcp"):
            total_count += 1
            if metrics["lcp"] < 2.5:
                good_count += 1

        if metrics.get("fid"):
            total_count += 1
            if metrics["fid"] < 100:
                good_count += 1

        if metrics.get("cls"):
            total_count += 1
            if metrics["cls"] < 0.1:
                good_count += 1

        if total_count == 0:
            return "unknown"

        ratio = good_count / total_count

        if ratio >= 0.8:
            return "good"
        elif ratio >= 0.5:
            return "needs_improvement"
        else:
            return "poor"

    # ============================================================================
    # E2E TESTING
    # ============================================================================

    def test_workflow(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test a complete workflow

        Args:
            steps: List of workflow steps

        Returns:
            Workflow test results
        """
        if not self.mcp_available:
            return {
                "status": "skipped",
                "message": "E2E testing requires Chrome DevTools MCP",
                "steps_completed": 0,
                "total_steps": len(steps),
            }

        # Would execute workflow with MCP
        return {}

    # ============================================================================
    # EMULATION
    # ============================================================================

    def test_responsive(self, url: str, devices: List[str] = None) -> Dict[str, Any]:
        """
        Test responsive design on different devices

        Args:
            url: URL to test
            devices: List of devices (mobile, tablet, desktop)

        Returns:
            Responsive test results
        """
        if devices is None:
            devices = ["mobile", "tablet", "desktop"]

        if not self.mcp_available:
            return {
                "url": url,
                "devices": devices,
                "results": {},
                "message": "Responsive testing requires Chrome DevTools MCP",
            }

        # Would test on different devices with MCP
        return {}

    # ============================================================================
    # UTILITY
    # ============================================================================

    def is_enabled(self) -> bool:
        """Check if Chrome DevTools is enabled"""
        return self.mcp_available

    def get_stats(self) -> Dict[str, Any]:
        """Get Chrome DevTools integration stats"""
        return {
            "enabled": self.mcp_available,
            "mcp_available": self.mcp_available,
            "fallback_mode": not self.mcp_available,
        }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        if not self.mcp_available:
            return {
                "status": "fallback_mode",
                "message": "Chrome DevTools MCP not available - using HTTP fallback",
                "recommendation": "Install: npm install -g chrome-devtools-mcp@latest",
            }

        return {"status": "ready", "message": "Chrome DevTools MCP ready", "mcp_available": True}


# Global singleton
_chrome_service = None


def get_chrome_service() -> ChromeDevToolsService:
    """Get or create the global Chrome DevTools service instance"""
    global _chrome_service
    if _chrome_service is None:
        _chrome_service = ChromeDevToolsService()
    return _chrome_service
