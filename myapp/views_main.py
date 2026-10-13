from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.core.mail import EmailMultiAlternatives
import os
from .forms import *
from collections import defaultdict
from django.core.paginator import Paginator
from openai import OpenAI
from django.urls import reverse
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Lecture, Course
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.contrib.auth.models import Group
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
import csv
from django.http import HttpResponse
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
import json


from .utils import *
from decimal import Decimal
# Create your views here.



def mainView():
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    return {
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    }
    


def custom_404(request, exception):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    context = {
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    }
    return render(request, '404.html', context) 
                  
def MyHome(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    GetAboutSchoolSec = AboutSchool.objects.all()[1] if AboutSchool.objects.count() > 1 else None
    QuestionCount = Question.objects.distinct().count()
    TeacherCount = Teacher.objects.distinct().count()
    CourseCount = Course.objects.distinct().count()
    SliderImagex = SliderImage.objects.all()
    StudentCount = Student.objects.distinct().count()

    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if not all([name, email, subject, message]):
            return JsonResponse({'error': 'All fields are required.'}, status=400)

        # Save to database
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        # Send email
        try:
            send_mail(
                subject=f"New Contact Message: {subject}",
                message=f"From: {name} <{email}>\n\nMessage:\n{message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        # If AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': 'Your message has been sent successfully!'})

        # Fallback (non-AJAX)
        messages.success(request, "Your message has been sent successfully!")
        return redirect('MyHome')

    context = {
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
        'GetAboutSchoolSec': GetAboutSchoolSec,
        'QuestionCount': QuestionCount,
        'TeacherCount': TeacherCount,
        'courseCount': CourseCount,
        'StudentCount': StudentCount,
        'slides':SliderImagex
    }
    return render(request, 'index.html', context)


def load_classgroups(request):
    department_id = request.GET.get('department_id')
    classgroups = ClassGroup.objects.filter(department_id=department_id).values('id', 'name')
    return JsonResponse(list(classgroups), safe=False)


def load_courses(request):
    department_id = request.GET.get('department_id')
    classgroup_id = request.GET.get('classgroup_id')
    courses = Course.objects.filter(department_id=department_id, classgroup_id=classgroup_id).values('id', 'title')
    return JsonResponse(list(courses), safe=False)


def register_student(request):
    # Fetch school details
    getTitle = title.objects.first()
    getLogo = schoollogo.objects.first()
    GetAboutSchool = AboutSchool.objects.first()

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()  # ✅ The form handles both User + Student creation internally

                # ✅ Automatically add to "Student" group
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)

                messages.success(request, f"✅ Student '{user.get_full_name()}' registered successfully!")
                return redirect('SuccessPage')  # change to your real success page
            except IntegrityError as e:
                if 'admission_number' in str(e):
                    messages.error(request, "⚠️ This admission/matric number already exists.")
                else:
                    messages.error(request, f"⚠️ Database error: {str(e)}")
        else:
            # Collect all form errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            messages.error(request, "⚠️ Please fix these errors: " + "; ".join(error_messages))
    else:
        form = StudentRegistrationForm()

    context = {
        'form': form,
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    }
    return render(request, 'student_registration.html', context)




@login_required(login_url='LoginUser')
def lecture_list(request):
    if not request.user.groups.filter(name='Educator').exists():
        return redirect("LoginUser")
    
    user = request.user
    print(user)
    teacher = get_object_or_404(Teacher, user=user)
    the_courses = teacher.courses.all()
    courses = Course.objects.all()
    lectures = Lecture.objects.filter(course__in=courses).order_by("-created_at")
    # Metrics
    total_lectures = lectures.count()
    total_views = sum(l.views for l in lectures)
    new_this_week = lectures.filter(created_at__gte=timezone.now()-timezone.timedelta(days=7)).count()
    avg_completion = 75  # placeholder, compute from sessions if you track them

    # Breakdown for charts
    types_breakdown = {}
    for l in lectures:
        types_breakdown[l.content_type] = types_breakdown.get(l.content_type, 0) + 1

    views_series = [
        {"date": l.created_at.strftime("%Y-%m-%d"), "views": l.views}
        for l in lectures.order_by("created_at")[:10]
    ]
    assignment_fetch = Assignment.objects.all().distinct()
    context = {
        "lectures": lectures,
        "assignment_fetch":assignment_fetch,
        "courses": courses,
        "the_course":the_courses,
        "total_lectures": total_lectures,
        "total_views": total_views,
        "new_this_week": new_this_week,
        "avg_completion": avg_completion,
        "types_breakdown_json": json.dumps(types_breakdown),
        "views_series_json": json.dumps(views_series),
        "top_tags": [],  # compute if needed
        "recent_activity": [],  # fill with logs if you track them
    }
    return render(request, "elearning/lecture_list.html", context)


@login_required(login_url='LoginUser')
def delete_assignment_ajax(request, assignment_id):
    if not request.user.groups.filter(name='Educator').exists():
        return JsonResponse({"error": "Not authorized"}, status=403)

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        teacher = Teacher.objects.get(user=request.user)
        assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
        assignment.delete()
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid request"}, status=400)



@login_required(login_url='LoginUser')
def add_assignment_ajax(request):
    if not request.user.groups.filter(name='Educator').exists():
        return JsonResponse({"error": "Not authorized"}, status=403)

    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        teacher = Teacher.objects.get(user=request.user)
        course_id = request.POST.get("course")
        title = request.POST.get("title")
        description = request.POST.get("description")
        attachment = request.FILES.get("attachment")
        due_date_str = request.POST.get("due_date")

        if not (course_id and title and due_date_str):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        try:
            course = Course.objects.get(id=course_id)
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()

            assignment = Assignment.objects.create(
                teacher=teacher,
                course=course,
                title=title,
                description=description,
                attachment=attachment, 
                due_date=due_date
            )

            data = {
                "id": assignment.id,
                "title": assignment.title,
                'attachment':assignment.attachment.url if assignment.attachment else "",
                "course": assignment.course.title,  # FIXED
                "due_date": assignment.due_date.strftime("%Y-%m-%d")
            }

            return JsonResponse({"success": True, "assignment": data})
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)

    return JsonResponse({"error": "Invalid request"}, status=400)




def lecture_preview(request, pk):
    lecture = get_object_or_404(Lecture, pk=pk)

    # Increment views and update last_viewed
    lecture.views += 1
    lecture.last_viewed = timezone.now()
    lecture.save()

    return render(request, "elearning/lecture_preview.html", {"lecture": lecture})


def lecture_student_view(request, pk):
    lecture = get_object_or_404(Lecture, pk=pk)
    avg_rating = lecture.votes.aggregate(Avg("rating"))["rating__avg"]
    return render(request, "elearning/lecture_student_view.html", {
        "lecture": lecture,
        "avg_rating": round(avg_rating or 0, 1),
    })

@csrf_exempt
def lecture_vote(request, pk):
    if request.method == "POST":
        lecture = get_object_or_404(Lecture, pk=pk)
        rating = int(request.POST.get("rating"))
        vote, created = LectureVote.objects.update_or_create(
            lecture=lecture, student=request.user,
            defaults={"rating": rating}
        )
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid request"}, status=400)

def lecture_upload(request):
    if request.method == "POST":
        title = request.POST.get("title")
        course_id = request.POST.get("course_id")
        course = get_object_or_404(Course, id=course_id)
        content_type = request.POST.get("content_type")
        description = request.POST.get("description")
        tags = request.POST.get("tags", "")
        status = request.POST.get("status", "DRAFT")
        duration = request.POST.get("duration")

        lecture = Lecture.objects.create(
            title=title,
            description=description,
            course=course,
            content_type=content_type,
            tags=tags,
            status=status,
            duration=duration or None,
        )
        if content_type != "LINK" and "file" in request.FILES:
            lecture.file = request.FILES["file"]
        elif content_type == "LINK":
            lecture.external_url = request.POST.get("external_url")
        lecture.save()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def lecture_toggle_status(request):
    if request.method == "POST":
        lecture_id = request.POST.get("lecture_id")
        lecture = get_object_or_404(Lecture, id=lecture_id)
        lecture.status = "LIVE" if lecture.status == "DRAFT" else "DRAFT"
        lecture.save()
        return JsonResponse({"success": True, "status": lecture.status})
    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def lecture_delete(request):
    if request.method == "POST":
        lecture_id = request.POST.get("lecture_id")
        lecture = get_object_or_404(Lecture, id=lecture_id)
        lecture.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid request"}, status=400)


def export_lectures_csv(request):
    lectures = Lecture.objects.all()
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="lectures.csv"'
    writer = csv.writer(response)
    writer.writerow(["Title", "Course", "Type", "Views", "Status", "Created"])
    for l in lectures:
        writer.writerow([l.title, l.course.title, l.content_type, l.views, l.status, l.created_at])
    return response

def register_teacher(request):
    getTitle = title.objects.first()
    getLogo = schoollogo.objects.first()
    GetAboutSchool = AboutSchool.objects.first()

    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            teacher = form.save()  # ✅ form already creates linked user
            educator_group, _ = Group.objects.get_or_create(name='Educator')
            teacher.user.groups.add(educator_group)

            messages.success(request, f"✅ {teacher.full_name} registered successfully and added to Educator group.")
            return redirect('teacher_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').capitalize()}: {error}")
    else:
        form = TeacherRegistrationForm()

    context = {
        'form': form,
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    }
    return render(request, 'teacher_form.html', context)


def teacher_list(request):
    getTitle = title.objects.first()
    getLogo = schoollogo.objects.first()
    GetAboutSchool = AboutSchool.objects.first()
    teachers= Teacher.objects.all().select_related('user')  # Efficiently fetch related user info
    context = {
        'teachers': teachers,
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    }
    return render(request, 'teacher_list.html',context)


def SuccessPage(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    context = {
        'getTitle':getTitle,
        'getLogo':getLogo,
        'AboutSchool':GetAboutSchool
    }
    return render(request, 'success_page.html', context)


def LoginUser(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    
    next_url = request.GET.get('next') or request.POST.get('next') or None
    
    if request.method == "POST":
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if user.groups.filter(name="Educator").exists():
                return redirect("Teacherdashboard")

            if user.groups.filter(name="Student").exists():
                return redirect("student_dashboard")

            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")
        else:
            messages.warning(request, 'Authentication Failed... Username or Password Error')
    else:
        form = LoginForm()
    context = {
        'getTitle':getTitle,
        'getLogo':getLogo,
        'AboutSchool':GetAboutSchool,
        'form': form, 'next': next_url or '',
    }
    return render(request, 'login.html', context)

# API_URL = "https://router.huggingface.co/hf-inference/models/valurank/MiniLM-L6-Keyword-Extraction/pipeline/sentence-similarity"
import requests
API_FOR_GEN = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"

HF_TOKEN = settings.HF_TOKEN_API
API_URL = "https://router.huggingface.co/valurank/MiniLM-L6-Keyword-Extraction/pipeline/sentence-similarity"


headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Quick test function










import wikipedia
@login_required(login_url='LoginUser')
def student_dashboard(request):
    
    video_id = None
    raw_query = request.GET.get("q")

    # Run keyphrase extraction if user enters a query
    hr_result = None
    query_text = None
    resultMain = None

    if raw_query:
        hr_result =  raw_query

        # HuggingFace returns [{"score":..., "word": "keyword"}, ...]
        if hr_result:
            query_text = hr_result  # use best keyword
            try:
                summary = wikipedia.summary(query_text, sentences=3)  # FIXED
                resultMain = summary
                if resultMain:
                    print(resultMain)
                else:
                    print("Failed")
            except wikipedia.exceptions.DisambiguationError as e:
                resultMain = f"Multiple results found: {e.options}"
            except Exception as e:
                resultMain = f"Error: {str(e)}"
        else:
            query_text = raw_query
            print(query_text)


        # YOUTUBE SEARCH
        api_key = settings.YOUTUBE_API_KEY
        url = "https://www.googleapis.com/youtube/v3/search"

        params = {
            "part": "snippet",
            "q": query_text,
            "type": "video",
            "maxResults": 1,
            "key": api_key,
        }

        yt_response = requests.get(url, params=params).json()
        if yt_response.get("items"):
            video_id = yt_response["items"][0]["id"]["videoId"]

    # -------- DB DATA -------- #
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    GetAboutSchoolSec = AboutSchool.objects.all()[1] if AboutSchool.objects.count() > 1 else None

    student = get_object_or_404(Student, user=request.user)

    courses = (
        student.courses
        .all()
        .prefetch_related("lectures", "lectures__votes")
    )

    total_lectures = sum(c.lectures.count() for c in courses)
    total_votes = sum(l.votes.count() for c in courses for l in c.lectures.all())
    user = request.user
    courseUser = get_object_or_404(Student, user=user)
    getTheCourse = courseUser.courses.all()
    assessment_count = Assignment.objects.filter(course__in=getTheCourse).distinct().count()

    # Compute completed lectures for the chart
    for c in courses:
    # If no completed lecture logic yet, assume 0 completed
        c.completed_lectures = getattr(c, "completed_lectures", 0)
        c.remaining_lectures = c.lectures.count() - c.completed_lectures

    return render(request, "elearning/student_dashboard.html", {
        "student": student,
        "getTitle": getTitle,
        "getLogo": getLogo,
        "assessment_count":assessment_count,
        "GetAboutSchool": GetAboutSchool,
        "GetAboutSchoolSec": GetAboutSchoolSec,

        "courses": courses,
        "total_lectures": total_lectures,
        "total_votes": total_votes,

        # VIDEO
        "video_id": video_id,
        "query": query_text,
        # "results":resultMain,
    })
    
    
@login_required(login_url='LoginUser')
def course_detail(request, course_id):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    GetAboutSchoolSec = AboutSchool.objects.all()[1] if AboutSchool.objects.count() > 1 else None
    course = get_object_or_404(Course, id=course_id)
    return render(request, "elearning/course_detail.html", {
        "course": course,
        'getTitle':getTitle,
        'getLogo':getLogo,
        'GetAboutSchoolSec':GetAboutSchoolSec,
        'GetAboutSchool':GetAboutSchool,
        "student": request.user.student_profile,  # if you have Student linked to User
    })


# @login_required(login_url='LoginUser')
# def techcourse_list(request):
#     techcourses = TechCourse.objects.all()
#     context = {
#         "techcourses": techcourses
#     }
#     context.update(mainView())
#     return render(request, "elearning/techcourse.html", context)


@login_required(login_url='LoginUser')
def techcourse_list(request):
    category_id = request.GET.get("category")

    techcourses = TechCourse.objects.all().order_by("-created_at")
    categories = TechCourse_Category.objects.all()

    if category_id:
        techcourses = techcourses.filter(category_id=category_id)

    paginator = Paginator(techcourses, 6)  # 6 courses per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "techcourses": page_obj,
        "categories": categories,
        "active_category": category_id,
    }

    context.update(mainView())
    return render(request, "elearning/techcourse.html", context)

import re

@login_required(login_url="LoginUser")
def techcourse_detail(request, id):
    course = get_object_or_404(TechCourse, id=id)

    video_id = None
    drive_id = None

    # If YouTube Link
    if "youtube" in course.link or "youtu.be" in course.link:
        match = re.search(r"(?:v=|youtu\.be/)([^&?/]+)", course.link)
        if match:
            video_id = match.group(1)

    # If Google Drive Link
    elif "drive.google.com" in course.link:
        match = re.search(r"/d/([^/]+)", course.link)
        if match:
            drive_id = match.group(1)

    context = {
        "course": course,
        "video_id": video_id,
        "drive_id": drive_id,
    }

    context.update(mainView())

    return render(request, "elearning/techcourse_detail.html", context)


# -- E library -- #
login_required(login_url="LoginUser")
def elibrary_list(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    
    """Show all resources in the E-Library"""
    resources = Elibrary.objects.all().order_by("-uploaded_at")
    context = {
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
        "elibrary_list": resources
    }
    return render(request, "elearning/elibrary.html", context)



@login_required
def assignments_view(request):
    """
    Student Assignment Dashboard
    """

    try:
        student = request.user.student_profile
    except Exception:
        student = None

    today = timezone.now().date()

    # Fetch assignments (latest first)
    assignments = Assignment.objects.select_related(
        'teacher'
    ).order_by('-due_date')

    # Fetch student submissions
    submissions = AssignmentSubmission.objects.filter(
        student=student
    ).select_related('assignment')

    # Map submissions by assignment id
    submission_map = {
        s.assignment_id: s for s in submissions
    }

    # Attach dynamic fields for template
    for assignment in assignments:
        assignment.is_due = timezone.now() > assignment.due_date

        submission = submission_map.get(assignment.id)

        assignment.is_submitted = True if submission else False
        assignment.score = submission.score if submission else None
        assignment.feedback = submission.feedback if submission else None

    context = {
        "assignments": assignments,
        "student": student,        
    }
    context.update(mainView())
    
    return render(request, "elearning/assignments.html", context)


@login_required
def submit_assignment(request, assignment_id):

    assignment = get_object_or_404(Assignment, id=assignment_id)

    try:
        student = request.user.student_profile
    except:
        messages.error(request, "Student profile not found.")
        return redirect('assignments_view')

    now = timezone.now()

    # Check deadline
    is_due = now > assignment.due_date

    # Prevent multiple submissions
    already_submitted = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student
    ).first()

    if already_submitted:
        messages.warning(request, "You already submitted this assignment.")
        return redirect('assignments_view')

    if request.method == "POST":

        if is_due:
            messages.error(request, "Assignment is overdue.")
            return redirect('assignments_view')

        form = AssignmentSubmissionForm(request.POST, request.FILES)

        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = student
            submission.save()

            messages.success(request, "Assignment submitted successfully.")
            return redirect('assignments_view')

    else:
        form = AssignmentSubmissionForm()

    context = {
        "assignment": assignment,
        "form": form,
        "is_due": is_due
    }
    context.update(mainView())
    
    return render(request, "elearning/submit_assignment.html", context)


# -- Times Table --
@login_required
def create_timetable(request):
    form = TimetableForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Timetable entry created successfully")
                return redirect("create_timetable")
            except Exception as e:
                messages.error(request, f"Error: {e}")

    return render(request, "elearning/timetablecreate.html", {"form": form})

def student_timetable(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    
    """Show all resources in the E-Library"""
    
    
    student = request.user.student_profile
    enrollment = student.enrollments.filter(session__is_current=True).first()

    timetable = Timetable.objects.filter(
        session=enrollment.session,
        classgroup=enrollment.classgroup
    ).select_related(
        'course', 'teacher', 'classroom', 'day', 'time_slot'
    )
    context = {
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
        "timetable": timetable
    }
    return render(request, "elearning/timetable_view.html", context)
    

@login_required
def teacher_timetable(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    teacher = request.user.teacher_profile

    timetable = Timetable.objects.filter(
        teacher=teacher,
        session__is_current=True
    ).select_related(
        'course', 'classgroup', 'classroom', 'day', 'time_slot'
    )

    return render(request, "elearning/teacherTimeTableView.html", {
        "timetable": timetable,
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    })

def timetable_grid(request):
    timetable_qs = Timetable.objects.select_related(
        'classgroup', 'course', 'day', 'time_slot'
    )
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    time_slots = TimeSlot.objects.all().order_by('start_time')
    days = Day.objects.all()
    classes = ClassGroup.objects.all()

    # Structure:
    # timetable[class][day][time_slot] = course
    timetable = defaultdict(lambda: defaultdict(dict))

    for entry in timetable_qs:
        timetable[entry.classgroup][entry.day][entry.time_slot] = entry.course.title

    context = {
        'time_slots': time_slots,
        'days': days,
        'classes': classes,
        'timetable': timetable,
        'getTitle': getTitle,
        'getLogo': getLogo,
        'AboutSchool': GetAboutSchool,
    }
    return render(request, 'elearning/timetablegrid.html', context)



def elibrary_detail(request, pk):
    """Show details of a single resource"""
    resource = get_object_or_404(Elibrary, pk=pk)
    return render(request, "elearning/elibrary_detail.html", {
        "resource": resource
    })

# AI - Assistance 
import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from .models import Student, Lecture

import PyPDF2
import docx
client = OpenAI(api_key=settings.OPENAI_API_KEY)
@login_required(login_url="LoginUser")
@csrf_exempt
def ai_assistance(request):

    # ==============================
    # STUDENT + LECTURES CONTEXT
    # ==============================
    user = request.user
    getStudent = get_object_or_404(Student, user=user)

    getStudentCourse = getStudent.courses.all()
    getLectures = Lecture.objects.filter(course__in=getStudentCourse)

    context = {
        "getLectures": getLectures
    }

    context.update(mainView())

    # ==============================
    # PAGE LOAD (GET)
    # ==============================
    if request.method == "GET":
        return render(request, "elearning/ai_assistance.html", context)

    # ==============================
    # AI CHAT + FILE SUPPORT (POST)
    # ==============================
    if request.method == "POST":

        prompt = request.POST.get("prompt", "").strip()
        uploaded_file = request.FILES.get("file")

        # ==============================
        # 1. HANDLE FILE UPLOAD
        # ==============================
        if uploaded_file:

            filename = uploaded_file.name.lower()
            file_text = ""

            try:
                # TXT FILES
                if filename.endswith(".txt"):
                    file_text = uploaded_file.read().decode("utf-8")

                # PDF FILES
                elif filename.endswith(".pdf"):
                    reader = PyPDF2.PdfReader(uploaded_file)

                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            file_text += extracted + "\n"

                # DOCX FILES
                elif filename.endswith(".docx"):
                    document = docx.Document(uploaded_file)

                    for para in document.paragraphs:
                        file_text += para.text + "\n"

                else:
                    return JsonResponse({
                        "response": "Unsupported file type. Upload PDF, DOCX, or TXT only."
                    })

                # ==============================
                # SAVE DOCUMENT INTO SESSION MEMORY
                # ==============================
                request.session["uploaded_doc"] = file_text

                return JsonResponse({
                    "response": f"Document '{uploaded_file.name}' uploaded successfully.\n\nNow ask me questions from it!"
                })

            except Exception as e:
                return JsonResponse({
                    "response": f"Error reading document: {str(e)}"
                })

        # ==============================
        # 2. HANDLE NORMAL QUESTIONS
        # ==============================

        # If no prompt provided
        if not prompt:
            return JsonResponse({
                "response": "Please type a question or upload a document."
            })

        # Get stored document memory
        stored_doc = request.session.get("uploaded_doc", "")

        # If user asks from document but none uploaded
        if "document" in prompt.lower() and not stored_doc:
            return JsonResponse({
                "response": "No document uploaded yet. Please upload one first."
            })

        # ==============================
        # 3. BUILD FINAL PROMPT WITH MEMORY
        # ==============================
        if stored_doc:
            final_prompt = f"""
        You are an educational AI assistant.

        The student uploaded this document:

        DOCUMENT CONTENT:
        {stored_doc}

        Now answer this question based strictly on the document:

        QUESTION:
        {prompt}

        Explain clearly like a tutor.
        """
        else:
            final_prompt = prompt

        # ==============================
        # 4. SEND TO OPENAI
        # ==============================
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an educational AI assistant for Secondary School students."
                },
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],
            max_tokens=500
        )

        answer = response.choices[0].message.content

        return JsonResponse({"response": answer})   

@login_required
def logout_user(request):
    """Logs out the current user and redirects to login page."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('LoginUser')  # Change to your actual login URL name

def dashboard(request):
    return render(request, 'dashboard.html')

def Teacherdashboard(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    context = {
        'getTitle':getTitle,
        'getLogo':getLogo,
        'AboutSchool':GetAboutSchool,        
    }
    return render(request, 'Teacherdashboard.html', context)


@login_required
def add_questions(request, exam_id=None):
    teacher = getattr(request.user, 'teacher_profile', None)
    if not teacher:
        messages.error(request, "You must be logged in as a teacher.")
        return redirect('Teacherdashboard')

    departments = teacher.department.all()
    classes = teacher.class_groups.all()
    courses = teacher.courses.all()
    exam = None

    # Editing existing exam
    if exam_id:
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.created_by != request.user:
            messages.error(request, "You don’t have permission to edit this exam.")
            return redirect('Teacherdashboard')

    # Handle course selection (create or reuse exam)
    elif request.method == 'POST' and 'select_course' in request.POST:
        dept_id = request.POST.get('department')
        class_id = request.POST.get('classgroup')
        course_id = request.POST.get('course')

        if not (dept_id and class_id and course_id):
            messages.warning(request, "Please select department, class, and course.")
            return redirect('add_questions')

        department = get_object_or_404(Department, id=dept_id)
        classgroup = get_object_or_404(ClassGroup, id=class_id)
        course = get_object_or_404(Course, id=course_id)

        # ✅ Check if exam already exists for this teacher, class, and course
        existing_exam = Exam.objects.filter(
            course=course,
            class_groups=classgroup,
            created_by=request.user,
            title__icontains=classgroup.name  # Adjust this if titles are unique differently
        ).first()

        if existing_exam:
            messages.info(request, f"Exam for '{course.title}' ({classgroup.name}) already exists.")
            return redirect('add_questions', exam_id=existing_exam.id)
        else:
            # Create new exam
            exam = Exam.objects.create(
                course=course,
                class_groups=classgroup,
                title=f"{course.title} Exam ({classgroup.name})",
                created_by=request.user,
            )
            messages.success(request, f"Exam '{exam.title}' created successfully.")
            return redirect('add_questions', exam_id=exam.id)

    # Add questions to an existing exam
    if request.method == 'POST' and 'save_questions' in request.POST:
        exam_id = request.POST.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id)

        created_count = 0
        question_index = 1
        term = request.POST.get('term', '').strip().title()

        while True:
            q_text = request.POST.get(f'question_text_{question_index}')
            if not q_text:
                break

            option_a = request.POST.get(f'option_a_{question_index}', '').strip()
            option_b = request.POST.get(f'option_b_{question_index}', '').strip()
            option_c = request.POST.get(f'option_c_{question_index}', '').strip()
            option_d = request.POST.get(f'option_d_{question_index}', '').strip()
            correct = request.POST.get(f'correct_answer_{question_index}', '').strip().upper()

            if q_text.strip() and correct in ['A', 'B', 'C', 'D']:
                Question.objects.create(
                    exam=exam,
                    question_text=q_text.strip(),
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_answer=correct,
                    term=term
                )
                created_count += 1

            question_index += 1

        if created_count:
            messages.success(request, f"{created_count} question(s) added to '{exam.title}'.")
            return redirect('exam_detail', exam_id=exam.id)
        else:
            messages.warning(request, "No valid questions were submitted.")

    context = {
        'exam': exam,
        'departments': departments,
        'classes': classes,
        'courses': courses,
        'teacher': teacher,
        'form': QuestionForm(),
    }
    return render(request, 'add_questions.html', context)



# @login_required
# def add_questions(request, exam_id=None):
#     teacher = getattr(request.user, 'teacher_profile', None)
#     if not teacher:
#         messages.error(request, "You must be logged in as a teacher.")
#         return redirect('Teacherdashboard')

#     departments = teacher.department.all()
#     classes = teacher.class_groups.all()
#     courses = teacher.courses.all()
#     exam = None

#     # --- Editing existing exam ---
#     if exam_id:
#         exam = get_object_or_404(Exam, id=exam_id)
#         if exam.created_by != request.user:
#             messages.error(request, "You don’t have permission to edit this exam.")
#             return redirect('Teacherdashboard')

#     # --- Handle course selection (create or reuse exam) ---
#     elif request.method == 'POST' and 'select_course' in request.POST:
#         dept_id = request.POST.get('department')
#         class_id = request.POST.get('classgroup')
#         course_id = request.POST.get('course')

#         if not (dept_id and class_id and course_id):
#             messages.warning(request, "Please select department, class, and course.")
#             return redirect('add_questions')

#         department = get_object_or_404(Department, id=dept_id)
#         classgroup = get_object_or_404(ClassGroup, id=class_id)
#         course = get_object_or_404(Course, id=course_id)

#         # ✅ Check if exam already exists for this teacher, class, and course
#         existing_exam = Exam.objects.filter(
#             course=course,
#             created_by=request.user,
#             title__icontains=classgroup.name
#         ).first()

#         if existing_exam:
#             messages.info(request, f"Exam for '{course.title}' ({classgroup.name}) already exists.")
#             return redirect('add_questions_with_id', exam_id=existing_exam.id)
#         else:
#             # ✅ Create new exam
#             exam = Exam.objects.create(
#                 course=course,
#                 title=f"{course.title} Exam ({classgroup.name})",
#                 created_by=request.user,
#             )
#             messages.success(request, f"Exam '{exam.title}' created successfully.")
#             return redirect('add_questions_with_id', exam_id=exam.id)

#     # --- Add questions to an existing exam ---
#     if request.method == 'POST' and 'save_questions' in request.POST:
#         exam_id = request.POST.get('exam_id')
#         exam = get_object_or_404(Exam, id=exam_id)

#         created_count = 0
#         question_index = 1
#         term = request.POST.get('term', '').strip().title()

#         while True:
#             q_text = request.POST.get(f'question_text_{question_index}')
#             if not q_text:
#                 break

#             option_a = request.POST.get(f'option_a_{question_index}', '').strip()
#             option_b = request.POST.get(f'option_b_{question_index}', '').strip()
#             option_c = request.POST.get(f'option_c_{question_index}', '').strip()
#             option_d = request.POST.get(f'option_d_{question_index}', '').strip()
#             correct = request.POST.get(f'correct_answer_{question_index}', '').strip().upper()

#             if q_text.strip() and correct in ['A', 'B', 'C', 'D']:
#                 Question.objects.create(
#                     exam=exam,
#                     question_text=q_text.strip(),
#                     option_a=option_a,
#                     option_b=option_b,
#                     option_c=option_c,
#                     option_d=option_d,
#                     correct_answer=correct,
#                     term=term
#                 )
#                 created_count += 1

#             question_index += 1

#         if created_count:
#             messages.success(request, f"{created_count} question(s) added to '{exam.title}'.")
#             return redirect('exam_detail', exam_id=exam.id)
#         else:
#             messages.warning(request, "No valid questions were submitted.")

#     context = {
#         'exam': exam,
#         'departments': departments,
#         'classes': classes,
#         'courses': courses,
#         'teacher': teacher,
#         'form': QuestionForm(),
#     }
#     return render(request, 'add_questions.html', context)




# def exam_detail(request, exam_id):
#     # Get the specific exam or return 404 if not found
#     exam = get_object_or_404(Exam, id=exam_id)
    
#     # Fetch all courses created by the same teacher
#     courses = Exam.objects.filter(created_by=exam.created_by).distinct()
    
#     # Fetch all questions for this exam
#     questions = Question.objects.filter(exam=exam).order_by('id')

#     context = {
#         'exam': exam,
#         'courses': courses,  # pass to template
#         'questions': questions,
#     }

#     return render(request, 'exam_details.html', context)


# @login_required
# def exam_detail(request, exam_id):
#     exam = get_object_or_404(Exam, id=exam_id)

#     teacher = request.user
#     exams = Exam.objects.filter(created_by=teacher).select_related('course').order_by('course__title')
#     questions = Question.objects.filter(exam=exam).order_by('id')

#     # Related info
#     # Related info
#     department = exam.course.department
#     course = exam.course
#     classgroup = exam.class_groups  # ✅ correct class group
#     all_classgroups = ClassGroup.objects.all().order_by('name')

#     # ✅ Fetch all exam schedules related to this exam
#     schedules = ExamSchedule.objects.filter(exam=exam).select_related(
#         'department', 'class_level', 'course_name'
#     ).order_by('-scheduled_date', '-start_time')  # Latest first

#     # ✅ If you still need a single schedule for modal or display
#     schedule = schedules.first() if schedules.exists() else None

#     # ✅ Get students registered for this course
#     students = Student.objects.filter(
#         courses=course,
#         level_or_class=classgroup
#     ).select_related('department').distinct()

#     context = {
#         'exam': exam,
#         'course': course,
#         'exams': exams,
#         'all_classgroups': all_classgroups, 
#         'questions': questions,
#         'department': department,
#         'classgroup': classgroup,
#         'students': students,
#         'schedules': schedules,  # ✅ all schedules
#         'schedule': schedule,    # ✅ first schedule (optional)
#     }

#     return render(request, 'exam_details.html', context)



@login_required
def exam_detail(request, exam_id):
    getSession = Session.objects.all()
    exam = get_object_or_404(
        Exam.objects.select_related('course__department').prefetch_related('questions'),
        id=exam_id
    )

    teacher = request.user

    # Fetch only this teacher's exams (for sidebar or listing)
    exams = (
        Exam.objects.filter(created_by=teacher)
        .select_related('course__department')
        .order_by('course__title')
    )

    import re
    for e in exams:
        class_name = e.class_groups.name.strip() if e.class_groups else ""
        raw_title = e.title.strip()

        # Remove any prefix like "SS1", "JSS2", "Year 1", etc.
        raw_title_clean = re.sub(r'^(SS|JSS|Grade|Year)\s*\d+\s*[A-Z]?\s*', '', raw_title, flags=re.IGNORECASE).strip()
        e.display_title = f"{class_name} {raw_title_clean}"
            
    course = exam.course
    department = course.department
    classgroup = exam.class_groups  # ✅ the assigned class
    print(classgroup)
    all_classgroups = ClassGroup.objects.all().order_by('name')

    # ✅ Get all exam schedules for this exam
    schedules = (
        ExamSchedule.objects.filter(exam=exam)
        .select_related('department', 'class_level', 'course_name')
        .order_by('-scheduled_date', '-start_time')
    )

    schedule = schedules.first() if schedules.exists() else None
    print(course)

    # ✅ Fetch all students registered for this course *and* class group
    students = (
        Student.objects.filter(courses=course, level_or_class=classgroup)
        .select_related('department', 'level_or_class')
        .distinct()
    )

    context = {
        'exam': exam,
        'getSession':getSession,
        'course': course,
        'department': department,
        'classgroup': classgroup,
        'exams': exams,
        'questions': exam.questions.all(),
        'students': students,
        'all_classgroups': all_classgroups,
        'schedules': schedules,
        'schedule': schedule,
    }

    return render(request, 'exam_details.html', context)


@login_required
def MyStudent(request, classgroup_id, course_id):
    classgroup = get_object_or_404(ClassGroup, id=classgroup_id)
    course = get_object_or_404(Course, id=course_id)

    # ✅ Fetch students registered for this course AND in this class group
    students = (
        Student.objects.filter(
            level_or_class=classgroup,
            
        )
        .select_related('department', 'level_or_class')
        .distinct()
    )

    context = {
        'classgroup': classgroup,
        'course': course,
        'students': students,
    }

    return render(request, 'MyStudent.html', context)




@login_required
def publish_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.method == "POST":
        selected_ids = request.POST.getlist("class_groups")
        target_groups = ClassGroup.objects.filter(id__in=selected_ids)

        # Get all questions from the current exam
        questions = Question.objects.filter(exam=exam)

        published_to = []   # Keep track of new publications
        skipped = []        # Keep track of duplicates

        for group in target_groups:
            # ✅ Check if an exam already exists for this course and class group
            existing_exam = Exam.objects.filter(
                course=exam.course,
                class_groups=group,
                created_by=request.user
            ).first()

            if existing_exam:
                skipped.append(group.name)
                continue  # skip this one — it's already published

            # ✅ Create a new exam for this class group
            new_exam = Exam.objects.create(
                course=exam.course,
                class_groups=group,
                created_by=request.user,
                title=f"{exam.course.title} Exam ({group.name})"
            )

            # ✅ Copy questions to the new exam
            Question.objects.bulk_create([
                Question(
                    exam=new_exam,
                    question_text=q.question_text,
                    option_a=q.option_a,
                    option_b=q.option_b,
                    option_c=q.option_c,
                    option_d=q.option_d,
                    correct_answer=q.correct_answer,
                    term = q.term
                ) for q in questions
            ])

            published_to.append(group.name)

        # ✅ Prepare feedback message
        message_parts = []
        if published_to:
            message_parts.append(f"Published to: {', '.join(published_to)}.")
        if skipped:
            message_parts.append(f"Skipped duplicates for: {', '.join(skipped)}.")

        message = " ".join(message_parts) or "No class groups selected."

        return JsonResponse({
            "success": True,
            "message": message
        })

    return JsonResponse({"error": "Invalid request."}, status=400)




@login_required
def edit_question(request):
    if request.method == "POST":
        qid = request.POST.get("question_id")
        question = get_object_or_404(Question, id=qid)
        question.question_text = request.POST.get("question_text")
        question.option_a = request.POST.get("option_a")
        question.option_b = request.POST.get("option_b")
        question.option_c = request.POST.get("option_c")
        question.option_d = request.POST.get("option_d")
        question.correct_answer = request.POST.get("correct_answer")
        question.term = request.POST.get("term")
        question.save()
        messages.success(request, "Question updated successfully!")
        return redirect('exam_detail', exam_id=question.exam.id)



def teacher_manage_course(request):
    teacher = request.user
    # Fetch all courses that have exams by this teacher
    courses = (
        Course.objects
        .filter(exam__created_by=teacher)
        .annotate(question_count=Count('exam__questions', distinct=True))  # ✅ Count questions per course
        .distinct()
        .prefetch_related('exam_set')
    )

    # ✅ Total count of all questions created by this teacher
    total_question_count = Question.objects.filter(exam__created_by=teacher).count()

    context = {
        'courses': courses,
        'total_question_count': total_question_count
    }
    return render(request, 'teacher_manage_course.html', context)


@login_required
def schedule_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    session = Session.objects.all()
    

    if request.method == 'POST':
        department_id = request.POST.get('department_id')
        class_level_id = request.POST.get('classgroup_id')
        course_id = request.POST.get('course_id')
        scheduled_date = request.POST.get('scheduled_date')
        start_time = request.POST.get('start_time')
        duration_minutes = request.POST.get('duration_minutes')
        total_questions = request.POST.get('total_questions')
        term = request.POST.get('term')
        session_id = request.POST.get('session')
        session_instance = get_object_or_404(Session, id=session_id)

        # ✅ Step 1: Validate required fields
        if not (department_id and class_level_id and course_id and scheduled_date and start_time and duration_minutes and total_questions and term):
            return JsonResponse({'status': 'error', 'message': 'All fields are required.'})

        # ✅ Step 2: Convert numeric fields
        try:
            total_questions = int(total_questions)
            duration_minutes = int(duration_minutes)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid numeric input.'})

        # ✅ Step 3: Check question count
        available_questions = Question.objects.filter(exam=exam).count()
        if total_questions > available_questions:
            return JsonResponse({
                'status': 'error',
                'message': f'You cannot schedule {total_questions} questions. '
                           f'Only {available_questions} question(s) exist for this exam.'
            })

        # ✅ Step 4: Fetch related objects
        department = get_object_or_404(Department, id=department_id)
        class_level = get_object_or_404(ClassGroup, id=class_level_id)
        course = get_object_or_404(Course, id=course_id)
        
        try:
            combined_str = f"{scheduled_date} {start_time}"
            naive_datetime = datetime.strptime(combined_str, "%Y-%m-%d %H:%M")
            aware_datetime = timezone.make_aware(naive_datetime, timezone.get_current_timezone())
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid date/time format: {e}'})

        # ✅ Step 5: Check if schedule already exists for same exam, department, class, course & term
        existing_schedule = ExamSchedule.objects.filter(
            exam=exam,
            department=department,
            class_level=class_level,
            course_name=course,
            term=term,
        ).first()

        if existing_schedule:
            # ✅ Update existing schedule
            existing_schedule.scheduled_date = scheduled_date
            existing_schedule.start_time = start_time
            existing_schedule.duration_minutes = duration_minutes
            existing_schedule.total_questions = total_questions
            existing_schedule.save()

            return JsonResponse({
                'status': 'updated',
                'message': 'Existing exam schedule updated successfully!'
            })
        else:
            # ✅ Create new schedule if none exists
            ExamSchedule.objects.create(
                exam=exam,
                department=department,
                class_level=class_level,
                course_name=course,
                scheduled_date=scheduled_date,
                start_time=start_time,
                duration_minutes=duration_minutes,
                total_questions=total_questions,
                created_by=request.user,
                term=term,
                session=session_instance,
            )

            return JsonResponse({'status': 'success', 'message': 'Exam scheduled successfully!'})

    # ✅ GET request: load page
    departments = Department.objects.all()
    class_levels = ClassGroup.objects.all()

    return render(request, 'exam_details.html', {
        'exam': exam,
        'departments': departments,
        'class_levels': class_levels,
        'getSession':session,
    })



# student dashboard and exam pick
from django.utils import timezone
# @login_required
# def student_portal(request):
#     getLogo = schoollogo.objects.first()
#     getTitle = title.objects.first()
#     student = request.user.student_profile
#     courses = student.courses.all()

#     today = timezone.localdate()
#     now = timezone.localtime().time()

#     # ✅ Fetch all scheduled exams for student's department and class
#     # exams = ExamSchedule.objects.filter(
#     #     department=student.department,
#     #     class_level__name__iexact=student.level_or_class
#     # ).select_related('course_name', 'exam')
#     print(student.level_or_class.id)
    

#     exams = ExamSchedule.objects.filter(class_level=student.level_or_class, department=student.department)
#     # ✅ Annotate each exam with its current status
#     for exam in exams:
#         if exam.scheduled_date == today and exam.start_time <= now:
#             exam.status = "ongoing"
#         elif exam.scheduled_date > today or (exam.scheduled_date == today and exam.start_time > now):
#             exam.status = "upcoming"
#         else:
#             exam.status = "completed"

#     # ✅ (Optional) Map each course to its exam
#     course_exams = {}
#     for course in courses:
#         scheduled_exam = exams.filter(course_name=course).first()
#         course_exams[course.id] = scheduled_exam
        
    
#     print("Student level:", student.level_or_class, student.level_or_class.id)
#     print("ExamSchedule levels:", ExamSchedule.objects.values_list('class_level_id', 'class_level__name'))
#     print("Student department:", student.department_id)
#     print("Exam departments:", ExamSchedule.objects.values_list('department_id', 'department__name'))


#     return render(request, 'student_portal.html', {
#         'student': student,
#         'courses': courses,
#         'getTitle': getTitle,
#         'getLogo': getLogo,
#         'exams': exams,
#         'today': today,
#         'now': now,
#         'course_exams': course_exams,
#     })
    
from django.utils import timezone
from django.contrib.auth.decorators import login_required


@login_required
def student_portal(request):
    getLogo = schoollogo.objects.first()
    getTitle = title.objects.first()
    
    
    # try:
    student = getattr(request.user, "student_profile", None)
    if not student:
        messages.warning(request, "Student profile not found. Please contact admin.")
        return redirect("LoginUser")
    # except Exception as e:
    #     return render(request, "student_portal.html", 
    #                   {"Oops": "This user doesn't have a valid student account. {e}"})

    # 🔹 All sessions for sidebar
    sessions = Session.objects.all().order_by("-name")

    # 🔹 Selected session (from query string or default current)
    session_id = request.GET.get("session")
    if session_id:
        selected_session = get_object_or_404(Session, id=session_id)
    else:
        selected_session = Session.objects.filter(is_current=True).first()
    
    request.session['theSession']  = selected_session.id
        
    # 🔹 Selected term (from query string or default First Term)
    selected_term = request.GET.get("term", "First Term")
    is_ajax = request.GET.get("ajax")

    # 🔹 Get enrollment for this student in selected session
    enrollment = StudentEnrollment.objects.filter(
        student=student, session=selected_session
    ).first()

    # 🔹 Prefetch all exams for this term/session
    exams_qs = ExamSchedule.objects.filter(
        class_level=student.level_or_class,
        department=student.department,
        term=selected_term
    ).select_related("course_name", "exam")

    # Build a map {course_id: exam}
    exams_map = {}
    for exam in exams_qs:
        exam.status = exam.computed_status
        exams_map[exam.course_name_id] = exam

    # 🔹 Build courses list with attached exam info
    courses = []
    if enrollment:
        regs = CourseRegistration.objects.filter(enrollment=enrollment).select_related("course")
        for reg in regs:
            exam = exams_map.get(reg.course.id)
            courses.append({"course": reg.course, "exam": exam})

    terms = ["First Term", "Second Term", "Third Term"]

    # 🔹 AJAX response (only exams list)
    if is_ajax:
        return render(request, "exam_list.html", {"exams": exams_qs})

    return render(request, "student_portal.html", {
        "student": student,
        "sessions": sessions,
        "selected_session": selected_session,
        "courses": courses,   # ✅ list of dicts: {course, exam}
        "getTitle": getTitle,
        "getLogo": getLogo,
        "exams": exams_qs,
        "selected_term": selected_term,
        "terms": terms,
    })

   
# import random
# @login_required
# def take_exam(request, course_id):
#     AggrePercentage = AgregatedPercentahe.objects.all().first()
#     getThePercent = AggrePercentage.scorePercent
#     import random
#     student = get_object_or_404(Student, user=request.user)

#     # ✅ Prevent multiple active exam sessions
#     if request.session.get('exam_in_progress') and request.session['exam_in_progress'] != course_id:
#         return render(request, "exam_not_found.html", {
#             "message": "You already have an active exam session in progress."
#         })
#     else:
#         request.session['exam_in_progress'] = course_id

#     # ✅ Fetch the scheduled exam for this course, department, and class
#     exam_schedule = ExamSchedule.objects.filter(
#         course_name_id=course_id,
#         department=student.department,
#         class_level=student.level_or_class
#     ).select_related('exam', 'course_name').first()

#     if not exam_schedule:
#         return render(request, "exam_not_found.html", {
#             "message": "No scheduled exam found for your class or department."
#         })

#     exam = exam_schedule.exam
#     questions = list(exam.questions.all())

#     # ✅ Handle no questions
#     if not questions:
#         return render(request, "exam_not_found.html", {
#             "message": f"No questions found for {exam.title}. Please contact your instructor."
#         })

#     # ✅ Randomize question order and options
#     random.shuffle(questions)
#     for q in questions:
#         options = [q.option_a, q.option_b, q.option_c, q.option_d]
#         random.shuffle(options)
#         q.shuffled_options = options

#     # ✅ Check if student already took this exam
#     existing_result = MarkedExam.objects.filter(student=student, exam=exam).first()
#     if existing_result:
#         return render(request, "exam_not_found.html", {
#             "message": f"You have already taken the exam: {exam.title}.",
#         })

#     if request.method == "POST":
#         answers = {}
#         score = 0

#         for question in questions:
#             selected = request.POST.get(f"question_{question.id}")
#             selected_answer = selected or "Not Answered"
#             answers[question.id] = selected_answer
#             if selected_answer == question.correct_answer:
#                 score += 1

#         total_questions = len(questions)
#         percentage = round((score / total_questions) * getThePercent, 2)

#         # ✅ Double-check no duplicate submission
#         if not MarkedExam.objects.filter(student=student, exam=exam).exists():
#             MarkedExam.objects.create(
#                 exam=exam,
#                 student=student,
#                 department=student.department,
#                 course=exam.course,
#                 exam_number=student.admission_number,
#                 username=student.user.username,
#                 full_name=student.full_name,
#                 total_score=score,
#                 total_questions=total_questions,
#                 percentage=percentage
#             )

#         # ✅ End session
#         request.session.pop('exam_in_progress', None)

#         return render(request, "exam_result.html", {
#             "exam": exam,
#             "questions": questions,
#             "answers": answers,
#             "score": score,
#             "total": total_questions,
#             "percentage": percentage,
#             "student": student,
#         })

#     # ✅ If GET request, render exam page
#     return render(request, "take_exam.html", {
#         "exam": exam,
#         "questions": questions,
#         "exam_schedule": exam_schedule,
#         "student": student,
#     })

import random
@login_required
def take_exam(request, course_id):
    # ✅ Get system configuration for scoring
    AggrePercentage = AgregatedPercentahe.objects.first()
    getThePercent = AggrePercentage.scorePercent if AggrePercentage else 100
    term = request.GET.get('term', '').strip()
    print(term)

    # ✅ Get current logged-in student
    student = get_object_or_404(Student, user=request.user)
    session_idx = request.session.get('theSession')

      

    selected_session = get_object_or_404(Session, id=session_idx)

    print(selected_session)

    # ✅ Prevent multiple active exam sessions
    active_exam = request.session.get('exam_in_progress')
    if active_exam and active_exam != course_id:
        return render(request, "exam_not_found.html", {
            "message": "You already have an active exam session in progress."
        })
    else:
        request.session['exam_in_progress'] = course_id

    # ✅ Fetch the scheduled exam
    exam_schedule = ExamSchedule.objects.filter(
        course_name_id=course_id,
        department=student.department,
        class_level=student.level_or_class,
        term__iexact=term.strip(),
        session=selected_session
    ).select_related('exam', 'course_name',).first()

    if not exam_schedule:
        return render(request, "exam_not_found.html", {
            "message": "No scheduled exam found for your class or department."
        })

    exam = exam_schedule.exam
    questions = list(exam.questions.filter(term__iexact=term.strip()))

    # ✅ Handle no questions
    if not questions:
        return render(request, "exam_not_found.html", {
            "message": f"No questions found for {exam.title}. Please contact your instructor."
        })

    # ✅ Randomize question and option order
    random.shuffle(questions)
    for q in questions:
        options = [q.option_a, q.option_b, q.option_c, q.option_d]
        random.shuffle(options)
        q.shuffled_options = options

    # ✅ Check if the student already took the exam
    if MarkedExam.objects.filter(student=student, exam=exam, term=term, session=selected_session).exists():
        return render(request, "exam_not_found.html", {
            "message": f"You have already taken the exam: {exam.title}.",
        })

    # ✅ If student submits exam
    if request.method == "POST":
        score = 0
        answers = {}

        for question in questions:
            selected_answer = request.POST.get(f"question_{question.id}", "Not Answered")
            answers[question.id] = selected_answer

            if selected_answer == question.correct_answer:
                score += 1

        total_questions = len(questions)
        percentage = round((score / total_questions) * getThePercent, 2)

        # ✅ Double-check to avoid duplicate insertion
        if not MarkedExam.objects.filter(student=student, exam=exam, term=term, session=selected_session).exists():
            MarkedExam.objects.create(
                exam=exam,
                student=student,
                department=student.department,
                course=exam.course,
                exam_number=student.admission_number,
                username=student.user.username,
                full_name=student.full_name,
                total_score=score,
                total_questions=total_questions,
                percentage=percentage,
                term=term,
                session=selected_session
            )

        # ✅ Clear session after exam completion
        request.session.pop('exam_in_progress', None)

        return render(request, "exam_result.html", {
            "exam": exam,
            "questions": questions,
            "answers": answers,
            "score": score,
            "total": total_questions,
            "percentage": percentage,
            "student": student,
        })

    # ✅ For GET request — render the exam page
    return render(request, "take_exam.html", {
        "term":term,
        "exam": exam,
        "questions": questions,
        "exam_schedule": exam_schedule,
        "student": student,
        "selected_session":selected_session
    })



login_required
def exam_not_found(request):
    return render(request, 'exam_not_found.html')


from django.db import transaction
from django.db.models import Sum
@login_required
def student_score(request, student_id, course_id):
    AggrePercentage = AgregatedPercentahe.objects.first()
    getThePercent = AggrePercentage.scorePercent if AggrePercentage else 100

    student = get_object_or_404(Student, id=student_id)
    getSession = Session.objects.all()
    course = get_object_or_404(Course, id=course_id)
    scores = MarkedExam.objects.filter(student=student, course=course)\
        .select_related('course', 'exam', 'department')

    if request.method == 'POST':
        total_questions = int(request.POST.get('total_questions', 0))
        total_score = int(request.POST.get('total_score', 0))
        test_type = request.POST.get('test_type')
        Testterm = request.POST.get('Testterm')
        session_id = request.POST.get('session')
        session_instance = get_object_or_404(Session, id=session_id)
        
        # percentage = (total_score / total_questions) * getThePercent if total_questions > 0 else 0
        
        try:
            # ClassGroup is already stored on the student model
            class_instance = student.level_or_class
            print(class_instance)

            obj, created = TestScore.objects.update_or_create(
                student=student,
                course=course,
                department=student.department,
                class_group=str(student.level_or_class),  # ensure string
                test_type=test_type.strip(),              # ensure exact match
                Testterm=Testterm.strip(),              # ensure exact match
                session=session_instance,              # ensure exact match
                defaults={
                    'total_questions': total_questions,
                    'total_score': total_score,
                }
            )


            return JsonResponse({'message': 'Score added successfully!'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    exam_aggregates = scores.aggregate(
        total_score=Sum('total_score'),
        total_questions=Sum('total_questions')
    )

    exam_total_score = exam_aggregates['total_score'] or 0
    exam_total_questions = exam_aggregates['total_questions'] or 0

    exam_percentage = (exam_total_score / exam_total_questions * 70) if exam_total_questions > 0 else 0
    
    Testscores = TestScore.objects.filter(
        student=student,
        course=course
    ).select_related('course', 'department')

    aggregates = Testscores.aggregate(
        total_score_sum=Sum('total_score'),
        total_questions_sum=Sum('total_questions')
    )

    total_score_sum = aggregates['total_score_sum'] or 0
    total_questions_sum = aggregates['total_questions_sum'] or 0

    test_percentage = round((total_score_sum / total_questions_sum) * 30, 2) if total_questions_sum > 0 else 0
    total_percentage = exam_percentage + test_percentage
    print(Testscores)
    context = {
        'Testscores':Testscores,
        'total_score_sum':total_score_sum,
        'test_percentage': round(test_percentage,2),
        'total_percentage': round(total_percentage,2),
        'student': student, 
        'course': course,
        'getSession':getSession, 
        'scores': scores
    }
    return render(request, 'studentScore.html', context)



@login_required
def export_student_scores_csv(request, student_id, course_id):
    student = get_object_or_404(Student, id=student_id)
    course = get_object_or_404(Course, id=course_id)

    # Fetch marked exams for this student and course
    scores = MarkedExam.objects.filter(student=student, course=course).select_related('exam', 'department', 'course')

    # Create the CSV response
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{student.full_name}_marked_exams.csv"'},
    )

    writer = csv.writer(response)
    # CSV header
    writer.writerow([
        'S/N', 'Student Name', 'Exam Title', 'Course', 'Department',
        'Total Questions', 'Total Score', 'Percentage', 'Date Taken'
    ])

    # Write data rows
    for idx, score in enumerate(scores, start=1):
        writer.writerow([
            idx,
            score.full_name,
            score.exam.title if score.exam else "-",
            score.course.title if score.course else "-",
            score.department.name if score.department else "-",
            score.total_questions,
            score.total_score,
            f"{score.percentage:.2f}%",
            score.date_taken.strftime("%Y-%m-%d %H:%M"),
        ])

    return response

from django.db.models import Sum

def CheckResult(request):
    try:
        # School info
        getTitle = title.objects.first()
        getLogo = schoollogo.objects.first()
        GetAboutSchool = AboutSchool.objects.first()

        student = None
        results = None
        ts_score_map = {}
        term = None
        error = None
        resultCount = 0
        session = 0
        total_exam_score = 0
        total_test_score = 0
        grand_total = 0
        overall_percentage = 0

        if request.method == "POST":
            form = ResultCheckForm(request.POST)

            if form.is_valid():
                admission_number = form.cleaned_data["admission_number"]
                access_code = form.cleaned_data["access_code"]
                term = form.cleaned_data["term"]
                session = form.cleaned_data["session"]

                try:
                    # Get student
                    student = Student.objects.get(admission_number=admission_number)

                    # Validate access code
                    ResultAccessCode.objects.get(code=access_code)

                    # Fetch exam results
                    results = (
                        MarkedExam.objects
                        .filter(student=student, term=term, session=session)
                        .select_related('exam', 'course', 'department')
                    )
                    resultCount = results.count()

                    # Aggregate test scores per course
                    Testscores = (
                        TestScore.objects
                        .filter(student=student, Testterm=term, session=session)
                        .values('course_id')
                        .annotate(total_test_score=Sum('total_score'), total_test_max=Sum('total_questions'))
                    )

                    # Convert to dict → { course_id : {'score': ..., 'max': ...} }
                    ts_score_map = {
                        ts['course_id']: {'score': ts['total_test_score'], 'max': ts['total_test_max']}
                        for ts in Testscores
                    }

                    # Calculate totals & overall percentage
                    total_exam_score = results.aggregate(total=Sum('total_score'))['total'] or 0
                    total_exam_max = results.aggregate(total=Sum('total_questions'))['total'] or 0
                    total_test_score = sum(ts['score'] or 0 for ts in ts_score_map.values())
                    total_test_max = sum(ts['max'] or 0 for ts in ts_score_map.values())
                    grand_total = total_exam_score + total_test_score
                    grand_max = total_exam_max + total_test_max
                    overall_percentage = (grand_total / grand_max * 100) if grand_max > 0 else 0

                    # No result found
                    if not results.exists() and not ts_score_map:
                        error = f"No results found for {term} or {session}."

                except Student.DoesNotExist:
                    error = "Invalid admission number."

                except ResultAccessCode.DoesNotExist:
                    error = "Invalid result access code."

                except Exception as e:
                    print("\n🔥🔥 INNER VIEW ERROR 🔥🔥")
                    print(e)
                    print("------------------------------------\n")
                    error = "An unexpected error occurred."

        else:
            form = ResultCheckForm()

        context = {
            'getTitle': getTitle,
            'getLogo': getLogo,
            'AboutSchool': GetAboutSchool,
            'form': form,
            'resultCount': resultCount,
            'student': student,
            'results': results,
            'ts_score_map': ts_score_map,
            'term': term,
            'session':session,
            'error': error,
            'total_exam_score': total_exam_score,
            'total_test_score': total_test_score,
            'grand_total': grand_total,
            'overall_percentage': overall_percentage,
        }

        return render(request, 'checkResult.html', context)

    except Exception as e:
        print("\n🔥🔥 OUTER VIEW ERROR 🔥🔥")
        print(e)
        print("------------------------------------\n")
        return HttpResponse("Internal Server Error", status=500)

   
def bulk_sms_page(request):
    
    # Get all students in the "Student" group
    student_group = Group.objects.get(name="Student")
    students_users = student_group.user_set.all()
    students = Student.objects.filter(user__in=students_users)

    # Distinct class list
    classes = ClassGroup.objects.all().distinct()
    department = Department.objects.all().distinct()
    print(department)

    # Distinct status list (optional)
    # statuses = Student.objects.values_list("status", flat=True).distinct()
    # print(classes)

    return render(
        request,
        "bulk_sms.html",
        {"students": students, "classes": classes,"department":department},
    )


# def bulk_sms_page(request):
#     student_group = Group.objects.get(name="Student")
#     students_users = student_group.user_set.all()
#     students = Student.objects.filter(user__in=students_users)

#     return render(request, "bulk_sms.html", {"students": students})


from django.views.decorators.csrf import csrf_exempt
import json


from .utils import *
@csrf_exempt
def send_bulk_sms(request):
    if request.method == "POST":
        data = json.loads(request.body)
        getTitle = title.objects.first()
        getLogo = schoollogo.objects.first()
        logo_url = request.build_absolute_uri(getLogo.LogoImage.url) if getLogo else ""
        recipients = data.get("recipients", [])
        addEmails = data.get("addEmails", [])
        
        emails = [
            r.get("email")
            for r in recipients
            if r.get("email") not in [None, "", "undefined"]
        ]
        
        # Extract phone numbers
        phone_numbers_raw = [r["phone"] for r in recipients]

        # Clean + dedupe + normalize
        phone_numbers = clean_phone_numbers(phone_numbers_raw)

        Themessage = data.get("message", "")
        from_email=settings.DEFAULT_FROM_EMAIL
        if addEmails == "Yes":
            try:
                subject = f"New Message from {getTitle}"
                from_email = settings.DEFAULT_FROM_EMAIL

                # Text version (fallback for old email clients)
                text_content = f"""
            New Message from {getTitle}

            Sender: {getTitle}
            Email: {from_email}

            Message:
            {Themessage}

            Thank you.
            """

                # HTML version (Professional & Stunning)
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px; margin:auto; background:#ffffff; border-radius:10px; padding:30px; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                        
                        <tr>
                            <td style="text-align:center; padding-bottom:20px;">
                                <h2 style="margin:0; color:#2a6edc;">📘 School Notification</h2>
                                <p style="color:#777; margin-top:5px;">A new message has been sent to you</p>
                            </td>
                        </tr>
                        
                        <td align="center">
                            <a href="{logo_url}">
                                <img src="{logo_url}" alt="School Logo"
                                    style="width:130px;margin-bottom:20px;">
                            </a>
                        </td>
                        class="brand-logo">
                        <tr>
                            <td style="padding:20px;">
                                <h3 style="margin-bottom:10px; color:#333;">Message Details</h3>
                                
                                <p style="color:#444; line-height:1.6;">
                                    <strong>Sender Name:</strong> {getTitle}<br>
                                    <strong>Sender Email:</strong> {from_email}
                                </p>

                                <div style="background:#f1f1f1; padding:15px; border-left:4px solid #2a6edc; border-radius:5px; margin-top:15px;">
                                    <p style="margin:0; color:#333; font-size:15px; line-height:1.6;">
                                        {Themessage}
                                    </p>
                                </div>

                                <p style="margin-top:30px; color:#555;">
                                    Thank you for staying connected with our school.<br>
                                    <strong>School Administration</strong><br>
                                    <strong>{getTitle.phonNo}</strong>
                                </p>
                            </td>
                        </tr>

                    </table>

                    <p style="text-align:center; color:#aaa; margin-top:20px; font-size:13px;">
                        &copy; {getTitle} School • All Rights Reserved
                    </p>
                </body>
                </html>
                """

                # Send email with both HTML + text
                email = EmailMultiAlternatives(subject, text_content, from_email, emails)
                email.attach_alternative(html_content, "text/html")
                email.send()

                messages.success(request, "Email also sent successfully")

            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        # CALL THE RENAMED API FUNCTION
        results = send_sms(phone_numbers, Themessage)

        # Flash messages
        if results['success']:
            messages.success(
                request,
                "SMS sent successfully to: " + ", ".join(results["success"])
            )

        if results["failed"]:
            fail_msg = "; ".join(
                [f"{f['number']} ({f['error']})" for f in results["failed"]]
            )
            messages.error(request, "Failed: " + fail_msg)

        return JsonResponse({
            "status": "success",
            "count": len(phone_numbers),
            "sent": results["success"],
            "failed": results["failed"]
        })

    return JsonResponse({"error": "Invalid request"}, status=400)

from decimal import Decimal
from django.db.models.functions import TruncMonth
@login_required
def pay_fee(request, enrollment_id):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id)
    fee = SchoolFee.objects.filter(
        session=enrollment.session, 
        classgroup=enrollment.classgroup
    ).first()

    if not fee:
        return redirect('parent_child_dashboard')

    payment, _ = FeePayment.objects.get_or_create(enrollment=enrollment, fee=fee)

    percentage_paid = (payment.amount_paid / fee.amount * 100) if fee.amount > 0 else 0
    balance = fee.amount - payment.amount_paid
    history = payment.installments.all().order_by('-date_paid')
    monthly_payments = (
        payment.installments
        .annotate(month=TruncMonth("date_paid"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    labels = [p["month"].strftime("%b %Y") for p in monthly_payments]
    data = [float(p["total"]) for p in monthly_payments]


    min_first_payment = fee.deposit_amount  # Decimal
    has_paid_before = payment.amount_paid > 0

    if request.method == "POST":
        amount = Decimal(request.POST.get("amount"))

        # 🔥 Enforce minimum initial deposit
        if not has_paid_before:
            if amount < min_first_payment:
                return render(request, "payments/pay_fee.html", {
                    "error": f"Initial deposit is ₦{min_first_payment}. You entered ₦{amount}.",
                    "enrollment": enrollment,
                    "fee": fee,
                    "payment": payment,
                    "percentage_paid": percentage_paid,
                    "balance": balance,
                    "history": history,
                })

        # 🔥 Prevent overpayment
        if amount > balance:
            return render(request, "payments/pay_fee.html", {
                "error": f"You cannot pay more than the remaining balance ₦{balance}.",
                "enrollment": enrollment,
                "fee": fee,
                "payment": payment,
                "percentage_paid": percentage_paid,
                "balance": balance,
                "history": history,
            })

        # 🔥 Redirect to Paystack for actual payment
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

        data = {
            "email": enrollment.student.user.email,
            "amount": int(amount * 100),  # convert to kobo
            "currency": "NGN",
            "callback_url": request.build_absolute_uri(
                reverse("paystack_callback")
            ),
            "metadata": {
                "enrollment_id": enrollment.id,
                "amount": str(amount)
            }
        }

        response = requests.post(paystack_url, headers=headers, json=data)
        resp_data = response.json()

        if resp_data.get("status"):
            return redirect(resp_data["data"]["authorization_url"])

        return render(request, "payments/pay_fee.html", {
            "error": "Payment initialization failed.",
            "enrollment": enrollment,
            "fee": fee,
            "payment": payment,
            "percentage_paid": percentage_paid,
            "balance": balance,
            "history": history,
        })

    return render(request, "payments/pay_fee.html", {
        "enrollment": enrollment,
        "fee": fee,
        "payment": payment,
        "percentage_paid": percentage_paid,
        "balance": balance,
        "history": history,
        "labels": labels,
        "data": data,
        'getTitle':getTitle,
        'getLogo':getLogo,
        'AboutSchool':GetAboutSchool,  
    })
 

@login_required
def payment_success(request):
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    context = {
        'getTitle':getTitle,
        'getLogo':getLogo,
        'AboutSchool':GetAboutSchool, 
    }
    return render(request, "payments/payment_success.html", context)



@login_required
def paystack_callback(request):
    reference = request.GET.get("reference")
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"

    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    response = requests.get(verify_url, headers=headers).json()

    if not response.get("status"):
        return HttpResponse("Payment verification failed.")

    data = response["data"]
    metadata = data.get("metadata", {})
    amount = Decimal(data["amount"]) / 100
    enrollment_id = metadata.get("enrollment_id")

    enrollment = StudentEnrollment.objects.get(id=enrollment_id)
    fee = SchoolFee.objects.filter(
        session=enrollment.session,
        classgroup=enrollment.classgroup
    ).first()

    payment, _ = FeePayment.objects.get_or_create(enrollment=enrollment, fee=fee)

    # create installment
    InstallmentPayment.objects.create(payment=payment, amount=amount)

    payment.amount_paid += amount
    if payment.amount_paid >= fee.amount:
        payment.is_fully_paid = True
    payment.save()

    messages.success(request, "Payment successful!")
    return redirect("parent_child_dashboard")


def parent_access(request):
    context = getContextSchool()
    """Parent login page using admission number + access code"""
    if request.method == "POST":
        admission_number = request.POST.get("admission_number")
        access_code_input = request.POST.get("access_code")

        try:
            student = Student.objects.get(admission_number=admission_number)
            access = ResultAccessCode.objects.get(code=access_code_input)
            
            # Save student ID in session
            request.session['parent_student_id'] = student.id
            return redirect('parent_child_dashboard')

        except (Student.DoesNotExist, ResultAccessCode.DoesNotExist):
            return render(request, "payments/parent_access.html", context)
    
    return render(request, "payments/parent_access.html", context)

def parent_child_dashboard(request):
    # firstName = request.user.first_name
    # lastName = request.user.last_name
    # userName = request.user.username
    # getFullName = f'{firstName} {lastName} - {userName}'
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()

    """Dashboard for a single child accessed via access code"""
    student_id = request.session.get('parent_student_id')
    if not student_id:
        return redirect('parent_access')

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return redirect('parent_access')

    # Fetch all enrollments for the student
    enrollments = StudentEnrollment.objects.filter(student=student)

    dashboard_data = []
    for enroll in enrollments:
        # Try to get the fee for this enrollment's session and class
        fee = SchoolFee.objects.filter(session=enroll.session, classgroup=enroll.classgroup).first()

        if fee:
            payment, _ = FeePayment.objects.get_or_create(enrollment=enroll, fee=fee)
            percentage_paid = (payment.total_paid / fee.amount * 100) if fee.amount > 0 else 0
            balance = fee.amount - payment.total_paid
            history = payment.installments.all().order_by('-date_paid')
        else:
            # No fee assigned yet
            payment = None
            percentage_paid = 0
            balance = 0
            history = []

        dashboard_data.append({
            "enrollment": enroll,
            "fee": fee,
            "payment": payment,
            "percentage_paid": round(percentage_paid, 2),
            "balance": balance,
            "history": history
        })
    getTitle = title.objects.all().first()
    getLogo = schoollogo.objects.all().first()
    GetAboutSchool = AboutSchool.objects.all().first()
    context = {
        "student": student,
        # "getFullName":getFullName,
        "dashboard_data": dashboard_data,
        'getTitle':getTitle,
        'getLogo':getLogo,
        'AboutSchool':GetAboutSchool,
    }

    return render(request, "payments/parent_child_dashboard.html", context)


# def assignment(request):
    
    
    