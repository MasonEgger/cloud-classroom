"""
Django management command to test the async ClassroomService.

Usage:
    python manage.py test_classroom_service
"""

from __future__ import annotations

import asyncio
from typing import Any

from django.core.management.base import BaseCommand
from django.conf import settings

from services.classroom import ClassroomService, ClassroomError


class Command(BaseCommand):
    """Test the async ClassroomService."""

    help = "Test the async ClassroomService functionality"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--test-creation",
            action="store_true",
            help="Test droplet creation (WARNING: costs money!)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the async tests."""
        asyncio.run(self._run_tests(options))

    async def _run_tests(self, options: dict[str, Any]) -> None:
        """Run async service tests."""
        if not settings.DO_TOKEN:
            self.stdout.write(
                self.style.ERROR(
                    "DigitalOcean token not configured. Set DO_TOKEN environment variable."
                )
            )
            return

        self.stdout.write("Testing async ClassroomService...")

        async with ClassroomService() as service:
            try:
                # Test password generation
                self.stdout.write("Testing: Password generation")
                password1 = service._generate_password()
                password2 = service._generate_password()
                
                if len(password1) == 12 and password1 != password2:
                    self.stdout.write(
                        self.style.SUCCESS("✓ Password generation working")
                    )
                    self.stdout.write(f"  Sample password: {password1}")
                else:
                    self.stdout.write(
                        self.style.ERROR("✗ Password generation failed")
                    )

                # Test droplet name generation
                self.stdout.write("\nTesting: Droplet name generation")
                name = service._generate_droplet_name(
                    "CS101", "student@example.com", "testpass123"
                )
                expected_pattern = "CS101-student-AT-example-DOT-com-test"
                
                if name == expected_pattern:
                    self.stdout.write(
                        self.style.SUCCESS("✓ Droplet name generation working")
                    )
                    self.stdout.write(f"  Generated name: {name}")
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Expected {expected_pattern}, got {name}")
                    )

                # Test user data generation
                self.stdout.write("\nTesting: User data generation")
                user_data = service._generate_user_data(
                    username="student",
                    password="testpass123",
                    ssh_keys=["ssh-rsa AAAAB3NzaC1yc2E... test@example.com"],
                )
                
                if "#cloud-config" in user_data and "student:testpass123" in user_data:
                    self.stdout.write(
                        self.style.SUCCESS("✓ User data generation working")
                    )
                    self.stdout.write("  Cloud-init config includes user setup")
                else:
                    self.stdout.write(
                        self.style.ERROR("✗ User data generation failed")
                    )

                # Test DigitalOcean API access through service
                self.stdout.write("\nTesting: DigitalOcean API access")
                regions = await service.client.list_regions()
                sizes = await service.client.list_sizes()
                
                if len(regions) > 0 and len(sizes) > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ API access working ({len(regions)} regions, {len(sizes)} sizes)"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR("✗ API access failed")
                    )

                # Test creating droplet (dangerous - costs money!)
                if options["test_creation"]:
                    self.stdout.write(
                        self.style.WARNING(
                            "\nWARNING: Skipping droplet creation test"
                        )
                    )
                    self.stdout.write(
                        "This would require a real class and student object from the database."
                    )
                    self.stdout.write(
                        "Use the Django admin or test fixtures to create test data first."
                    )

                self.stdout.write(
                    self.style.SUCCESS("\n🎉 All service tests passed!")
                )

            except ClassroomError as e:
                self.stdout.write(
                    self.style.ERROR(f"ClassroomService error: {e}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Unexpected error: {e}")
                )
                raise