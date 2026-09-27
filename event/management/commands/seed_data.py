# event/management/commands/seed_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from event.models import Genre, Event, CustomUser # Ensure CustomUser, Event, Genre are imported correctly

class Command(BaseCommand):
    help = 'Seeds the database with initial Genre and Event data.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Starting database seeding..."))

        # --- 1. Get or Create an Organizer User ---
        # We'll use the first superuser found, or create a dummy one if none exists.
        try:
            organizer_user = CustomUser.objects.filter(is_superuser=True).first()
            if not organizer_user:
                # Create a basic superuser if none exists, for the purpose of seeding
                self.stdout.write(self.style.WARNING("No superuser found. Creating a dummy organizer user..."))
                organizer_user = CustomUser.objects.create_superuser(
                    email='organizer@example.com',
                    password='password123',
                    mobile='1234567890' # Optional, based on your CustomUser definition
                )
                self.stdout.write(self.style.SUCCESS(f"Created new organizer user: {organizer_user.email}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Using existing organizer user: {organizer_user.email}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error getting/creating organizer user: {e}"))
            return # Exit if we can't get an organizer

        # --- 2. Define and Create Genres ---
        genres_to_create = [
            {'name': 'Music', 'slug': 'music', 'icon': 'fa-music'},
            {'name': 'Technology', 'slug': 'technology', 'icon': 'fa-laptop-code'},
            {'name': 'Arts & Culture', 'slug': 'arts-culture', 'icon': 'fa-palette'},
            {'name': 'Sports', 'slug': 'sports', 'icon': 'fa-futbol'},
            {'name': 'Food & Drink', 'slug': 'food-drink', 'icon': 'fa-utensils'},
            {'name': 'Education', 'slug': 'education', 'icon': 'fa-graduation-cap'},
        ]

        created_genres = []
        for g_data in genres_to_create:
            genre, created = Genre.objects.get_or_create(
                slug=g_data['slug'],
                defaults={'name': g_data['name'], 'icon': g_data['icon']}
            )
            created_genres.append(genre)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Genre: {genre.name}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Genre already exists: {genre.name}"))

        # --- 3. Create Events for Each Genre ---
        self.stdout.write(self.style.NOTICE("Creating events (3 per genre)..."))

        # Get choices for audience_type and event_type from the Event model
        audience_types = [choice[0] for choice in Event.AUDIENCE_CHOICES]
        event_types = [choice[0] for choice in Event.EVENT_TYPE_CHOICES]

        for genre in created_genres:
            for i in range(1, 4): # Create 3 events for each genre
                event_date = timezone.localdate() + timedelta(days=random.randint(15, 365)) # Event in future
                event_time = timezone.datetime(2000, 1, 1, random.randint(9, 20), random.choice([0, 30])).time()
                total_tickets = random.randint(100, 1000)
                price = round(random.uniform(50.00, 500.00), 2)

                event_title = f"{genre.name} Fest: Day {i}" if i == 1 else f"{genre.name} Summit {i}"
                event_description = (
                    f"Join us for an exciting {genre.name.lower()} event! "
                    f"This is event number {i} in the series."
                )
                event_location = f"Hall {random.randint(1, 10)}, City Plaza, Randomville"

                Event.objects.create(
                    title=event_title,
                    description=event_description,
                    date=event_date,
                    time=event_time,
                    location=event_location,
                    total_tickets=total_tickets,
                    tickets_sold=0, # Start with no tickets sold
                    price=price,
                    organizer=organizer_user,
                    genre=genre,
                    image=None, # You can specify a path here if you have dummy images set up
                    audience_type=random.choice(audience_types),
                    event_type=random.choice(event_types),
                    is_published=True, # Make them visible
                )
                self.stdout.write(self.style.SUCCESS(f"  - Created Event: '{event_title}' for {genre.name}"))

        self.stdout.write(self.style.SUCCESS("\nDatabase seeding completed successfully!"))