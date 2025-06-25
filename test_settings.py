"""
Django settings for testing.
"""

from do_classroom.settings import *

# Test database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable migrations for faster testing
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Simplify password validation for testing
AUTH_PASSWORD_VALIDATORS = []

# Use faster password hasher for testing
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable debug toolbar and browser reload in tests
DEBUG = False
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in [
    "debug_toolbar",
    "django_browser_reload", 
    "silk",
]]

# Remove debug middleware
MIDDLEWARE = [mw for mw in MIDDLEWARE if not any([
    "debug_toolbar" in mw,
    "browser_reload" in mw,
    "silk" in mw,
])]

# Mock DigitalOcean token for tests
DO_TOKEN = "test_token_for_testing"

# Skip email verification in tests
ACCOUNT_EMAIL_VERIFICATION = "none"