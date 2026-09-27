from django.urls import path
from . import views
from .views import (
    CustomPasswordResetFromKeyView,
    CreateEventView,
    EventCreatedSuccessView,
    booking_success_view,
    PasswordResetSuccessView,
    book_event_view,
    confirm_payment_view,
    confirm_booking_view,
    razorpay_webhook,
    my_events, # Ensure my_events is imported
    edit_event, # Ensure edit_event is imported
    cancel_event, # NEW: Import cancel_event
)
from django.conf import settings

app_name = 'event'

urlpatterns = [
    path('', views.event_list, name='event_list'),

    path('browse-genres/', views.genre_list_view, name='browse_genres'),

    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('search/', views.event_search, name='event_search'),
    path('genres/', views.genre_list_view, name='genre_list'), # You can keep this or remove if 'browse_genres' is sufficient
    path('genres/<slug:slug>/', views.events_by_genre, name='events_by_genre'),

    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('mobile-login/', views.mobile_login_view, name='mobile_login'),

    path('accounts/password/reset/done/', views.custom_password_reset_done, name='account_reset_password_done'),
    path('accounts/password/reset/key/done/', PasswordResetSuccessView.as_view(), name='password_reset_success'),
    path(
    'accounts/password/reset/key/<uid>/<token>/',
    CustomPasswordResetFromKeyView.as_view(),
    name='account_reset_password_from_key',
),

    # --- New/Updated Event Management Paths ---
    path('my-events/', my_events, name='my_events'), # Corrected to use imported view
    path('event/<int:pk>/edit/', edit_event, name='edit_event'), # Corrected to use imported view
    path('event/<int:pk>/cancel/', cancel_event, name='cancel_event'), # NEW: Cancel Event URL
    path('create/', CreateEventView.as_view(), name='create_event'),
    path('event/success/<int:pk>/', EventCreatedSuccessView.as_view(), name='event_created_success'),
    # --- End New/Updated Event Management Paths ---

    path('events/<int:event_id>/book/', book_event_view, name='book_event'),
    path('confirm-payment/', confirm_payment_view, name='confirm_payment'),
    path('confirm_booking/', confirm_booking_view, name='confirm_booking'),
    path('booking-success/', booking_success_view, name='booking_success'),
    path('razorpay-webhook/', razorpay_webhook, name='razorpay_webhook'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('booking/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('help/', views.help_page_view, name='help_page'),
    path('terms-and-conditions/', views.terms_and_conditions_view, name='terms_and_conditions'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('refund-policy/', views.refund_policy_view, name='refund_policy'),
]