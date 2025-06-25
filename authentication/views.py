from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


# TODO: Implement HTMX authentication views
@login_required
def check(request):
    """Check if user is authenticated."""
    return JsonResponse({"message": "authenticated"})
