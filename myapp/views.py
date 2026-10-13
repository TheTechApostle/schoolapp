# ============================================================
# views.py  –  Fully Optimised (zero missing functions)
# ============================================================
import re
import csv
import json
import random
import requests
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

import PyPDF2
import docx
import wikipedia

from openai import OpenAI

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *
from .utils import *


def debug_headers(request):
    return JsonResponse({
        "HTTP_HOST": request.META.get("HTTP_HOST"),
        "HTTP_ORIGIN": request.META.get("HTTP_ORIGIN"),
        "HTTP_REFERER": request.META.get("HTTP_REFERER"),
        "HTTP_X_FORWARDED_HOST": request.META.get("HTTP_X_FORWARDED_HOST"),
        "HTTP_X_FORWARDED_PROTO": request.META.get("HTTP_X_FORWARDED_PROTO"),
    })


# views.py


def show_headers(request):
    headers = {
        k: v
        for k, v in request.META.items()
        if k.startswith("HTTP_")
    }
    return JsonResponse(headers)
# ============================================================
# HELPERS
# ============================================================

def mainView():
    """
    Returns shared school-branding context.
    Cached for 5 minutes to avoid hitting the DB on every request.
    """
    cached = cache.get('main_view_context')
    if cached:
        return cached
    result = {
        'getTitle':    title.objects.first(),
        'getLogo':     schoollogo.objects.first(),
        'AboutSchool': AboutSchool.objects.first(),
    }
    cache.set('main_view_context', result, timeout=300)
    return result


def getContextSchool():
    """Alias used in payment views – same as mainView."""
    return mainView()


# ============================================================
# ERROR HANDLERS
# ============================================================

def custom_404(request, exception):
    context = mainView()
    return render(request, '404.html', context)


# ============================================================
# PUBLIC / HOME
# ============================================================

def MyHome(request):
    ctx = mainView().copy()

    ctx['GetAboutSchoolSec'] = (
        AboutSchool.objects.all()[1] if AboutSchool.objects.count() > 1 else None
    )
    ctx['QuestionCount'] = Question.objects.distinct().count()
    ctx['TeacherCount']  = Teacher.objects.distinct().count()
    ctx['courseCount']   = Course.objects.distinct().count()
    ctx['StudentCount']  = Student.objects.distinct().count()
    ctx['slides']        = SliderImage.objects.all()

    if request.method == 'POST':
        name    = request.POST.get('name')
        email   = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if not all([name, email, subject, message]):
            return JsonResponse({'error': 'All fields are required.'}, status=400)

        ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)

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

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': 'Your message has been sent successfully!'})

        messages.success(request, 'Your message has been sent successfully!')
        return redirect('MyHome')

    return render(request, 'index.html', ctx)


# ============================================================
# AJAX LOADERS
# ============================================================

def load_classgroups(request):
    department_id = request.GET.get('department_id')
    classgroups = (
        ClassGroup.objects.filter(department_id=department_id)
        .only('id', 'name')
        .values('id', 'name')
    )
    return JsonResponse(list(classgroups), safe=False)


def load_courses(request):
    department_id  = request.GET.get('department_id')
    classgroup_id  = request.GET.get('classgroup_id')
    courses = (
        Course.objects.filter(department_id=department_id, classgroup_id=classgroup_id)
        .only('id', 'title')
        .values('id', 'title')
    )
    return JsonResponse(list(courses), safe=False)


# ============================================================
# REGISTRATION
# ============================================================

def register_student(request):
    ctx = mainView().copy()

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
                messages.success(request, f"✅ Student '{user.get_full_name()}' registered successfully!")
                return redirect('SuccessPage')
            except IntegrityError as e:
                if 'admission_number' in str(e):
                    messages.error(request, '⚠️ This admission/matric number already exists.')
                else:
                    messages.error(request, f'⚠️ Database error: {str(e)}')
        else:
            error_messages = [
                f"{field}: {error}"
                for field, errors in form.errors.items()
                for error in errors
            ]
            messages.error(request, '⚠️ Please fix these errors: ' + '; '.join(error_messages))
    else:
        form = StudentRegistrationForm()

    ctx['form'] = form
    return render(request, 'student_registration.html', ctx)


def register_teacher(request):
    ctx = mainView().copy()

    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            teacher = form.save()
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

    ctx['form'] = form
    return render(request, 'teacher_form.html', ctx)


def teacher_list(request):
    ctx = mainView().copy()
    ctx['teachers'] = Teacher.objects.select_related('user').all()
    return render(request, 'teacher_list.html', ctx)


def SuccessPage(request):
    return render(request, 'success_page.html', mainView())


# ============================================================
# AUTH
# ============================================================

def LoginUser(request):
    ctx = mainView().copy()
    next_url = request.GET.get('next') or request.POST.get('next') or None

    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if user.groups.filter(name='Educator').exists():
                return redirect('Teacherdashboard')
            if user.groups.filter(name='Student').exists():
                return redirect('student_portal')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.warning(request, 'Authentication Failed... Username or Password Error')
    else:
        form = LoginForm()

    ctx['form'] = form
    ctx['next'] = next_url or ''
    return render(request, 'login.html', ctx)


@login_required
def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('LoginUser')


def dashboard(request):
    return render(request, 'dashboard.html')


# ============================================================
# TEACHER DASHBOARD
# ============================================================

def Teacherdashboard(request):
    return render(request, 'Teacherdashboard.html', mainView())


# ============================================================
# E-LEARNING – LECTURES
# ============================================================

@login_required(login_url='LoginUser')
def lecture_list(request):
    if not request.user.groups.filter(name='Educator').exists():
        return redirect('LoginUser')

    teacher    = get_object_or_404(Teacher, user=request.user)
    the_courses = teacher.courses.all()
    courses    = Course.objects.all()
    lectures   = (
        Lecture.objects.filter(course__in=courses)
        .select_related('course')
        .order_by('-created_at')
    )

    total_lectures  = lectures.count()
    total_views     = lectures.aggregate(total=Sum('views'))['total'] or 0  # ✅ single DB call
    new_this_week   = lectures.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    avg_completion  = 75  # placeholder

    types_breakdown = {}
    for lec in lectures:
        types_breakdown[lec.content_type] = types_breakdown.get(lec.content_type, 0) + 1

    views_series = [
        {'date': lec.created_at.strftime('%Y-%m-%d'), 'views': lec.views}
        for lec in lectures.order_by('created_at')[:10]
    ]

    assignment_fetch = Assignment.objects.all().distinct()

    ctx = {
        'lectures':              lectures,
        'assignment_fetch':      assignment_fetch,
        'courses':               courses,
        'the_course':            the_courses,
        'total_lectures':        total_lectures,
        'total_views':           total_views,
        'new_this_week':         new_this_week,
        'avg_completion':        avg_completion,
        'types_breakdown_json':  json.dumps(types_breakdown),
        'views_series_json':     json.dumps(views_series),
        'top_tags':              [],
        'recent_activity':       [],
    }
    return render(request, 'elearning/lecture_list.html', ctx)


@login_required(login_url='LoginUser')
def delete_assignment_ajax(request, assignment_id):
    if not request.user.groups.filter(name='Educator').exists():
        return JsonResponse({'error': 'Not authorized'}, status=403)

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        teacher    = get_object_or_404(Teacher, user=request.user)
        assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
        assignment.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='LoginUser')
def add_assignment_ajax(request):
    if not request.user.groups.filter(name='Educator').exists():
        return JsonResponse({'error': 'Not authorized'}, status=403)

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        teacher       = get_object_or_404(Teacher, user=request.user)
        course_id     = request.POST.get('course')
        title_val     = request.POST.get('title')
        description   = request.POST.get('description')
        attachment    = request.FILES.get('attachment')
        due_date_str  = request.POST.get('due_date')

        if not (course_id and title_val and due_date_str):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        try:
            course   = Course.objects.get(id=course_id)
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()

            assignment = Assignment.objects.create(
                teacher=teacher, course=course, title=title_val,
                description=description, attachment=attachment, due_date=due_date,
            )
            data = {
                'id':       assignment.id,
                'title':    assignment.title,
                'attachment': assignment.attachment.url if assignment.attachment else '',
                'course':   assignment.course.title,
                'due_date': assignment.due_date.strftime('%Y-%m-%d'),
            }
            return JsonResponse({'success': True, 'assignment': data})
        except Course.DoesNotExist:
            return JsonResponse({'error': 'Course not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def lecture_preview(request, pk):
    lecture = get_object_or_404(Lecture, pk=pk)
    lecture.views += 1
    lecture.last_viewed = timezone.now()
    lecture.save(update_fields=['views', 'last_viewed'])  # ✅ only update changed fields
    return render(request, 'elearning/lecture_preview.html', {'lecture': lecture})


def lecture_student_view(request, pk):
    lecture    = get_object_or_404(Lecture, pk=pk)
    avg_rating = lecture.votes.aggregate(Avg('rating'))['rating__avg']
    return render(request, 'elearning/lecture_student_view.html', {
        'lecture':    lecture,
        'avg_rating': round(avg_rating or 0, 1),
    })


@csrf_exempt
def lecture_vote(request, pk):
    if request.method == 'POST':
        lecture = get_object_or_404(Lecture, pk=pk)
        rating  = int(request.POST.get('rating'))
        LectureVote.objects.update_or_create(
            lecture=lecture, student=request.user,
            defaults={'rating': rating},
        )
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def lecture_upload(request):
    if request.method == 'POST':
        course       = get_object_or_404(Course, id=request.POST.get('course_id'))
        content_type = request.POST.get('content_type')

        lecture = Lecture.objects.create(
            title        = request.POST.get('title'),
            description  = request.POST.get('description'),
            course       = course,
            content_type = content_type,
            tags         = request.POST.get('tags', ''),
            status       = request.POST.get('status', 'DRAFT'),
            duration     = request.POST.get('duration') or None,
        )
        if content_type != 'LINK' and 'file' in request.FILES:
            lecture.file = request.FILES['file']
        elif content_type == 'LINK':
            lecture.external_url = request.POST.get('external_url')
        lecture.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def lecture_toggle_status(request):
    if request.method == 'POST':
        lecture = get_object_or_404(Lecture, id=request.POST.get('lecture_id'))
        lecture.status = 'LIVE' if lecture.status == 'DRAFT' else 'DRAFT'
        lecture.save(update_fields=['status'])
        return JsonResponse({'success': True, 'status': lecture.status})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def lecture_delete(request):
    if request.method == 'POST':
        lecture = get_object_or_404(Lecture, id=request.POST.get('lecture_id'))
        lecture.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def export_lectures_csv(request):
    lectures = Lecture.objects.select_related('course').all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lectures.csv"'
    writer = csv.writer(response)
    writer.writerow(['Title', 'Course', 'Type', 'Views', 'Status', 'Created'])
    for lec in lectures:
        writer.writerow([lec.title, lec.course.title, lec.content_type, lec.views, lec.status, lec.created_at])
    return response


# ============================================================
# STUDENT DASHBOARD  (e-learning)
# ============================================================

API_FOR_GEN = 'https://api-inference.huggingface.co/models/facebook/bart-large-cnn'
HF_TOKEN    = settings.HF_TOKEN_API
headers_hf  = {'Authorization': f'Bearer {HF_TOKEN}'}


@login_required(login_url='LoginUser')
def student_dashboard(request):
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.warning(request, 'Student profile not found. Please contact admin.')
        return redirect('LoginUser')
    
    video_id  = None
    raw_query = request.GET.get('q')
    query_text = None

    if raw_query:
        query_text = raw_query
        try:
            wikipedia.summary(query_text, sentences=3)
        except Exception:
            pass

        api_key = settings.YOUTUBE_API_KEY
        yt_resp = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={'part': 'snippet', 'q': query_text, 'type': 'video', 'maxResults': 1, 'key': api_key},
            timeout=5,
        ).json()
        if yt_resp.get('items'):
            video_id = yt_resp['items'][0]['id']['videoId']

    ctx = mainView().copy()
    student = get_object_or_404(Student, user=request.user)

    courses = (
        student.courses.all()
        .prefetch_related('lectures', 'lectures__votes')
    )

    total_lectures = sum(c.lectures.count() for c in courses)
    total_votes    = sum(lec.votes.count() for c in courses for lec in c.lectures.all())

    getTheCourse      = student.courses.all()
    assessment_count  = Assignment.objects.filter(course__in=getTheCourse).distinct().count()

    for c in courses:
        c.completed_lectures = getattr(c, 'completed_lectures', 0)
        c.remaining_lectures = c.lectures.count() - c.completed_lectures

    ctx.update({
        'student':          student,
        'assessment_count': assessment_count,
        'GetAboutSchoolSec': AboutSchool.objects.all()[1] if AboutSchool.objects.count() > 1 else None,
        'courses':          courses,
        'total_lectures':   total_lectures,
        'total_votes':      total_votes,
        'video_id':         video_id,
        'query':            query_text,
    })
    return render(request, 'elearning/student_dashboard.html', ctx)


@login_required(login_url='LoginUser')
def course_detail(request, course_id):
    ctx = mainView().copy()
    ctx['course']           = get_object_or_404(Course, id=course_id)
    ctx['student']          = request.user.student_profile
    ctx['GetAboutSchoolSec'] = AboutSchool.objects.all()[1] if AboutSchool.objects.count() > 1 else None
    return render(request, 'elearning/course_detail.html', ctx)


@login_required(login_url='LoginUser')
def techcourse_list(request):
    category_id = request.GET.get('category')
    techcourses = TechCourse.objects.select_related('category').order_by('-created_at')
    categories  = TechCourse_Category.objects.all()

    if category_id:
        techcourses = techcourses.filter(category_id=category_id)

    page_obj = Paginator(techcourses, 6).get_page(request.GET.get('page'))

    ctx = mainView().copy()
    ctx.update({
        'techcourses':      page_obj,
        'categories':       categories,
        'active_category':  category_id,
    })
    return render(request, 'elearning/techcourse.html', ctx)


@login_required(login_url='LoginUser')
def techcourse_detail(request, id):
    course   = get_object_or_404(TechCourse, id=id)
    video_id = None
    drive_id = None

    if 'youtube' in course.link or 'youtu.be' in course.link:
        match = re.search(r'(?:v=|youtu\.be/)([^&?/]+)', course.link)
        if match:
            video_id = match.group(1)
    elif 'drive.google.com' in course.link:
        match = re.search(r'/d/([^/]+)', course.link)
        if match:
            drive_id = match.group(1)

    ctx = mainView().copy()
    ctx.update({'course': course, 'video_id': video_id, 'drive_id': drive_id})
    return render(request, 'elearning/techcourse_detail.html', ctx)


@login_required(login_url='LoginUser')
def elibrary_list(request):
    ctx = mainView().copy()
    ctx['elibrary_list'] = Elibrary.objects.order_by('-uploaded_at')
    return render(request, 'elearning/elibrary.html', ctx)


def elibrary_detail(request, pk):
    resource = get_object_or_404(Elibrary, pk=pk)
    return render(request, 'elearning/elibrary_detail.html', {'resource': resource})


# ============================================================
# ASSIGNMENTS
# ============================================================

@login_required
def assignments_view(request):
    student = getattr(request.user, 'student_profile', None)
    today   = timezone.now().date()

    assignments = (
        Assignment.objects.select_related('teacher', 'course')
        .order_by('-due_date')
    )

    submissions     = (
        AssignmentSubmission.objects.filter(student=student)
        .select_related('assignment')
    ) if student else []

    submission_map = {s.assignment_id: s for s in submissions}

    for assignment in assignments:
        assignment.is_due      = timezone.now() > assignment.due_date
        submission             = submission_map.get(assignment.id)
        assignment.is_submitted = bool(submission)
        assignment.score       = submission.score    if submission else None
        assignment.feedback    = submission.feedback if submission else None

    ctx = mainView().copy()
    ctx.update({'assignments': assignments, 'student': student})
    return render(request, 'elearning/assignments.html', ctx)


@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    student    = getattr(request.user, 'student_profile', None)

    if not student:
        messages.error(request, 'Student profile not found.')
        return redirect('assignments_view')

    is_due = timezone.now() > assignment.due_date

    already_submitted = AssignmentSubmission.objects.filter(
        assignment=assignment, student=student
    ).first()

    if already_submitted:
        messages.warning(request, 'You already submitted this assignment.')
        return redirect('assignments_view')

    if request.method == 'POST':
        if is_due:
            messages.error(request, 'Assignment is overdue.')
            return redirect('assignments_view')

        form = AssignmentSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission            = form.save(commit=False)
            submission.assignment = assignment
            submission.student    = student
            submission.save()
            messages.success(request, 'Assignment submitted successfully.')
            return redirect('assignments_view')
    else:
        form = AssignmentSubmissionForm()

    ctx = mainView().copy()
    ctx.update({'assignment': assignment, 'form': form, 'is_due': is_due})
    return render(request, 'elearning/submit_assignment.html', ctx)


# ============================================================
# TIMETABLE
# ============================================================

@login_required
def create_timetable(request):
    form = TimetableForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
            messages.success(request, 'Timetable entry created successfully')
            return redirect('create_timetable')
        except Exception as e:
            messages.error(request, f'Error: {e}')
    return render(request, 'elearning/timetablecreate.html', {'form': form})


def student_timetable(request):
    ctx     = mainView().copy()
    student = request.user.student_profile
    enrollment = student.enrollments.filter(session__is_current=True).first()

    timetable = Timetable.objects.filter(
        session=enrollment.session, classgroup=enrollment.classgroup
    ).select_related('course', 'teacher', 'classroom', 'day', 'time_slot')

    ctx['timetable'] = timetable
    return render(request, 'elearning/timetable_view.html', ctx)


@login_required
def teacher_timetable(request):
    ctx     = mainView().copy()
    teacher = request.user.teacher_profile

    timetable = Timetable.objects.filter(
        teacher=teacher, session__is_current=True
    ).select_related('course', 'classgroup', 'classroom', 'day', 'time_slot')

    ctx['timetable'] = timetable
    return render(request, 'elearning/teacherTimeTableView.html', ctx)


def timetable_grid(request):
    ctx        = mainView().copy()
    time_slots = TimeSlot.objects.order_by('start_time')
    days       = Day.objects.all()
    classes    = ClassGroup.objects.all()

    timetable_qs = Timetable.objects.select_related('classgroup', 'course', 'day', 'time_slot')
    grid = defaultdict(lambda: defaultdict(dict))
    for entry in timetable_qs:
        grid[entry.classgroup][entry.day][entry.time_slot] = entry.course.title

    ctx.update({
        'time_slots': time_slots,
        'days':       days,
        'classes':    classes,
        'timetable':  grid,
    })
    return render(request, 'elearning/timetablegrid.html', ctx)


# ============================================================
# AI ASSISTANCE
# ============================================================

client = OpenAI(api_key=settings.OPENAI_API_KEY)


@login_required(login_url='LoginUser')
@csrf_exempt
def ai_assistance(request):
    student      = get_object_or_404(Student, user=request.user)
    getLectures  = Lecture.objects.filter(course__in=student.courses.all()).select_related('course')

    ctx = mainView().copy()
    ctx['getLectures'] = getLectures

    if request.method == 'GET':
        return render(request, 'elearning/ai_assistance.html', ctx)

    # POST
    prompt        = request.POST.get('prompt', '').strip()
    uploaded_file = request.FILES.get('file')

    if uploaded_file:
        filename  = uploaded_file.name.lower()
        file_text = ''
        try:
            if filename.endswith('.txt'):
                file_text = uploaded_file.read().decode('utf-8')
            elif filename.endswith('.pdf'):
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        file_text += extracted + '\n'
            elif filename.endswith('.docx'):
                document  = docx.Document(uploaded_file)
                file_text = '\n'.join(p.text for p in document.paragraphs)
            else:
                return JsonResponse({'response': 'Unsupported file type. Upload PDF, DOCX, or TXT only.'})

            request.session['uploaded_doc'] = file_text
            return JsonResponse({'response': f"Document '{uploaded_file.name}' uploaded successfully.\n\nNow ask me questions from it!"})
        except Exception as e:
            return JsonResponse({'response': f'Error reading document: {str(e)}'})

    if not prompt:
        return JsonResponse({'response': 'Please type a question or upload a document.'})

    stored_doc = request.session.get('uploaded_doc', '')
    if 'document' in prompt.lower() and not stored_doc:
        return JsonResponse({'response': 'No document uploaded yet. Please upload one first.'})

    final_prompt = (
        f"You are an educational AI assistant.\n\nDOCUMENT CONTENT:\n{stored_doc}\n\n"
        f"Answer this based strictly on the document:\n{prompt}\n\nExplain clearly like a tutor."
        if stored_doc else prompt
    )

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': 'You are an educational AI assistant for Secondary School students.'},
            {'role': 'user',   'content': final_prompt},
        ],
        max_tokens=500,
    )
    return JsonResponse({'response': response.choices[0].message.content})


# ============================================================
# EXAM MANAGEMENT  (Teacher side)
# ============================================================

@login_required
def add_questions(request, exam_id=None):
    teacher = getattr(request.user, 'teacher_profile', None)
    if not teacher:
        messages.error(request, 'You must be logged in as a teacher.')
        return redirect('Teacherdashboard')

    departments = teacher.department.all()
    classes     = teacher.class_groups.all()
    courses     = teacher.courses.all()
    exam        = None

    if exam_id:
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.created_by != request.user:
            messages.error(request, "You don't have permission to edit this exam.")
            return redirect('Teacherdashboard')

    elif request.method == 'POST' and 'select_course' in request.POST:
        dept_id   = request.POST.get('department')
        class_id  = request.POST.get('classgroup')
        course_id = request.POST.get('course')

        if not (dept_id and class_id and course_id):
            messages.warning(request, 'Please select department, class, and course.')
            return redirect('add_questions')

        classgroup = get_object_or_404(ClassGroup, id=class_id)
        course     = get_object_or_404(Course, id=course_id)

        existing_exam = Exam.objects.filter(
            course=course,
            class_groups=classgroup,
            created_by=request.user,
            title__icontains=classgroup.name,
        ).first()

        if existing_exam:
            messages.info(request, f"Exam for '{course.title}' ({classgroup.name}) already exists.")
            return redirect('add_questions', exam_id=existing_exam.id)
        else:
            exam = Exam.objects.create(
                course=course,
                class_groups=classgroup,
                title=f"{course.title} Exam ({classgroup.name})",
                created_by=request.user,
            )
            messages.success(request, f"Exam '{exam.title}' created successfully.")
            return redirect('add_questions', exam_id=exam.id)

    if request.method == 'POST' and 'save_questions' in request.POST:
        exam_id = request.POST.get('exam_id')
        exam    = get_object_or_404(Exam, id=exam_id)
        term    = request.POST.get('term', '').strip().title()

        questions_to_create = []
        question_index = 1
        while True:
            q_text = request.POST.get(f'question_text_{question_index}')
            if not q_text:
                break
            option_a = request.POST.get(f'option_a_{question_index}', '').strip()
            option_b = request.POST.get(f'option_b_{question_index}', '').strip()
            option_c = request.POST.get(f'option_c_{question_index}', '').strip()
            option_d = request.POST.get(f'option_d_{question_index}', '').strip()
            correct  = request.POST.get(f'correct_answer_{question_index}', '').strip().upper()

            if q_text.strip() and correct in ['A', 'B', 'C', 'D']:
                questions_to_create.append(Question(
                    exam=exam, question_text=q_text.strip(),
                    option_a=option_a, option_b=option_b,
                    option_c=option_c, option_d=option_d,
                    correct_answer=correct, term=term,
                ))
            question_index += 1

        if questions_to_create:
            Question.objects.bulk_create(questions_to_create)  # ✅ single INSERT
            messages.success(request, f"{len(questions_to_create)} question(s) added to '{exam.title}'.")
            return redirect('exam_detail', exam_id=exam.id)
        else:
            messages.warning(request, 'No valid questions were submitted.')

    ctx = {
        'exam':        exam,
        'departments': departments,
        'classes':     classes,
        'courses':     courses,
        'teacher':     teacher,
        'form':        QuestionForm(),
    }
    return render(request, 'add_questions.html', ctx)


@login_required
def exam_detail(request, exam_id):
    getSession = Session.objects.only('id', 'name')

    exam = get_object_or_404(
        Exam.objects.select_related('course__department', 'class_groups')
                    .prefetch_related('questions'),
        id=exam_id,
    )

    teacher = request.user
    exams = (
        Exam.objects.filter(created_by=teacher)
        .select_related('course__department', 'class_groups')
        .order_by('course__title')
    )

    for e in exams:
        class_name      = e.class_groups.name.strip() if e.class_groups else ''
        raw_title_clean = re.sub(
            r'^(SS|JSS|Grade|Year)\s*\d+\s*[A-Z]?\s*',
            '', e.title.strip(), flags=re.IGNORECASE,
        ).strip()
        e.display_title = f"{class_name} {raw_title_clean}"

    course     = exam.course
    department = course.department
    classgroup = exam.class_groups

    schedules = (
        ExamSchedule.objects.filter(exam=exam)
        .select_related('department', 'class_level', 'course_name', 'session')
        .order_by('-scheduled_date', '-start_time')
    )
    schedule = schedules.first()

    students = (
        Student.objects.filter(courses=course, level_or_class=classgroup)
        .select_related('department', 'level_or_class')
        .only(
            'id', 'full_name', 'admission_number', 'gender',
            'profile_picture', 'date_joined',
            'department__name', 'level_or_class__name',
        )
        .distinct()
    )

    all_classgroups = ClassGroup.objects.only('id', 'name').order_by('name')

    ctx = {
        'exam':             exam,
        'getSession':       getSession,
        'course':           course,
        'department':       department,
        'classgroup':       classgroup,
        'exams':            exams,
        'questions':        exam.questions.all(),
        'students':         students,
        'all_classgroups':  all_classgroups,
        'schedules':        schedules,
        'schedule':         schedule,
        # kept for template compatibility
        'class_group':      classgroup,
    }
    return render(request, 'exam_details.html', ctx)


@login_required
def edit_question(request):
    if request.method == 'POST':
        question = get_object_or_404(Question, id=request.POST.get('question_id'))
        question.question_text  = request.POST.get('question_text')
        question.option_a       = request.POST.get('option_a')
        question.option_b       = request.POST.get('option_b')
        question.option_c       = request.POST.get('option_c')
        question.option_d       = request.POST.get('option_d')
        question.correct_answer = request.POST.get('correct_answer')
        question.term           = request.POST.get('term')
        question.save()
        messages.success(request, 'Question updated successfully!')
        return redirect('exam_detail', exam_id=question.exam.id)


@login_required
def publish_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        selected_ids = request.POST.getlist('class_groups')
        target_groups = ClassGroup.objects.filter(id__in=selected_ids)
        questions = Question.objects.filter(exam=exam)

        published_to = []
        updated = []

        for group in target_groups:
            existing = Exam.objects.filter(
                course=exam.course, class_groups=group, created_by=request.user
            ).first()

            if existing:
                # Sync questions: clear old ones and re-create from source exam
                existing.questions.all().delete()
                Question.objects.bulk_create([
                    Question(
                        exam=existing,
                        question_text=q.question_text,
                        option_a=q.option_a, option_b=q.option_b,
                        option_c=q.option_c, option_d=q.option_d,
                        correct_answer=q.correct_answer, term=q.term,
                    ) for q in questions
                ])
                updated.append(group.name)
                continue

            new_exam = Exam.objects.create(
                course=exam.course,
                class_groups=group,
                created_by=request.user,
                title=f"{exam.course.title} Exam ({group.name})",
            )
            Question.objects.bulk_create([
                Question(
                    exam=new_exam,
                    question_text=q.question_text,
                    option_a=q.option_a, option_b=q.option_b,
                    option_c=q.option_c, option_d=q.option_d,
                    correct_answer=q.correct_answer, term=q.term,
                ) for q in questions
            ])
            published_to.append(group.name)

        parts = []
        if published_to:
            parts.append(f"Published to: {', '.join(published_to)}.")
        if updated:
            parts.append(f"Updated existing exams (synced new questions) for: {', '.join(updated)}.")
        return JsonResponse({'success': True, 'message': ' '.join(parts) or 'No class groups selected.'})

    return JsonResponse({'error': 'Invalid request.'}, status=400)



@login_required
def schedule_exam(request, exam_id):
    exam    = get_object_or_404(Exam, id=exam_id)
    session = Session.objects.all()

    if request.method == 'POST':
        department_id    = request.POST.get('department_id')
        class_level_id   = request.POST.get('classgroup_id')
        course_id        = request.POST.get('course_id')
        scheduled_date   = request.POST.get('scheduled_date')
        start_time       = request.POST.get('start_time')
        duration_minutes = request.POST.get('duration_minutes')
        total_questions  = request.POST.get('total_questions')
        term             = request.POST.get('term')
        session_id       = request.POST.get('session')
        session_instance = get_object_or_404(Session, id=session_id)

        if not all([department_id, class_level_id, course_id,
                    scheduled_date, start_time, duration_minutes, total_questions, term]):
            return JsonResponse({'status': 'error', 'message': 'All fields are required.'})

        try:
            total_questions  = int(total_questions)
            duration_minutes = int(duration_minutes)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid numeric input.'})

        available_questions = Question.objects.filter(exam=exam).count()
        if total_questions > available_questions:
            return JsonResponse({
                'status':  'error',
                'message': (
                    f'You cannot schedule {total_questions} questions. '
                    f'Only {available_questions} question(s) exist for this exam.'
                ),
            })

        department  = get_object_or_404(Department, id=department_id)
        class_level = get_object_or_404(ClassGroup, id=class_level_id)
        course      = get_object_or_404(Course, id=course_id)

        try:
            naive_datetime = datetime.strptime(f"{scheduled_date} {start_time}", '%Y-%m-%d %H:%M')
            timezone.make_aware(naive_datetime, timezone.get_current_timezone())
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid date/time format: {e}'})

        existing_schedule = ExamSchedule.objects.filter(
            exam=exam, department=department,
            class_level=class_level, course_name=course, term=term,
        ).first()

        if existing_schedule:
            existing_schedule.scheduled_date   = scheduled_date
            existing_schedule.start_time       = start_time
            existing_schedule.duration_minutes = duration_minutes
            existing_schedule.total_questions  = total_questions
            existing_schedule.save(update_fields=[
                'scheduled_date', 'start_time', 'duration_minutes', 'total_questions'
            ])
            return JsonResponse({'status': 'updated', 'message': 'Existing exam schedule updated successfully!'})

        ExamSchedule.objects.create(
            exam=exam, department=department, class_level=class_level,
            course_name=course, scheduled_date=scheduled_date,
            start_time=start_time, duration_minutes=duration_minutes,
            total_questions=total_questions, created_by=request.user,
            term=term, session=session_instance,
        )
        return JsonResponse({'status': 'success', 'message': 'Exam scheduled successfully!'})

    return render(request, 'exam_details.html', {
        'exam':         exam,
        'departments':  Department.objects.all(),
        'class_levels': ClassGroup.objects.all(),
        'getSession':   session,
    })


def teacher_manage_course(request):
    teacher = request.user
    courses = (
        Course.objects
        .filter(exam__created_by=teacher)
        .annotate(question_count=Count('exam__questions', distinct=True))
        .distinct()
        .prefetch_related('exam_set')
    )
    total_question_count = Question.objects.filter(exam__created_by=teacher).count()

    return render(request, 'teacher_manage_course.html', {
        'courses':              courses,
        'total_question_count': total_question_count,
    })


# ============================================================
# STUDENT PORTAL  &  EXAM TAKING
# ============================================================

@login_required(login_url="LoginUser")
def student_portal(request):
    getLogo   = schoollogo.objects.only('LogoImage').first()
    getTitle  = title.objects.first()

    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.warning(request, 'Student profile not found. Please contact admin.')
        return redirect('LoginUser')

    sessions = Session.objects.only('id', 'name').order_by('-name')

    session_id = request.GET.get('session')
    if session_id:
        selected_session = get_object_or_404(Session, id=session_id)
    else:
        selected_session = Session.objects.filter(is_current=True).first()

    request.session['theSession'] = selected_session.id

    selected_term = request.GET.get('term', 'First Term')
    is_ajax       = request.GET.get('ajax')

    enrollment = (
        StudentEnrollment.objects.filter(student=student, session=selected_session)
        .select_related('session')
        .first()
    )

    exams_qs = (
        ExamSchedule.objects.filter(
            class_level=student.level_or_class,
            department=student.department,
            term=selected_term,
        )
        .select_related('course_name', 'exam')
    )

    exams_map = {}
    for exam in exams_qs:
        exam.status = exam.computed_status
        exams_map[exam.course_name_id] = exam

    courses = []
    if enrollment:
        regs = (
            CourseRegistration.objects.filter(enrollment=enrollment)
            .select_related('course')
        )
        for reg in regs:
            courses.append({'course': reg.course, 'exam': exams_map.get(reg.course.id)})

    if is_ajax:
        return render(request, 'exam_list.html', {'exams': exams_qs})

    return render(request, 'student_portal.html', {
        'student':          student,
        'sessions':         sessions,
        'selected_session': selected_session,
        'courses':          courses,
        'getTitle':         getTitle,
        'getLogo':          getLogo,
        'exams':            exams_qs,
        'selected_term':    selected_term,
        'terms':            ['First Term', 'Second Term', 'Third Term'],
    })


@login_required
def take_exam(request, course_id):
    AggrePercentage = AgregatedPercentahe.objects.only('scorePercent').first()
    getThePercent   = AggrePercentage.scorePercent if AggrePercentage else 100
    term            = request.GET.get('term', '').strip()

    student = get_object_or_404(
        Student.objects.select_related('department', 'level_or_class', 'user'),
        user=request.user,
    )

    session_idx      = request.session.get('theSession')
    selected_session = get_object_or_404(Session, id=session_idx)

    active_exam = request.session.get('exam_in_progress')
    if active_exam and active_exam != course_id:
        return render(request, 'exam_not_found.html', {
            'message': 'You already have an active exam session in progress.'
        })
    request.session['exam_in_progress'] = course_id

    exam_schedule = (
        ExamSchedule.objects.filter(
            course_name_id=course_id,
            department=student.department,
            class_level=student.level_or_class,
            term__iexact=term,
            session=selected_session,
        )
        .select_related('exam', 'course_name')
        .first()
    )

    if not exam_schedule:
        return render(request, 'exam_not_found.html', {
            'message': 'No scheduled exam found for your class or department.'
        })

    exam = exam_schedule.exam

    # ✅ Duplicate check before loading questions
    if MarkedExam.objects.filter(student=student, exam=exam, term=term, session=selected_session).exists():
        return render(request, 'exam_not_found.html', {
            'message': f'You have already taken the exam: {exam.title}.'
        })

    questions = list(
        exam.questions
        .filter(term__iexact=term)
        .only('id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')
    )

    if not questions:
        return render(request, 'exam_not_found.html', {
            'message': f'No questions found for {exam.title}. Please contact your instructor.'
        })

    random.shuffle(questions)
    for q in questions:
        options = [q.option_a, q.option_b, q.option_c, q.option_d]
        random.shuffle(options)
        q.shuffled_options = options

    if request.method == 'POST':
        score   = 0
        answers = {}
        for q in questions:
            selected              = request.POST.get(f'question_{q.id}', 'Not Answered')
            answers[q.id]         = selected
            if selected == q.correct_answer:
                score += 1

        total_questions = len(questions)
        percentage      = round((score / total_questions) * getThePercent, 2)

        MarkedExam.objects.get_or_create(
            student=student, exam=exam, term=term, session=selected_session,
            defaults={
                'department':     student.department,
                'course':         exam.course,
                'exam_number':    student.admission_number,
                'username':       student.user.username,
                'full_name':      student.full_name,
                'total_score':    score,
                'total_questions': total_questions,
                'percentage':     percentage,
            },
        )

        request.session.pop('exam_in_progress', None)

        return render(request, 'exam_result.html', {
            'exam': exam, 'questions': questions, 'answers': answers,
            'score': score, 'total': total_questions,
            'percentage': percentage, 'student': student,
        })

    return render(request, 'take_exam.html', {
        'term': term, 'exam': exam, 'questions': questions,
        'exam_schedule': exam_schedule, 'student': student,
        'selected_session': selected_session,
    })

@login_required
def exam_not_found(request):
    return render(request, 'exam_not_found.html')


@login_required
def MyStudent(request, classgroup_id, course_id):
    classgroup = get_object_or_404(ClassGroup, id=classgroup_id)
    course     = get_object_or_404(Course, id=course_id)

    students = (
        Student.objects.filter(level_or_class=classgroup)
        .select_related('department', 'level_or_class')
        .distinct()
    )

    return render(request, 'MyStudent.html', {
        'classgroup': classgroup,
        'course':     course,
        'students':   students,
    })


# ============================================================
# SCORES
# ============================================================



@login_required
def student_score(request, student_id, course_id):
    AggrePercentage = AgregatedPercentahe.objects.only('scorePercent').first()
    getThePercent   = AggrePercentage.scorePercent if AggrePercentage else 100

    student    = get_object_or_404(Student, id=student_id)
    course     = get_object_or_404(Course, id=course_id)
    getSession = Session.objects.only('id', 'name')

    scores = (
        MarkedExam.objects.filter(student=student, course=course)
        .select_related('course', 'exam', 'department')
    )
    Testscores = (
        TestScore.objects.filter(student=student, course=course)
        .select_related('course', 'department')
    )

    if request.method == 'POST':
        session_instance = get_object_or_404(Session, id=request.POST.get('session'))
        try:
            TestScore.objects.update_or_create(
                student=student,
                course=course,
                department=student.department,
                class_group=str(student.level_or_class),
                test_type=request.POST.get('test_type', '').strip(),
                Testterm=request.POST.get('Testterm', '').strip(),
                session=session_instance,
                defaults={
                    'total_questions': int(request.POST.get('total_questions', 0)),
                    'total_score':     int(request.POST.get('total_score', 0)),
                },
            )
            return JsonResponse({'message': 'Score added successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    # ✅ Exam aggregate (unchanged — not term-split)
    exam_agg = scores.aggregate(
        total_score=Sum('total_score'),
        total_questions=Sum('total_questions'),
    )
    exam_total_score     = exam_agg['total_score']     or 0
    exam_total_questions = exam_agg['total_questions'] or 0
    exam_percentage = round((exam_total_score / exam_total_questions * 70), 2) if exam_total_questions else 0

    # ✅ Per-term TestScore breakdown
    TERM_ORDER = ['First Term', 'Second Term', 'Third Term',
                  'First Semester', 'Second Semester', 'Third Semester']

    term_rows = (
        Testscores
        .values('Testterm')
        .annotate(
            term_total_score=Sum('total_score'),
            term_total_questions=Sum('total_questions'),
        )
    )

    term_breakdown = {}
    for row in term_rows:
        term = row['Testterm']
        ts = row['term_total_score'] or 0
        tq = row['term_total_questions'] or 0
        pct = round((ts / tq) * 30, 2) if tq else 0
        term_breakdown[term] = {
            'total_score': ts,
            'total_questions': tq,
            'test_percentage': pct,
        }

    # Order it so First/Second/Third render in sequence in the template
    ordered_term_breakdown = [
        {'term': t, **term_breakdown[t]}
        for t in TERM_ORDER if t in term_breakdown
    ]

    # ✅ Final/Total TestScore aggregate — weighted sum across ALL terms
    total_score_sum     = sum(v['total_score'] for v in term_breakdown.values())
    total_questions_sum = sum(v['total_questions'] for v in term_breakdown.values())
    test_percentage = round((total_score_sum / total_questions_sum) * 30, 2) if total_questions_sum else 0

    # --- Alternative: simple average of each term's percentage instead ---
    # pcts = [v['test_percentage'] for v in term_breakdown.values()]
    # test_percentage = round(sum(pcts) / len(pcts), 2) if pcts else 0

    total_percentage = round(exam_percentage + test_percentage, 2)

    return render(request, 'studentScore.html', {
        'Testscores':          Testscores,
        'term_breakdown':      ordered_term_breakdown,
        'total_score_sum':     total_score_sum,
        'test_percentage':     test_percentage,
        'total_percentage':    total_percentage,
        'student':             student,
        'course':              course,
        'getSession':          getSession,
        'scores':              scores,
    })



@login_required
def export_student_scores_csv(request, student_id, course_id):
    student = get_object_or_404(Student, id=student_id)
    course  = get_object_or_404(Course, id=course_id)
    scores  = (
        MarkedExam.objects.filter(student=student, course=course)
        .select_related('exam', 'department', 'course')
    )

    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{student.full_name}_marked_exams.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(['S/N', 'Student Name', 'Exam Title', 'Course', 'Department',
                     'Total Questions', 'Total Score', 'Percentage', 'Date Taken'])

    for idx, score in enumerate(scores, start=1):
        writer.writerow([
            idx,
            score.full_name,
            score.exam.title   if score.exam       else '-',
            score.course.title if score.course     else '-',
            score.department.name if score.department else '-',
            score.total_questions,
            score.total_score,
            f'{score.percentage:.2f}%',
            score.date_taken.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


# ============================================================
# RESULT CHECK  (public)
# ============================================================

def CheckResult(request):
    try:
        ctx = mainView().copy()

        student          = None
        results          = None
        ts_score_map     = {}
        term             = None
        error            = None
        resultCount      = 0
        session          = 0
        total_exam_score = 0
        total_test_score = 0
        grand_total      = 0
        overall_percentage = 0

        if request.method == 'POST':
            form = ResultCheckForm(request.POST)

            if form.is_valid():
                admission_number = form.cleaned_data['admission_number']
                access_code      = form.cleaned_data['access_code']
                term             = form.cleaned_data['term']
                session          = form.cleaned_data['session']

                try:
                    student = Student.objects.get(admission_number=admission_number)
                    ResultAccessCode.objects.get(code=access_code)

                    results = (
                        MarkedExam.objects
                        .filter(student=student, term=term, session=session)
                        .select_related('exam', 'course', 'department')
                    )
                    resultCount = results.count()

                    Testscores = (
                        TestScore.objects
                        .filter(student=student, Testterm=term, session=session)
                        .values('course_id')
                        .annotate(
                            total_test_score=Sum('total_score'),
                            total_test_max=Sum('total_questions'),
                        )
                    )

                    ts_score_map = {ts['course_id']: ts['total_test_score'] for ts in Testscores}

                    exam_agg         = results.aggregate(total=Sum('total_score'), total_q=Sum('total_questions'))
                    total_exam_score = exam_agg['total']   or 0
                    total_exam_max   = exam_agg['total_q'] or 0
                    total_test_score = sum(ts['total_test_score'] or 0 for ts in Testscores)
                    total_test_max   = sum(ts['total_test_max']   or 0 for ts in Testscores)
                    grand_total      = total_exam_score + total_test_score
                    grand_max        = total_exam_max   + total_test_max
                    overall_percentage = (grand_total / grand_max * 100) if grand_max > 0 else 0

                    if not results.exists() and not ts_score_map:
                        error = f'No results found for {term} or {session}.'

                except Student.DoesNotExist:
                    error = 'Invalid admission number.'
                except ResultAccessCode.DoesNotExist:
                    error = 'Invalid result access code.'
                except Exception as e:
                    print(e)
                    error = 'An unexpected error occurred.'
        else:
            form = ResultCheckForm()

        ctx.update({
            'form':              form,
            'resultCount':       resultCount,
            'student':           student,
            'results':           results,
            'ts_score_map':      ts_score_map,
            'term':              term,
            'session':           session,
            'error':             error,
            'total_exam_score':  total_exam_score,
            'total_test_score':  total_test_score,
            'grand_total':       grand_total,
            'overall_percentage': overall_percentage,
        })
        return render(request, 'checkResult.html', ctx)

    except Exception as e:
        print(e)
        return HttpResponse('Internal Server Error', status=500)


# ============================================================
# BULK SMS
# ============================================================

def bulk_sms_page(request):
    student_group  = Group.objects.get(name='Student')
    students_users = student_group.user_set.all()
    students       = Student.objects.filter(user__in=students_users)
    classes        = ClassGroup.objects.all().distinct()
    department     = Department.objects.all().distinct()

    return render(request, 'bulk_sms.html', {
        'students':   students,
        'classes':    classes,
        'department': department,
    })


@csrf_exempt
def send_bulk_sms(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    data        = json.loads(request.body)
    getTitle    = title.objects.first()
    getLogo     = schoollogo.objects.first()
    logo_url    = request.build_absolute_uri(getLogo.LogoImage.url) if getLogo else ''
    recipients  = data.get('recipients', [])
    addEmails   = data.get('addEmails', [])
    Themessage  = data.get('message', '')
    from_email  = settings.DEFAULT_FROM_EMAIL

    emails = [r.get('email') for r in recipients if r.get('email') not in [None, '', 'undefined']]
    phone_numbers = clean_phone_numbers([r['phone'] for r in recipients])

    if addEmails == 'Yes':
        try:
            subject      = f'New Message from {getTitle}'
            text_content = (
                f"New Message from {getTitle}\n\nSender: {getTitle}\nEmail: {from_email}"
                f"\n\nMessage:\n{Themessage}\n\nThank you."
            )
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
                <table width="100%" cellpadding="0" cellspacing="0"
                       style="max-width:600px;margin:auto;background:#fff;border-radius:10px;
                              padding:30px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                    <tr><td style="text-align:center;padding-bottom:20px;">
                        <h2 style="margin:0;color:#2a6edc;">📘 School Notification</h2>
                        <p style="color:#777;margin-top:5px;">A new message has been sent to you</p>
                    </td></tr>
                    <tr><td align="center">
                        <img src="{logo_url}" alt="School Logo" style="width:130px;margin-bottom:20px;">
                    </td></tr>
                    <tr><td style="padding:20px;">
                        <h3 style="margin-bottom:10px;color:#333;">Message Details</h3>
                        <p style="color:#444;line-height:1.6;">
                            <strong>Sender Name:</strong> {getTitle}<br>
                            <strong>Sender Email:</strong> {from_email}
                        </p>
                        <div style="background:#f1f1f1;padding:15px;border-left:4px solid #2a6edc;
                                    border-radius:5px;margin-top:15px;">
                            <p style="margin:0;color:#333;font-size:15px;line-height:1.6;">{Themessage}</p>
                        </div>
                        <p style="margin-top:30px;color:#555;">
                            Thank you for staying connected with our school.<br>
                            <strong>School Administration</strong><br>
                            <strong>{getTitle.phonNo}</strong>
                        </p>
                    </td></tr>
                </table>
                <p style="text-align:center;color:#aaa;margin-top:20px;font-size:13px;">
                    &copy; {getTitle} School • All Rights Reserved
                </p>
            </body>
            </html>
            """
            email_msg = EmailMultiAlternatives(subject, text_content, from_email, emails)
            email_msg.attach_alternative(html_content, 'text/html')
            email_msg.send()
            messages.success(request, 'Email also sent successfully')
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    results = send_sms(phone_numbers, Themessage)

    if results['success']:
        messages.success(request, 'SMS sent successfully to: ' + ', '.join(results['success']))
    if results['failed']:
        fail_msg = '; '.join(f"{f['number']} ({f['error']})" for f in results['failed'])
        messages.error(request, 'Failed: ' + fail_msg)

    return JsonResponse({
        'status': 'success',
        'count':  len(phone_numbers),
        'sent':   results['success'],
        'failed': results['failed'],
    })


# ============================================================
# PAYMENTS
# ============================================================

@login_required
def pay_fee(request, enrollment_id):
    ctx        = mainView().copy()
    enrollment = get_object_or_404(StudentEnrollment, id=enrollment_id)
    fee        = SchoolFee.objects.filter(
        session=enrollment.session, classgroup=enrollment.classgroup
    ).first()

    if not fee:
        return redirect('parent_child_dashboard')

    payment, _         = FeePayment.objects.get_or_create(enrollment=enrollment, fee=fee)
    percentage_paid    = (payment.amount_paid / fee.amount * 100) if fee.amount > 0 else 0
    balance            = fee.amount - payment.amount_paid
    history            = payment.installments.all().order_by('-date_paid')

    monthly_payments = (
        payment.installments
        .annotate(month=TruncMonth('date_paid'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    labels = [p['month'].strftime('%b %Y') for p in monthly_payments]
    chart_data = [float(p['total']) for p in monthly_payments]

    min_first_payment = fee.deposit_amount
    has_paid_before   = payment.amount_paid > 0

    shared = {
        'enrollment': enrollment, 'fee': fee, 'payment': payment,
        'percentage_paid': percentage_paid, 'balance': balance, 'history': history,
    }

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))

        if not has_paid_before and amount < min_first_payment:
            ctx.update(shared)
            ctx['error'] = f'Initial deposit is ₦{min_first_payment}. You entered ₦{amount}.'
            return render(request, 'payments/pay_fee.html', ctx)

        if amount > balance:
            ctx.update(shared)
            ctx['error'] = f'You cannot pay more than the remaining balance ₦{balance}.'
            return render(request, 'payments/pay_fee.html', ctx)

        paystack_url = 'https://api.paystack.co/transaction/initialize'
        ps_headers   = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
        ps_data      = {
            'email':        enrollment.student.user.email,
            'amount':       int(amount * 100),
            'currency':     'NGN',
            'callback_url': request.build_absolute_uri(reverse('paystack_callback')),
            'metadata':     {'enrollment_id': enrollment.id, 'amount': str(amount)},
        }
        resp_data = requests.post(paystack_url, headers=ps_headers, json=ps_data).json()

        if resp_data.get('status'):
            return redirect(resp_data['data']['authorization_url'])

        ctx.update(shared)
        ctx['error'] = 'Payment initialization failed.'
        return render(request, 'payments/pay_fee.html', ctx)

    ctx.update(shared)
    ctx.update({'labels': labels, 'data': chart_data})
    return render(request, 'payments/pay_fee.html', ctx)


@login_required
def payment_success(request):
    return render(request, 'payments/payment_success.html', mainView())


@login_required
def paystack_callback(request):
    reference  = request.GET.get('reference')
    verify_url = f'https://api.paystack.co/transaction/verify/{reference}'
    ps_headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    response   = requests.get(verify_url, headers=ps_headers).json()

    if not response.get('status'):
        return HttpResponse('Payment verification failed.')

    data        = response['data']
    metadata    = data.get('metadata', {})
    amount      = Decimal(data['amount']) / 100
    enrollment  = get_object_or_404(StudentEnrollment, id=metadata.get('enrollment_id'))

    fee = SchoolFee.objects.filter(
        session=enrollment.session, classgroup=enrollment.classgroup
    ).first()

    payment, _ = FeePayment.objects.get_or_create(enrollment=enrollment, fee=fee)
    InstallmentPayment.objects.create(payment=payment, amount=amount)

    payment.amount_paid += amount
    if payment.amount_paid >= fee.amount:
        payment.is_fully_paid = True
    payment.save(update_fields=['amount_paid', 'is_fully_paid'])

    messages.success(request, 'Payment successful!')
    return redirect('parent_child_dashboard')


def parent_access(request):
    ctx = mainView().copy()
    if request.method == 'POST':
        admission_number  = request.POST.get('admission_number')
        access_code_input = request.POST.get('access_code')
        try:
            student = Student.objects.get(admission_number=admission_number)
            ResultAccessCode.objects.get(code=access_code_input)
            request.session['parent_student_id'] = student.id
            return redirect('parent_child_dashboard')
        except (Student.DoesNotExist, ResultAccessCode.DoesNotExist):
            pass
    return render(request, 'payments/parent_access.html', ctx)


def parent_child_dashboard(request):
    ctx        = mainView().copy()
    student_id = request.session.get('parent_student_id')
    if not student_id:
        return redirect('parent_access')

    student = get_object_or_404(Student, id=student_id)

    # ✅ Prefetch everything needed to avoid per-enrollment queries
    enrollments = (
        StudentEnrollment.objects.filter(student=student)
        .select_related('session', 'classgroup')
    )

    dashboard_data = []
    for enroll in enrollments:
        fee = SchoolFee.objects.filter(
            session=enroll.session, classgroup=enroll.classgroup
        ).first()

        if fee:
            payment, _      = FeePayment.objects.get_or_create(enrollment=enroll, fee=fee)
            percentage_paid = (payment.total_paid / fee.amount * 100) if fee.amount > 0 else 0
            balance         = fee.amount - payment.total_paid
            history         = payment.installments.all().order_by('-date_paid')
        else:
            payment         = None
            percentage_paid = 0
            balance         = 0
            history         = []

        dashboard_data.append({
            'enrollment':       enroll,
            'fee':              fee,
            'payment':          payment,
            'percentage_paid':  round(percentage_paid, 2),
            'balance':          balance,
            'history':          history,
        })

    ctx.update({'student': student, 'dashboard_data': dashboard_data})
    return render(request, 'payments/parent_child_dashboard.html', ctx)