from django.shortcuts import redirect, render
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
    return render(request, 'index.html', {'username': username,  'profile': profile})

@login_required
def student_list(request):
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
    }

    return render(request, 'students/student_list.html', context)

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
