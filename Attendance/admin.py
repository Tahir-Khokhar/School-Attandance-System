from django.contrib import admin
from .models import UserProfile, Student, Attendance


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "full_name", "roll_number", "student_class", "section")
    list_filter = ("student_class", "section")
    search_fields = ("full_name", "student_id", "roll_number")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status", "marked_by", "marked_at")
    list_filter = ("status", "date", "student__student_class")
    search_fields = ("student__full_name",)
