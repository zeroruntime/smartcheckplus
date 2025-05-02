from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Q
import json
import uuid
import csv

from .models import (
    RegularStudent, TemporaryStudent, Guest, AccessLog,
    LabSession, SystemSettings
)

# Create your views here.
def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'pages/landing.html')

@login_required
def dashboard(request):
    username = request.user.username
    profile = request.user.profile

     # Get counts for dashboard stats
    regular_count = RegularStudent.objects.filter(is_active=True).count()
    temporary_count = TemporaryStudent.objects.filter(is_active=True, valid_until__gte=timezone.now()).count()

    # Get current lab occupancy
    current_sessions = LabSession.objects.filter(exit_time__isnull=True)
    occupancy_count = current_sessions.count()

    # Get today's logs
    today = timezone.now().date()
    today_logs = AccessLog.objects.filter(timestamp__date=today)
    entry_count = today_logs.filter(log_type='entry').count()
    exit_count = today_logs.filter(log_type='exit').count()

    # Recent activity
    recent_logs = AccessLog.objects.all().order_by('-timestamp')[:10]

    # Who's currently in the lab
    current_users = []
    for session in current_sessions:
        if session.regular_student:
            user = session.regular_student
            user_type = 'Regular Student'
        elif session.temporary_student:
            user = session.temporary_student
            user_type = 'Temporary Student'
        elif session.guest:
            user = session.guest
            user_type = 'Guest'
        else:
            continue

        current_users.append({
            'name': f"{user.first_name} {user.last_name}",
            'id': getattr(user, 'student_id', getattr(user, 'guest_id', 'Unknown')),
            'entry_time': session.entry_time,
            'type': user_type,
        })

    context = {
        'regular_count': regular_count,
        'temporary_count': temporary_count,
        'occupancy_count': occupancy_count,
        'entry_count': entry_count,
        'exit_count': exit_count,
        'recent_logs': recent_logs,
        'current_users': current_users,
    }
    return render(request, 'index.html', {'username': username,  'profile': profile})

@login_required
def student_list(request):
    username = request.user.username
    profile = request.user.profile

    query = request.GET.get('q', '')
    student_type = request.GET.get('type', 'regular')

    if student_type == 'regular':
        students = RegularStudent.objects.all()
    elif student_type == 'temporary':
        students = TemporaryStudent.objects.all()
    else:
        # Default to regular if invalid type
        students = RegularStudent.objects.all()
        student_type = 'regular'

    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(student_id__icontains=query)
        )

    # Pagination
    paginator = Paginator(students, 20)  # 20 students per page
    page = request.GET.get('page')

    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'Student Management',
        'students': students,
        'student_type': student_type,
        'query': query,
        'username': username,
        'profile': profile,
    }

    return render(request, 'students/student_list.html', context)

@login_required
def student_detail(request, student_id):
    username = request.user.username
    profile = request.user.profile

    # Try to find the student in either regular or temporary students
    regular_student = RegularStudent.objects.filter(student_id=student_id).first()
    temporary_student = TemporaryStudent.objects.filter(student_id=student_id).first()

    if regular_student:
        student = regular_student
        student_type = 'regular'
    elif temporary_student:
        student = temporary_student
        student_type = 'temporary'
    else:
        messages.error(request, f'Student with ID {student_id} not found.')
        print(f'Student with ID {student_id} not found.')
        return redirect('student_list')

    # Get access logs for this student
    if student_type == 'regular':
        logs = AccessLog.objects.filter(regular_student=student).order_by('-timestamp')
    else:
        logs = AccessLog.objects.filter(temporary_student=student).order_by('-timestamp')

    # Paginate logs
    paginator = Paginator(logs, 20)  # 20 logs per page
    page = request.GET.get('page')

    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)

    context = {
        'page_title': f'Student: {student.first_name} {student.last_name}',
        'student': student,
        'student_type': student_type,
        'logs': logs,
        'username': username,
        'profile': profile
    }

    return render(request, 'students/student_detail.html', context)

@login_required
def add_regular_student(request):
    username = request.user.username
    profile = request.user.profile

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        class_status = request.POST.get('class_status')
        boarding_status = request.POST.get('boarding_status')
        year_joined = request.POST.get('year_joined')
        additional_notes = request.POST.get('additional_notes', '')
        photo = request.FILES.get('photo')

        # Validate required fields
        if not all([first_name, last_name, class_status, boarding_status, year_joined]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('add_regular_student')

        try:
            # Create the student
            student = RegularStudent(
                first_name=first_name,
                last_name=last_name,
                class_status=class_status,
                boarding_status=boarding_status,
                year_joined=int(year_joined),
                additional_notes=additional_notes,
                created_by=request.user
            )

            if photo:
                student.photo = photo

            student.save()  # This will generate the student ID and QR code

            messages.success(request, f'Student {student.first_name} {student.last_name} added successfully with ID: {student.student_id}')
            return redirect('student_detail', student_id=student.student_id)

        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
            return redirect('add_regular_student')

    # GET request - show the form
    current_year = timezone.now().year
    context = {
        'page_title': 'Add Regular Student',
        'current_year': current_year,
        'username': username,
        'profile': profile
    }
    return render(request, 'students/add_regular_student.html', context)

@login_required
def add_temporary_student(request):
    username = request.user.username
    profile = request.user.profile

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        class_status = request.POST.get('class_status')
        boarding_status = request.POST.get('boarding_status')
        year_joined = request.POST.get('year_joined')
        reason = request.POST.get('reason')
        valid_until_str = request.POST.get('valid_until')
        photo = request.FILES.get('photo')

        # Validate required fields
        if not all([first_name, last_name, class_status, boarding_status, year_joined, reason, valid_until_str]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('add_temporary_student')

        try:
            # Parse the valid_until date
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())

            # Create the student
            student = TemporaryStudent(
                first_name=first_name,
                last_name=last_name,
                class_status=class_status,
                boarding_status=boarding_status,
                year_joined=int(year_joined),
                reason=reason,
                valid_until=valid_until,
                created_by=request.user
            )

            if photo:
                student.photo = photo

            student.save()  # This will generate the student ID and QR code

            messages.success(request, f'Temporary student {student.first_name} {student.last_name} added successfully with ID: {student.student_id}')
            return redirect('student_detail', student_id=student.student_id)

        except Exception as e:
            messages.error(request, f'Error adding temporary student: {str(e)}')
            return redirect('add_temporary_student')

    # GET request - show the form
    current_year = timezone.now().year
    # Calculate default expiry date (1 week from now)
    default_expiry = (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    context = {
        'page_title': 'Add Temporary Student',
        'current_year': current_year,
        'default_expiry': default_expiry,
        'username': username,
        'profile': profile
    }
    return render(request, 'students/add_temp_student.html', context)

@login_required
def guest_list(request):
    username = request.user.username
    profile = request.user.profile

    query = request.GET.get('q', '')
    guests = Guest.objects.all().order_by('-created_at')

    if query:
        guests = guests.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(school_or_organization__icontains=query) |
            Q(guest_id__icontains=query)
        )

    # Pagination
    paginator = Paginator(guests, 20)  # 20 guests per page
    page = request.GET.get('page')

    try:
        guests = paginator.page(page)
    except PageNotAnInteger:
        guests = paginator.page(1)
    except EmptyPage:
        guests = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'Guest Management',
        'guests': guests,
        'query': query,
        'username': username,
        'profile': profile
    }

    return render(request, 'guests/guest_list.html', context)

@login_required
def add_guest(request):
    username = request.user.username
    profile = request.user.profile

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        school_or_organization = request.POST.get('school_or_organization')
        purpose = request.POST.get('purpose')
        contact_number = request.POST.get('contact_number', '')
        email = request.POST.get('email', '')

        # Validate required fields
        if not all([first_name, last_name, school_or_organization, purpose]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('add_guest')

        try:
            # Create the guest
            guest = Guest(
                first_name=first_name,
                last_name=last_name,
                school_or_organization=school_or_organization,
                purpose=purpose,
                contact_number=contact_number,
                email=email,
                created_by=request.user
            )

            guest.save()  # This will generate the guest ID and QR code

            messages.success(request, f'Guest {guest.first_name} {guest.last_name} added successfully with ID: {guest.guest_id}')

            # If the "Check In Now" checkbox is checked, automatically log the guest's entry
            # if request.POST.get('check_in_now'):
            #     scanner = QRCodeScanner(request.user)
            #     result = scanner.process_scan(guest.guest_id)
            #     if result['status'] == 'success':
            #         messages.success(request, f'Guest has been checked in successfully.')
            #     else:
            #         messages.error(request, f'Failed to check in guest: {result["message"]}')

            # return redirect('guest_detail', guest_id=guest.guest_id)

        except Exception as e:
            messages.error(request, f'Error adding guest: {str(e)}')
            return redirect('add_guest')

    # GET request - show the form
    context = {
        'page_title': 'Add Guest',
        'username': username,
        'profile': profile
    }
    return render(request, 'guests/add_guest.html', context)

@login_required
def guest_detail(request, guest_id):
    username = request.user.username
    profile = request.user.profile

    guest = get_object_or_404(Guest, guest_id=guest_id)

    # Get access logs for this guest
    logs = AccessLog.objects.filter(guest=guest).order_by('-timestamp')

    # Paginate logs
    paginator = Paginator(logs, 20)  # 20 logs per page
    page = request.GET.get('page')

    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)

    context = {
        'page_title': f'Guest: {guest.first_name} {guest.last_name}',
        'guest': guest,
        'logs': logs,
        'username': username,
        'profile': profile
    }

    return render(request, 'guests/guest_detail.html', context)

# ACCESS CONTROL
@login_required
def access_logs(request):
    # Get filter parameters
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    user_type = request.GET.get('user_type', '')
    log_type = request.GET.get('log_type', '')
    query = request.GET.get('q', '')

    # Apply filters
    logs = AccessLog.objects.all().order_by('-timestamp')

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            logs = logs.filter(timestamp__gte=start_date)
        except ValueError:
            pass  # Invalid date format, ignore filter

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            # Add one day to include the end date fully
            end_date = end_date + timedelta(days=1)
            logs = logs.filter(timestamp__lt=end_date)
        except ValueError:
            pass  # Invalid date format, ignore filter

    if user_type:
        logs = logs.filter(user_type=user_type)

    if log_type:
        logs = logs.filter(log_type=log_type)

    if query:
        # Complex query across multiple related models
        regular_ids = RegularStudent.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(student_id__icontains=query)
        ).values_list('id', flat=True)

        temp_ids = TemporaryStudent.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(student_id__icontains=query)
        ).values_list('id', flat=True)

        guest_ids = Guest.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(guest_id__icontains=query) |
            Q(school_or_organization__icontains=query)
        ).values_list('id', flat=True)

        logs = logs.filter(
            Q(regular_student_id__in=regular_ids) |
            Q(temporary_student_id__in=temp_ids) |
            Q(guest_id__in=guest_ids)
        )

    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page = request.GET.get('page')

    try:
        logs = paginator.page(page)
    except PageNotAnInteger:
        logs = paginator.page(1)
    except EmptyPage:
        logs = paginator.page(paginator.num_pages)

    context = {
        'page_title': 'Access Logs',
        'logs': logs,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'user_type': user_type,
        'log_type': log_type,
        'query': query,
    }

    return render(request, 'control/access_logs.html', context)

@login_required
def system_settings(request):
    username = request.user.username
    profile = request.user.profile

    # Only allow staff/admin to access settings
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access system settings.')
        print(f'You do not have permission to access system settings.')
        return redirect('dashboard')

    # Get or create settings
    settings, created = SystemSettings.objects.get_or_create(id=1)

    if request.method == 'POST':
        settings.school_name = request.POST.get('school_name', settings.school_name)
        settings.qr_code_timeout = int(request.POST.get('qr_code_timeout', settings.qr_code_timeout))
        settings.require_supervisor_confirmation = request.POST.get('require_supervisor_confirmation') == 'on'
        settings.temporary_access_max_days = int(request.POST.get('temporary_access_max_days', settings.temporary_access_max_days))

        if 'school_logo' in request.FILES:
            settings.school_logo = request.FILES['school_logo']

        settings.save()
        messages.success(request, 'System settings updated successfully.')
        return redirect('system_settings')

    context = {
        'page_title': 'System Settings',
        'settings': settings,
        'username': username,
        'profile': profile
    }

    return render(request, 'control/system_settings.html', context)


# AUTHENTICATION VIEWS
def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        print(f"Trying to log in with: {username}, {password}")  # Debugging

        user = authenticate(request, username=username, password=password)

        if user is None:
            print("Authentication failed")
            messages.error(request, "Invalid Username or Password", extra_tags="error-message")
            return redirect("/login")

        print(f"User {user} authenticated successfully!")
        login(request, user)
        return redirect("/dashboard/")

    return render(request, "pages/authentication-login.html")

def logout_user(request):
    logout(request)
    return redirect("/")
