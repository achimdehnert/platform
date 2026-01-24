"""
Writing Hub Import Views
Import existing manuscripts and planning documents into new projects
"""
import os
import json
import tempfile
from pathlib import Path
from django.conf import settings
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from apps.bfagent.models import BookProjects, BookChapters, Characters, Worlds, BookTypes
from .services import ImportService

# Try to import AI service
try:
    from .services.ai_import_service import AIImportService, analyze_document_with_ai
    AI_IMPORT_AVAILABLE = True
except ImportError:
    AI_IMPORT_AVAILABLE = False


class BookReengineerService:
    """Service wrapper for the BookReengineer parser"""
    
    @staticmethod
    def parse_uploaded_file_with_ai(uploaded_file, use_ai: bool = True):
        """Parse an uploaded file using AI when available"""
        content = ''
        for chunk in uploaded_file.chunks():
            content += chunk.decode('utf-8')
        
        if use_ai and AI_IMPORT_AVAILABLE:
            try:
                result = analyze_document_with_ai(content, uploaded_file.name, use_ai=True)
                if result and result.get('ai_analyzed'):
                    return result
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"AI analysis failed, using rules: {e}")
        
        # Fallback to rule-based
        return BookReengineerService.parse_uploaded_file(uploaded_file)
    
    @staticmethod
    def parse_file_path_with_ai(file_path: str, use_ai: bool = True):
        """Parse a file from filesystem using AI when available"""
        if use_ai and AI_IMPORT_AVAILABLE:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = analyze_document_with_ai(content, os.path.basename(file_path), use_ai=True)
                if result and result.get('ai_analyzed'):
                    return result
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"AI analysis failed, using rules: {e}")
        
        # Fallback to rule-based
        return BookReengineerService.parse_file_path(file_path)
    
    @staticmethod
    def parse_uploaded_file(uploaded_file):
        """Parse an uploaded file and return analysis results"""
        from .management.commands.reengineer_book import BookReengineer
        
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk.decode('utf-8'))
            temp_path = f.name
        
        try:
            # Run analysis
            reeng = BookReengineer(temp_path, verbose=False)
            result = reeng.analyze()
            return result
        finally:
            # Cleanup temp file
            os.unlink(temp_path)
    
    @staticmethod
    def parse_file_path(file_path):
        """Parse a file from the filesystem"""
        from .management.commands.reengineer_book import BookReengineer
        
        reeng = BookReengineer(file_path, verbose=False)
        return reeng.analyze()


@login_required
def import_project_start(request):
    """Start page for importing a project from existing materials"""
    
    # Get example files from books directory
    books_dir = Path(__file__).parent.parent.parent / 'books'
    example_files = []
    
    if books_dir.exists():
        for md_file in books_dir.rglob('*.md'):
            rel_path = md_file.relative_to(books_dir)
            example_files.append({
                'path': str(md_file),
                'name': md_file.name,
                'folder': str(rel_path.parent),
                'size': md_file.stat().st_size,
            })
    
    context = {
        'example_files': example_files[:20],  # Limit to 20
        'title': 'Projekt importieren',
    }
    return render(request, 'writing_hub/import/import_start.html', context)


@login_required
@require_http_methods(["POST"])
def import_project_analyze(request):
    """Analyze uploaded or selected files (supports multiple)"""
    
    all_results = []
    errors = []
    
    # Check if AI analysis is requested (default: True if available)
    use_ai = request.POST.get('use_ai', 'true').lower() == 'true'
    use_ai = use_ai and AI_IMPORT_AVAILABLE
    
    # Collect all files to process
    files_to_process = []
    
    # Check for uploaded files
    uploaded_files = request.FILES.getlist('files')
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.md'):
            files_to_process.append({
                'type': 'upload',
                'file': uploaded_file,
                'name': uploaded_file.name,
            })
        else:
            errors.append(f"Übersprungen (kein .md): {uploaded_file.name}")
    
    # Check for server file paths (JSON array)
    file_paths_json = request.POST.get('file_paths', '[]')
    try:
        server_paths = json.loads(file_paths_json)
        for path in server_paths:
            if os.path.exists(path):
                files_to_process.append({
                    'type': 'path',
                    'path': path,
                    'name': os.path.basename(path),
                })
            else:
                errors.append(f"Nicht gefunden: {path}")
    except json.JSONDecodeError:
        pass
    
    if not files_to_process:
        messages.error(request, "Keine gültigen Dateien ausgewählt.")
        return redirect('writing_hub:import_project_start')
    
    # Process each file
    combined_analysis = {
        'title': '',
        'document_type': 'mixed',
        'word_count': 0,
        'chapter_count': 0,
        'characters': [],
        'locations': [],
        'subplots': [],
        'story_arc': {'type': '', 'parts': 0, 'twists': 0},
        'working_titles': [],
        'chapters': [],
        'sources': [],
        'file_count': len(files_to_process),
        'ai_analyzed': False,
    }
    
    for file_info in files_to_process:
        try:
            # Use AI-powered analysis when available
            if file_info['type'] == 'upload':
                if use_ai:
                    result = BookReengineerService.parse_uploaded_file_with_ai(file_info['file'], use_ai=True)
                else:
                    result = BookReengineerService.parse_uploaded_file(file_info['file'])
            else:
                if use_ai:
                    result = BookReengineerService.parse_file_path_with_ai(file_info['path'], use_ai=True)
                else:
                    result = BookReengineerService.parse_file_path(file_info['path'])
            
            # Check if we got AI result (dict) or rule-based result (object)
            is_ai_result = isinstance(result, dict)
            
            if is_ai_result:
                # AI result is already a dict - merge directly
                combined_analysis['ai_analyzed'] = result.get('ai_analyzed', False)
                
                if not combined_analysis['title'] and result.get('title'):
                    combined_analysis['title'] = result['title']
                
                # Store premise, logline and raw_content
                if result.get('premise') and not combined_analysis.get('premise'):
                    combined_analysis['premise'] = result['premise']
                if result.get('logline') and not combined_analysis.get('logline'):
                    combined_analysis['logline'] = result['logline']
                if result.get('setting') and not combined_analysis.get('setting'):
                    combined_analysis['setting'] = result['setting']
                if result.get('raw_content'):
                    combined_analysis['raw_content'] = result.get('raw_content', '')
                
                combined_analysis['word_count'] += result.get('word_count', 0)
                combined_analysis['chapter_count'] += result.get('chapter_count', 0)
                
                # Merge characters
                existing_char_names = {c['name'] for c in combined_analysis['characters']}
                for c in result.get('characters', []):
                    if c.get('name') and c['name'] not in existing_char_names:
                        combined_analysis['characters'].append(c)
                        existing_char_names.add(c['name'])
                
                # Merge locations
                existing_loc_names = {l['name'] for l in combined_analysis['locations']}
                for l in result.get('locations', []):
                    if l.get('name') and l['name'] not in existing_loc_names:
                        combined_analysis['locations'].append(l)
                        existing_loc_names.add(l['name'])
                
                # Merge chapters
                combined_analysis['chapters'].extend(result.get('chapters', []))
                
                # Merge story arc
                if result.get('story_arc', {}).get('type') and not combined_analysis['story_arc']['type']:
                    combined_analysis['story_arc'] = result['story_arc']
                
                # Merge subplots
                combined_analysis['subplots'].extend(result.get('subplots', []))
                combined_analysis['working_titles'].extend(result.get('working_titles', []))
                combined_analysis['sources'].extend(result.get('sources', []))
                
            else:
                # Rule-based result is an object with attributes
                if not combined_analysis['title'] and result.title:
                    combined_analysis['title'] = result.title
                
                combined_analysis['word_count'] += result.word_count or 0
                combined_analysis['chapter_count'] += result.chapter_count or 0
                
                # Merge characters (dedupe by name) - store full data
                existing_char_names = {c['name'] if isinstance(c, dict) else c for c in combined_analysis['characters']}
                for c in result.characters:
                    if c.name not in existing_char_names:
                        combined_analysis['characters'].append({
                            'name': c.name,
                            'role': c.role if c.role != 'unknown' else '',
                            'age': c.age or '',
                            'background': c.background or '',
                            'motivation': c.motivation or '',
                            'arc': c.arc or '',
                            'traits': c.traits or [],
                            'source_file': file_info['name'],
                        })
                        existing_char_names.add(c.name)
                
                # Merge locations (dedupe by name) - store full data
                existing_loc_names = {l['name'] if isinstance(l, dict) else l for l in combined_analysis['locations']}
                for l in result.locations:
                    if l.name not in existing_loc_names:
                        combined_analysis['locations'].append({
                            'name': l.name,
                            'description': l.description or '',
                            'features': l.features or [],
                            'source_file': file_info['name'],
                        })
                        existing_loc_names.add(l.name)
                
                # Merge subplots
                for s in result.subplots:
                    combined_analysis['subplots'].append(s.name)
                
                # Use first story arc found
                if result.story_arc and result.story_arc.structure_type and not combined_analysis['story_arc']['type']:
                    combined_analysis['story_arc'] = {
                        'type': result.story_arc.structure_type,
                        'parts': len(result.story_arc.parts),
                        'twists': len(result.story_arc.twists),
                    }
                
                # Merge working titles
                combined_analysis['working_titles'].extend(result.working_titles)
                
                # Merge chapters with source info
                for c in result.chapters:
                    combined_analysis['chapters'].append({
                        'number': c.number,
                        'title': c.title,
                        'word_count': c.word_count,
                        'status': c.status,
                        'pov': c.pov,
                        'location': c.location,
                        'beats': c.beats[:5] if c.beats else [],
                        'source_file': file_info['name'],
                    })
                
                combined_analysis['sources'].append({
                    'filename': file_info['name'],
                    'type': file_info['type'],
                    'word_count': result.word_count,
                    'chapter_count': result.chapter_count,
                    'document_type': result.document_type,
                })
                
                # Store raw content for fallback extraction
                if not combined_analysis.get('raw_content'):
                    try:
                        if file_info['type'] == 'upload':
                            file_info['file'].seek(0)
                            combined_analysis['raw_content'] = file_info['file'].read().decode('utf-8', errors='ignore')
                        else:
                            with open(file_info['path'], 'r', encoding='utf-8', errors='ignore') as f:
                                combined_analysis['raw_content'] = f.read()
                    except:
                        pass
            
        except Exception as e:
            errors.append(f"Fehler bei {file_info['name']}: {str(e)}")
    
    # Show warnings for any errors
    for error in errors:
        messages.warning(request, error)
    
    if not combined_analysis['sources']:
        messages.error(request, "Keine Datei konnte erfolgreich analysiert werden.")
        return redirect('writing_hub:import_project_start')
    
    # Set default title if none found
    if not combined_analysis['title']:
        if len(combined_analysis['sources']) == 1:
            combined_analysis['title'] = combined_analysis['sources'][0]['filename'].replace('.md', '')
        else:
            combined_analysis['title'] = f"Import ({len(combined_analysis['sources'])} Dateien)"
    
    # Debug: Log what we're storing
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Storing analysis - Title: {combined_analysis.get('title')}")
    logger.info(f"Storing analysis - Chapters: {len(combined_analysis.get('chapters', []))}")
    logger.info(f"Storing analysis - Characters: {len(combined_analysis.get('characters', []))}")
    logger.info(f"Storing analysis - Locations: {len(combined_analysis.get('locations', []))}")
    if combined_analysis.get('characters'):
        logger.info(f"First character: {combined_analysis['characters'][0]}")
    
    # Store analysis in session
    request.session['import_analysis'] = combined_analysis
    request.session.modified = True  # Ensure session is saved
    
    return redirect('writing_hub:import_project_preview')


@login_required
def import_project_preview(request):
    """Preview analyzed data before creating project"""
    
    analysis = request.session.get('import_analysis')
    if not analysis:
        messages.warning(request, "Keine Analyse-Daten gefunden. Bitte erneut importieren.")
        return redirect('writing_hub:import_project_start')
    
    context = {
        'analysis': analysis,
        'title': 'Import-Vorschau',
    }
    return render(request, 'writing_hub/import/import_preview.html', context)


@login_required
@require_http_methods(["POST"])
def import_project_create(request):
    """Create project from analyzed data with selected items"""
    import logging
    logger = logging.getLogger(__name__)
    
    analysis = request.session.get('import_analysis')
    if not analysis:
        messages.error(request, "Keine Analyse-Daten gefunden.")
        return redirect('writing_hub:import_project_start')
    
    # Get form data
    title = request.POST.get('title', analysis.get('title', 'Neues Projekt'))
    genre = request.POST.get('genre', 'Fiction')
    description = request.POST.get('description', '')
    
    # Get selected items (individual checkboxes)
    selected_chapter_indices = request.POST.getlist('chapters')  # List of indices
    selected_characters = request.POST.getlist('characters')      # List of names
    selected_locations = request.POST.getlist('locations')        # List of names
    
    # Debug logging
    logger.info(f"Import Create - Title: {title}")
    logger.info(f"Import Create - Chapters selected: {selected_chapter_indices}")
    logger.info(f"Import Create - Characters selected: {selected_characters}")
    logger.info(f"Import Create - Locations selected: {selected_locations}")
    logger.info(f"Import Create - Analysis chapters: {len(analysis.get('chapters', []))}")
    logger.info(f"Import Create - Analysis characters: {len(analysis.get('characters', []))}")
    logger.info(f"Import Create - Analysis locations: {len(analysis.get('locations', []))}")
    
    # Get default book type
    default_book_type = BookTypes.objects.first()
    
    # Build description from analysis if not provided
    if not description:
        desc_parts = []
        if analysis.get('story_arc', {}).get('type'):
            desc_parts.append(f"Struktur: {analysis['story_arc']['type']}")
        if analysis.get('subplots'):
            desc_parts.append(f"Subplots: {', '.join(analysis['subplots'][:3])}")
        description = ' | '.join(desc_parts)
    
    # Build source info string
    source_files = []
    if analysis.get('sources'):
        source_files = [s['filename'] for s in analysis['sources']]
    
    # Store import metadata
    import_meta = {
        'imported_from': ', '.join(source_files) if source_files else 'Unknown',
        'document_type': analysis.get('document_type', 'mixed'),
        'original_word_count': analysis.get('word_count', 0),
        'import_date': str(__import__('datetime').datetime.now()),
        'file_count': len(source_files),
    }
    
    # Extract premise and logline from analysis
    premise = analysis.get('premise') or analysis.get('story_premise') or ''
    logline = analysis.get('logline') or analysis.get('tagline') or ''
    setting_location = analysis.get('setting') or ''
    
    # Try to extract from raw content if not in structured data
    if not premise and analysis.get('raw_content'):
        raw = analysis['raw_content']
        # Look for "Premise:" or "Erweitertes Premise:" section
        import re
        premise_match = re.search(r'(?:Erweitertes\s+)?Premise[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)', raw, re.IGNORECASE | re.DOTALL)
        if premise_match:
            premise = premise_match.group(1).strip()[:2000]
    
    if not logline and analysis.get('raw_content'):
        raw = analysis['raw_content']
        logline_match = re.search(r'Logline[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)', raw, re.IGNORECASE | re.DOTALL)
        if logline_match:
            logline = logline_match.group(1).strip()[:500]
    
    # Create project with all available data
    project = BookProjects.objects.create(
        title=title,
        genre=genre,
        description=description[:2000],
        story_premise=premise[:2000] if premise else '',
        tagline=logline[:500] if logline else '',
        setting_location=setting_location[:500] if setting_location else '',
        target_word_count=analysis.get('word_count') or 50000,
        status='planning' if analysis.get('document_type') == 'planning' else 'writing',
        content_rating='General',
        book_type=default_book_type,
        genre_settings=json.dumps(import_meta),
    )
    
    created_items = {'chapters': 0, 'characters': 0, 'locations': 0}
    
    # Import selected chapters
    if selected_chapter_indices and analysis.get('chapters'):
        for idx_str in selected_chapter_indices:
            try:
                idx = int(idx_str)
                if 0 <= idx < len(analysis['chapters']):
                    ch_data = analysis['chapters'][idx]
                    BookChapters.objects.create(
                        project=project,
                        title=ch_data['title'],
                        chapter_number=ch_data['number'],
                        content='',
                        status='outlined' if ch_data.get('status') == 'planned' else 'draft',
                        notes=f"POV: {ch_data.get('pov', 'N/A')}\nOrt: {ch_data.get('location', 'N/A')}\nBeats: {', '.join(ch_data.get('beats', [])[:3])}\nQuelle: {ch_data.get('source_file', 'N/A')}",
                    )
                    created_items['chapters'] += 1
            except (ValueError, IndexError):
                continue
    
    # Import selected characters with full parsed data
    if selected_characters:
        # Build lookup dict for character data
        char_data_lookup = {c['name']: c for c in analysis.get('characters', []) if isinstance(c, dict)}
        
        for char_name in selected_characters:
            char_data = char_data_lookup.get(char_name, {})
            
            # Build description from available data
            desc_parts = []
            if char_data.get('background'):
                desc_parts.append(char_data['background'])
            if char_data.get('motivation'):
                desc_parts.append(f"Motivation: {char_data['motivation']}")
            if char_data.get('traits'):
                desc_parts.append(f"Eigenschaften: {', '.join(char_data['traits'][:5])}")
            
            # Parse age - must be int or None, not empty string
            age_value = char_data.get('age')
            if age_value:
                try:
                    age_value = int(age_value)
                except (ValueError, TypeError):
                    age_value = None
            else:
                age_value = None
            
            Characters.objects.create(
                project=project,
                name=char_name,
                role=char_data.get('role') or 'Importiert',
                age=age_value,
                background=char_data.get('background') or '',
                motivation=char_data.get('motivation') or '',
                arc=char_data.get('arc') or '',
                description='\n'.join(desc_parts) if desc_parts else f"Importiert aus: {', '.join(source_files[:2])}",
            )
            created_items['characters'] += 1
    
    # Import selected locations as worlds with full parsed data
    # City → Country mapping for common German/European cities
    CITY_TO_COUNTRY = {
        'münchen': 'Deutschland', 'berlin': 'Deutschland', 'hamburg': 'Deutschland',
        'frankfurt': 'Deutschland', 'köln': 'Deutschland', 'düsseldorf': 'Deutschland',
        'wien': 'Österreich', 'zürich': 'Schweiz', 'paris': 'Frankreich',
        'london': 'England', 'new york': 'USA', 'los angeles': 'USA',
        'rom': 'Italien', 'madrid': 'Spanien', 'amsterdam': 'Niederlande',
    }
    
    if selected_locations:
        # Build lookup dict for location data
        loc_data_lookup = {l['name']: l for l in analysis.get('locations', []) if isinstance(l, dict)}
        created_countries = set()
        
        for loc_name in selected_locations[:20]:  # Limit to 20
            loc_data = loc_data_lookup.get(loc_name, {})
            
            # Build description from available data
            desc = loc_data.get('description') or ''
            if loc_data.get('features'):
                if desc:
                    desc += '\n\n'
                desc += f"Merkmale: {', '.join(loc_data['features'][:5])}"
            
            # Check if this is a city and infer country
            loc_lower = loc_name.lower().split()[0]  # Handle "München 2026" → "münchen"
            country = CITY_TO_COUNTRY.get(loc_lower)
            
            # Create country world first if not yet created
            if country and country not in created_countries:
                Worlds.objects.create(
                    project=project,
                    name=country,
                    description=f"Land/Region - enthält {loc_name}",
                )
                created_countries.add(country)
                created_items['locations'] += 1
            
            # Create location world
            Worlds.objects.create(
                project=project,
                name=loc_name,
                description=desc or f"Importiert aus: {', '.join(source_files[:2])}",
            )
            created_items['locations'] += 1
    
    # Auto-create world from setting if no locations selected but setting exists
    if not selected_locations and analysis.get('setting'):
        setting = analysis['setting']
        Worlds.objects.create(
            project=project,
            name=setting[:200],
            description=f"Hauptschauplatz der Geschichte",
        )
        created_items['locations'] += 1
    
    # Fallback: Extract locations from raw content if nothing was created
    if created_items['locations'] == 0 and analysis.get('raw_content'):
        raw = analysis['raw_content']
        # Look for common location patterns in German text
        import re
        
        # Extract cities from "München 2026" or "Berlin," patterns
        city_patterns = [
            r'(München|Berlin|Hamburg|Frankfurt|Köln|Wien|Zürich)\s*\d*',
            r'(München|Berlin|Hamburg|Frankfurt|Köln|Wien|Zürich),',
        ]
        found_cities = set()
        for pattern in city_patterns:
            matches = re.findall(pattern, raw, re.IGNORECASE)
            found_cities.update(m if isinstance(m, str) else m[0] for m in matches)
        
        # Create worlds for found cities
        for city in list(found_cities)[:3]:  # Limit to 3
            city_clean = city.strip().title()
            # Get country
            country = CITY_TO_COUNTRY.get(city_clean.lower())
            
            if country:
                # Create country first
                if not Worlds.objects.filter(project=project, name=country).exists():
                    Worlds.objects.create(
                        project=project,
                        name=country,
                        description=f"Land - enthält {city_clean}",
                    )
                    created_items['locations'] += 1
            
            # Create city
            Worlds.objects.create(
                project=project,
                name=city_clean,
                description=f"Extrahiert aus Dokument",
            )
            created_items['locations'] += 1
            logger.info(f"Auto-extracted location: {city_clean}")
    
    # Clear session data
    if 'import_analysis' in request.session:
        del request.session['import_analysis']
    
    # Success message
    msg_parts = [f'Projekt "{title}" erstellt']
    if created_items['chapters']:
        msg_parts.append(f"{created_items['chapters']} Kapitel")
    if created_items['characters']:
        msg_parts.append(f"{created_items['characters']} Charaktere")
    if created_items['locations']:
        msg_parts.append(f"{created_items['locations']} Locations")
    
    messages.success(request, ' • '.join(msg_parts))
    
    return redirect('writing_hub:project_hub', project_id=project.id)


@login_required
def import_project_cancel(request):
    """Cancel import and clear session data"""
    if 'import_analysis' in request.session:
        del request.session['import_analysis']
    messages.info(request, "Import abgebrochen.")
    return redirect('writing_hub:projects_list')


# =============================================================================
# IMPORT INTO EXISTING PROJECT (Supplement/Merge)
# =============================================================================

@login_required
def import_to_project_start(request, project_id):
    """Start import into existing project - show file upload"""
    
    project = get_object_or_404(BookProjects, pk=project_id)
    
    # Get existing data counts
    existing_chapters = BookChapters.objects.filter(project=project).count()
    existing_characters = Characters.objects.filter(project=project).count()
    existing_worlds = Worlds.objects.filter(project=project).count()
    
    # Find example files
    books_dir = os.path.join(settings.BASE_DIR, 'books')
    example_files = []
    if os.path.exists(books_dir):
        for root, dirs, files in os.walk(books_dir):
            for f in files:
                if f.endswith('.md'):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, settings.BASE_DIR)
                    example_files.append({
                        'name': f,
                        'path': full_path,
                        'rel_path': rel_path,
                        'size': os.path.getsize(full_path),
                    })
    
    context = {
        'project': project,
        'existing_chapters': existing_chapters,
        'existing_characters': existing_characters,
        'existing_worlds': existing_worlds,
        'example_files': example_files[:20],
        'title': f'Import in "{project.title}"',
    }
    return render(request, 'writing_hub/import/import_to_project_start.html', context)


@login_required
@require_http_methods(["POST"])
def import_to_project_analyze(request, project_id):
    """Analyze files for merging into existing project"""
    
    project = get_object_or_404(BookProjects, pk=project_id)
    
    errors = []
    files_to_process = []
    
    # Collect uploaded files
    uploaded_files = request.FILES.getlist('files')
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.md'):
            files_to_process.append({
                'type': 'upload',
                'file': uploaded_file,
                'name': uploaded_file.name,
            })
        else:
            errors.append(f"Übersprungen (kein .md): {uploaded_file.name}")
    
    # Collect server file paths
    file_paths_json = request.POST.get('file_paths', '[]')
    try:
        server_paths = json.loads(file_paths_json)
        for path in server_paths:
            if os.path.exists(path):
                files_to_process.append({
                    'type': 'path',
                    'path': path,
                    'name': os.path.basename(path),
                })
            else:
                errors.append(f"Nicht gefunden: {path}")
    except json.JSONDecodeError:
        pass
    
    if not files_to_process:
        messages.error(request, "Keine gültigen Dateien ausgewählt.")
        return redirect('writing_hub:import_to_project_start', project_id=project_id)
    
    # Get existing items for comparison - include data to check for placeholders
    existing_chapters = {
        ch.title: ch for ch in BookChapters.objects.filter(project=project)
    }
    existing_characters = {
        ch.name: ch for ch in Characters.objects.filter(project=project)
    }
    existing_worlds = {
        w.name: w for w in Worlds.objects.filter(project=project)
    }
    
    # Helper to check if text is placeholder
    def is_placeholder(text):
        if not text:
            return True
        text_lower = text.lower().strip()
        placeholders = ['aus import', 'automatisch', 'importiert', 'ergänzt']
        for p in placeholders:
            if p in text_lower:
                return True
        return len(text.strip()) < 10
    
    # Process files and mark new vs existing
    combined_analysis = {
        'chapters': [],
        'characters': [],
        'locations': [],
        'sources': [],
        'word_count': 0,
        'story_arc': {},
        'subplots': [],
    }
    
    for file_info in files_to_process:
        try:
            if file_info['type'] == 'upload':
                result = BookReengineerService.parse_uploaded_file(file_info['file'])
            else:
                result = BookReengineerService.parse_file_path(file_info['path'])
            
            combined_analysis['word_count'] += result.word_count or 0
            
            # Chapters - mark as new or existing (all existing can be updated)
            for c in result.chapters:
                existing_ch = existing_chapters.get(c.title)
                is_new = existing_ch is None
                can_update = True  # ALL existing items can be updated - parser might have found new data
                combined_analysis['chapters'].append({
                    'number': c.number,
                    'title': c.title,
                    'word_count': c.word_count,
                    'status': c.status,
                    'pov': c.pov,
                    'location': c.location,
                    'beats': c.beats[:5] if c.beats else [],
                    'source_file': file_info['name'],
                    'is_new': is_new,
                    'can_update': can_update,
                })
            
            # Characters - mark as new or existing (all existing can be updated)
            for char in result.characters:
                existing_char = existing_characters.get(char.name)
                is_new = existing_char is None
                # ALL existing items can be updated - parser might have found new data
                can_update = not is_new
                if char.name not in [c['name'] for c in combined_analysis['characters']]:
                    combined_analysis['characters'].append({
                        'name': char.name,
                        'role': char.role if char.role != 'unknown' else '',
                        'age': char.age or '',
                        'background': char.background or '',
                        'motivation': char.motivation or '',
                        'arc': char.arc or '',
                        'traits': char.traits or [],
                        'is_new': is_new,
                        'can_update': can_update,
                        'source_file': file_info['name'],
                    })
            
            # Locations - mark as new or existing (all existing can be updated)
            for loc in result.locations:
                existing_loc = existing_worlds.get(loc.name)
                is_new = existing_loc is None
                # ALL existing items can be updated - parser might have found new data
                can_update = not is_new
                if loc.name not in [l['name'] for l in combined_analysis['locations']]:
                    combined_analysis['locations'].append({
                        'name': loc.name,
                        'description': loc.description or '',
                        'features': loc.features or [],
                        'is_new': is_new,
                        'can_update': can_update,
                        'source_file': file_info['name'],
                    })
            
            # Story arc
            if result.story_arc and result.story_arc.structure_type and not combined_analysis['story_arc']:
                combined_analysis['story_arc'] = {
                    'type': result.story_arc.structure_type,
                    'parts': len(result.story_arc.parts),
                    'twists': len(result.story_arc.twists),
                }
            
            # Subplots
            for s in result.subplots:
                combined_analysis['subplots'].append(s.name)
            
            combined_analysis['sources'].append({
                'filename': file_info['name'],
                'word_count': result.word_count,
                'chapter_count': result.chapter_count,
            })
            
        except Exception as e:
            errors.append(f"Fehler bei {file_info['name']}: {str(e)}")
    
    for error in errors:
        messages.warning(request, error)
    
    if not combined_analysis['sources']:
        messages.error(request, "Keine Datei konnte analysiert werden.")
        return redirect('writing_hub:import_to_project_start', project_id=project_id)
    
    # Store in session
    request.session['import_merge_analysis'] = combined_analysis
    request.session['import_merge_project_id'] = project_id
    
    return redirect('writing_hub:import_to_project_preview', project_id=project_id)


@login_required
def import_to_project_preview(request, project_id):
    """Preview what will be merged into existing project"""
    
    project = get_object_or_404(BookProjects, pk=project_id)
    analysis = request.session.get('import_merge_analysis')
    
    if not analysis:
        messages.error(request, "Keine Analyse-Daten gefunden.")
        return redirect('writing_hub:import_to_project_start', project_id=project_id)
    
    # Categorize items: new, updatable (has placeholder), or unchanged
    new_chapters = [c for c in analysis['chapters'] if c.get('is_new')]
    updatable_chapters = [c for c in analysis['chapters'] if not c.get('is_new') and c.get('can_update')]
    unchanged_chapters = [c for c in analysis['chapters'] if not c.get('is_new') and not c.get('can_update')]
    
    new_characters = [c for c in analysis['characters'] if c.get('is_new')]
    updatable_characters = [c for c in analysis['characters'] if not c.get('is_new') and c.get('can_update')]
    unchanged_characters = [c for c in analysis['characters'] if not c.get('is_new') and not c.get('can_update')]
    
    new_locations = [l for l in analysis['locations'] if l.get('is_new')]
    updatable_locations = [l for l in analysis['locations'] if not l.get('is_new') and l.get('can_update')]
    unchanged_locations = [l for l in analysis['locations'] if not l.get('is_new') and not l.get('can_update')]
    
    # Debug info in messages
    total_parsed = len(analysis['chapters']) + len(analysis['characters']) + len(analysis['locations'])
    total_new = len(new_chapters) + len(new_characters) + len(new_locations)
    total_updatable = len(updatable_chapters) + len(updatable_characters) + len(updatable_locations)
    messages.info(request, f"Analyse: {total_parsed} Items gefunden, {total_new} neu, {total_updatable} aktualisierbar")
    
    context = {
        'project': project,
        'analysis': analysis,
        'new_chapters': new_chapters,
        'updatable_chapters': updatable_chapters,
        'unchanged_chapters': unchanged_chapters,
        'new_characters': new_characters,
        'updatable_characters': updatable_characters,
        'unchanged_characters': unchanged_characters,
        'new_locations': new_locations,
        'updatable_locations': updatable_locations,
        'unchanged_locations': unchanged_locations,
        'title': f'Import-Vorschau: {project.title}',
    }
    return render(request, 'writing_hub/import/import_to_project_preview.html', context)


@login_required
@require_http_methods(["POST"])
def import_to_project_merge(request, project_id):
    """Execute merge - add/update items in existing project using ImportService"""
    
    project = get_object_or_404(BookProjects, pk=project_id)
    analysis = request.session.get('import_merge_analysis')
    
    if not analysis:
        messages.error(request, "Keine Analyse-Daten gefunden.")
        return redirect('writing_hub:import_to_project_start', project_id=project_id)
    
    # Get selected items
    selected_chapter_indices = [int(i) for i in request.POST.getlist('chapters') if i.isdigit()]
    selected_characters = request.POST.getlist('characters')
    selected_locations = request.POST.getlist('locations')
    update_existing = request.POST.get('update_existing') == 'on'
    update_description = request.POST.get('update_description') == 'on'
    
    # Use ImportService for centralized logic
    import_service = ImportService(project)
    
    # Import selected chapters
    for idx in selected_chapter_indices:
        if 0 <= idx < len(analysis.get('chapters', [])):
            import_service.import_chapter(analysis['chapters'][idx])
    
    # Import selected characters (will update placeholders automatically)
    char_data_lookup = {c['name']: c for c in analysis.get('characters', [])}
    for char_name in selected_characters:
        char_data = char_data_lookup.get(char_name, {'name': char_name})
        import_service.import_character(char_data)
    
    # Import selected locations (will update placeholders automatically)
    loc_data_lookup = {l['name']: l for l in analysis.get('locations', [])}
    for loc_name in selected_locations:
        loc_data = loc_data_lookup.get(loc_name, {'name': loc_name})
        import_service.import_location(loc_data)
    
    # Optionally update description with subplots/story arc
    if update_description and analysis.get('subplots'):
        current_desc = project.description or ''
        new_info = f"\n\n--- Import-Ergänzung ---\nSubplots: {', '.join(analysis['subplots'][:5])}"
        if analysis.get('story_arc', {}).get('type'):
            new_info += f"\nStruktur: {analysis['story_arc']['type']}"
        project.description = current_desc + new_info
        project.save()
    
    # Clear session
    if 'import_merge_analysis' in request.session:
        del request.session['import_merge_analysis']
    if 'import_merge_project_id' in request.session:
        del request.session['import_merge_project_id']
    
    # Get stats from ImportService
    stats = import_service.stats
    
    # Success message
    if stats.total_created == 0 and stats.total_updated == 0:
        messages.info(request, "Keine Änderungen vorgenommen.")
    else:
        messages.success(request, f"Import: {stats.summary()}")
    
    return redirect('writing_hub:project_hub', project_id=project.id)
