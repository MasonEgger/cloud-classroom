"""
Utility functions for using async services in Django views.

Provides helpers to bridge async services with Django's sync views
until we fully migrate to async views.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, TypeVar

from django.http import JsonResponse

T = TypeVar("T")


def run_async_in_sync(coro: Awaitable[T]) -> T:
    """
    Run an async coroutine in a sync context.
    
    This is a helper for using async services in sync Django views.
    For new views, prefer using async views directly.
    
    Args:
        coro: The async coroutine to run
        
    Returns:
        The result of the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, use sync_to_async
            return asyncio.create_task(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create a new one
        return asyncio.run(coro)


async def json_response_async(data: dict[str, Any], status: int = 200) -> JsonResponse:
    """Create a JsonResponse asynchronously."""
    return JsonResponse(data, status=status)


def handle_service_error(error: Exception) -> JsonResponse:
    """
    Handle service errors and return appropriate JSON response.
    
    Args:
        error: The service error
        
    Returns:
        JsonResponse with error details
    """
    from services.classroom import ClassroomError
    from services.digitalocean import DOError

    if isinstance(error, DOError):
        return JsonResponse(
            {
                "error": "DigitalOcean API Error",
                "message": error.message,
                "status_code": error.status_code,
            },
            status=error.status_code or 500,
        )
    elif isinstance(error, ClassroomError):
        return JsonResponse(
            {
                "error": "Classroom Service Error",
                "message": str(error),
            },
            status=400,
        )
    else:
        return JsonResponse(
            {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            },
            status=500,
        )


class AsyncServiceMixin:
    """
    Mixin for Django views that need to use async services.
    
    Provides common patterns for handling async operations in views.
    """

    def run_async(self, coro: Awaitable[T]) -> T:
        """Run an async coroutine from a sync view method."""
        return run_async_in_sync(coro)

    def handle_service_exception(self, error: Exception) -> JsonResponse:
        """Handle service exceptions and return appropriate response."""
        return handle_service_error(error)
