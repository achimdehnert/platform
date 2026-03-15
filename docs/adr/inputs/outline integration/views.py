"""research-hub: Outline Webhook Endpoint.

Fixes B2: HMAC-Signatur-Validierung (ADR-050 Inter-Hub-Standard).

Outline sendet einen Webhook bei document.create und document.update Events.
Der Webhook-Payload enthält die Document-ID — wir laden den vollen Inhalt
via outline_mcp Client und triggern dann den Celery-Enrichment-Task.

URL: POST /api/v1/knowledge/webhook/outline/
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .services import KnowledgeDocumentService
from .tasks import enrich_knowledge_document

logger = logging.getLogger(__name__)

_SUPPORTED_EVENTS = frozenset(
    [
        "documents.create",
        "documents.update",
        "documents.delete",
    ]
)


def _verify_outline_signature(request: HttpRequest) -> bool:
    """Verify HMAC-SHA256 signature from Outline webhook.

    Outline sends X-Outline-Signature: sha256=<hex> in the request header.
    We verify against OUTLINE_WEBHOOK_SECRET from settings.

    This is the B2 fix: unauthenticated webhook endpoint → HMAC verification.
    """
    signature_header = request.headers.get("X-Outline-Signature", "")
    if not signature_header.startswith("sha256="):
        logger.warning("Outline webhook: missing or malformed signature header.")
        return False

    received_sig = signature_header[len("sha256="):]
    secret: str = getattr(settings, "OUTLINE_WEBHOOK_SECRET", "")
    if not secret:
        logger.error(
            "OUTLINE_WEBHOOK_SECRET not configured — rejecting all webhooks. "
            "Set OUTLINE_WEBHOOK_SECRET in .env (Phase 5.3)."
        )
        return False

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received_sig, expected_sig)


@method_decorator(csrf_exempt, name="dispatch")
class OutlineWebhookView(View):
    """Handle incoming Outline webhook events.

    Supported events:
        documents.create — create or update KnowledgeDocument, trigger enrichment
        documents.update — same as create (upsert)
        documents.delete — soft-delete KnowledgeDocument

    Auth: HMAC-SHA256 via X-Outline-Signature header (B2 fix).
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        if not _verify_outline_signature(request):
            return JsonResponse(
                {"error": "Invalid signature."}, status=401
            )

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        event = payload.get("event", "")
        if event not in _SUPPORTED_EVENTS:
            # Acknowledge unknown events silently — Outline may add new event types
            return JsonResponse({"ok": True, "processed": False, "event": event})

        document_payload = payload.get("payload", {}).get("model", {})
        outline_document_id: str = document_payload.get("id", "")
        if not outline_document_id:
            return JsonResponse(
                {"error": "Missing document ID in payload."}, status=400
            )

        # tenant_id resolution: Outline is a single-tenant system in our setup.
        # Default tenant_id is read from settings (platform-wide Outline tenant).
        tenant_id: int = getattr(settings, "OUTLINE_TENANT_ID", 1)

        service = KnowledgeDocumentService()

        if event == "documents.delete":
            service.soft_delete_by_outline_id(
                tenant_id=tenant_id,
                outline_id=outline_document_id,
            )
            return JsonResponse({"ok": True, "processed": True, "event": event})

        # documents.create or documents.update → upsert + async enrichment
        knowledge_doc = service.upsert_from_outline_id(
            tenant_id=tenant_id,
            outline_id=outline_document_id,
            collection_id=document_payload.get("collectionId", ""),
            outline_url=document_payload.get("url", ""),
            title=document_payload.get("title", ""),
        )

        # Trigger async AI-enrichment (Phase 5.9)
        enrich_knowledge_document.delay(knowledge_doc.id)

        return JsonResponse({"ok": True, "processed": True, "document_id": knowledge_doc.public_id.hex})
