from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register-teacher/", views.register_teacher, name="register_teacher"),
    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_add, name="student_add"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
    # Attendance
    path("attendance/mark/", views.mark_attendance, name="mark_attendance"),
    # Reports
    path("reports/daily/", views.daily_report, name="daily_report"),
    path("reports/monthly/", views.monthly_report, name="monthly_report"),
]
