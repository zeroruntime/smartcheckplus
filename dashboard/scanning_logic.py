from django.db import transaction
from django.utils import timezone
from .models import (
    RegularStudent, TemporaryStudent, Guest, AccessLog, LabSession
)
import uuid

class QRCodeScanner:
    """
    Handles the logic for scanning QR codes and logging access.
    """
    def __init__(self, supervisor):
        self.supervisor = supervisor

    def process_scan(self, qr_code_data):
        """
        Process a QR code scan and determine what action to take
        """
        # Determine the type of QR code (Regular, Temporary, or Guest)
        user_object, user_type = self._identify_user(qr_code_data)

        if not user_object:
            return {
                'status': 'error',
                'message': 'Invalid QR code or user not found',
                'data': None
            }

        # Check if the user is valid (active and within validity period)
        if not self._is_valid_user(user_object, user_type):
            return {
                'status': 'error',
                'message': 'Access denied. User is inactive or access has expired.',
                'data': {
                    'user_type': user_type,
                    'user_name': f"{user_object.first_name} {user_object.last_name}",
                    'user_id': self._get_user_id(user_object, user_type)
                }
            }

        # Check if the user is currently inside the lab
        is_inside = self._is_inside_lab(user_object, user_type)

        # Log the entry or exit based on current status
        log_type = 'exit' if is_inside else 'entry'
        with transaction.atomic():
            log_entry = self._create_log_entry(user_object, user_type, log_type)

            # If this is an entry, create a new lab session
            if log_type == 'entry':
                session = self._create_lab_session(user_object, user_type, log_entry)
                response_message = f"Welcome to the lab, {user_object.first_name}!"
            else:
                # If this is an exit, update the existing lab session
                session = self._update_lab_session(user_object, user_type, log_entry)
                duration_mins = int((timezone.now() - session.entry_time).total_seconds() // 60)
                response_message = f"Goodbye, {user_object.first_name}! You spent {duration_mins} minutes in the lab."

        return {
            'status': 'success',
            'message': response_message,
            'data': {
                'user_type': user_type,
                'user_name': f"{user_object.first_name} {user_object.last_name}",
                'user_id': self._get_user_id(user_object, user_type),
                'log_type': log_type,
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'session_id': str(session.id) if session else None
            }
        }

    def _identify_user(self, qr_code_data):
        """
        Identify the user type and object based on the QR code data
        """
        # Try to find a regular student with this ID
        try:
            student = RegularStudent.objects.get(student_id=qr_code_data)
            return student, 'regular'
        except RegularStudent.DoesNotExist:
            pass

        # Try to find a temporary student with this ID
        try:
            temp_student = TemporaryStudent.objects.get(student_id=qr_code_data)
            return temp_student, 'temporary'
        except TemporaryStudent.DoesNotExist:
            pass

        # Try to find a guest with this ID
        try:
            guest = Guest.objects.get(guest_id=qr_code_data)
            return guest, 'guest'
        except Guest.DoesNotExist:
            pass

        # No user found with this QR code
        return None, None

    def _is_valid_user(self, user_object, user_type):
        """
        Check if the user is valid (active and within validity period)
        """
        if user_type == 'regular':
            # Regular students just need to be active
            return user_object.is_active

        elif user_type == 'temporary':
            # Temporary students need to be active and within validity period
            return user_object.is_valid()

        elif user_type == 'guest':
            # Guests are always valid if they exist
            # Could add additional validation if needed
            return True

        return False

    def _is_inside_lab(self, user_object, user_type):
        """
        Check if the user is currently inside the lab
        """
        # Find the most recent session for this user
        if user_type == 'regular':
            session = LabSession.objects.filter(
                regular_student=user_object,
                exit_time__isnull=True
            ).first()
        elif user_type == 'temporary':
            session = LabSession.objects.filter(
                temporary_student=user_object,
                exit_time__isnull=True
            ).first()
        elif user_type == 'guest':
            session = LabSession.objects.filter(
                guest=user_object,
                exit_time__isnull=True
            ).first()
        else:
            return False

        # If there's an open session, they're inside
        return session is not None

    def _create_log_entry(self, user_object, user_type, log_type):
        """
        Create a new access log entry
        """
        log_entry = AccessLog(
            user_type=user_type,
            log_type=log_type,
            recorded_by=self.supervisor
        )

        # Set the appropriate user field based on type
        if user_type == 'regular':
            log_entry.regular_student = user_object
        elif user_type == 'temporary':
            log_entry.temporary_student = user_object
        elif user_type == 'guest':
            log_entry.guest = user_object

        # Generate a unique session ID for entry logs
        if log_type == 'entry':
            log_entry.session_id = uuid.uuid4()

        log_entry.save()
        return log_entry

    def _create_lab_session(self, user_object, user_type, log_entry):
        """
        Create a new lab session on entry
        """
        session = LabSession(
            user_type=user_type,
            entry_time=timezone.now(),
            entry_log=log_entry
        )

        # Set the appropriate user field based on type
        if user_type == 'regular':
            session.regular_student = user_object
        elif user_type == 'temporary':
            session.temporary_student = user_object
        elif user_type == 'guest':
            session.guest = user_object

        session.save()
        return session

    def _update_lab_session(self, user_object, user_type, log_entry):
        """
        Update an existing lab session on exit
        """
        # Find the open session for this user
        if user_type == 'regular':
            session = LabSession.objects.filter(
                regular_student=user_object,
                exit_time__isnull=True
            ).first()
        elif user_type == 'temporary':
            session = LabSession.objects.filter(
                temporary_student=user_object,
                exit_time__isnull=True
            ).first()
        elif user_type == 'guest':
            session = LabSession.objects.filter(
                guest=user_object,
                exit_time__isnull=True
            ).first()

        if session:
            # Update the session with exit information
            session.exit_time = timezone.now()
            session.exit_log = log_entry
            session.save()

        return session

    def _get_user_id(self, user_object, user_type):
        """
        Get the user ID based on type
        """
        if user_type in ['regular', 'temporary']:
            return user_object.student_id
        elif user_type == 'guest':
            return user_object.guest_id
        return None
