from django.db import models, transaction
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F

class CustomUserManager(BaseUserManager):
    def create_user(self, email, mobile=None, password=None, **extra_fields):
        if not email and not mobile:
            raise ValueError('The Email or Mobile field must be set')
        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, mobile=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, mobile, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email or self.mobile or f"User {self.id}"

    @property
    def username(self):
        return self.email or self.mobile or f"user_{self.id}"

from django.db import models

class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.ImageField(upload_to='genre_icons/', blank=True, null=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    total_tickets = models.IntegerField(default=0, verbose_name="Total Tickets")
    tickets_sold = models.IntegerField(default=0, verbose_name="Tickets Sold")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_events')

    max_participants = models.IntegerField(default=0, verbose_name="Max Participants")
    organizer_name = models.CharField(max_length=255, verbose_name="Organizer Name", blank=True, null=True)
    image_url = models.URLField(max_length=200, blank=True, null=True, verbose_name="Image URL")

    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name='events', verbose_name="Genre")
    image = models.ImageField(upload_to='event_images/', blank=True, null=True, verbose_name="Image")
    is_cancelled = models.BooleanField(default=False)

    AUDIENCE_CHOICES = [
        ('general', 'General Public'),
        ('students', 'Students'),
        ('members', 'Members Only'),
    ]
    audience_type = models.CharField(max_length=50, choices=AUDIENCE_CHOICES, default='general', verbose_name="Audience Type")

    EVENT_TYPE_CHOICES = [
        ('conference', 'Conference'),
        ('concert', 'Concert'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('other', 'Other'),
    ]
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, default='other', verbose_name="Event Type")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return self.title

    @property
    def is_upcoming(self):
        return self.date >= timezone.localdate()

    @property
    def tickets_remaining(self):
        return self.total_tickets - self.tickets_sold

    @property
    def is_fully_booked(self):
        return self.tickets_remaining <= 0

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    payment_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'event', 'payment_id')

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({'quantity': "Quantity must be a positive number."})

        if not self.event.is_upcoming:
            raise ValidationError("Cannot book tickets for an event that has already passed.")

        if self._state.adding:
            if self.event.tickets_remaining < self.quantity:
                raise ValidationError({'quantity': f"Not enough tickets available. Only {self.event.tickets_remaining} tickets remaining for '{self.event.title}'."})

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new_booking = self._state.adding

        with transaction.atomic():
            if is_new_booking and self.is_paid:
                Event.objects.filter(pk=self.event.pk).update(tickets_sold=F('tickets_sold') + self.quantity)

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} for {self.event.title} by {self.user.username} ({'Paid' if self.is_paid else 'Unpaid'})"