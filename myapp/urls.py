from django.urls import path
from . import views


# urlpatterns = [
#     # ----------------------------
#     # 🏠 Home & Authentication
#     # ----------------------------
#     path('', views.MyHome, name='MyHome'),
#     path('login/', views.LoginUser, name='LoginUser'),

#     # ----------------------------
#     # 🎓 Student Routes
#     # ----------------------------
#     path('register/student/', views.register_student, name='register_student'),
#     path('register/student/SuccessPage/', views.SuccessPage, name='SuccessPage'),
#     path('CBT/student/dashboard/', views.dashboard, name='dashboard'),
#     path('portal/', views.student_portal, name='student_portal'),

#     # ----------------------------
#     # 👩‍🏫 Teacher Routes
#     # ----------------------------
#     path('CBT/Teacherdashboard/', views.Teacherdashboard, name='Teacherdashboard'),
#     path('CBT/Teacherdashboard/manage-course/', views.teacher_manage_course, name='teacher_manage_course'),

#     # Add or edit exam questions
#     path('CBT/Teacherdashboard/add-questions/', views.add_questions, name='add_questions'),
#     path('CBT/Teacherdashboard/add-questions/<int:exam_id>/', views.add_questions, name='add_questions_with_id'),

#     # ----------------------------
#     # 🧾 Exam Management (Teacher)
#     # ----------------------------
#     path('exam/detail/<int:exam_id>/', views.exam_detail, name='exam_detail'),
#     path('exam/<int:exam_id>/schedule/', views.schedule_exam, name='schedule_exam'),
#     path('exam/<int:exam_id>/edit-question/', views.edit_question, name='edit_question'),
#     path('exam/not-found/', views.exam_not_found, name='exam_not_found'),

#     # ----------------------------
#     # 🧑‍🎓 Student Exam Participation
#     # ----------------------------
#     path('exam/take/<int:course_id>/', views.take_exam, name='take_exam'),
# ]



urlpatterns = [
    path('', views.MyHome, name='MyHome'),
    path("debug-headers/", views.debug_headers),
    path("show-headers/", views.show_headers),
    path('register/student/', views.register_student, name='register_student'),
    path("bulk-sms/", views.bulk_sms_page, name="bulk_sms"),
    path("api/send-bulk-sms/", views.send_bulk_sms, name="send_bulk_sms"),
    path('e_learning/teacher/', views.lecture_list, name='lecture_list'),
    path("lectures/upload/", views.lecture_upload, name="lecture_upload"),
    path("lectures/toggle/", views.lecture_toggle_status, name="lecture_toggle_status"),
    path("lectures/delete/", views.lecture_delete, name="lecture_delete"),
    path("lectures/export/", views.export_lectures_csv, name="export_lectures_csv"),
    path("lectures/<int:pk>/preview/", views.lecture_preview, name="lecture_preview"), 
    path("Elerning/student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("lectures/<int:pk>/view/", views.lecture_student_view, name="lecture_student_view"),
    path("lectures/<int:pk>/vote/", views.lecture_vote, name="lecture_vote"),
    path("student_courses/<int:course_id>/", views.course_detail, name="course_detail"),
    path('teachers/teacher_list', views.teacher_list, name='teacher_list'),
    path('logout/', views.logout_user, name='logout_user'),
    path('register/Teacher/', views.register_teacher, name='register_teacher'),
    path('ajax/load-classgroups/', views.load_classgroups, name='ajax_load_classgroups'),
    path('ajax/load-courses/', views.load_courses, name='ajax_load_courses'),
    path('register/student/SuccessPage', views.SuccessPage, name='SuccessPage'),
    path('CBT/student/dashboard', views.dashboard, name='dashboard'),
    path('CBT/Teacherdashboard', views.Teacherdashboard, name='Teacherdashboard'),
    path('exams/<int:exam_id>/add-questions/', views.add_questions, name='add_questions'),
    path('CBT/Teacherdashboard/add_questions', views.add_questions, name='add_questions'),
    path('portal/', views.student_portal, name='student_portal'),
      # Page to start exam
    path('CBT/Teacherdashboard/teacher_manage_course', views.teacher_manage_course, name='teacher_manage_course'),
    path('exam/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('examStudent/<int:classgroup_id>/course/<int:course_id>/', views.MyStudent, name='myStudent'),
    path('question/edit/', views.edit_question, name='edit_question'),
    path('exam/<int:exam_id>/schedule/', views.schedule_exam, name='schedule_exam'),
    path('login/', views.LoginUser, name="LoginUser"),
    path('exam/exam_not_found', views.exam_not_found, name="exam_not_found"),
    path('takeexam/<int:course_id>/', views.take_exam, name='take_exam'),
    path('exam/<int:exam_id>/publish/', views.publish_exam, name='publish_exam'),
    path('Student/ResultCheck', views.CheckResult, name='CheckResult'),
    # urls.py
    path('students/<int:student_id>/scores/<int:course_id>/', views.student_score, name='student_score'),
    path('student/<int:student_id>/course/<int:course_id>/export_csv/', 
         views.export_student_scores_csv, name='export_student_scores_csv'),
    path("parent/access/", views.parent_access, name="parent_access"),
    path("parent/dashboard/", views.parent_child_dashboard, name="parent_child_dashboard"),
    path("pay_fee/<int:enrollment_id>/", views.pay_fee, name="pay_fee"),
    path("paystack/callback/", views.paystack_callback, name="paystack_callback"),
    path("payment_success/", views.payment_success, name="payment_success"),
    path("elearning/elibrary", views.elibrary_list, name="elibrary_list"), 
    path("<int:pk>/", views.elibrary_detail, name="elibrary_detail"),
    path("timetable/create/", views.create_timetable, name="create_timetable"),
    path("timetable/student/", views.student_timetable, name="student_timetable"),
    path("timetable/teacher/", views.teacher_timetable, name="teacher_timetable"),
    path("school/timetable_grid/", views.timetable_grid, name="timetable_grid"),
    path('assignments/add/', views.add_assignment_ajax, name='add_assignment_ajax'),
    path('assignments/view/', views.assignments_view, name='assignments_view'),
    path('ai_assistance/', views.ai_assistance, name='ai_assistance'),
    path('techcourse/', views.techcourse_list, name='techcourse_list'),
    path("techcourse/<int:id>/", views.techcourse_detail, name="techcourse_detail"),
    path('assignments/submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('assignments/delete/<int:assignment_id>/', views.delete_assignment_ajax, name='delete_assignment_ajax'),
]

