"""
Domain Management Views

Web interface for managing domain templates
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from apps.genagent.domains import DomainRegistry, install_domain
from apps.genagent.models import Phase, Action
import json


@require_http_methods(["GET"])
def domain_list(request):
    """
    List all available domain templates (HYBRID: Code-based + Database)
    
    GET /genagent/domains/
    """
    # Import templates to ensure registration
    from apps.genagent.domains.templates import book  # noqa: F401
    from apps.genagent.models import CustomDomain
    
    # Get code-based templates
    code_domains = DomainRegistry.list_all()
    stats = DomainRegistry.get_statistics()
    
    # Get database-backed custom domains
    custom_domains = CustomDomain.objects.filter(is_active=True).order_by('category', 'name')
    
    # Combine both types
    all_domains = list(code_domains)
    
    # Convert CustomDomain objects to a compatible format
    for custom in custom_domains:
        # Add marker to identify custom domains
        custom.is_custom = True
        custom.domain_id = f"custom_{custom.pk}"  # Unique ID for custom domains
        all_domains.append(custom)
    
    # Organize by category
    domains_by_category = {}
    for domain in all_domains:
        category = domain.category
        if category not in domains_by_category:
            domains_by_category[category] = []
        domains_by_category[category].append(domain)
    
    # Update stats to include custom domains
    stats['total_templates'] = stats.get('total_templates', 0) + custom_domains.count()
    stats['custom_domains'] = custom_domains.count()
    
    context = {
        'domains': all_domains,
        'domains_by_category': domains_by_category,
        'stats': stats,
        'categories': DomainRegistry.list_categories(),
        'tags': DomainRegistry.list_tags(),
        'custom_domains_count': custom_domains.count(),
    }
    
    return render(request, 'genagent/domains/domain_list.html', context)


@require_http_methods(["GET"])
def domain_detail(request, domain_id):
    """
    Show details of a specific domain template
    
    GET /genagent/domains/<domain_id>/
    """
    try:
        template = DomainRegistry.get(domain_id)
    except KeyError:
        messages.error(request, f"Domain '{domain_id}' not found")
        return render(request, 'genagent/domains/domain_not_found.html', {
            'domain_id': domain_id,
            'available_domains': DomainRegistry.list_ids()
        })
    
    stats = template.get_statistics()
    
    context = {
        'template': template,
        'stats': stats,
        'phases': template.phases,
        'all_actions': template.get_all_actions(),
    }
    
    return render(request, 'genagent/domains/domain_detail.html', context)


@require_http_methods(["GET"])
def domain_install_wizard(request, domain_id):
    """
    Installation wizard for domain template
    
    GET /genagent/domains/<domain_id>/install/
    """
    try:
        template = DomainRegistry.get(domain_id)
    except KeyError:
        messages.error(request, f"Domain '{domain_id}' not found")
        return render(request, 'genagent/domains/domain_not_found.html', {
            'domain_id': domain_id
        })
    
    context = {
        'template': template,
        'required_fields': template.required_fields,
        'optional_fields': template.optional_fields,
    }
    
    return render(request, 'genagent/domains/domain_install_wizard.html', context)


@require_http_methods(["POST"])
def domain_install_execute(request, domain_id):
    """
    Execute domain installation
    
    POST /genagent/domains/<domain_id>/install/execute/
    """
    try:
        template = DomainRegistry.get(domain_id)
    except KeyError:
        return JsonResponse({
            'success': False,
            'error': f"Domain '{domain_id}' not found"
        }, status=404)
    
    # Parse context from POST data
    try:
        if request.content_type == 'application/json':
            context = json.loads(request.body)
        else:
            context = dict(request.POST)
            # Remove CSRF token
            context.pop('csrfmiddlewaretoken', None)
            # Convert single-item lists to values
            context = {k: v[0] if isinstance(v, list) and len(v) == 1 else v 
                      for k, v in context.items()}
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f"Invalid context data: {e}"
        }, status=400)
    
    # Check for dry_run parameter
    dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
    
    # Validate required fields
    missing_fields = template.validate_required_fields(context)
    if missing_fields:
        return JsonResponse({
            'success': False,
            'error': f"Missing required fields: {', '.join(missing_fields)}",
            'missing_fields': missing_fields
        }, status=400)
    
    # Install domain
    try:
        phase_id = install_domain(domain_id, context, dry_run=dry_run)
        
        if dry_run:
            return JsonResponse({
                'success': True,
                'dry_run': True,
                'message': 'Dry run successful - no database changes made',
                'would_create': {
                    'phases': len(template.phases),
                    'actions': len(template.get_all_actions())
                }
            })
        else:
            # Get created objects
            phase = Phase.objects.get(id=phase_id)
            phases_created = Phase.objects.filter(id__gte=phase_id).count()
            actions_created = Action.objects.filter(phase__id__gte=phase_id).count()
            
            messages.success(
                request, 
                f"Domain '{template.display_name}' installed successfully! "
                f"Created {phases_created} phases and {actions_created} actions."
            )
            
            return JsonResponse({
                'success': True,
                'phase_id': phase_id,
                'message': f"Domain installed successfully",
                'created': {
                    'phases': phases_created,
                    'actions': actions_created
                },
                'redirect_url': f'/genagent/domains/{domain_id}/installed/{phase_id}/'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def domain_installed_success(request, domain_id, phase_id):
    """
    Show success page after installation
    
    GET /genagent/domains/<domain_id>/installed/<phase_id>/
    """
    try:
        template = DomainRegistry.get(domain_id)
        phase = Phase.objects.get(id=phase_id)
        
        # Get all created phases
        phases = Phase.objects.filter(id__gte=phase_id).order_by('order')
        
        context = {
            'template': template,
            'phase': phase,
            'phases': phases,
            'success': True
        }
        
        return render(request, 'genagent/domains/domain_installed.html', context)
        
    except (KeyError, Phase.DoesNotExist) as e:
        messages.error(request, f"Error: {e}")
        return render(request, 'genagent/domains/domain_not_found.html', {
            'domain_id': domain_id
        })


@require_http_methods(["GET"])
def domain_search(request):
    """
    Search domain templates
    
    GET /genagent/domains/search/?q=<query>&category=<cat>&tags=<tag1,tag2>
    """
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    tags = request.GET.get('tags', '').split(',') if request.GET.get('tags') else None
    
    # Ensure templates are loaded
    from apps.genagent.domains.templates import book  # noqa: F401
    
    results = DomainRegistry.search(
        query=query if query else None,
        category=category if category else None,
        tags=tags
    )
    
    context = {
        'results': results,
        'query': query,
        'category': category,
        'tags': tags,
        'result_count': len(results)
    }
    
    return render(request, 'genagent/domains/domain_search_results.html', context)


@require_http_methods(["GET"])
def domain_api_list(request):
    """
    API endpoint for domain list
    
    GET /genagent/api/domains/
    """
    from apps.genagent.domains.templates import book  # noqa: F401
    
    domains = DomainRegistry.list_all()
    
    data = {
        'domains': [
            {
                'domain_id': d.domain_id,
                'display_name': d.display_name,
                'description': d.description,
                'category': d.category,
                'tags': d.tags,
                'phases_count': len(d.phases),
                'actions_count': len(d.get_all_actions()),
                'icon': d.icon,
                'color': d.color,
            }
            for d in domains
        ]
    }
    
    return JsonResponse(data)


@require_http_methods(["GET"])
def domain_api_detail(request, domain_id):
    """
    API endpoint for domain detail
    
    GET /genagent/api/domains/<domain_id>/
    """
    try:
        template = DomainRegistry.get(domain_id)
        
        data = {
            'domain_id': template.domain_id,
            'display_name': template.display_name,
            'description': template.description,
            'icon': template.icon,
            'color': template.color,
            'category': template.category,
            'tags': template.tags,
            'version': template.version,
            'author': template.author,
            'required_fields': template.required_fields,
            'optional_fields': template.optional_fields,
            'phases': [
                {
                    'name': p.name,
                    'description': p.description,
                    'order': p.order,
                    'color': p.color,
                    'icon': p.icon,
                    'actions_count': len(p.actions),
                    'actions': [
                        {
                            'name': a.name,
                            'description': a.description,
                            'handler_class': a.handler_class,
                            'order': a.order,
                        }
                        for a in p.actions
                    ]
                }
                for p in template.phases
            ],
            'statistics': template.get_statistics()
        }
        
        return JsonResponse(data)
        
    except KeyError:
        return JsonResponse({
            'error': f"Domain '{domain_id}' not found"
        }, status=404)


@require_http_methods(["POST"])
def domain_add_phase(request, domain_id):
    """
    Add a new phase to a domain template
    
    POST /genagent/domains/<domain_id>/add-phase/
    """
    try:
        # Get form data
        name = request.POST.get('name', '')
        description = request.POST.get('description', '')
        color = request.POST.get('color', '#6366f1')
        order = int(request.POST.get('order', 0))
        required = request.POST.get('required') == 'on'
        
        # Validate input
        if not name or not description:
            return HttpResponse(
                '<div class="alert alert-danger">Phase name and description are required</div>',
                status=400
            )
        
        # Create phase HTML (for template preview - not database)
        phase_html = f'''
        <div class="card mb-3" id="phase-{order}" style="border-left: 4px solid {color};">
            <div class="card-header" style="background-color: {color}20; cursor: pointer;" 
                 data-bs-toggle="collapse" 
                 data-bs-target="#phase-content-{order}"
                 aria-expanded="true">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">
                        <span class="badge" style="background-color: {color};">
                            <i class="bi bi-circle-fill"></i> Phase {order + 1}
                        </span>
                        {name}
                        {'<span class="badge bg-warning">Optional</span>' if not required else ''}
                    </h6>
                    <div>
                        <span class="badge bg-secondary">0 Actions</span>
                        <i class="bi bi-chevron-down ms-2"></i>
                    </div>
                </div>
            </div>
            <div class="card-body collapse show" id="phase-content-{order}">
                <p class="text-muted">{description}</p>
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> 
                    This is a preview. To persist changes, export and reimport the domain template.
                </div>
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0">
                        <thead>
                            <tr>
                                <th width="5%">#</th>
                                <th width="25%">Action</th>
                                <th width="35%">Description</th>
                                <th width="30%">Handler</th>
                                <th width="5%">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="5" class="text-center text-muted">
                                    No actions defined yet. 
                                    <button class="btn btn-sm btn-outline-primary ms-2">
                                        <i class="bi bi-plus"></i> Add Action
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        '''
        
        # Close modal and return success
        response = HttpResponse(phase_html)
        response['HX-Trigger'] = 'closeModal'
        return response
        
    except Exception as e:
        return HttpResponse(
            f'<div class="alert alert-danger">Error adding phase: {str(e)}</div>',
            status=500
        )


# ============================================================
# CUSTOM DOMAIN CRUD VIEWS
# Database-backed domain templates (novel, essay, movie, etc.)
# ============================================================

@require_http_methods(["GET", "POST"])
def custom_domain_create(request):
    """
    Create new custom domain template
    
    GET/POST /genagent/domains/custom/create/
    """
    from apps.genagent.models import CustomDomain
    
    if request.method == "POST":
        try:
            # Extract form data
            domain_id = request.POST.get('domain_id', '').strip()
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            category = request.POST.get('category', 'other')
            icon = request.POST.get('icon', 'bi-file-text')
            color = request.POST.get('color', '#3B82F6')
            
            # Validation
            if not domain_id:
                messages.error(request, "Domain ID is required")
                return render(request, 'genagent/domains/custom_domain_form.html', {
                    'title': 'Create Custom Domain',
                    'categories': CustomDomain.CATEGORY_CHOICES
                })
            
            if not name:
                messages.error(request, "Name is required")
                return render(request, 'genagent/domains/custom_domain_form.html', {
                    'title': 'Create Custom Domain',
                    'categories': CustomDomain.CATEGORY_CHOICES
                })
            
            # Check if domain_id already exists
            if CustomDomain.objects.filter(domain_id=domain_id).exists():
                messages.error(request, f"Domain ID '{domain_id}' already exists")
                return render(request, 'genagent/domains/custom_domain_form.html', {
                    'title': 'Create Custom Domain',
                    'categories': CustomDomain.CATEGORY_CHOICES
                })
            
            # Create custom domain
            custom_domain = CustomDomain.objects.create(
                domain_id=domain_id,
                name=name,
                description=description,
                category=category,
                icon=icon,
                color=color,
                phases_config=[],
                required_fields=[],
                optional_fields=[]
            )
            
            messages.success(request, f"Custom domain '{name}' created successfully!")
            
            # HTMX: Return updated list
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = f'/genagent/domains/custom/{custom_domain.pk}/'
                return response
            
            return render(request, 'genagent/domains/custom_domain_detail.html', {
                'domain': custom_domain
            })
            
        except Exception as e:
            messages.error(request, f"Error creating custom domain: {str(e)}")
            return render(request, 'genagent/domains/custom_domain_form.html', {
                'title': 'Create Custom Domain',
                'categories': CustomDomain.CATEGORY_CHOICES
            })
    
    # GET request
    context = {
        'title': 'Create Custom Domain',
        'categories': CustomDomain.CATEGORY_CHOICES
    }
    return render(request, 'genagent/domains/custom_domain_form.html', context)


@require_http_methods(["GET"])
def custom_domain_detail(request, pk):
    """
    Show custom domain details
    
    GET /genagent/domains/custom/<pk>/
    """
    from apps.genagent.models import CustomDomain
    
    domain = get_object_or_404(CustomDomain, pk=pk)
    stats = domain.get_statistics()
    
    context = {
        'domain': domain,
        'stats': stats,
    }
    
    return render(request, 'genagent/domains/custom_domain_detail.html', context)


@require_http_methods(["GET", "POST"])
def custom_domain_edit(request, pk):
    """
    Edit existing custom domain
    
    GET/POST /genagent/domains/custom/<pk>/edit/
    """
    from apps.genagent.models import CustomDomain
    
    domain = get_object_or_404(CustomDomain, pk=pk)
    
    if request.method == "POST":
        try:
            # Update fields
            domain.name = request.POST.get('name', domain.name).strip()
            domain.description = request.POST.get('description', domain.description).strip()
            domain.category = request.POST.get('category', domain.category)
            domain.icon = request.POST.get('icon', domain.icon)
            domain.color = request.POST.get('color', domain.color)
            domain.is_active = request.POST.get('is_active') == 'on'
            
            domain.save()
            
            messages.success(request, f"Custom domain '{domain.name}' updated successfully!")
            
            # HTMX: Return updated detail view
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = f'/genagent/domains/custom/{domain.pk}/'
                return response
            
            return render(request, 'genagent/domains/custom_domain_detail.html', {
                'domain': domain,
                'stats': domain.get_statistics()
            })
            
        except Exception as e:
            messages.error(request, f"Error updating custom domain: {str(e)}")
    
    # GET request
    context = {
        'title': f'Edit {domain.name}',
        'domain': domain,
        'categories': CustomDomain.CATEGORY_CHOICES
    }
    return render(request, 'genagent/domains/custom_domain_form.html', context)


@require_http_methods(["POST"])
def custom_domain_delete(request, pk):
    """
    Delete custom domain
    
    POST /genagent/domains/custom/<pk>/delete/
    """
    from apps.genagent.models import CustomDomain
    
    domain = get_object_or_404(CustomDomain, pk=pk)
    domain_name = domain.name
    
    try:
        domain.delete()
        messages.success(request, f"Custom domain '{domain_name}' deleted successfully!")
        
        # HTMX: Redirect to list
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = '/genagent/domains/'
            return response
        
        return render(request, 'genagent/domains/domain_list.html', {
            'domains': DomainRegistry.list_all(),
            'stats': DomainRegistry.get_statistics()
        })
        
    except Exception as e:
        messages.error(request, f"Error deleting custom domain: {str(e)}")
        return render(request, 'genagent/domains/custom_domain_detail.html', {
            'domain': domain,
            'stats': domain.get_statistics()
        })
