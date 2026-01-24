import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.presentation_studio.models import DesignProfile

templates = [
    {
        'profile_name': 'Corporate Blue',
        'colors': {
            'primary': '#1F4E78',
            'secondary': '#5B9BD5',
            'accent1': '#E74C3C',
            'accent2': '#27AE60',
            'text': '#2C3E50',
            'background': '#FFFFFF',
            'light_bg': '#F5F5F5',
        },
        'fonts': {
            'heading': 'Calibri Bold',
            'body': 'Calibri',
            'caption': 'Calibri Light',
        }
    },
    {
        'profile_name': 'Academic Style',
        'colors': {
            'primary': '#2C3E50',
            'secondary': '#3498DB',
            'accent1': '#27AE60',
            'accent2': '#F39C12',
            'text': '#333333',
            'background': '#FAFAFA',
            'light_bg': '#F9F9F9',
        },
        'fonts': {
            'heading': 'Times New Roman',
            'body': 'Georgia',
            'caption': 'Georgia Italic',
        }
    },
    {
        'profile_name': 'Modern Minimal',
        'colors': {
            'primary': '#E74C3C',
            'secondary': '#9B59B6',
            'accent1': '#F39C12',
            'accent2': '#1ABC9C',
            'text': '#2C3E50',
            'background': '#FFFFFF',
            'light_bg': '#FAFAFA',
        },
        'fonts': {
            'heading': 'Montserrat Bold',
            'body': 'Open Sans',
            'caption': 'Open Sans Light',
        }
    },
]

created_count = 0
for template_data in templates:
    profile, created = DesignProfile.objects.get_or_create(
        profile_name=template_data['profile_name'],
        is_system_template=True,
        defaults={
            'source_type': 'template',
            'colors': template_data['colors'],
            'fonts': template_data['fonts'],
            'is_active': True,
        }
    )
    
    if created:
        created_count += 1
        print(f'✓ Created template: {profile.profile_name}')
    else:
        print(f'- Template already exists: {profile.profile_name}')

print(f'\n✅ Total: {created_count} new templates, {len(templates) - created_count} existing')
print(f'📊 Database now has {DesignProfile.objects.count()} design profiles total')
