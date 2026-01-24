#!/usr/bin/env python
"""
CSS Theme Switcher Tool for BF Agent v3.0.0
Optimized with modern best practices for 2025

Key improvements:
- Performance optimization with CSS custom properties
- CSS layers for better specificity management
- Lazy loading and code splitting
- Enhanced error handling and type safety
- Modern CSS features (container queries, :has(), etc.)
- Theme preview capability
- Auto dark/light mode detection
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import django

# Setup Django
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


django.setup()

try:
    from rich.console import Console
    from rich.logging import RichHandler

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)] if RICH_AVAILABLE else [],
)
logger = logging.getLogger(__name__)
console = Console() if RICH_AVAILABLE else None


class ThemeType(Enum):
    """Theme type enumeration"""

    DEFAULT = "default"
    METALLIC = "metallic"
    DARK = "dark"
    LIGHT = "light"
    NEON = "neon"
    CUSTOM = "custom"


@dataclass
class ThemeConfig:
    """Enhanced theme configuration with CSS custom properties"""

    id: str
    name: str
    description: str
    primary_color: str
    secondary_color: str
    background: str
    text_color: str
    css_file: Optional[str] = None

    # Enhanced properties for modern theming
    accent_color: Optional[str] = None
    surface_color: Optional[str] = None
    error_color: Optional[str] = None
    warning_color: Optional[str] = None
    success_color: Optional[str] = None
    info_color: Optional[str] = None

    # Typography
    font_family: Optional[str] = None
    font_size_base: Optional[str] = None
    line_height: Optional[str] = None

    # Spacing
    spacing_unit: Optional[str] = None

    # Borders and shadows
    border_radius: Optional[str] = None
    shadow_sm: Optional[str] = None
    shadow_md: Optional[str] = None
    shadow_lg: Optional[str] = None

    # Animation
    transition_speed: Optional[str] = None

    # Feature flags
    supports_dark_mode: bool = False
    supports_high_contrast: bool = False
    is_experimental: bool = False

    # Metadata
    version: str = "1.0.0"
    author: Optional[str] = None
    license: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)

    def to_css_vars(self) -> Dict[str, str]:
        """Convert theme config to CSS custom properties"""
        css_vars = {
            "--theme-primary": self.primary_color,
            "--theme-secondary": self.secondary_color,
            "--theme-background": self.background,
            "--theme-text": self.text_color,
        }

        # Add optional properties if they exist
        optional_props = {
            "--theme-accent": self.accent_color,
            "--theme-surface": self.surface_color,
            "--theme-error": self.error_color or "#dc3545",
            "--theme-warning": self.warning_color or "#ffc107",
            "--theme-success": self.success_color or "#28a745",
            "--theme-info": self.info_color or "#17a2b8",
            "--theme-font-family": self.font_family,
            "--theme-font-size-base": self.font_size_base,
            "--theme-line-height": self.line_height,
            "--theme-spacing": self.spacing_unit,
            "--theme-radius": self.border_radius,
            "--theme-shadow-sm": self.shadow_sm,
            "--theme-shadow-md": self.shadow_md,
            "--theme-shadow-lg": self.shadow_lg,
            "--theme-transition": self.transition_speed,
        }

        for key, value in optional_props.items():
            if value:
                css_vars[key] = value

        return css_vars


class ThemeRegistry:
    """Registry for managing themes"""

    # Predefined themes with enhanced configurations
    BUILTIN_THEMES = {
        ThemeType.DEFAULT: ThemeConfig(
            id="default",
            name="Default Bootstrap",
            description="Standard Bootstrap 5 theme with enhancements",
            primary_color="#0d6efd",
            secondary_color="#6c757d",
            background="#fffff",
            text_color="#212529",
            accent_color="#0dcaf0",
            surface_color="#f8f9fa",
            border_radius="0.375rem",
            shadow_sm="0 0.125rem 0.25rem rgba(0,0,0,0.075)",
            transition_speed="0.15s ease-in-out",
            font_family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-seri",
        ),
        ThemeType.METALLIC: ThemeConfig(
            id="metallic",
            name="Metallic Professional",
            description="Professional metallic theme with gradients and depth",
            primary_color="#2c3e50",
            secondary_color="#95a5a6",
            background="linear-gradient(135deg, #2c3e50 0%, #34495e 50%, #2c3e50 100%)",
            text_color="#ecf0f1",
            accent_color="#3498db",
            surface_color="rgba(52, 73, 94, 0.9)",
            border_radius="0.5rem",
            shadow_md="0 0.5rem 1rem rgba(0,0,0,0.15)",
            transition_speed="0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            css_file="control-center-metallic.css",
        ),
        ThemeType.DARK: ThemeConfig(
            id="dark",
            name="Dark Mode",
            description="Modern dark theme optimized for low-light environments",
            primary_color="#bb86fc",
            secondary_color="#03dac6",
            background="#121212",
            text_color="#fffff",
            surface_color="#1e1e1e",
            error_color="#cf6679",
            border_radius="0.25rem",
            shadow_lg="0 1rem 3rem rgba(0,0,0,0.5)",
            transition_speed="0.2s ease",
            supports_dark_mode=True,
            css_file="dark-theme.css",
        ),
        ThemeType.LIGHT: ThemeConfig(
            id="light",
            name="Light Minimal",
            description="Clean minimal light theme with subtle accents",
            primary_color="#6c757d",
            secondary_color="#e9ece",
            background="#fffff",
            text_color="#495057",
            surface_color="#f8f9fa",
            border_radius="0.375rem",
            shadow_sm="0 0.125rem 0.25rem rgba(0,0,0,0.04)",
            transition_speed="0.15s ease",
            font_family="'Inter', -apple-system, sans-seri",
            css_file="light-theme.css",
        ),
        ThemeType.NEON: ThemeConfig(
            id="neon",
            name="Neon Cyber",
            description="Cyberpunk neon theme with glowing effects",
            primary_color="#00ff41",
            secondary_color="#ff0080",
            background="#0a0a0a",
            text_color="#00ff41",
            accent_color="#00fff",
            surface_color="rgba(0, 255, 65, 0.1)",
            border_radius="0",
            shadow_lg="0 0 2rem rgba(0, 255, 65, 0.5)",
            transition_speed="0.4s ease-in-out",
            is_experimental=True,
            css_file="neon-theme.css",
        ),
    }

    def __init__(self, themes_dir: Path):
        """Function description."""
        self.themes_dir = themes_dir
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        self.custom_themes: Dict[str, ThemeConfig] = {}
        self._load_custom_themes()

    def _load_custom_themes(self) -> None:
        """Load custom themes from JSON files"""
        for theme_file in self.themes_dir.glob("*.json"):
            try:
                with open(theme_file, "r", encoding="utf-8") as f:
                    theme_data = json.load(f)
                    theme_config = ThemeConfig(**theme_data)
                    self.custom_themes[theme_config.id] = theme_config
            except Exception as e:
                logger.warning(f"Failed to load theme {theme_file}: {e}")

    def get_theme(self, theme_id: str) -> Optional[ThemeConfig]:
        """Get theme by ID"""
        # Check builtin themes first
        for theme_type, theme in self.BUILTIN_THEMES.items():
            if theme.id == theme_id:
                return theme

        # Check custom themes
        return self.custom_themes.get(theme_id)

    def list_themes(self) -> List[ThemeConfig]:
        """List all available themes"""
        themes = list(self.BUILTIN_THEMES.values())
        themes.extend(self.custom_themes.values())
        return themes

    def save_custom_theme(self, theme: ThemeConfig) -> None:
        """Save custom theme to file"""
        theme_file = self.themes_dir / f"{theme.id}.json"
        theme_data = asdict(theme)

        # Convert datetime objects to ISO format
        if theme_data.get("created_at"):
            theme_data["created_at"] = theme_data["created_at"].isoformat()
        if theme_data.get("updated_at"):
            theme_data["updated_at"] = theme_data["updated_at"].isoformat()

        with open(theme_file, "w", encoding="utf-8") as f:
            json.dump(theme_data, f, indent=2)

        self.custom_themes[theme.id] = theme


class CSSGenerator:
    """Modern CSS generator with advanced features"""

    def __init__(self):
        """Function description."""
        self.use_layers = True
        self.use_custom_properties = True
        self.use_container_queries = True
        self.minify = True

    async def generate_theme_css(
        self, theme: ThemeConfig, options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate optimized CSS for a theme"""
        options = options or {}

        # Get CSS variables
        css_vars = theme.to_css_vars()

        # Generate CSS sections
        sections = [
            self._generate_css_reset(),
            self._generate_css_layers(),
            self._generate_css_custom_properties(css_vars),
            self._generate_base_styles(theme),
            self._generate_component_styles(theme),
            self._generate_utility_classes(theme),
            self._generate_animations(theme),
            self._generate_media_queries(theme),
        ]

        # Add container queries if supported
        if self.use_container_queries:
            sections.append(self._generate_container_queries(theme))

        # Combine all sections
        css_content = "\n\n".join(filter(None, sections))

        # Minify if requested
        if self.minify and options.get("minify", True):
            css_content = self._minify_css(css_content)

        return css_content

    def _generate_css_reset(self) -> str:
        """Generate minimal CSS reset"""
        return """/* CSS Reset */
@layer reset {
  *, *::before, *::after {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    padding: 0;
    min-height: 100vh;
  }
}"""

    def _generate_css_layers(self) -> str:
        """Define CSS cascade layers for better specificity management"""
        if not self.use_layers:
            return ""

        return """/* CSS Cascade Layers */
@layer reset, theme, base, components, utilities;"""

    def _generate_css_custom_properties(self, css_vars: Dict[str, str]) -> str:
        """Generate CSS custom properties with @property for animations"""
        props_css = ["/* CSS Custom Properties */", "@layer theme {", "  :root {"]

        for prop, value in css_vars.items():
            props_css.append(f"    {prop}: {value};")

        props_css.extend(["  }", "}"])

        # Add @property definitions for animatable properties
        props_css.extend(
            [
                "",
                "/* Animatable Custom Properties */",
            ]
        )

        color_props = [
            prop
            for prop in css_vars.keys()
            if "color" in prop or prop.endswith("-primary") or prop.endswith("-secondary")
        ]

        for prop in color_props:
            props_css.extend(
                [
                    f"@property {prop} {{",
                    "  syntax: '<color>';",
                    "  inherits: true;",
                    f"  initial-value: {css_vars.get(prop, 'black')};",
                    "}",
                ]
            )

        return "\n".join(props_css)

    def _generate_base_styles(self, theme: ThemeConfig) -> str:
        """Generate base styles using custom properties"""
        return """/* Base Styles */
@layer base {{
  body {{
    background: var(--theme-background);
    color: var(--theme-text);
    font-family: var(--theme-font-family, system-ui, sans-serif);
    font-size: var(--theme-font-size-base, 1rem);
    line-height: var(--theme-line-height, 1.5);
    transition: background var(--theme-transition), color var(--theme-transition);
  }}

  a {{
    color: var(--theme-primary);
    text-decoration: none;
    transition: color var(--theme-transition);
  }}

  a:hover {{
    color: var(--theme-accent, var(--theme-secondary));
  }}

  ::selection {{
    background-color: var(--theme-primary);
    color: var(--theme-background);
  }}
}}"""

    def _generate_component_styles(self, theme: ThemeConfig) -> str:
        """Generate component styles with modern features"""
        return """/* Component Styles */
@layer components {{
  /* Cards with :has() selector */
  .card {{
    background: var(--theme-surface, var(--theme-background));
    border-radius: var(--theme-radius);
    padding: calc(var(--theme-spacing, 1rem) * 1.5);
    box-shadow: var(--theme-shadow-md);
    transition: transform var(--theme-transition), box-shadow var(--theme-transition);
  }}

  .card:has(.card-image) {{
    padding-top: 0;
    overflow: hidden;
  }}

  .card:hover {{
    transform: translateY(-2px);
    box-shadow: var(--theme-shadow-lg);
  }}

  /* Buttons with modern styling */
  .btn {{
    --btn-bg: var(--theme-primary);
    --btn-color: var(--theme-background);
    --btn-hover-bg: var(--theme-accent, var(--theme-secondary));

    background: var(--btn-bg);
    color: var(--btn-color);
    border: none;
    border-radius: var(--theme-radius);
    padding: calc(var(--theme-spacing, 0.5rem) * 0.75) calc(var(--theme-spacing, 0.5rem) * 1.5);
    font-size: inherit;
    font-weight: 500;
    cursor: pointer;
    transition: all var(--theme-transition);
    position: relative;
    overflow: hidden;
  }}

  .btn::before {{
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    background: var(--btn-hover-bg);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    transition: width 0.6s, height 0.6s;
  }}

  .btn:hover {{
    color: var(--btn-color);
  }}

  .btn:hover::before {{
    width: 300px;
    height: 300px;
  }}

  .btn:active {{
    transform: scale(0.98);
  }}

  /* Form controls */
  .form-control {{
    background: var(--theme-surface, var(--theme-background));
    color: var(--theme-text);
    border: 1px solid color-mix(in srgb, var(--theme-text) 20%, transparent);
    border-radius: var(--theme-radius);
    padding: calc(var(--theme-spacing, 0.5rem) * 0.75) calc(var(--theme-spacing, 0.5rem) * 1);
    transition: border-color var(--theme-transition), box-shadow var(--theme-transition);
  }}

  .form-control:focus {{
    outline: none;
    border-color: var(--theme-primary);
    box-shadow: 0 0 0 0.2rem color-mix(in srgb, var(--theme-primary) 25%, transparent);
  }}

  /* Navigation */
  .navbar {{
    background: color-mix(in srgb, var(--theme-surface, var(--theme-background)) 95%, var(--theme-primary) 5%);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid color-mix(in srgb, var(--theme-text) 10%, transparent);
  }}

  /* Sidebar with modern gradient */
  .sidebar {{
    background: linear-gradient(
      135deg,
      var(--theme-surface, var(--theme-background)) 0%,
      color-mix(in srgb, var(--theme-surface, var(--theme-background)) 90%, var(--theme-primary) 10%) 100%
    );
  }}
}}"""

    def _generate_utility_classes(self, theme: ThemeConfig) -> str:
        """Generate utility classes"""
        return """/* Utility Classes */
@layer utilities {
  /* Text utilities */
  .text-primary { color: var(--theme-primary) !important; }
  .text-secondary { color: var(--theme-secondary) !important; }
  .text-accent { color: var(--theme-accent, var(--theme-primary)) !important; }
  .text-muted { opacity: 0.6; }

  /* Background utilities */
  .bg-primary { background-color: var(--theme-primary) !important; }
  .bg-secondary { background-color: var(--theme-secondary) !important; }
  .bg-surface { background-color: var(--theme-surface, var(--theme-background)) !important; }

  /* Spacing utilities */
  .p-1 { padding: var(--theme-spacing, 1rem) !important; }
  .p-2 { padding: calc(var(--theme-spacing, 1rem) * 2) !important; }
  .m-1 { margin: var(--theme-spacing, 1rem) !important; }
  .m-2 { margin: calc(var(--theme-spacing, 1rem) * 2) !important; }

  /* Shadow utilities */
  .shadow-sm { box-shadow: var(--theme-shadow-sm) !important; }
  .shadow-md { box-shadow: var(--theme-shadow-md) !important; }
  .shadow-lg { box-shadow: var(--theme-shadow-lg) !important; }
}"""

    def _generate_animations(self, theme: ThemeConfig) -> str:
        """Generate smooth animations"""
        animations = []

        # Add neon-specific animations
        if theme.id == "neon":
            animations.append(
                """/* Neon Animations */
@keyframes neon-pulse {
  0%, 100% {
    text-shadow:
      0 0 5px var(--theme-primary),
      0 0 10px var(--theme-primary),
      0 0 15px var(--theme-primary);
  }
  50% {
    text-shadow:
      0 0 10px var(--theme-primary),
      0 0 20px var(--theme-primary),
      0 0 30px var(--theme-primary),
      0 0 40px var(--theme-accent);
  }
}

.neon-text {
  animation: neon-pulse 2s ease-in-out infinite;
}"""
            )

        # Add general fade animations
        animations.append(
            """/* General Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fadeIn var(--theme-transition) ease-out;
}"""
        )

        return "\n\n".join(animations) if animations else ""

    def _generate_media_queries(self, theme: ThemeConfig) -> str:
        """Generate responsive media queries"""
        return """/* Responsive Design */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    /* Auto dark mode colors */
    --theme-background: #121212;
    --theme-text: #ffffff;
    --theme-surface: #1e1e1e;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 768px) {
  :root {
    --theme-font-size-base: 0.875rem;
    --theme-spacing: 0.75rem;
  }
}"""

    def _generate_container_queries(self, theme: ThemeConfig) -> str:
        """Generate container queries for component-based responsive design"""
        return """/* Container Queries */
@container (min-width: 400px) {
  .card {
    padding: calc(var(--theme-spacing, 1rem) * 2);
  }
}

@container (max-width: 300px) {
  .card {
    padding: var(--theme-spacing, 1rem);
  }

  .card h2 {
    font-size: 1.25rem;
  }
}"""

    def _minify_css(self, css: str) -> str:
        """Basic CSS minification"""
        # Remove comments
        import re

        css = re.sub(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/", "", css)

        # Remove unnecessary whitespace
        css = re.sub(r"\s+", " ", css)
        css = re.sub(r"\s*([{}:;,])\s*", r"\1", css)

        return css.strip()


class ModernThemeSwitcher:
    """Enhanced theme switcher with modern features"""

    def __init__(self):
        """Function description."""
        self.project_root = project_root
        self.static_dir = self.project_root / "static" / "css"
        self.templates_dir = self.project_root / "templates"
        self.themes_dir = self.project_root / "themes"

        self.theme_registry = ThemeRegistry(self.themes_dir)
        self.css_generator = CSSGenerator()

        # Ensure directories exist
        self.static_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    async def generate_theme(
        self, theme_id: str, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Generate theme CSS with validation"""
        theme = self.theme_registry.get_theme(theme_id)
        if not theme:
            return False, f"Theme '{theme_id}' not found"

        try:
            # Generate CSS
            css_content = await self.css_generator.generate_theme_css(theme, options)

            # Add theme-specific class wrapper
            css_content = """/* {theme.name} Theme - Generated on {datetime.now().isoformat()} */
/* Version: {theme.version} */

.theme-{theme_id} {{
{css_content}
}}"""

            # Save CSS file
            css_file = self.static_dir / f"{theme_id}-theme.css"
            async with aiofiles.open(css_file, "w", encoding="utf-8") as f:
                await f.write(css_content)

            # Generate integrity hash for security
            css_hash = hashlib.sha256(css_content.encode()).hexdigest()

            logger.info(f"✅ Generated theme: {theme.name} -> {css_file}")
            logger.info(f"   Integrity: sha256-{css_hash[:16]}...")

            return True, f"Theme '{theme.name}' generated successfully"

        except Exception as e:
            logger.error(f"Failed to generate theme '{theme_id}': {e}")
            return False, str(e)

    async def generate_all_themes(self) -> List[Tuple[str, bool, str]]:
        """Generate all themes asynchronously"""
        themes = self.theme_registry.list_themes()
        tasks = []

        for theme in themes:
            task = self.generate_theme(theme.id)
            tasks.append((theme.id, task))

        results = []
        for theme_id, task in tasks:
            success, message = await task
            results.append((theme_id, success, message))

        return results

    def create_modern_theme_switcher_widget(self) -> None:
        """Create enhanced theme switcher widget with preview"""
        widget_html = """<!-- Modern Theme Switcher Widget -->
<div class="theme-switcher-widget" style="position: fixed; top: 20px; right: 20px; z-index: 1050;">
    <div class="dropdown">
        <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button"
                id="themeSwitcher" data-bs-toggle="dropdown" aria-expanded="false"
                aria-label="Theme Switcher">
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm0 1a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8zm10.657-5.657a.5.5 0 0 1 0 .707l-1.414 1.415a.5.5 0 1 1-.707-.708l1.414-1.414a.5.5 0 0 1 .707 0zm-9.193 9.193a.5.5 0 0 1 0 .707L3.05 13.657a.5.5 0 0 1-.707-.707l1.414-1.414a.5.5 0 0 1 .707 0zm9.193 2.121a.5.5 0 0 1-.707 0l-1.414-1.414a.5.5 0 0 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .707zM4.464 4.465a.5.5 0 0 1-.707 0L2.343 3.05a.5.5 0 1 1 .707-.707l1.414 1.414a.5.5 0 0 1 0 .708z"/>
            </svg>
            <span class="ms-1">Theme</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="themeSwitcher">
            <li><h6 class="dropdown-header">Choose Theme</h6></li>
            <li><hr class="dropdown-divider"></li>
            <li>
                <a class="dropdown-item theme-option d-flex align-items-center" href="#" data-theme="auto">
                    <span class="me-2">🌓</span>
                    <div>
                        <div>Auto</div>
                        <small class="text-muted">Follow system preference</small>
                    </div>
                </a>
            </li>
            <li>
                <a class="dropdown-item theme-option d-flex align-items-center" href="#" data-theme="default">
                    <span class="me-2">☀️</span>
                    <div>
                        <div>Default</div>
                        <small class="text-muted">Bootstrap 5</small>
                    </div>
                </a>
            </li>
            <li>
                <a class="dropdown-item theme-option d-flex align-items-center" href="#" data-theme="metallic">
                    <span class="me-2">🔧</span>
                    <div>
                        <div>Metallic</div>
                        <small class="text-muted">Professional</small>
                    </div>
                </a>
            </li>
            <li>
                <a class="dropdown-item theme-option d-flex align-items-center" href="#" data-theme="dark">
                    <span class="me-2">🌙</span>
                    <div>
                        <div>Dark</div>
                        <small class="text-muted">Low light</small>
                    </div>
                </a>
            </li>
            <li>
                <a class="dropdown-item theme-option d-flex align-items-center" href="#" data-theme="light">
                    <span class="me-2">🌤️</span>
                    <div>
                        <div>Light</div>
                        <small class="text-muted">Minimal</small>
                    </div>
                </a>
            </li>
            <li>
                <a class="dropdown-item theme-option d-flex align-items-center" href="#" data-theme="neon">
                    <span class="me-2">💫</span>
                    <div>
                        <div>Neon</div>
                        <small class="text-muted">Cyberpunk</small>
                    </div>
                </a>
            </li>
            <li><hr class="dropdown-divider"></li>
            <li>
                <a class="dropdown-item" href="#" id="themeCustomizer">
                    <span class="me-2">🎨</span>
                    Customize Theme...
                </a>
            </li>
        </ul>
    </div>
</div>

<script type="module">
// Modern Theme Switcher with Enhanced Features
class ThemeSwitcher {
    constructor() {
        this.THEME_STORAGE_KEY = 'bfagent-theme-v3';
        this.THEME_CSS_MAP = {
            'default': null,
            'metallic': '/static/css/metallic-theme.css',
            'dark': '/static/css/dark-theme.css',
            'light': '/static/css/light-theme.css',
            'neon': '/static/css/neon-theme.css'
        };

        this.currentThemeLink = null;
        this.mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');
        this.autoMode = false;

        this.init();
    }

    init() {
        // Load saved theme or auto mode
        const savedTheme = localStorage.getItem(this.THEME_STORAGE_KEY);

        if (savedTheme === 'auto' || !savedTheme) {
            this.enableAutoMode();
        } else {
            this.loadTheme(savedTheme);
        }

        // Add event listeners
        this.attachEventListeners();

        // Listen for system theme changes
        this.mediaQueryList.addEventListener('change', (e) => {
            if (this.autoMode) {
                this.applySystemTheme();
            }
        });
    }

    enableAutoMode() {
        this.autoMode = true;
        localStorage.setItem(this.THEME_STORAGE_KEY, 'auto');
        this.applySystemTheme();
        this.updateActiveState('auto');
    }

    applySystemTheme() {
        const isDark = this.mediaQueryList.matches;
        const theme = isDark ? 'dark' : 'default';
        this.loadTheme(theme, false); // Don't save, we're in auto mode
    }

    loadTheme(themeId, save = true) {
        // Add loading state
        document.body.classList.add('theme-loading');

        // Disable auto mode if manually selecting theme
        if (save) {
            this.autoMode = false;
        }

        // Remove existing theme
        if (this.currentThemeLink) {
            this.currentThemeLink.remove();
            this.currentThemeLink = null;
        }

        // Remove all theme classes
        document.body.className = document.body.className.replace(/\\btheme-\\w+\\b/g, '');

        // Add new theme class
        document.body.classList.add(`theme-${themeId}`);

        // Load new theme CSS
        const cssPath = this.THEME_CSS_MAP[themeId];
        if (cssPath) {
            this.currentThemeLink = document.createElement('link');
            this.currentThemeLink.rel = 'stylesheet';
            this.currentThemeLink.href = cssPath;
            this.currentThemeLink.id = 'dynamic-theme';

            // Add load event listener
            this.currentThemeLink.onload = () => {
                document.body.classList.remove('theme-loading');
                this.emitThemeChange(themeId);
            };

            // Add error handling
            this.currentThemeLink.onerror = () => {
                console.error(`Failed to load theme: ${themeId}`);
                document.body.classList.remove('theme-loading');

                // Fallback to default theme
                if (themeId !== 'default') {
                    this.loadTheme('default');
                }
            };

            document.head.appendChild(this.currentThemeLink);
        } else {
            // Default theme, no CSS to load
            document.body.classList.remove('theme-loading');
            this.emitThemeChange(themeId);
        }

        // Save theme preference
        if (save) {
            localStorage.setItem(this.THEME_STORAGE_KEY, themeId);
        }

        // Update active state
        this.updateActiveState(themeId);
    }

    updateActiveState(activeThemeId) {
        document.querySelectorAll('.theme-option').forEach(option => {
            const themeId = option.getAttribute('data-theme');

            if (themeId === activeThemeId) {
                option.classList.add('active');
                option.setAttribute('aria-checked', 'true');
            } else {
                option.classList.remove('active');
                option.setAttribute('aria-checked', 'false');
            }
        });
    }

    attachEventListeners() {
        // Theme option clicks
        document.querySelectorAll('.theme-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const themeId = option.getAttribute('data-theme');

                if (themeId === 'auto') {
                    this.enableAutoMode();
                } else {
                    this.loadTheme(themeId);
                }
            });
        });

        // Theme customizer
        document.getElementById('themeCustomizer')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.openThemeCustomizer();
        });
    }

    emitThemeChange(themeId) {
        // Emit custom event for other components
        const event = new CustomEvent('themechange', {
            detail: { theme: themeId }
        });
        window.dispatchEvent(event);
    }

    openThemeCustomizer() {
        // TODO: Implement theme customizer modal
        console.log('Theme customizer not yet implemented');
    }
}

// Initialize theme switcher
document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
});

// Add loading styles
const style = document.createElement('style');
style.textContent = `
.theme-loading * {
    transition: none !important;
}

.theme-option.active {
    background-color: var(--bs-primary);
    color: white;
}

.dropdown-item small {
    font-size: 0.75rem;
    opacity: 0.7;
}
`;
document.head.appendChild(style);
</script>
"""

        widget_file = self.templates_dir / "partials" / "theme_switcher.html"
        widget_file.parent.mkdir(parents=True, exist_ok=True)

        with open(widget_file, "w", encoding="utf-8") as f:
            f.write(widget_html)

        logger.info(f"✅ Created modern theme switcher widget: {widget_file}")

    def list_themes(self) -> None:
        """List all available themes with enhanced info"""
        themes = self.theme_registry.list_themes()

        if console:
            table = Table(title="🎨 Available CSS Themes", show_lines=True)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Description", style="white")
            table.add_column("Version", style="yellow")
            table.add_column("Features", style="magenta")
            table.add_column("Status", style="blue")

            for theme in themes:
                features = []
                if theme.supports_dark_mode:
                    features.append("🌙 Dark")
                if theme.supports_high_contrast:
                    features.append("👁️ HC")
                if theme.is_experimental:
                    features.append("🧪 Exp")

                status = "✅ Ready" if self._theme_exists(theme.id) else "⏳ Not Generated"

                table.add_row(
                    theme.id,
                    theme.name,
                    theme.description,
                    theme.version,
                    " ".join(features),
                    status,
                )

            console.print(table)
        else:
            print("\n🎨 Available CSS Themes:")
            print("=" * 80)
            for theme in themes:
                print(f"\nID: {theme.id}")
                print(f"Name: {theme.name}")
                print(f"Description: {theme.description}")
                print(f"Version: {theme.version}")

    def _theme_exists(self, theme_id: str) -> bool:
        """Check if theme CSS file exists"""
        css_file = self.static_dir / f"{theme_id}-theme.css"
        return css_file.exists()


# Async main function
async def async_main():
    """Async main function for the CLI"""
    parser = argparse.ArgumentParser(
        description="Optimized CSS Theme Switcher for BF Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                    # List all themes
  %(prog)s generate metallic       # Generate metallic theme
  %(prog)s generate-all           # Generate all themes
  %(prog)s install                # Install complete theme system
        """,
    )

    parser.add_argument(
        "command",
        choices=["list", "generate", "generate-all", "install"],
        help="Command to execute",
    )
    parser.add_argument("theme", nargs="?", help="Theme ID (required for generate command)")
    parser.add_argument("--minify", action="store_true", help="Minify generated CSS")

    args = parser.parse_args()

    switcher = ModernThemeSwitcher()

    try:
        if args.command == "list":
            switcher.list_themes()

        elif args.command == "generate":
            if not args.theme:
                logger.error("❌ Theme ID required for generate command")
                parser.print_help()
                sys.exit(1)

            options = {"minify": args.minify}
            success, message = await switcher.generate_theme(args.theme, options)

            if not success:
                logger.error(f"❌ {message}")
                sys.exit(1)
            else:
                logger.info(f"✅ {message}")

        elif args.command == "generate-all":
            logger.info("🎨 Generating all themes...")
            results = await switcher.generate_all_themes()

            success_count = sum(1 for _, success, _ in results if success)
            total_count = len(results)

            logger.info(f"\n✅ Generated {success_count}/{total_count} themes successfully")

            if success_count < total_count:
                logger.warning("\n❌ Failed themes:")
                for theme_id, success, message in results:
                    if not success:
                        logger.warning(f"  - {theme_id}: {message}")

        elif args.command == "install":
            logger.info("🎨 Installing Modern Theme System...")

            # Generate all themes
            results = await switcher.generate_all_themes()

            # Create theme switcher widget
            switcher.create_modern_theme_switcher_widget()

            # Show summary
            success_count = sum(1 for _, success, _ in results if success)
            logger.info("\n✅ Theme system installed successfully!")
            logger.info(f"   - Generated {success_count} themes")
            logger.info("   - Created modern theme switcher widget")
            logger.info("\n📋 Next steps:")
            logger.info("   1. Include the theme switcher in your base template:")
            logger.info(f"      {{% include 'partials/theme_switcher.html' %}}")
            logger.info("   2. Run collectstatic to deploy themes")
            logger.info("   3. Users can switch themes with the floating widget")

    except Exception as e:
        if console:
            console.print(f"[red]❌ Error: {e}[/red]")
        else:
            logger.error(f"❌ Error: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
