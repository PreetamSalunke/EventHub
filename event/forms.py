from django import forms
from .models import Event, Genre
from allauth.account.forms import SignupForm
from django.utils import timezone

class MobileLoginForm(forms.Form):
    mobile = forms.CharField(max_length=15,
                             widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-danger'}))

class OTPVerifyForm(forms.Form):
    otp = forms.CharField(max_length=6,
                          widget=forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-danger'}))

class EventForm(forms.ModelForm):
    # Widgets for better HTML5 input types and styling
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control-dark'}),
        help_text='Format: YYYY-MM-DD'
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control-dark'}),
        help_text='Format: HH:MM (24-hour)'
    )
    title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control-dark', 'placeholder': 'Event Title'}),
        max_length=200
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control-dark', 'rows': 4, 'placeholder': 'Detailed description of the event'}),
        required=False # Make optional if empty descriptions are allowed
    )
    location = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control-dark', 'placeholder': 'Venue, City, or Online Link'}),
        max_length=255
    )
    total_tickets = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control-dark', 'min': 0}),
        label="Total Available Tickets"
    )
    price = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control-dark', 'step': '0.01', 'min': '0.00'}),
        max_digits=10,
        decimal_places=2,
        label="Ticket Price"
    )
    max_participants = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control-dark', 'min': 0}),
        label="Maximum Participants",
        required=False # Can be optional if total_tickets covers this
    )
    organizer_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control-dark', 'placeholder': 'Name of the Organizer/Host'}),
        max_length=255,
        required=False
    )
    image_url = forms.URLField(
        widget=forms.URLInput(attrs={'class': 'form-control-dark', 'placeholder': 'Optional image URL (e.g., from Unsplash)'}),
        required=False,
        max_length=200
    )
    image = forms.ImageField( # For file upload
        widget=forms.FileInput(attrs={'class': 'form-control-dark'}),
        required=False,
        help_text="Upload an event image (overrides image URL if both are provided)."
    )
    genre = forms.ModelChoiceField(
        queryset=Genre.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select-dark'}),
        empty_label="Select a Genre",
        required=False # Or True, depending on your business logic
    )
    audience_type = forms.ChoiceField(
        choices=Event.AUDIENCE_CHOICES, # Use the choices from the model
        widget=forms.Select(attrs={'class': 'form-select-dark'}),
        label="Audience Type"
    )
    event_type = forms.ChoiceField(
        choices=Event.EVENT_TYPE_CHOICES, # Use the choices from the model
        widget=forms.Select(attrs={'class': 'form-select-dark'}),
        label="Event Type"
    )
    is_published = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        label="Publish Event (make it visible to others)"
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'date', 'time', 'location',
            'total_tickets', 'price', 'max_participants', 'organizer_name',
            'image_url', 'image', 'genre', 'audience_type', 'event_type',
            'is_published'
        ]


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields.pop('username', None)

        for field_name, field in self.fields.items():
            if hasattr(field, 'widget'):
                current_attrs = field.widget.attrs
                if 'class' in current_attrs:
                    if 'form-control' not in current_attrs['class']:
                        current_attrs['class'] += ' form-control bg-dark text-white border-danger'
                else:
                    current_attrs['class'] = 'form-control bg-dark text-white border-danger'
                field.widget.attrs.update(current_attrs)