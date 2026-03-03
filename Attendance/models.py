from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("teacher", "Teacher"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="teacher")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Student(models.Model):
    CLASS_CHOICES = [(str(i), str(i)) for i in range(1, 13)]
    SECTION_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]

    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20)
    student_class = models.CharField(max_length=5, choices=CLASS_CHOICES)
    section = models.CharField(max_length=5, choices=SECTION_CHOICES)
    parent_contact = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("roll_number", "student_class", "section")
        ordering = ["student_class", "section", "roll_number"]

    def __str__(self):
        return f"{self.full_name} (Class {self.student_class}-{self.section})"

    def attendance_percentage(self, month=None, year=None):
        records = self.attendance_records.all()
        if month and year:
            records = records.filter(date__month=month, date__year=year)
        total = records.count()
        if total == 0:
            return 0
        present = records.filter(status__in=["present", "late"]).count()
        return round((present / total) * 100, 1)


class Attendance(models.Model):
    STATUS_CHOICES = (
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.status}"
