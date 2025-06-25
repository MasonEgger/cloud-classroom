"""
Classroom management service using async DigitalOcean operations.

This service layer handles the orchestration of classroom resources,
including droplet creation, management, and cleanup operations.
"""

from __future__ import annotations

import asyncio
import secrets
import string
from datetime import datetime
from typing import Any

import structlog
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction

from classes.models import Class
from droplet.models import Droplet
from services.digitalocean import DigitalOceanClient, DOError
from students.models import Student

logger = structlog.get_logger(__name__)


class ClassroomError(Exception):
    """Base exception for classroom management operations."""


class ClassroomService:
    """
    Service for managing classroom droplets and resources.
    
    Provides high-level operations for creating, managing, and cleaning up
    classroom environments using the async DigitalOcean API.
    """

    def __init__(self, do_token: str | None = None) -> None:
        self.do_token = do_token or settings.DO_TOKEN
        self._client: DigitalOceanClient | None = None

    async def __aenter__(self) -> ClassroomService:
        """Async context manager entry."""
        self._client = DigitalOceanClient(self.do_token)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def client(self) -> DigitalOceanClient:
        """Get the DigitalOcean client."""
        if not self._client:
            msg = "ClassroomService must be used as async context manager"
            raise ClassroomError(msg)
        return self._client

    def _generate_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits
        # Ensure at least one uppercase, lowercase, and digit
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
        ]

        # Fill the rest randomly
        for _ in range(length - 3):
            password.append(secrets.choice(alphabet))

        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return "".join(password)

    def _generate_droplet_name(
        self,
        class_prefix: str,
        student_email: str,
        password_hint: str,
    ) -> str:
        """Generate a unique droplet name."""
        # Clean email for use in hostname
        clean_email = student_email.replace("@", "-AT-").replace(".", "-DOT-")
        return f"{class_prefix}-{clean_email}-{password_hint[:4]}"

    def _generate_user_data(
        self,
        username: str = "student",
        password: str | None = None,
        ssh_keys: list[str] | None = None,
    ) -> str:
        """Generate cloud-init user data for droplet setup."""
        if not password:
            password = self._generate_password()

        user_data = f"""#cloud-config
users:
  - name: {username}
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL:ALL) ALL']
    lock-passwd: false
"""

        # Add SSH keys if provided
        if ssh_keys:
            user_data += """    ssh_authorized_keys:
"""
            for key in ssh_keys:
                user_data += f"      - {key}\n"

        user_data += f"""
chpasswd:
  list: |
    {username}:{password}
  expire: false

# Disable root login and set up basic security
runcmd:
  - passwd -l root
  - ufw --force enable
  - ufw allow ssh
  - ufw allow 80
  - ufw allow 443
  - apt-get update
  - apt-get install -y htop curl wget git
"""

        return user_data

    async def create_droplet_for_student(
        self,
        class_obj: Class,
        student: Student,
        ssh_keys: list[str] | None = None,
    ) -> tuple[Droplet, dict[str, Any]]:
        """
        Create a droplet for a student in a class.
        
        Args:
            class_obj: The class configuration
            student: The student who will own the droplet
            ssh_keys: Optional SSH keys to add to the droplet
            
        Returns:
            Tuple of (Django Droplet model, connection info dict)
        """
        password = self._generate_password()
        droplet_name = self._generate_droplet_name(
            class_obj.prefix,
            student.user.email,
            password,
        )

        # Get teacher SSH keys if forced
        teacher_ssh_keys = []
        if class_obj.force_teacher_ssh_key:
            # Use sync_to_async to access related objects
            teachers = await sync_to_async(list)(class_obj.teacher_set.all())
            for teacher in teachers:
                try:
                    profile = await sync_to_async(
                        lambda: teacher.user.profile
                    )()
                    if profile.ssh_key:
                        teacher_ssh_keys.append(profile.ssh_key.strip())
                except Exception:
                    # Profile doesn't exist or no SSH key
                    pass

        all_ssh_keys = (ssh_keys or []) + teacher_ssh_keys

        # Generate user data
        user_data = self._generate_user_data(
            username="student",
            password=password,
            ssh_keys=all_ssh_keys if all_ssh_keys else None,
        )

        try:
            # Create the droplet
            logger.info(
                "Creating droplet for student",
                class_name=class_obj.name,
                student_email=student.user.email,
                droplet_name=droplet_name,
                region=class_obj.droplet_region,
                size=class_obj.droplet_size,
                image=class_obj.droplet_image,
            )

            do_droplet = await self.client.create_droplet(
                name=droplet_name,
                region=class_obj.droplet_region,
                size=class_obj.droplet_size,
                image=class_obj.droplet_image,
                ssh_keys=all_ssh_keys if all_ssh_keys else None,
                user_data=user_data,
                private_networking=class_obj.droplet_priv_net,
                ipv6=class_obj.droplet_ipv6,
                tags=["cloud-classroom", f"class-{class_obj.id}", f"student-{student.id}"],
                monitoring=True,  # Enable monitoring for classroom droplets
            )

            # Wait for droplet to become active
            logger.info("Waiting for droplet to become active", droplet_id=do_droplet.id)
            active_droplet = await self.client.wait_for_droplet_active(
                do_droplet.id,
                max_wait=300,  # 5 minutes
            )

            # Create Django model using database transaction
            async with sync_to_async(transaction.atomic)():
                django_droplet = await sync_to_async(Droplet.objects.create)(
                    name=droplet_name,
                    class_id=class_obj,
                    droplet_id=active_droplet.id,
                    initial_password=password,
                    region=active_droplet.region["slug"],
                    image=str(active_droplet.image.get("slug", active_droplet.image.get("id"))),
                    ip_addr=active_droplet.ip_address or "",
                    owner=student.user,
                    size_slug=active_droplet.size_slug,
                    status=active_droplet.status,
                )

            connection_info = {
                "droplet_id": active_droplet.id,
                "droplet_ip": active_droplet.ip_address,
                "username": "student",
                "password": password,
                "ssh_command": f"ssh student@{active_droplet.ip_address}",
                "name": droplet_name,
            }

            logger.info(
                "Droplet created successfully",
                droplet_id=active_droplet.id,
                ip_address=active_droplet.ip_address,
                student_email=student.user.email,
            )

            return django_droplet, connection_info

        except DOError as e:
            logger.error(
                "Failed to create droplet",
                error=e.message,
                class_name=class_obj.name,
                student_email=student.user.email,
            )
            raise ClassroomError(f"Failed to create droplet: {e.message}") from e

    async def delete_droplet(self, droplet: Droplet) -> None:
        """
        Delete a droplet both from DigitalOcean and Django.
        
        Args:
            droplet: The Django Droplet model instance
        """
        try:
            # Delete from DigitalOcean
            await self.client.delete_droplet(droplet.droplet_id)
            logger.info("Droplet deleted from DigitalOcean", droplet_id=droplet.droplet_id)

            # Update Django model
            async with sync_to_async(transaction.atomic)():
                droplet.destroyed_at = datetime.now()
                await sync_to_async(droplet.save)()

            logger.info("Droplet marked as destroyed in database", droplet_id=droplet.droplet_id)

        except DOError as e:
            if e.status_code == 404:
                # Droplet already deleted on DigitalOcean, just update database
                logger.warning(
                    "Droplet not found on DigitalOcean, updating database",
                    droplet_id=droplet.droplet_id,
                )
                async with sync_to_async(transaction.atomic)():
                    droplet.destroyed_at = datetime.now()
                    await sync_to_async(droplet.save)()
            else:
                logger.error(
                    "Failed to delete droplet",
                    error=e.message,
                    droplet_id=droplet.droplet_id,
                )
                raise ClassroomError(f"Failed to delete droplet: {e.message}") from e

    async def power_action_droplet(
        self,
        droplet: Droplet,
        action: str,
    ) -> dict[str, Any]:
        """
        Perform a power action on a droplet.
        
        Args:
            droplet: The Django Droplet model instance
            action: One of 'power_on', 'power_off', 'shutdown', 'reboot'
            
        Returns:
            Action result from DigitalOcean API
        """
        try:
            if action == "power_on":
                result = await self.client.power_on_droplet(droplet.droplet_id)
            elif action == "power_off":
                result = await self.client.power_off_droplet(droplet.droplet_id)
            elif action == "shutdown":
                result = await self.client.shutdown_droplet(droplet.droplet_id)
            elif action == "reboot":
                result = await self.client.reboot_droplet(droplet.droplet_id)
            else:
                raise ClassroomError(f"Unknown power action: {action}")

            logger.info(
                "Power action performed",
                action=action,
                droplet_id=droplet.droplet_id,
                action_id=result.get("id"),
            )

            return result

        except DOError as e:
            logger.error(
                "Failed to perform power action",
                action=action,
                error=e.message,
                droplet_id=droplet.droplet_id,
            )
            raise ClassroomError(f"Failed to {action} droplet: {e.message}") from e

    async def cleanup_class_droplets(self, class_obj: Class) -> dict[str, int]:
        """
        Clean up all droplets for a class.
        
        Args:
            class_obj: The class to clean up
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            "deleted": 0,
            "already_destroyed": 0,
            "errors": 0,
        }

        # Get all active droplets for this class
        droplets = await sync_to_async(list)(
            Droplet.objects.filter(
                class_id=class_obj,
                destroyed_at__isnull=True,
            )
        )

        logger.info(
            "Starting class cleanup",
            class_name=class_obj.name,
            droplet_count=len(droplets),
        )

        # Delete droplets concurrently (but limit concurrency)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent deletions

        async def delete_single_droplet(droplet: Droplet) -> None:
            async with semaphore:
                try:
                    await self.delete_droplet(droplet)
                    stats["deleted"] += 1
                except ClassroomError:
                    stats["errors"] += 1

        # Run deletions concurrently
        tasks = [delete_single_droplet(droplet) for droplet in droplets]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Update class destroyed timestamp
        async with sync_to_async(transaction.atomic)():
            class_obj.destroyed_at = datetime.now()
            await sync_to_async(class_obj.save)()

        logger.info(
            "Class cleanup completed",
            class_name=class_obj.name,
            **stats,
        )

        return stats

    async def sync_droplet_status(self, droplet: Droplet) -> Droplet:
        """
        Sync droplet status from DigitalOcean API.
        
        Args:
            droplet: The Django Droplet model instance
            
        Returns:
            Updated droplet instance
        """
        try:
            do_droplet = await self.client.get_droplet(droplet.droplet_id)

            # Update Django model
            async with sync_to_async(transaction.atomic)():
                droplet.status = do_droplet.status
                droplet.ip_addr = do_droplet.ip_address or ""
                await sync_to_async(droplet.save)()

            logger.info(
                "Droplet status synced",
                droplet_id=droplet.droplet_id,
                status=do_droplet.status,
                ip_address=do_droplet.ip_address,
            )

            return droplet

        except DOError as e:
            if e.status_code == 404:
                # Droplet deleted on DigitalOcean
                async with sync_to_async(transaction.atomic)():
                    droplet.destroyed_at = datetime.now()
                    droplet.status = "destroyed"
                    await sync_to_async(droplet.save)()

                logger.info(
                    "Droplet not found on DigitalOcean, marked as destroyed",
                    droplet_id=droplet.droplet_id,
                )
            else:
                logger.error(
                    "Failed to sync droplet status",
                    error=e.message,
                    droplet_id=droplet.droplet_id,
                )
                raise ClassroomError(f"Failed to sync droplet status: {e.message}") from e

        return droplet
