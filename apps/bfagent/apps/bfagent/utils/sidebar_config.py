"""
Domain-Aware Sidebar Navigation Configuration

Central configuration for sidebar navigation across all domains.
Each domain gets its own navigation structure with sections and items.

Feature: #147 - Domain-Aware Sidebar Navigation
"""

SIDEBAR_NAVIGATION = {
    "bookwriting": {
        "domain_name": "Book Writing Studio",
        "domain_icon": "bi-book",
        "sections": [
            {
                "title": "WRITING & CONTENT",
                "items": [
                    {"name": "Books", "url": "bfagent:project-list", "icon": "bi-book"},
                    {"name": "Chapters", "url": "bfagent:chapter-list", "icon": "bi-file-text"},
                    {
                        "name": "Image Gallery",
                        "url": "bfagent:illustration:gallery",
                        "icon": "bi-images",
                    },
                    {"name": "Characters", "url": "bfagent:character-list", "icon": "bi-people"},
                    {
                        "name": "Plot Points",
                        "url": "bfagent:plotpoint-list",
                        "icon": "bi-diagram-3",
                    },
                    {"name": "Worlds", "url": "bfagent:world-list", "icon": "bi-globe"},
                    {"name": "Story Arcs", "url": "bfagent:storyarc-list", "icon": "bi-bezier"},
                    {"name": "Artifacts", "url": "bfagent:artifact-list", "icon": "bi-gem"},
                ],
            },
        ],
    },
    "medtrans": {
        "domain_name": "Medical Translation",
        "domain_icon": "bi-translate",
        "sections": [
            {
                "title": "TRANSLATION",
                "items": [
                    {
                        "name": "Presentations",
                        "url": "medtrans:presentation-list",
                        "icon": "bi-file-slides",
                    },
                    {"name": "Customers", "url": "medtrans:customer-list", "icon": "bi-people"},
                ],
            },
        ],
    },
    "genagent": {
        "domain_name": "GenAgent",
        "domain_icon": "bi-robot",
        "sections": [
            {
                "title": "AGENT DEVELOPMENT",
                "items": [
                    {"name": "Domains", "url": "genagent:domain-list", "icon": "bi-grid"},
                    {"name": "Actions", "url": "genagent:action-list", "icon": "bi-lightning"},
                    {"name": "Handlers", "url": "genagent:handler-list", "icon": "bi-code-square"},
                    {
                        "name": "Registry",
                        "url": "genagent:registry-dashboard",
                        "icon": "bi-database",
                    },
                ],
            },
        ],
    },
    "control_center": {
        "domain_name": "Control Center",
        "domain_icon": "bi-gear-fill",
        "sections": [
            {
                "title": "📁 DATA MANAGEMENT",
                "items": [
                    {
                        "name": "Master Data Dashboard",
                        "url": "control_center:dashboard",
                        "icon": "bi-house-gear",
                        "badge": "V2",
                        "badge_color": "primary",
                    },
                    {
                        "name": "Domain Arts",
                        "url": "control_center:dashboard",  # TODO: Dedicated URL
                        "icon": "bi-grid-3x3",
                        "badge": "Core",
                        "badge_color": "info",
                    },
                    {
                        "name": "Domain Types",
                        "url": "control_center:dashboard",  # TODO: Dedicated URL
                        "icon": "bi-diagram-2",
                        "badge": "Core",
                        "badge_color": "info",
                    },
                    {
                        "name": "Workflow Phases",
                        "url": "control_center:dashboard",  # TODO: Dedicated URL
                        "icon": "bi-arrow-right-circle",
                        "badge": "Core",
                        "badge_color": "info",
                    },
                    {
                        "name": "Genres",
                        "url": "control_center:dashboard",
                        "icon": "bi-tag",
                    },
                    {
                        "name": "Illustration Styles",
                        "url": "control_center:dashboard",
                        "icon": "bi-palette",
                    },
                    {
                        "name": "Target Audiences",
                        "url": "control_center:dashboard",
                        "icon": "bi-people",
                    },
                ],
            },
            {
                "title": "⚙️ WORKFLOW CONFIGURATION",
                "items": [
                    {
                        "name": "Workflow Dashboard",
                        "url": "control_center:dashboard",
                        "icon": "bi-speedometer2",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Project Type Phases",
                        "url": "control_center:dashboard",
                        "icon": "bi-list-check",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Phase Actions Management",
                        "url": "control_center:dashboard",
                        "icon": "bi-gear",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Legacy Workflow",
                        "url": "control_center:dashboard",
                        "icon": "bi-diagram-2",
                        "badge": "Legacy",
                        "badge_color": "secondary",
                    },
                ],
            },
            {
                "title": "🤖 AI ENGINE",
                "items": [
                    {
                        "name": "AI Agents",
                        "url": "control_center:dashboard",
                        "icon": "bi-robot",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Agent Actions",
                        "url": "control_center:dashboard",
                        "icon": "bi-lightning",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "LLM Models",
                        "url": "control_center:dashboard",
                        "icon": "bi-cpu",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Prompt Templates",
                        "url": "control_center:dashboard",
                        "icon": "bi-file-earmark-text",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Handlers Registry",
                        "url": "control_center:dashboard",
                        "icon": "bi-gear-wide-connected",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                    {
                        "name": "Execution History",
                        "url": "bfagent:execution-list",
                        "icon": "bi-clock-history",
                        "badge": "Legacy",
                        "badge_color": "secondary",
                    },
                ],
            },
            {
                "title": "ILLUSTRATION SYSTEM",
                "items": [
                    {
                        "name": "Generated Images",
                        "url": "bfagent:illustration:gallery",
                        "icon": "bi-images",
                    },
                ],
            },
            # {
            #     "title": "FEATURE MANAGEMENT",
            #     "items": [
            #         {
            #             "name": "Feature Planning",
            #             "url": "control_center:feature-planning-dashboard",
            #             "icon": "bi-kanban",
            #         },
            #     ],
            # },
            {
                "title": "NAVIGATION SYSTEM",
                "items": [
                    {
                        "name": "Domain Navigator",
                        "url": "control_center:dashboard",
                        "icon": "bi-list-nested",
                        "badge": "NEW",
                        "badge_color": "success",
                    },
                    {
                        "name": "Navigation Dashboard",
                        "url": "control_center:dashboard",
                        "icon": "bi-compass",
                    },
                    {
                        "name": "Sections",
                        "url": "control_center:dashboard",
                        "icon": "bi-folder",
                    },
                    {
                        "name": "Items",
                        "url": "control_center:dashboard",
                        "icon": "bi-list",
                    },
                    {
                        "name": "Preview",
                        "url": "control_center:dashboard",
                        "icon": "bi-eye",
                    },
                ],
            },
            {
                "title": "SYSTEM MANAGEMENT",
                "items": [
                    {
                        "name": "Enterprise Tools",
                        "url": "control_center:dashboard",
                        "icon": "bi-tools",
                    },
                    {
                        "name": "Migration Registry",
                        "url": "control_center:migration-registry-dashboard",
                        "icon": "bi-database-gear",
                    },
                    {
                        "name": "Model Consistency",
                        "url": "control_center:model-consistency",
                        "icon": "bi-check-circle",
                    },
                ],
            },
        ],
    },
    "writing_hub": {
        "domain_name": "Writing Hub V2",
        "domain_icon": "bi-pen",
        "sections": [
            {
                "title": "PROJECTS & CONTENT",
                "items": [
                    {
                        "name": "Projects",
                        "url": "writing_hub:book-projects-v2-list",
                        "icon": "bi-folder",
                        "badge": "V2",
                        "badge_color": "success",
                    },
                ],
            },
            {
                "title": "STORY ENGINE",
                "items": [
                    {
                        "name": "Story Generator",
                        "url": "writing_hub:story_generator",
                        "icon": "bi-magic",
                        "badge": "AI",
                        "badge_color": "info",
                    },
                    {
                        "name": "Chapter Writer",
                        "url": "writing_hub:chapter_writer",
                        "icon": "bi-robot",
                    },
                ],
            },
        ],
    },
    # Global items shown in all domains
    "global": {
        "sections": [
            {
                "title": "NAVIGATION",
                "items": [
                    {"name": "Home", "url": "hub:home", "icon": "bi-house-door-fill"},
                ],
            },
        ]
    },
}


def get_sidebar_for_domain(domain: str) -> dict:
    """
    Get sidebar configuration for a specific domain.

    Args:
        domain: Domain identifier (bookwriting, medtrans, genagent, control_center)

    Returns:
        Dictionary with domain_name, domain_icon, and sections

    Example:
        >>> config = get_sidebar_for_domain('bookwriting')
        >>> print(config['domain_name'])
        'Book Writing Studio'
    """
    # Default to bookwriting if domain not found
    if domain not in SIDEBAR_NAVIGATION:
        domain = "bookwriting"

    domain_config = SIDEBAR_NAVIGATION.get(domain, SIDEBAR_NAVIGATION["bookwriting"])

    # Add global items
    global_sections = SIDEBAR_NAVIGATION.get("global", {}).get("sections", [])
    all_sections = domain_config.get("sections", []) + global_sections

    return {
        "domain_name": domain_config.get("domain_name", domain.title()),
        "domain_icon": domain_config.get("domain_icon", "bi-circle"),
        "sections": all_sections,
    }


def get_all_domains() -> list:
    """
    Get list of all available domains.

    Returns:
        List of domain identifiers
    """
    return [key for key in SIDEBAR_NAVIGATION.keys() if key != "global"]
