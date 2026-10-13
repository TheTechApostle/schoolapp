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

    # Create new exam
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

        exam = Exam.objects.create(
            course=course,
            title=f"{course.title} Exam ({classgroup.name})",
            created_by=request.user,
        )

        messages.success(request, f"Exam '{exam.title}' created successfully.")
        return redirect('add_questions', exam_id=exam.id)

    elif request.method == 'POST' and 'save_questions' in request.POST:
        exam_id = request.POST.get('exam_id')
        exam = get_object_or_404(Exam, id=exam_id)

        created_count = 0
        question_index = 1

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
                    correct_answer=correct
                )
                created_count += 1

            question_index += 1

        if created_count:
            messages.success(request, f"{created_count} question(s) added to '{exam.title}'.")
            return redirect('exam_detail', exam_id=exam.id)
        else:
            messages.warning(request, "No valid questions were submitted.")
    print("POST DATA:", request.POST)

    # Render template
    context = {
        'exam': exam,
        'departments': departments,
        'classes': classes,
        'courses': courses,
        'teacher': teacher,
        'form': QuestionForm(),
    }
    return render(request, 'add_questions.html', context)


