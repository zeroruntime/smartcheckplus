from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, RegularStudent, TemporaryStudent, Guest,
    AccessLog, LabSession, SystemSettings
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'phone_number')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone_number')


class BaseStudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'student_id', 'class_status', 'boarding_status', 'is_active', 'qr_code_preview')
    list_filter = ('boarding_status', 'class_status', 'year_joined', 'is_active')
    search_fields = ('first_name', 'last_name', 'student_id')
    readonly_fields = ('qr_code_preview',)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No QR Code"

    qr_code_preview.short_description = 'QR Code'


@admin.register(RegularStudent)
class RegularStudentAdmin(BaseStudentAdmin):
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'photo')
        }),
        ('School Details', {
            'fields': ('year_joined', 'class_status', 'boarding_status')
        }),
        ('System Information', {
            'fields': ('student_id', 'qr_code', 'qr_code_preview', 'is_active')
        }),
        ('Additional Information', {
            'fields': ('additional_notes', 'created_by')
        }),
    )


@admin.register(TemporaryStudent)
class TemporaryStudentAdmin(BaseStudentAdmin):
    list_display = BaseStudentAdmin.list_display + ('valid_from', 'valid_until', 'is_valid')
    list_filter = BaseStudentAdmin.list_filter + ('valid_from', 'valid_until')
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'photo')
        }),
        ('School Details', {
            'fields': ('year_joined', 'class_status', 'boarding_status')
        }),
        ('Access Information', {
            'fields': ('valid_from', 'valid_until', 'reason')
        }),
        ('System Information', {
            'fields': ('student_id', 'qr_code', 'qr_code_preview', 'is_active')
        }),
        ('Administration', {
            'fields': ('created_by',)
        }),
    )
    readonly_fields = BaseStudentAdmin.readonly_fields + ('is_valid',)

    def is_valid(self, obj):
        return obj.is_valid()

    is_valid.boolean = True
    is_valid.short_description = 'Is Valid'


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'school_or_organization',
                    'created_at', 'guest_id', 'qr_code_preview')
    list_filter = ('school_or_organization', 'created_at')
    search_fields = ('first_name', 'last_name', 'school_or_organization', 'guest_id')
    readonly_fields = ('qr_code_preview', 'guest_id')

    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'contact_number', 'email')
        }),
        ('Visit Details', {
            'fields': ('school_or_organization', 'purpose')
        }),
        ('System Information', {
            'fields': ('guest_id', 'qr_code', 'qr_code_preview')
        }),
        ('Administration', {
            'fields': ('created_by',)
        }),
    )

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No QR Code"

    qr_code_preview.short_description = 'QR Code'


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'user_type', 'log_type', 'timestamp', 'recorded_by')
    list_filter = ('user_type', 'log_type', 'timestamp', 'recorded_by')
    search_fields = ('regular_student__first_name', 'regular_student__last_name',
                    'temporary_student__first_name', 'temporary_student__last_name',
                    'guest__first_name', 'guest__last_name')
    date_hierarchy = 'timestamp'

    def get_name(self, obj):
        return obj.get_user_name()

    get_name.short_description = 'Name'


@admin.register(LabSession)
class LabSessionAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'user_type', 'entry_time', 'exit_time', 'get_duration')
    list_filter = ('user_type', 'entry_time', 'exit_time')
    search_fields = ('regular_student__first_name', 'regular_student__last_name',
                    'temporary_student__first_name', 'temporary_student__last_name',
                    'guest__first_name', 'guest__last_name')
    date_hierarchy = 'entry_time'

    def get_name(self, obj):
        if obj.regular_student:
            return f"{obj.regular_student.first_name} {obj.regular_student.last_name}"
        elif obj.temporary_student:
            return f"{obj.temporary_student.first_name} {obj.temporary_student.last_name}"
        elif obj.guest:
            return f"{obj.guest.first_name} {obj.guest.last_name}"
        return "Unknown"

    def get_duration(self, obj):
        if obj.duration:
            minutes = obj.duration.total_seconds() // 60
            return f"{int(minutes)} min"
        return "In progress"

    get_name.short_description = 'Name'
    get_duration.short_description = 'Duration'


# @admin.register(IDCard)
# class IDCardAdmin(admin.ModelAdmin):
#     list_display = ('get_name', 'get_id', 'generated_at', 'printed')
#     list_filter = ('generated_at', 'printed')

#     def get_name(self, obj):
#         if obj.regular_student:
#             return f"{obj.regular_student.first_name} {obj.regular_student.last_name}"
#         elif obj.temporary_student:
#             return f"{obj.temporary_student.first_name} {obj.temporary_student.last_name}"
#         elif obj.guest:
#             return f"{obj.guest.first_name} {obj.guest.last_name}"
#         return "Unknown"

#     def get_id(self, obj):
#         if obj.regular_student:
#             return obj.regular_student.student_id
#         elif obj.temporary_student:
#             return obj.temporary_student.student_id
#         elif obj.guest:
#             return obj.guest.guest_id
#         return "Unknown"

#     get_name.short_description = 'Name'
#     get_id.short_description = 'ID'


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'qr_code_timeout', 'require_supervisor_confirmation')

    def has_add_permission(self, request):
        # Check if there's already an instance
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)
