"""BF Agent Views Package"""

# Import all view modules
from . import (
    auth_views,
    auto_illustration_views,
    book_reader,
    chapter_comment_views,
    chapter_views,
    character_views,
    code_review_views,
    context_enrichment_views,
    crud_views,
    enrichment_views_handler,
    enrichment_views_minimal,
    feature_planning_views,
    field_management_views,
    handler_generator_views,
    handler_management_views,
    handler_test_view,
    illustration_generation_views,
    illustration_views,
    image_gallery,
    main_views,
    main_views_clean,
    metrics_views,
    migration_registry_views,
    review_views,
    story_engine_views,
    test_studio_views,
    workflow_builder_views,
    workflow_dashboard,
    worlds_views,
    cascade_api,
)

# Re-export ALL functions from ALL view modules for backward compatibility
from .auth_views import *
from .auto_illustration_views import *
from .book_reader import *
from .chapter_comment_views import *
from .chapter_views import *
from .character_views import *
from .code_review_views import *
from .context_enrichment_views import *
from .crud_views import *
from .enrichment_views_handler import *
from .enrichment_views_minimal import *
from .feature_planning_views import *
from .field_management_views import *
from .handler_generator_views import *
from .handler_management_views import *
from .handler_test_view import *
from .illustration_generation_views import *
from .illustration_views import *

# Import specific classes
from .image_gallery import BookIllustrationsView, ImageDetailView, ImageGalleryView
from .main_views import *
from .main_views_clean import *
from .metrics_views import *
from .migration_registry_views import *
from .review_views import *
from .story_engine_views import *
from .test_studio_views import *
from .workflow_builder_views import *
from .workflow_dashboard import *
from .worlds_views import *
from .cascade_api import *

__all__ = [
    "ImageGalleryView",
    "ImageDetailView",
    "BookIllustrationsView",
]
