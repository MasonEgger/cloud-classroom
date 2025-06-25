"""
Tests for Django models.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from classes.models import Class
from droplet.models import Droplet
from students.models import Student
from teachers.models import Teacher
from users.models import User, Profile, validate_ssh_key


@pytest.mark.django_db
class TestUserModel:
    """Test suite for User model."""

    def test_create_user(self, user_factory):
        """Test creating a user."""
        user = user_factory(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert str(user) == "test@example.com"

    def test_user_email_unique(self, user_factory):
        """Test that user emails must be unique."""
        user_factory(email="test@example.com")
        
        with pytest.raises(IntegrityError):
            user_factory(email="test@example.com")

    def test_user_required_fields(self):
        """Test that email is required."""
        with pytest.raises((IntegrityError, ValueError)):
            User.objects.create(email=None)


@pytest.mark.django_db
class TestProfileModel:
    """Test suite for Profile model."""

    def test_create_profile(self, profile_factory):
        """Test creating a profile."""
        profile = profile_factory()
        assert profile.user is not None
        assert profile.ssh_key is not None

    def test_profile_str(self, profile_factory):
        """Test profile string representation."""
        profile = profile_factory()
        expected = f"Profile for {profile.user.email}"
        assert str(profile) == expected


class TestSSHKeyValidation:
    """Test suite for SSH key validation."""

    def test_valid_rsa_key(self):
        """Test valid RSA SSH key."""
        valid_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vbqajDhA test@example.com"
        # Should not raise any exception
        validate_ssh_key(valid_key)

    def test_valid_ed25519_key(self):
        """Test valid Ed25519 SSH key."""
        valid_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDhf1i5iSZxZOaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX test@example.com"
        # Should not raise any exception
        validate_ssh_key(valid_key)

    def test_invalid_ssh_key_format(self):
        """Test invalid SSH key format."""
        invalid_key = "not-a-valid-ssh-key"
        with pytest.raises(ValidationError):
            validate_ssh_key(invalid_key)

    def test_empty_ssh_key(self):
        """Test empty SSH key."""
        with pytest.raises(ValidationError):
            validate_ssh_key("")

    def test_ssh_key_with_only_whitespace(self):
        """Test SSH key with only whitespace."""
        with pytest.raises(ValidationError):
            validate_ssh_key("   ")


@pytest.mark.django_db
class TestStudentModel:
    """Test suite for Student model."""

    def test_create_student(self, student_factory):
        """Test creating a student."""
        student = student_factory()
        assert student.user is not None
        assert isinstance(student.user, User)

    def test_student_str(self, student_factory):
        """Test student string representation."""
        student = student_factory()
        expected = f"Student: {student.user.email}"
        assert str(student) == expected

    def test_student_user_relationship(self, user_factory):
        """Test student-user relationship."""
        user = user_factory()
        student = Student.objects.create(user=user)
        
        assert student.user == user
        assert hasattr(user, 'student')  # Reverse relationship


@pytest.mark.django_db
class TestTeacherModel:
    """Test suite for Teacher model."""

    def test_create_teacher(self, teacher_factory):
        """Test creating a teacher."""
        teacher = teacher_factory()
        assert teacher.user is not None
        assert isinstance(teacher.user, User)

    def test_teacher_str(self, teacher_factory):
        """Test teacher string representation."""
        teacher = teacher_factory()
        expected = f"Teacher: {teacher.user.email}"
        assert str(teacher) == expected


@pytest.mark.django_db
class TestClassModel:
    """Test suite for Class model."""

    def test_create_class(self, class_factory):
        """Test creating a class."""
        classroom = class_factory(name="Computer Science 101")
        assert classroom.name == "Computer Science 101"
        assert classroom.droplet_count == 1
        assert classroom.droplet_student_limit == 5

    def test_class_str(self, class_factory):
        """Test class string representation."""
        classroom = class_factory(name="CS 101")
        assert str(classroom) == "CS 101"

    def test_class_prefix_generation(self, class_factory):
        """Test that class prefix is generated."""
        classroom = class_factory()
        assert classroom.prefix is not None
        assert len(classroom.prefix) > 0

    def test_class_default_values(self, class_factory):
        """Test class default values."""
        classroom = class_factory()
        assert classroom.droplet_priv_net is False
        assert classroom.droplet_ipv6 is False
        assert classroom.droplet_student_limit == 5
        assert classroom.destroyed_at is None

    def test_class_many_to_many_relationships(self, class_factory, teacher_factory, student_factory):
        """Test class relationships with teachers and students."""
        classroom = class_factory()
        teacher = teacher_factory()
        student = student_factory()
        
        # Add relationships
        classroom.teacher_set.add(teacher)
        classroom.students.add(student)
        
        # Check relationships
        assert teacher in classroom.teacher_set.all()
        assert student in classroom.students.all()
        assert classroom in teacher.classes.all()
        assert classroom in student.classes.all()


@pytest.mark.django_db
class TestDropletModel:
    """Test suite for Droplet model."""

    def test_create_droplet(self, droplet_factory):
        """Test creating a droplet."""
        droplet = droplet_factory()
        assert droplet.name is not None
        assert droplet.droplet_id is not None
        assert droplet.class_id is not None
        assert droplet.owner is not None

    def test_droplet_str(self, droplet_factory):
        """Test droplet string representation."""
        droplet = droplet_factory(name="test-droplet")
        assert str(droplet) == "test-droplet"

    def test_droplet_default_values(self, droplet_factory):
        """Test droplet default values."""
        droplet = droplet_factory()
        assert droplet.status == "active"
        assert droplet.destroyed_at is None
        assert droplet.created_at is not None
        assert droplet.updated_at is not None

    def test_droplet_relationships(self, droplet_factory, class_factory, user_factory):
        """Test droplet relationships."""
        classroom = class_factory()
        owner = user_factory()
        
        droplet = droplet_factory(class_id=classroom, owner=owner)
        
        assert droplet.class_id == classroom
        assert droplet.owner == owner
        assert droplet in classroom.droplet_set.all()

    def test_droplet_unique_constraints(self, droplet_factory):
        """Test droplet unique constraints."""
        # Create first droplet
        droplet1 = droplet_factory(droplet_id=123456)
        
        # Try to create another droplet with same droplet_id
        with pytest.raises(IntegrityError):
            droplet_factory(droplet_id=123456)

    def test_droplet_timestamps(self, droplet_factory):
        """Test droplet timestamp behavior."""
        droplet = droplet_factory()
        
        # Check that timestamps are set
        assert droplet.created_at is not None
        assert droplet.updated_at is not None
        
        # updated_at should be close to created_at for new objects
        time_diff = droplet.updated_at - droplet.created_at
        assert time_diff.total_seconds() < 1


@pytest.mark.django_db
class TestModelRelationships:
    """Test complex relationships between models."""

    def test_classroom_with_students_and_droplets(
        self, 
        class_factory, 
        student_factory, 
        droplet_factory
    ):
        """Test classroom with students and their droplets."""
        classroom = class_factory(name="CS 101")
        
        # Create students
        student1 = student_factory()
        student2 = student_factory()
        
        # Add students to class
        classroom.students.add(student1, student2)
        
        # Create droplets for students
        droplet1 = droplet_factory(class_id=classroom, owner=student1.user)
        droplet2 = droplet_factory(class_id=classroom, owner=student2.user)
        
        # Verify relationships
        assert classroom.students.count() == 2
        assert classroom.droplet_set.count() == 2
        
        # Check that each student has access to their droplet
        student1_droplets = Droplet.objects.filter(
            class_id=classroom, 
            owner=student1.user
        )
        assert student1_droplets.count() == 1
        assert droplet1 in student1_droplets

    def test_teacher_multiple_classes(self, teacher_factory, class_factory):
        """Test teacher assigned to multiple classes."""
        teacher = teacher_factory()
        class1 = class_factory(name="CS 101")
        class2 = class_factory(name="CS 201")
        
        # Assign teacher to both classes
        class1.teacher_set.add(teacher)
        class2.teacher_set.add(teacher)
        
        # Verify relationships
        assert teacher.classes.count() == 2
        assert class1 in teacher.classes.all()
        assert class2 in teacher.classes.all()

    def test_cascade_deletion_behavior(
        self, 
        user_factory, 
        student_factory, 
        class_factory, 
        droplet_factory
    ):
        """Test cascade deletion behavior."""
        # Create user and student
        user = user_factory()
        student = student_factory(user=user)
        classroom = class_factory()
        droplet = droplet_factory(class_id=classroom, owner=user)
        
        # Delete the user - student and related objects should be affected
        user_id = user.id
        student_id = student.id
        droplet_id = droplet.id
        
        user.delete()
        
        # Student should be deleted (cascade)
        assert not Student.objects.filter(id=student_id).exists()
        
        # Droplet owner should be set to null or deleted based on model definition
        # (This depends on the actual model definition - adjust based on your CASCADE settings)