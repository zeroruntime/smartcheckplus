from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # Student URLS
    path('students/', views.student_list, name='student_list'),
    path('students/add-regular/', views.add_regular_student, name='add_regular_student'),
    path('students/add-temporary/', views.add_temporary_student, name='add_temporary_student'),
    path('students/<str:student_id>/', views.student_detail, name='student_detail'),


    # Guest URLS
    path('guests/', views.guest_list, name='guest_list'),
    path('guests/add/', views.add_guest, name='add_guest'),
    path('guests/<str:guest_id>/', views.guest_detail, name='guest_detail'),

    # Access URLS
    path('access/', views.access_logs, name='access_logs'),
    path('settings/', views.system_settings, name='system_settings'),
    path('scan/', views.scan_qr, name='scan_qr_code'),
    path('scan/process/', views.process_scan, name='process_scan'),

]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
