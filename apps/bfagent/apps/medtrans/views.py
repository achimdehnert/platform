import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.bfagent.decorators import medtrans_required
from .forms import CustomerForm, PresentationUploadForm
from .models import Customer, Presentation

logger = logging.getLogger(__name__)


@login_required
@medtrans_required
def presentation_list(request):
    """List all presentations for current user's customers"""
    customers = Customer.objects.filter(user=request.user)
    presentations = Presentation.objects.filter(customer__user=request.user).select_related(
        "customer"
    )

    context = {
        "presentations": presentations,
        "customers": customers,
        "customer_count": customers.count(),
        "presentation_count": presentations.count(),
    }
    return render(request, "medtrans/presentation_list.html", context)


@login_required
@medtrans_required
def presentation_upload(request):
    """Upload new PowerPoint presentation"""
    if request.method == "POST":
        form = PresentationUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            presentation = form.save()
            messages.success(
                request, f'Presentation "{presentation.filename}" uploaded successfully!'
            )

            # HTMX redirect pattern (BF Agent style)
            if request.headers.get("HX-Request"):
                return HttpResponse(status=204, headers={"HX-Redirect": "/medtrans/"})
            return redirect("medtrans:presentation-list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PresentationUploadForm(user=request.user)

    context = {"form": form}
    return render(request, "medtrans/presentation_upload.html", context)


@login_required
def customer_list(request):
    """List all customers for current user"""
    customers = Customer.objects.filter(user=request.user)
    context = {"customers": customers}
    return render(request, "medtrans/customer_list.html", context)


@login_required
def customer_create(request):
    """Create new customer"""
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.customer_name}" created successfully!')

            # HTMX redirect pattern
            if request.headers.get("HX-Request"):
                return HttpResponse(status=204, headers={"HX-Redirect": "/medtrans/customers/"})
            return redirect("medtrans:customer-list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerForm()

    context = {"form": form}
    return render(request, "medtrans/customer_create.html", context)


@login_required
@require_http_methods(["POST"])
def start_translation_pipeline(request, presentation_id):
    """
    Start complete translation pipeline: Extract → Translate → Repackage
    
    Returns JSON with results from each step
    """
    try:
        presentation = get_object_or_404(
            Presentation,
            id=presentation_id,
            customer__user=request.user
        )
        
        logger.info(f"Starting translation pipeline for presentation {presentation_id}")
        
        # Import handlers
        from .handlers import ExtractTextsHandler, TranslateTextsHandler, RepackagePPTXHandler
        
        results = {
            'presentation_id': presentation_id,
            'filename': presentation.filename,
            'steps': {}
        }
        
        # Step 1: Extract texts from PPTX
        logger.info("Step 1: Extracting texts...")
        presentation.status = 'extracting'
        presentation.save()
        
        extract_handler = ExtractTextsHandler()
        extract_result = extract_handler.execute({
            'pptx_file': presentation.pptx_file.path,
            'presentation_id': presentation_id,
            'customer_id': presentation.customer.customer_id
        })
        
        results['steps']['extract'] = extract_result
        
        if not extract_result.get('success'):
            presentation.status = 'uploaded'
            presentation.save()
            return JsonResponse({
                'success': False,
                'error': 'Text extraction failed',
                'results': results
            }, status=400)
        
        logger.info(f"Extracted {extract_result.get('total_texts', 0)} texts")
        
        # Step 2: Translate texts using DeepL
        logger.info("Step 2: Translating texts...")
        presentation.status = 'translating'
        presentation.save()
        
        translate_handler = TranslateTextsHandler()
        translate_result = translate_handler.execute({
            'presentation_id': presentation_id,
            'source_lang': presentation.source_language,
            'target_lang': presentation.target_language,
            'deepl_api_key': settings.DEEPL_API_KEY
        })
        
        results['steps']['translate'] = translate_result
        
        if not translate_result.get('success'):
            presentation.status = 'extracting'
            presentation.save()
            return JsonResponse({
                'success': False,
                'error': 'Translation failed',
                'results': results
            }, status=400)
        
        logger.info(f"Translated {translate_result.get('texts_translated', 0)} texts")
        
        # Step 3: Create translated PPTX
        logger.info("Step 3: Creating translated PPTX...")
        presentation.status = 'reviewing'
        presentation.save()
        
        # Generate output filename: original_name_orglang_targetlang_timestamp.pptx
        original_name = Path(presentation.filename).stem  # Filename without extension
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{original_name}_{presentation.source_language}_{presentation.target_language}_{timestamp}.pptx"
        output_dir = Path(settings.MEDIA_ROOT) / "medtrans" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / output_filename
        
        repackage_handler = RepackagePPTXHandler()
        repackage_result = repackage_handler.execute({
            'pptx_file': presentation.pptx_file.path,
            'output_file': str(output_file),
            'presentation_id': presentation_id,
            'deepl_api_key': settings.DEEPL_API_KEY
        })
        
        results['steps']['repackage'] = repackage_result
        
        if not repackage_result.get('success'):
            presentation.status = 'translating'
            presentation.save()
            return JsonResponse({
                'success': False,
                'error': 'PPTX creation failed',
                'results': results
            }, status=400)
        
        # Success - update presentation status
        presentation.status = 'completed'
        presentation.save()
        
        logger.info(f"Translation pipeline completed successfully for presentation {presentation_id}")
        
        return JsonResponse({
            'success': True,
            'message': f'Translation completed: {output_filename}',
            'output_file': str(output_file.relative_to(settings.MEDIA_ROOT)),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Translation pipeline failed: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def presentation_delete(request, presentation_id):
    """Delete a presentation and all associated data"""
    presentation = get_object_or_404(
        Presentation,
        id=presentation_id,
        customer__user=request.user
    )
    
    filename = presentation.filename
    
    # Delete the PPTX file
    if presentation.pptx_file:
        try:
            presentation.pptx_file.delete(save=False)
        except Exception as e:
            logger.warning(f"Could not delete file: {e}")
    
    # Delete presentation (cascade will delete PresentationText entries)
    presentation.delete()
    
    messages.success(request, f'Presentation "{filename}" deleted successfully!')
    return redirect('medtrans:presentation-list')


@login_required
@require_http_methods(["POST"])
def presentation_reset(request, presentation_id):
    """Reset presentation status to 'uploaded' for re-translation"""
    presentation = get_object_or_404(
        Presentation,
        id=presentation_id,
        customer__user=request.user
    )
    
    # Reset status and counters
    presentation.status = 'uploaded'
    presentation.total_texts = 0
    presentation.translated_texts = 0
    presentation.save()
    
    # Delete existing translations
    from .models import PresentationText
    PresentationText.objects.filter(presentation=presentation).delete()
    
    messages.info(request, f'Presentation "{presentation.filename}" reset. Ready for re-translation!')
    return redirect('medtrans:presentation-list')


@login_required
def presentation_edit(request, presentation_id):
    """Edit translated texts"""
    from .models import PresentationText
    
    presentation = get_object_or_404(
        Presentation,
        id=presentation_id,
        customer__user=request.user
    )
    
    # Get all translated texts, ordered by slide and text_id
    texts = PresentationText.objects.filter(
        presentation=presentation
    ).order_by('slide_number', 'text_id')
    
    context = {
        'presentation': presentation,
        'texts': texts,
    }
    return render(request, 'medtrans/presentation_edit.html', context)


@login_required
@require_http_methods(["POST"])
def presentation_update_texts(request, presentation_id):
    """Update translated texts from edit form"""
    from .models import PresentationText
    
    presentation = get_object_or_404(
        Presentation,
        id=presentation_id,
        customer__user=request.user
    )
    
    # Update all submitted texts
    updated_count = 0
    for key, value in request.POST.items():
        if key.startswith('text_'):
            # Extract the primary key ID from the field name
            pk_id = key.replace('text_', '')
            try:
                text_obj = PresentationText.objects.get(
                    id=pk_id,
                    presentation=presentation
                )
                # Only update if the value has changed
                if text_obj.translated_text != value:
                    text_obj.translated_text = value
                    text_obj.manually_edited = True
                    text_obj.save()
                    updated_count += 1
                    logger.info(f"Updated text {pk_id}: '{text_obj.translated_text[:50]}...'")
            except PresentationText.DoesNotExist:
                logger.warning(f"Text with ID {pk_id} not found for presentation {presentation_id}")
            except ValueError:
                logger.warning(f"Invalid ID format: {pk_id}")
    
    messages.success(request, f'Updated {updated_count} translations!')
    return redirect('medtrans:presentation-edit', presentation_id=presentation_id)


@login_required
@require_http_methods(["POST"])
def presentation_regenerate(request, presentation_id):
    """Regenerate PPTX file with current translations"""
    presentation = get_object_or_404(
        Presentation,
        id=presentation_id,
        customer__user=request.user
    )
    
    try:
        # Generate new output filename
        original_name = Path(presentation.filename).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{original_name}_{presentation.source_language}_{presentation.target_language}_{timestamp}.pptx"
        output_dir = Path(settings.MEDIA_ROOT) / "medtrans" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / output_filename
        
        # Import handler
        from apps.medtrans.handlers.repackage_handler import RepackagePPTXHandler
        
        # Execute repackaging
        repackage_handler = RepackagePPTXHandler()
        repackage_result = repackage_handler.execute({
            'pptx_file': presentation.pptx_file.path,
            'output_file': str(output_file),
            'presentation_id': presentation_id,
            'deepl_api_key': settings.DEEPL_API_KEY
        })
        
        if repackage_result.get('success'):
            messages.success(
                request,
                f'PPTX regenerated successfully: {output_filename}'
            )
        else:
            messages.error(
                request,
                f"PPTX regeneration failed: {repackage_result.get('error', 'Unknown error')}"
            )
    
    except Exception as e:
        logger.error(f"PPTX regeneration failed: {e}", exc_info=True)
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('medtrans:presentation-edit', presentation_id=presentation_id)
