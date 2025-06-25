"""
Django management command to test the new async DigitalOcean API client.

Usage:
    python manage.py test_do_api
"""

from __future__ import annotations

import asyncio
from typing import Any

from django.core.management.base import BaseCommand
from django.conf import settings

from services.digitalocean import DigitalOceanClient, DOError


class Command(BaseCommand):
    """Test the async DigitalOcean API client."""

    help = "Test the async DigitalOcean API client functionality"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--skip-droplets",
            action="store_true",
            help="Skip listing droplets (may be many)",
        )
        parser.add_argument(
            "--test-create",
            action="store_true",
            help="Test creating a small droplet (WARNING: costs money!)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the async tests."""
        asyncio.run(self._run_tests(options))

    async def _run_tests(self, options: dict[str, Any]) -> None:
        """Run async API tests."""
        if not settings.DO_TOKEN:
            self.stdout.write(
                self.style.ERROR(
                    "DigitalOcean token not configured. Set DO_TOKEN environment variable."
                )
            )
            return

        self.stdout.write("Testing async DigitalOcean API client...")

        async with DigitalOceanClient() as client:
            try:
                # Test listing regions
                self.stdout.write("Testing: List regions")
                regions = await client.list_regions()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Found {len(regions)} regions")
                )
                
                # Show a few regions
                for region in regions[:3]:
                    self.stdout.write(f"  - {region.slug}: {region.name}")

                # Test listing sizes
                self.stdout.write("\nTesting: List sizes")
                sizes = await client.list_sizes()
                available_sizes = [s for s in sizes if s.available]
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Found {len(available_sizes)} available sizes")
                )
                
                # Show a few sizes
                for size in available_sizes[:3]:
                    self.stdout.write(
                        f"  - {size.slug}: {size.vcpus} vCPU, {size.memory}MB RAM, ${size.price_monthly}/mo"
                    )

                # Test listing images
                self.stdout.write("\nTesting: List images")
                images = await client.list_images()
                ubuntu_images = [img for img in images if "ubuntu" in img.slug.lower()]
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Found {len(ubuntu_images)} Ubuntu images")
                )
                
                # Show a few Ubuntu images
                for image in ubuntu_images[:3]:
                    self.stdout.write(f"  - {image.slug}: {image.name}")

                # Test listing SSH keys
                self.stdout.write("\nTesting: List SSH keys")
                ssh_keys = await client.list_ssh_keys()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Found {len(ssh_keys)} SSH keys")
                )

                # Test listing droplets (optional)
                if not options["skip_droplets"]:
                    self.stdout.write("\nTesting: List droplets")
                    droplets = await client.list_droplets()
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Found {len(droplets)} droplets")
                    )
                    
                    # Show active droplets
                    active_droplets = [d for d in droplets if d.status == "active"]
                    for droplet in active_droplets[:3]:
                        self.stdout.write(
                            f"  - {droplet.name} ({droplet.id}): {droplet.ip_address} - {droplet.status}"
                        )

                # Test creating droplet (dangerous - costs money!)
                if options["test_create"]:
                    self.stdout.write(
                        self.style.WARNING(
                            "\nWARNING: Creating test droplet (this costs money!)"
                        )
                    )
                    
                    # Find smallest available size and a good region
                    smallest_size = min(available_sizes, key=lambda s: s.price_monthly)
                    nyc_regions = [r for r in regions if r.slug.startswith("nyc")]
                    test_region = nyc_regions[0] if nyc_regions else regions[0]
                    
                    # Use latest Ubuntu LTS
                    ubuntu_lts = [img for img in ubuntu_images if "22-04" in img.slug]
                    test_image = ubuntu_lts[0] if ubuntu_lts else ubuntu_images[0]
                    
                    test_droplet = await client.create_droplet(
                        name="cloud-classroom-test",
                        region=test_region.slug,
                        size=smallest_size.slug,
                        image=test_image.slug,
                        tags=["cloud-classroom", "test"],
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Created test droplet: {test_droplet.name} ({test_droplet.id})"
                        )
                    )
                    
                    # Wait for it to become active
                    self.stdout.write("Waiting for droplet to become active...")
                    active_droplet = await client.wait_for_droplet_active(
                        test_droplet.id, 
                        max_wait=180
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Droplet active: {active_droplet.ip_address}"
                        )
                    )
                    
                    # Clean up - delete the test droplet
                    self.stdout.write("Cleaning up test droplet...")
                    await client.delete_droplet(test_droplet.id)
                    self.stdout.write(
                        self.style.SUCCESS("✓ Test droplet deleted")
                    )

                self.stdout.write(
                    self.style.SUCCESS("\n🎉 All API tests passed!")
                )

            except DOError as e:
                self.stdout.write(
                    self.style.ERROR(f"DigitalOcean API error: {e.message}")
                )
                if e.status_code:
                    self.stdout.write(f"Status code: {e.status_code}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Unexpected error: {e}")
                )
                raise