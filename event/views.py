from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django import forms
import random
import requests
from django.contrib.auth.decorators import login_required
from allauth.account.views import PasswordResetFromKeyView
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden # Added HttpResponseForbidden
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date
import razorpay
import json
from razorpay.errors import SignatureVerificationError

from .models import Event, Genre, CustomUser, Booking
from .forms import EventForm # Already present, just confirming

User = get_user_model()

class MobileLoginForm(forms.Form):
    mobile = forms.CharField(max_length=15)

class OTPVerifyForm(forms.Form):
    otp = forms.CharField(max_length=6)

def send_otp_via_sms(mobile, otp):
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "authorization": "wF7xKYhqlsuOoeBAXzjLMgycmZrVEp0f8d53S1tI6HiT9WJk2n5G3xPruLybqldI0B8wapfE9JZWMKnO",
        "sender_id": "FSTSMS",
        "message": f"Your OTP is {otp}",
        "language": "english",
        "route": "q",
        "numbers": mobile
    }
    headers = {'cache-control': "no-cache"}
    response = requests.post(url, data=payload, headers=headers)
    print(f"[Fast2SMS] Response for {mobile}: {response.text}")

def mobile_login_view(request):
    if request.method == 'POST':
        form = MobileLoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            otp = str(random.randint(100000, 999999))
            request.session['otp'] = otp
            request.session['mobile'] = mobile
            send_otp_via_sms(mobile, otp)
            messages.info(request, f"OTP has been sent to {mobile}")
            return redirect('verify_otp')
    else:
        form = MobileLoginForm()
    return render(request, 'event/mobile_login.html', {'form': form})

def verify_otp_view(request):
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            session_otp = request.session.get('otp')
            mobile = request.session.get('mobile')
            if not session_otp or not mobile:
                messages.error(request, "Session expired. Try again.")
                return redirect('mobile_login')
            if entered_otp == session_otp:
                user, created = CustomUser.objects.get_or_create(mobile=mobile)
                if created:
                    user.set_unusable_password()
                    user.save()
                login(request, user)
                messages.success(request, "Logged in successfully.")
                request.session.pop('otp', None)
                request.session.pop('mobile', None)
                return redirect('event_list')
            else:
                messages.error(request, "Invalid OTP.")
    else:
        form = OTPVerifyForm()
    return render(request, 'event/verify_otp.html', {'form': form})

def event_list(request):
    # Ensure only non-cancelled upcoming events are shown on the main list
    events = Event.objects.filter(date__gte=timezone.localdate(), is_cancelled=False).order_by('date', 'time')

    date_range = request.GET.get('date_range')
    price_range = request.GET.get('price_range')
    location_city = request.GET.get('location_city')
    event_type = request.GET.get('event_type')
    audience = request.GET.get('audience')
    sort_by = request.GET.get('sort_by')

    today = timezone.localdate()

    if date_range:
        if date_range == 'today':
            events = events.filter(date=today)
        elif date_range == 'this_week':
            events = events.filter(date__range=[today, today + timedelta(days=6)])
        elif date_range == 'this_weekend':
            current_day_of_week = today.weekday()
            if current_day_of_week == 5:
                weekend_start = today
                weekend_end = today + timedelta(days=1)
            elif current_day_of_week == 6:
                weekend_start = today
                weekend_end = today
            else:
                days_until_saturday = (5 - current_day_of_week + 7) % 7
                weekend_start = today + timedelta(days=days_until_saturday)
                weekend_end = weekend_start + timedelta(days=1)
            events = events.filter(date__range=[weekend_start, weekend_end])
        elif date_range == 'next_month':
            current_month = today.month
            current_year = today.year
            if current_month == 12:
                next_month_start = date(current_year + 1, 1, 1)
            else:
                next_month_start = date(current_year, current_month + 1, 1)
            if next_month_start.month == 12:
                next_month_end = date(next_month_start.year, next_month_start.month, 31)
            else:
                next_month_end = date(next_month_start.year, next_month_start.month + 1, 1) - timedelta(days=1)
            events = events.filter(date__range=[next_month_start, next_month_end])

    if price_range:
        if price_range == 'free':
            events = events.filter(price__lte=0)
        elif price_range == 'paid':
            events = events.filter(price__gt=0)

    if location_city:
        events = events.filter(location__icontains=location_city)

    if event_type:
        events = events.filter(event_type=event_type)

    if audience:
        events = events.filter(audience_type=audience)

    if sort_by:
        if sort_by == 'event_date_asc':
            events = events.order_by('date', 'time')
        elif sort_by == 'event_date_desc':
            events = events.order_by('-date', '-time')
        elif sort_by == 'popularity':
            events = events.order_by('-bookings_count', '-views_count', 'date')
        elif sort_by == 'price_asc':
            events = events.order_by('price', 'date')
        elif sort_by == 'price_desc':
            events = events.order_by('-price', 'date')
        elif sort_by == 'relevance':
            events = events.order_by('date', 'time')
    else:
        events = events.order_by('date', 'time')

    context = {
        'events': events,
        'selected_date_range': date_range,
        'selected_price_range': price_range,
        'selected_location_city': location_city,
        'selected_event_type': event_type,
        'selected_audience': audience,
        'selected_sort_by': sort_by,
        'genres': Genre.objects.all(),
    }
    return render(request, 'event/event_list.html', context)

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'event/event_detail.html', {'event': event})

def event_search(request):
    query = request.GET.get('q')
    if query:
        # Filter out cancelled events from search results
        events = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(genre__name__icontains=query)
        ).filter(is_cancelled=False).distinct().order_by('date', 'time') # Added is_cancelled=False
    else:
        events = Event.objects.filter(is_cancelled=False).order_by('date', 'time') # Added is_cancelled=False
    return render(request, 'event/event_search.html', {'events': events, 'query': query})

def genre_list_view(request):
    genres = Genre.objects.annotate(count=Count('events'))
    return render(request, 'event/genre_list.html', {'genres': genres})

def events_by_genre(request, slug):
    genre = get_object_or_404(Genre, slug=slug)
    # Filter out cancelled events by genre
    events = Event.objects.filter(genre=genre, is_cancelled=False).order_by('date', 'time') # Added is_cancelled=False
    return render(request, 'event/events_by_genre.html', {'genre': genre, 'events': events})

@login_required
def my_bookings_view(request):
    bookings = Booking.objects.filter(user=request.user).order_by('event__date', 'event__time')
    context = {
        'bookings': bookings
    }
    return render(request, 'event/my_bookings.html', context)

@login_required
def booking_detail_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'event/booking_detail.html', {'booking': booking})

class CustomPasswordResetFromKeyView(PasswordResetFromKeyView):
    template_name = "account/password_reset_from_key.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("token_fail"):
            messages.error(self.request, "The password reset link is invalid or has expired.")
        return context
    def form_valid(self, form):
        messages.success(self.request, "Your password has been set. Redirecting to login...")
        return super().form_valid(form)

def custom_password_reset_done(request):
    messages.success(request, "Check your email for the password reset link.")
    return redirect('event:event_list')  # 👈 use the app namespace


class PasswordResetSuccessView(TemplateView):
    template_name = "account/password_reset_success.html"

@method_decorator(login_required, name='dispatch')
class CreateEventView(LoginRequiredMixin, View):
    login_url = 'account_login'
    redirect_field_name = 'next'

    def get(self, request):
        form = EventForm()
        return render(request, 'event/create_event.html', {'form': form})

    def post(self, request):
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            if not event.organizer_name:
                event.organizer_name = request.user.email # Or user.username if email is not guaranteed
            event.save()
            messages.success(request, f"🎉 Event '{event.title}' created successfully!")
            return redirect('event:event_created_success', pk=event.pk)
        else:
            # --- START OF ADDED DEBUGGING CODE ---
            print("\n--- FORM VALIDATION ERRORS ---")
            print(form.errors)
            print("-----------------------------\n")
            # --- END OF ADDED DEBUGGING CODE ---
            return render(request, 'event/create_event.html', {'form': form})

class EventCreatedSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'event/event_created_success.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = get_object_or_404(Event, pk=self.kwargs['pk'])
        return context

# --- Event Management Views ---

@login_required
def my_events(request):
    """
    Displays a list of events created by the currently logged-in user.
    """
    # Show all events, including cancelled ones, but perhaps distinguish them
    user_events = Event.objects.filter(organizer=request.user).order_by('-date', '-time')
    context = {
        'events': user_events,
        'page_title': 'My Created Events'
    }
    return render(request, 'event/my_events.html', context)

@login_required
def edit_event(request, pk):
    """
    Allows a logged-in user to edit their created event.
    """
    event = get_object_or_404(Event, pk=pk)

    # Security check: Ensure the logged-in user is the organizer of the event
    if event.organizer != request.user:
        messages.error(request, "You are not authorized to edit this event.")
        return redirect('event:my_events') # Redirect to their list of events

    # Prevent editing of cancelled events
    if event.is_cancelled:
        messages.warning(request, "This event has been cancelled and cannot be edited.")
        return redirect('event:event_detail', pk=event.pk) # Redirect to event detail

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event) # Pass request.FILES for image
        if form.is_valid():
            form.save()
            messages.success(request, f"Event '{event.title}' updated successfully!")
            return redirect('event:event_detail', pk=event.pk) # Redirect to the event's detail page
    else:
        form = EventForm(instance=event) # Pre-fill form with existing event data

    context = {
        'form': form,
        'event': event,
        'page_title': f'Edit Event: {event.title}'
    }
    return render(request, 'event/edit_event.html', context)

@login_required
def cancel_event(request, pk):
    """
    Handles the cancellation of an event by its organizer,
    displaying a warning and processing the cancellation.
    """
    event = get_object_or_404(Event, pk=pk)

    # Security check: Ensure only the organizer can cancel their event
    if event.organizer != request.user:
        messages.error(request, "You are not authorized to cancel this event.")
        return redirect('event:my_events')

    # Prevent cancelling events that are already cancelled
    if event.is_cancelled:
        messages.warning(request, "This event is already cancelled.")
        return redirect('event:event_detail', pk=event.pk)

    # You can add more conditions here, e.g., prevent cancellation close to event date
    # Example: If event date is within 24 hours
    if event.date == timezone.localdate() and event.time < timezone.localtime().time():
        messages.error(request, "This event has already started/passed and cannot be cancelled.")
        return redirect('event:my_events')
    elif event.date < timezone.localdate():
         messages.error(request, "This event has already passed and cannot be cancelled.")
         return redirect('event:my_events')
    elif timezone.make_aware(timezone.datetime.combine(event.date, event.time)) < (timezone.now() + timedelta(hours=24)):
        messages.warning(request, "Events cannot be cancelled within 24 hours of their start time.")
        return redirect('event:event_detail', pk=event.pk)

    # Define your cancellation policy/fees here
    cancellation_policy_message = """
    Please be aware of our cancellation policy:
    <ul>
        <li>Events cancelled more than 30 days before the start date: <strong>Full refund (minus 5% processing fee)</strong>.</li>
        <li>Events cancelled between 7 and 30 days before the start date: <strong>50% refund</strong>.</li>
        <li>Events cancelled less than 7 days before the start date: <strong>No refund</strong>.</li>
        <li>Any applicable booking fees or commissions are non-refundable.</li>
    </ul>
    Are you sure you want to proceed?
    """

    if request.method == 'POST':
        # Process cancellation
        event.is_cancelled = True # Mark event as cancelled
        event.save()
        messages.success(request, f"Event '{event.title}' has been successfully cancelled.")
        # TODO: Implement refund logic here if applicable, for all associated bookings
        return redirect('event:my_events')

    context = {
        'page_title': f"Confirm Cancellation of {event.title}",
        'event': event,
        'cancellation_policy': cancellation_policy_message,
    }
    return render(request, 'event/cancel_event_confirm.html', context)

# --- End Event Management Views ---

@login_required
def book_event_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Prevent booking cancelled events
    if event.is_cancelled:
        messages.error(request, "This event has been cancelled and cannot be booked.")
        return redirect('event:event_detail', pk=event.id)

    if not event.is_upcoming:
        messages.error(request, "Cannot book tickets for an event that has already passed.")
        return redirect('event:event_detail', pk=event.id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))

        if quantity <= 0:
            messages.error(request, "Quantity must be a positive number.")
            return redirect('event:book_event', event_id=event.id)

        if event.tickets_remaining < quantity:
            messages.error(request, f"Not enough tickets available. Only {event.tickets_remaining} tickets remaining.")
            return redirect('event:book_event', event_id=event.id)

        total_price = (event.price * quantity).quantize(Decimal('0.01'))

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_amount_paisa = int(total_price * 100)
        receipt_id = f"booking_receipt_{request.user.id}_{event.id}_{timezone.now().timestamp()}"

        order_data = {
            "amount": razorpay_amount_paisa,
            "currency": settings.RAZORPAY_CURRENCY,
            "receipt": receipt_id,
            "notes": {
                "user_id": str(request.user.id),
                "event_id": str(event.id),
                "quantity": str(quantity),
                "total_price": str(total_price),
            }
        }

        try:
            razorpay_order = client.order.create(order_data)

            request.session['booking_confirm_data'] = {
                'event_id': event.id,
                'quantity': quantity,
                'total_price': str(total_price),
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_order_amount_paisa': razorpay_amount_paisa,
                'razorpay_currency': settings.RAZORPAY_CURRENCY,
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'user_email': request.user.email if request.user.email else '',
                'user_mobile': request.user.mobile if hasattr(request.user, 'mobile') and request.user.mobile else '',
            }
            messages.info(request, "Please confirm your booking details.")
            return redirect('event:confirm_booking')

        except Exception as e:
            messages.error(request, f"Error creating Razorpay order: {e}")
            return redirect('event:book_event', event_id=event.id)
    else:
        context = {
            'event': event,
        }
        return render(request, 'event/book_event.html', context)


@login_required
def confirm_booking_view(request):
    booking_data = request.session.get('booking_confirm_data')

    if not booking_data:
        messages.error(request, "No booking details found. Please try again.")
        return redirect('event:event_list')

    event = get_object_or_404(Event, id=booking_data['event_id'])

    # Re-check if event is cancelled before confirmation
    if event.is_cancelled:
        messages.error(request, "This event has been cancelled and cannot be booked.")
        del request.session['booking_confirm_data'] # Clear session data
        return redirect('event:event_detail', pk=event.id)

    context = {
        'event': event,
        'quantity': booking_data['quantity'],
        'total_price': Decimal(booking_data['total_price']),
        'razorpay_order_id': booking_data['razorpay_order_id'],
        'razorpay_order_amount_paisa': booking_data['razorpay_order_amount_paisa'],
        'razorpay_currency': booking_data['razorpay_currency'],
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'user_email': booking_data['user_email'],
        'user_mobile': booking_data['user_mobile'],
    }
    return render(request, 'event/confirm_booking.html', context)


@login_required
@csrf_exempt
def confirm_payment_view(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')

            if not all([payment_id, order_id, signature]):
                messages.error(request, "Payment confirmation failed: Missing parameters.")
                print(f"❌ Confirm Payment: Missing params. P:{payment_id}, O:{order_id}, S:{signature}")
                return redirect('event:event_list')

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)

            order_info = client.order.fetch(order_id)
            notes = order_info.get('notes', {})

            user_id = int(notes.get('user_id'))
            event_id = int(notes.get('event_id'))
            quantity = int(notes.get('quantity'))
            total_price_from_notes = Decimal(notes.get('total_price')).quantize(Decimal('0.01'))

            user = get_object_or_404(User, id=user_id)
            event = get_object_or_404(Event, id=event_id)

            # Crucial re-check: Do not allow booking if event has been cancelled *after* order creation
            if event.is_cancelled:
                messages.error(request, f"Booking failed: Event '{event.title}' was cancelled.")
                # TODO: Initiate refund for the Razorpay payment here
                print(f"❌ Confirm Payment: Attempted to book cancelled event {event.id}. Initiating refund (mock).")
                return redirect('event:event_list')


            with transaction.atomic():
                existing_booking = Booking.objects.filter(payment_id=payment_id).first()
                if existing_booking:
                    messages.info(request, "This booking has already been processed!")
                    print(f"✅ Confirm Payment: Duplicate booking for payment {payment_id}. Redirecting to existing.")
                    return redirect('event:booking_detail', booking_id=existing_booking.id)

                booking = Booking.objects.create(
                    user=user,
                    event=event,
                    quantity=quantity,
                    total_price=total_price_from_notes,
                    payment_id=payment_id,
                    razorpay_order_id=order_id,
                    is_paid=True
                )

                request.session['last_booking_id'] = booking.id

                messages.success(request, f"Booking confirmed! You've booked {quantity} tickets for '{event.title}'.")
                print(f"✅ Confirm Payment: Booking {booking.id} created for event {event.title}.")
                return redirect('event:booking_success')

        except SignatureVerificationError as e:
            messages.error(request, f"Payment signature verification failed. Please try again or contact support.")
            print(f"❌ Confirm Payment: Signature Error: {e}")
            return redirect('event:event_list')
        except Exception as e:
            messages.error(request, f"An error occurred during payment confirmation: {e}. Please contact support.")
            print(f"❌ Confirm Payment: General Error: {e}")
            return redirect('event:event_list')
    else:
        messages.error(request, "Invalid request method for payment confirmation.")
        return redirect('event:event_list')

@login_required
def booking_success_view(request):
    booking_id = request.session.get('last_booking_id')

    if not booking_id:
        messages.warning(request, "No recent booking found. Showing your existing bookings.")
        return redirect('event:my_bookings')

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    request.session.pop('last_booking_id', None)

    return render(request, 'event/booking_success.html', {'booking': booking})

@csrf_exempt
def razorpay_webhook(request):
    if request.method == 'POST':
        try:
            payload = request.body.decode('utf-8')
            signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')

            if not hasattr(settings, 'RAZORPAY_WEBHOOK_SECRET') or not settings.RAZORPAY_WEBHOOK_SECRET:
                print("❌ Webhook Error: RAZORPAY_WEBHOOK_SECRET is not configured in settings. Please set it.")
                return JsonResponse({'status': 'error', 'message': 'Webhook secret not configured'}, status=500)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_webhook_signature(payload, signature, settings.RAZORPAY_WEBHOOK_SECRET)

            data = json.loads(payload)
            event_type = data.get('event')

            if event_type == 'payment.captured':
                payment_entity = data['payload']['payment']['entity']
                payment_id = payment_entity['id']
                order_id = payment_entity['order_id']

                print(f"✅ POST Webhook received: Payment {payment_id} for Order {order_id} captured.")

                with transaction.atomic():
                    existing_booking = Booking.objects.filter(payment_id=payment_id).first()

                    if existing_booking:
                        if not existing_booking.is_paid:
                            existing_booking.is_paid = True
                            existing_booking.save()
                            print(f"✅ POST Webhook: Existing booking {existing_booking.id} marked as paid.")
                        else:
                            print(f"✅ POST Webhook: Booking {existing_booking.id} already exists and is paid. Ignoring duplicate.")
                        return JsonResponse({'status': 'success', 'message': 'Booking processed or updated.'})
                    else:
                        try:
                            order_info = client.order.fetch(order_id)
                            notes = order_info.get('notes', {})

                            user_id = int(notes.get('user_id'))
                            event_id = int(notes.get('event_id'))
                            quantity = int(notes.get('quantity'))
                            total_price_from_notes = Decimal(notes.get('total_price')).quantize(Decimal('0.01'))

                            user = get_object_or_404(User, id=user_id)
                            event = get_object_or_404(Event, id=event_id)

                            # Crucial re-check: Do not create booking via webhook if event has been cancelled
                            if event.is_cancelled:
                                print(f"❌ POST Webhook: Attempted to create booking for cancelled event {event.id}. Initiating refund (mock).")
                                # TODO: Initiate refund for the Razorpay payment here if not already done
                                return JsonResponse({'status': 'error', 'message': 'Event cancelled, not creating booking.'}, status=200)

                            booking = Booking.objects.create(
                                user=user,
                                event=event,
                                quantity=quantity,
                                total_price=total_price_from_notes,
                                payment_id=payment_id,
                                razorpay_order_id=order_id,
                                is_paid=True
                            )
                            print(f"✅ POST Webhook: New booking {booking.id} created as primary for order {order_id}.")
                            return JsonResponse({'status': 'success', 'message': 'Booking created via webhook.'})

                        except Exception as e:
                            print(f"❌ POST Webhook: Error creating booking for order {order_id}: {e}")
                            return JsonResponse({'status': 'error', 'message': 'Failed to create booking via webhook, check logs.'}, status=200)

            print(f"ℹ️ POST Webhook: Event type '{event_type}' received but not specifically handled.")
            return JsonResponse({'status': 'ignored', 'message': f'Event type {event_type} not explicitly handled.'})

        except SignatureVerificationError as e:
            print("❌ Razorpay Webhook Signature verification failed:", e)
            return JsonResponse({'status': 'error', 'message': 'Signature verification failed'}, status=400)
        except json.JSONDecodeError:
            print("❌ Webhook: Invalid JSON payload.")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            print(f"❌ Webhook: Unexpected error in POST webhook processing: {e}")
            return JsonResponse({'status': 'error', 'message': f'Unexpected error: {e}'}, status=500)
    else:
        print(f"❌ Webhook: Method {request.method} not allowed for Razorpay webhook.")
        return JsonResponse({'status': 'error', 'message': 'Method not allowed for webhook'}, status=405)
    
def help_page_view(request):
    return render(request, 'help.html')

def terms_and_conditions_view(request):
    # You will need to create 'terms_and_conditions.html' in your templates folder
    return render(request, 'terms_and_conditions.html', {})

def privacy_policy_view(request):
    # You will need to create 'privacy_policy.html' in your templates folder
    return render(request, 'privacy_policy.html', {})

def refund_policy_view(request):
    # You will need to create 'refund_policy.html' in your templates folder
    return render(request, 'refund_policy.html', {})