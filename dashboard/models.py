from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import uuid
import os

class UserProfile(models.Model):
    """Extends the built-in User model with additional fields"""
    USER_TYPES = [
        ('admin', 'Administrator'),
        ('supervisor', 'Lab Supervisor'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_user_type_display()}"

class BaseStudent(models.Model):
    """Base abstract model for common student fields"""
    BOARDING_CHOICES = [
        ('Day', 'Day'),
        ('Boarding', 'Boarding'),
    ]

    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    year_joined = models.IntegerField()
    year_completed = models.IntegerField(blank=True, null=True)  # Auto-filled
    student_id = models.CharField(max_length=50, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    class_status = models.CharField(max_length=50)
    boarding_status = models.CharField(max_length=50, choices=BOARDING_CHOICES)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="%(class)s_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.year_joined and not self.year_completed:
            self.year_completed = self.year_joined + 3  # Adjust duration as needed
        super().save(*args, **kwargs)

    def generate_student_id(self):
        """Generates a unique student ID based on initials, year, and student type."""
        initials = (self.first_name[0] + self.last_name[0]).upper()
        init_year = self.year_joined + 3
        year = str(init_year)[-2:]

        from .models import RegularStudent, TemporaryStudent

        if isinstance(self, TemporaryStudent):
            type_prefix = "TMP"
            relevant_students = list(TemporaryStudent.objects.filter(year_joined=self.year_joined))
        elif isinstance(self, RegularStudent):
            type_prefix = ""
            relevant_students = list(RegularStudent.objects.filter(year_joined=self.year_joined))
        else:
            type_prefix = "UNK"
            relevant_students = []

        relevant_students.sort(key=lambda x: x.created_at)

        if relevant_students and relevant_students[-1].student_id:
            try:
                last_number = int(relevant_students[-1].student_id[-3:])
            except ValueError:
                last_number = 0
            new_number = str(last_number + 1).zfill(3)
        else:
            new_number = "001"

        return f"PRPC{year}-{type_prefix}{initials}{new_number}"


    def generate_qr_code(self):
        """Generates a QR code based on the student ID."""
        # Create a QR code with student_id as the data
        qr = qrcode.make(self.student_id)
        qr_io = BytesIO()
        qr.save(qr_io, format="PNG")

        # Save the QR code to the model's image field
        filename = f'qrcode_{self.student_id}.png'
        self.qr_code.save(filename, ContentFile(qr_io.getvalue()), save=False)
        
    @property
    def year_batch(self):
        """Returns the calculated graduation year (Year Joined + 3)"""
        return self.year_joined + 3

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.student_id}"


class RegularStudent(BaseStudent):
    """Regular students with permanent access to the lab"""
    additional_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self.generate_student_id()
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])


class TemporaryStudent(BaseStudent):
    """Temporary students with limited-time access to the lab"""
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    reason = models.CharField(max_length=255)

    @property
    def status(self):
        """Returns 'Active' if valid, 'Expired' otherwise"""
        now = timezone.now()
        return 'Active' if self.valid_from <= now <= self.valid_until else 'Expired'

    def is_valid(self):
        """Check if the temporary access is still valid"""
        return self.is_active and self.valid_from <= timezone.now() <= self.valid_until

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self.generate_student_id()
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])
        if self.valid_until < timezone.now():
            self.is_active = False
        super().save(*args, **kwargs)


class Guest(models.Model):
    """External visitors to the lab"""
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    school_or_organization = models.CharField(max_length=100)
    purpose = models.TextField()
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guest_created')
    created_at = models.DateTimeField(auto_now_add=True)
    guest_id = models.CharField(max_length=50, unique=True, blank=True)
    qr_code = models.ImageField(upload_to='guest_qrcodes/', blank=True, null=True)

    def generate_guest_id(self):
        """Generate a unique guest ID"""
        return f"GUEST-{uuid.uuid4().hex[:8].upper()}"

    def generate_qr_code(self):
        """Generates a QR code for temporary guest access."""
        qr = qrcode.make(self.guest_id)
        qr_io = BytesIO()
        qr.save(qr_io, format="PNG")
        filename = f'guest_qrcode_{self.guest_id}.png'
        self.qr_code.save(filename, ContentFile(qr_io.getvalue()), save=False)

    def save(self, *args, **kwargs):
        if not self.guest_id:
            self.guest_id = self.generate_guest_id()
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.school_or_organization}"


class AccessLog(models.Model):
    """Records every entry and exit from the lab"""
    LOG_TYPES = [
        ('entry', 'Entry'),
        ('exit', 'Exit'),
    ]

    USER_TYPES = [
        ('regular', 'Regular Student'),
        ('temporary', 'Temporary Student'),
        ('guest', 'Guest'),
    ]

    # Polymorphic relationship to different types of users
    regular_student = models.ForeignKey(RegularStudent, on_delete=models.CASCADE, null=True, blank=True)
    temporary_student = models.ForeignKey(TemporaryStudent, on_delete=models.CASCADE, null=True, blank=True)
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, null=True, blank=True)

    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    log_type = models.CharField(max_length=10, choices=LOG_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recorded_logs')

    # For pairing entry and exit logs
    session_id = models.UUIDField(blank=True, null=True)
    paired_log = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='paired_entry')

    def get_user_name(self):
        """Return the name of the person who entered/exited"""
        if self.regular_student:
            return f"{self.regular_student.first_name} {self.regular_student.last_name}"
        elif self.temporary_student:
            return f"{self.temporary_student.first_name} {self.temporary_student.last_name}"
        elif self.guest:
            return f"{self.guest.first_name} {self.guest.last_name}"
        return "Unknown"

    def get_user_id(self):
        """Return the ID of the person who entered/exited"""
        if self.regular_student:
            return self.regular_student.student_id
        elif self.temporary_student:
            return self.temporary_student.student_id
        elif self.guest:
            return self.guest.guest_id
        return None

    def __str__(self):
        return f"{self.get_log_type_display()} - {self.get_user_name()} - {self.timestamp}"


class LabSession(models.Model):
    """Tracks a complete lab session from entry to exit"""
    regular_student = models.ForeignKey(RegularStudent, on_delete=models.CASCADE, null=True, blank=True)
    temporary_student = models.ForeignKey(TemporaryStudent, on_delete=models.CASCADE, null=True, blank=True)
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, null=True, blank=True)

    user_type = models.CharField(max_length=20, choices=AccessLog.USER_TYPES)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    entry_log = models.OneToOneField(AccessLog, on_delete=models.CASCADE, related_name='entry_session')
    exit_log = models.OneToOneField(AccessLog, on_delete=models.CASCADE, null=True, blank=True, related_name='exit_session')

    def save(self, *args, **kwargs):
        if self.entry_time and self.exit_time:
            self.duration = self.exit_time - self.entry_time
        super().save(*args, **kwargs)

    def __str__(self):
        user_name = "Unknown"
        if self.regular_student:
            user_name = f"{self.regular_student.first_name} {self.regular_student.last_name}"
        elif self.temporary_student:
            user_name = f"{self.temporary_student.first_name} {self.temporary_student.last_name}"
        elif self.guest:
            user_name = f"{self.guest.first_name} {self.guest.last_name}"

        return f"{user_name} - {self.entry_time.strftime('%Y-%m-%d %H:%M')}"


# class IDCard(models.Model):
#     """Stores metadata for generated ID cards"""
#     regular_student = models.OneToOneField(RegularStudent, on_delete=models.CASCADE, null=True, blank=True)
#     temporary_student = models.OneToOneField(TemporaryStudent, on_delete=models.CASCADE, null=True, blank=True)
#     guest = models.OneToOneField(Guest, on_delete=models.CASCADE, null=True, blank=True)

#     generated_at = models.DateTimeField(auto_now_add=True)
#     card_image = models.ImageField(upload_to='id_cards/', blank=True, null=True)
#     printed = models.BooleanField(default=False)

#     def __str__(self):
#         if self.regular_student:
#             return f"ID Card: {self.regular_student.student_id}"
#         elif self.temporary_student:
#             return f"Temp ID Card: {self.temporary_student.student_id}"
#         elif self.guest:
#             return f"Guest Pass: {self.guest.guest_id}"
#         return "Unknown ID Card"


class SystemSettings(models.Model):
    """Single-instance model to store system-wide settings"""
    school_name = models.CharField(max_length=100, default="AI Lab")
    school_logo = models.ImageField(upload_to='system/', blank=True, null=True)
    qr_code_timeout = models.IntegerField(default=60, help_text="QR code validity timeout in seconds")
    require_supervisor_confirmation = models.BooleanField(default=True)
    temporary_access_max_days = models.IntegerField(default=30)

    class Meta:
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"
