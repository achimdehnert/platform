"""
Trip Forms - Multi-Step Wizard Forms
"""

from django import forms
from django.forms import inlineformset_factory

from .models import Trip, Stop, Transport


class TripBasicsForm(forms.ModelForm):
    """Step 1: Basic trip information."""
    
    class Meta:
        model = Trip
        fields = ['name', 'origin', 'start_date', 'end_date', 'trip_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'z.B. Italienreise 2025',
            }),
            'origin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'z.B. München',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'trip_type': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        
        if start and end and start > end:
            raise forms.ValidationError('Das Enddatum muss nach dem Startdatum liegen.')
        
        return cleaned_data


class StopForm(forms.ModelForm):
    """Form for a single stop."""
    
    class Meta:
        model = Stop
        fields = [
            'city', 'country', 'arrival_date', 'departure_date',
            'accommodation_type', 'notes'
        ]
        widgets = {
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Stadt',
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Land',
            }),
            'arrival_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'departure_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'accommodation_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notizen zum Aufenthalt...',
            }),
        }


class TransportForm(forms.ModelForm):
    """Form for transport between stops."""
    
    class Meta:
        model = Transport
        fields = ['transport_type', 'duration_minutes', 'departure_datetime']
        widgets = {
            'transport_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reisezeit in Minuten',
            }),
            'departure_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
        }


# Inline formsets for stops
StopFormSet = inlineformset_factory(
    Trip, Stop,
    form=StopForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class StoryPreferencesForm(forms.Form):
    """Step 3: Story preferences."""
    
    GENRE_CHOICES = [
        ('romance', 'Romance'),
        ('romantic_suspense', 'Romantic Suspense'),
        ('thriller', 'Thriller'),
        ('mystery', 'Mystery'),
        ('fantasy', 'Urban Fantasy'),
        ('adventure', 'Adventure'),
    ]
    
    SPICE_CHOICES = [
        ('sweet', 'Sweet (nur Händchen halten)'),
        ('mild', 'Mild (Küsse, aber Türen schließen)'),
        ('medium', 'Medium (Sinnlich, nicht explizit)'),
        ('spicy', 'Spicy (Explizitere Szenen)'),
    ]
    
    ENDING_CHOICES = [
        ('happy', 'Happy End'),
        ('hopeful', 'Hopeful End'),
        ('open', 'Offenes Ende'),
        ('bittersweet', 'Bittersüß'),
    ]
    
    GENDER_CHOICES = [
        ('female', 'Weiblich'),
        ('male', 'Männlich'),
        ('non_binary', 'Non-Binary'),
    ]
    
    genre = forms.ChoiceField(
        choices=GENRE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='romance',
    )
    
    spice_level = forms.ChoiceField(
        choices=SPICE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='mild',
    )
    
    ending_type = forms.ChoiceField(
        choices=ENDING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='happy',
    )
    
    protagonist_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Name der Protagonistin',
        }),
    )
    
    protagonist_gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='female',
    )
    
    triggers_avoid = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Themen die vermieden werden sollen (kommasepariert)',
        }),
        help_text='z.B. Spinnen, Höhen, Verlust eines Elternteils',
    )
    
    user_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Weitere Wünsche oder Hinweise für die Geschichte...',
        }),
    )
