from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LoginForm, StudentForm, TeacherRegistrationForm
from .models import Attendance, Student, UserProfile


# --- Authentication ---


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid username or password.")
    return render(request, "attendance/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def register_teacher(request):
    if not _is_admin(request.user):
        messages.error(request, "Only admins can register teachers.")
        return redirect("dashboard")
    form = TeacherRegistrationForm()
    if request.method == "POST":
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            UserProfile.objects.create(user=user, role=form.cleaned_data["role"])
            messages.success(request, f"Teacher '{user.username}' registered successfully.")
            return redirect("dashboard")
    return render(request, "attendance/register_teacher.html", {"form": form})


# --- Dashboard ---


@login_required
def dashboard(request):
    today = date.today()
    total_students = Student.objects.count()
    today_records = Attendance.objects.filter(date=today)
    present_today = today_records.filter(status="present").count()
    absent_today = today_records.filter(status="absent").count()
    late_today = today_records.filter(status="late").count()
    unmarked_today = total_students - today_records.count()

    # Students below 75% attendance this month
    low_attendance = []
    students = Student.objects.all()
    for student in students:
        pct = student.attendance_percentage(month=today.month, year=today.year)
        if pct < 75 and student.attendance_records.filter(
            date__month=today.month, date__year=today.year
        ).exists():
            low_attendance.append({"student": student, "percentage": pct})

    context = {
        "today": today,
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today,
        "late_today": late_today,
        "unmarked_today": unmarked_today,
        "low_attendance": low_attendance[:10],
    }
    return render(request, "attendance/dashboard.html", context)


# --- Student Management ---


@login_required
def student_list(request):
    students = Student.objects.all()
    query = request.GET.get("q", "")
    class_filter = request.GET.get("student_class", "")
    section_filter = request.GET.get("section", "")

    if query:
        students = students.filter(
            Q(full_name__icontains=query)
            | Q(student_id__icontains=query)
            | Q(roll_number__icontains=query)
        )
    if class_filter:
        students = students.filter(student_class=class_filter)
    if section_filter:
        students = students.filter(section=section_filter)

    context = {
        "students": students,
        "query": query,
        "class_filter": class_filter,
        "section_filter": section_filter,
        "class_choices": Student.CLASS_CHOICES,
        "section_choices": Student.SECTION_CHOICES,
    }
    return render(request, "attendance/student_list.html", context)


@login_required
def student_add(request):
    form = StudentForm()
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Student added successfully.")
            return redirect("student_list")
    return render(request, "attendance/student_form.html", {"form": form, "title": "Add Student"})


@login_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = StudentForm(instance=student)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated successfully.")
            return redirect("student_list")
    return render(
        request, "attendance/student_form.html", {"form": form, "title": "Edit Student"}
    )


@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        student.delete()
        messages.success(request, "Student deleted successfully.")
        return redirect("student_list")
    return render(request, "attendance/student_confirm_delete.html", {"student": student})


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    today = date.today()
    records = student.attendance_records.all()[:30]
    monthly_pct = student.attendance_percentage(month=today.month, year=today.year)
    overall_pct = student.attendance_percentage()
    context = {
        "student": student,
        "records": records,
        "monthly_pct": monthly_pct,
        "overall_pct": overall_pct,
    }
    return render(request, "attendance/student_detail.html", context)


# --- Attendance Marking ---


@login_required
def mark_attendance(request):
    today = date.today()
    selected_class = request.GET.get("student_class", "")
    selected_section = request.GET.get("section", "")
    selected_date = request.GET.get("date", today.isoformat())

    try:
        att_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        att_date = today

    students = Student.objects.none()
    existing = {}

    if selected_class and selected_section:
        students = Student.objects.filter(
            student_class=selected_class, section=selected_section
        )
        existing_records = Attendance.objects.filter(
            student__in=students, date=att_date
        )
        existing = {r.student_id: r.status for r in existing_records}

    if request.method == "POST" and selected_class and selected_section:
        for student in students:
            status = request.POST.get(f"status_{student.id}")
            if status in ("present", "absent", "late"):
                Attendance.objects.update_or_create(
                    student=student,
                    date=att_date,
                    defaults={"status": status, "marked_by": request.user},
                )
        messages.success(
            request,
            f"Attendance marked for Class {selected_class}-{selected_section} on {att_date}.",
        )
        return redirect(
            f"/attendance/mark/?student_class={selected_class}&section={selected_section}&date={att_date}"
        )

    context = {
        "students": students,
        "existing": existing,
        "selected_class": selected_class,
        "selected_section": selected_section,
        "selected_date": selected_date,
        "class_choices": Student.CLASS_CHOICES,
        "section_choices": Student.SECTION_CHOICES,
        "today": today,
    }
    return render(request, "attendance/mark_attendance.html", context)


# --- Reports ---


@login_required
def daily_report(request):
    today = date.today()
    selected_date = request.GET.get("date", today.isoformat())
    try:
        report_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        report_date = today

    records = Attendance.objects.filter(date=report_date).select_related("student")
    summary = records.values("status").annotate(count=Count("id"))

    summary_dict = {"present": 0, "absent": 0, "late": 0}
    for item in summary:
        summary_dict[item["status"]] = item["count"]

    context = {
        "records": records,
        "report_date": report_date,
        "selected_date": selected_date,
        "summary": summary_dict,
        "total": records.count(),
    }
    return render(request, "attendance/daily_report.html", context)


@login_required
def monthly_report(request):
    today = date.today()
    selected_month = request.GET.get("month", str(today.month))
    selected_year = request.GET.get("year", str(today.year))
    selected_class = request.GET.get("student_class", "")
    selected_section = request.GET.get("section", "")

    try:
        month = int(selected_month)
        year = int(selected_year)
    except ValueError:
        month = today.month
        year = today.year

    students = Student.objects.all()
    if selected_class:
        students = students.filter(student_class=selected_class)
    if selected_section:
        students = students.filter(section=selected_section)

    report_data = []
    for student in students:
        records = student.attendance_records.filter(date__month=month, date__year=year)
        total = records.count()
        present = records.filter(status__in=["present", "late"]).count()
        absent = records.filter(status="absent").count()
        pct = round((present / total) * 100, 1) if total > 0 else 0
        report_data.append(
            {
                "student": student,
                "total_days": total,
                "present": present,
                "absent": absent,
                "percentage": pct,
            }
        )

    context = {
        "report_data": report_data,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_class": selected_class,
        "selected_section": selected_section,
        "class_choices": Student.CLASS_CHOICES,
        "section_choices": Student.SECTION_CHOICES,
        "months": [(str(i), datetime(2000, i, 1).strftime("%B")) for i in range(1, 13)],
        "years": [str(y) for y in range(year - 2, year + 1)],
    }
    return render(request, "attendance/monthly_report.html", context)


# --- Helper ---


def _is_admin(user):
    try:
        return user.profile.role == "admin"
    except UserProfile.DoesNotExist:
        return user.is_superuser
