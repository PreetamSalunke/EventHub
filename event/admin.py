# your_app_name/admin.py
from django.contrib import admin
from .models import Event, Genre, CustomUser, Booking # <--- ADD THIS LINE to import your models

# Register your models here.
admin.site.register(Event)
admin.site.register(Genre)
admin.site.register(CustomUser)
admin.site.register(Booking)