# EventHub

A Django-based event management platform where users can browse, create, and book events. Includes Google login (django-allauth), email-based OTP mobile login, and Razorpay payment integration.

## Features
- Browse events with filters (date, price, city, audience) and sorting
- Create, edit, and cancel your own events
- Book events with Razorpay payment integration
- Google OAuth login + email/password login (django-allauth)
- Mobile login via OTP
- Genre-based browsing

## Tech Stack
- Python / Django
- SQLite (default dev database)
- django-allauth (authentication)
- Razorpay (payments)
- Bootstrap 5 (frontend)

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/PreetamSalunke/EventHub.git
cd EventHub
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create a `.env` file
Create a file named `.env` in the project root (same folder as `manage.py`) with the following variables:

```
DJANGO_SECRET_KEY=your-django-secret-key
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-app-password
RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret
```

> Note: You'll need your own Google OAuth credentials, Gmail app password, and Razorpay test keys to run all features. Core browsing/event features will still work with a dummy `DJANGO_SECRET_KEY` even without the other keys configured.

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Run the development server
```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** in your browser.

## Notes
- Default database is SQLite (`db.sqlite3`), created automatically on first migration — it will be empty, so you may need to add events via the admin panel or create-event form.
- To access the Django admin panel, create a superuser first:
  ```bash
  python manage.py createsuperuser
  ```
  Then visit `http://127.0.0.1:8000/admin/`.
