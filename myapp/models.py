from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone
# Create your models here.

class title(models.Model):
    name = models.CharField("Title", max_length=50)
    phonNo = models.CharField("Phone No", max_length=50)
    email = models.CharField("Email", max_length=50)
    address = models.CharField("Address", max_length=100)
    
    def __str__(self):
        return self.name

class schoollogo(models.Model):
    LogoText = models.TextField("Logo Text", max_length=50)
    LogoImage = models.FileField(upload_to="logo_images/")
    

class AboutSchool(models.Model):
    aboutus = models.CharField("About Us", max_length=50)
    mission = models.CharField("Mission", max_length=100)
    vision = models.CharField("Vision", max_length=100)
    aboutImage =  models.FileField(upload_to="aboutImage/")
    


class Department(models.Model):
    """Represents either a Department (University) or Class (Secondary School)"""
    LEVEL_CHOICES = [
        ('Secondary', 'Secondary School'),
        ('College', 'College'),
        ('Polytechnic', 'Polytechnic'),
        ('University', 'University'),
        ('Other', 'Other Institution'),
    ]

    institution_type = models.CharField(
        "Institution Type",
        max_length=20,
        choices=LEVEL_CHOICES,
        default='Secondary'
    )
    name = models.CharField("Department / Class Name", max_length=100, unique=True)
    description = models.TextField("Description", blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Department / Class"
        verbose_name_plural = "Departments / Classes"

    def __str__(self):
        return f"{self.name} ({self.institution_type})"
    
    

class ClassGroup(models.Model):
    """
    Represents a sub-class or level connected to a Department.
    Example:
        - SS1, SS2, SS3 under Secondary School Department
        - 100L, 200L under University Department
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="classes")
    name = models.CharField("Class / Level Name", max_length=100)
    description = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('department', 'name')
        verbose_name = "Class / Level"
        verbose_name_plural = "Classes / Levels"

    def __str__(self):
        return f"{self.name} - {self.department.name}"



class Course(models.Model):
    """Represents either a Course (Tertiary) or Subject (Secondary)"""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    # classgroup = models.ForeignKey(ClassGroup, verbose_name="Class / Level",  on_delete=models.CASCADE, related_name='courses')
    classgroup = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )
    title = models.CharField("Course / Subject Title", max_length=100)
    code = models.CharField("Course / Subject Code", max_length=20, unique=False)
    description = models.TextField("Description", blank=True, null=True)
    credit_unit = models.PositiveIntegerField(
        default=1,
        help_text="Can represent credit units (University) or subject weight (Secondary)"
    )
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = "Course / Subject"
        verbose_name_plural = "Courses / Subjects"

    def __str__(self):
        return f"{self.title} ({self.code})"



class Student(models.Model):
    """Universal model for students in both secondary and higher institutions"""
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='student_profile'
    )
    full_name = models.CharField("Full Name", max_length=150)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, related_name='students'
    )
    courses = models.ManyToManyField(
        Course, related_name='students', blank=True
    )

    admission_number = models.CharField(
        "Admission / Matric No.", max_length=50, unique=True
    )
    level_or_class = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, verbose_name="Class / Level ")
    
    
    guardian_name = models.CharField(
        "Parent / Guardian Name", max_length=100, blank=True, null=True
    )
    guardian_phone = models.CharField(
        "Parent / Guardian Phone", max_length=20, blank=True, null=True
    )
    email = models.EmailField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='student_profiles/', blank=True, null=True
    )
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = "Student / Learner"
        verbose_name_plural = "Students / Learners"

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"
    


# --------Updated / Add Models ----------

class Session(models.Model):
    name = models.CharField(max_length=20, unique=True)  # Example: 2024/2025
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-name']

    def __str__(self):
        return self.name

class StudentEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    classgroup = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'session')
        ordering = ['-session']

    def __str__(self):
        return f"{self.student.full_name} - {self.session}"



class CourseRegistration(models.Model):
    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name="registered_courses")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_registered = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('enrollment', 'course')

    def __str__(self):
        return f"{self.enrollment.student.full_name} - {self.course.title}"



#-----  Ended ----- 

#----- Term ------
class Term(models.Model):
    term = models.CharField(max_length=50)
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="term"
    )
    
    def __str__(self):
        return f'{self.term}'
#----- EndTerm ----

# ----- Payment Model -----
class SchoolFee(models.Model):
    PAYMENT_SCOPE = [
        ('SESSION', 'Session'),
        ('TERM', 'Term'),
    ]

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="fees"
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fees",
        help_text="Required if payment is term-based"
    )

    classgroup = models.ManyToManyField(
        ClassGroup, related_name='fees'
    )

    payment_scope = models.CharField(
        max_length=10,
        choices=PAYMENT_SCOPE,
        default='TERM'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    initial_deposit_percentage = models.PositiveIntegerField(
        default=30,
        help_text="Percentage required before access"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'term', 'payment_scope'],
                name='unique_fee_per_scope'
            )
        ]

    def __str__(self):
        scope = self.term.term if self.term else "Session"
        classes = ", ".join(self.classgroup.values_list('name', flat=True))
        return f"{classes} - {scope} ({self.session})"

    @property
    def deposit_amount(self):
        return round(
            (self.initial_deposit_percentage / 100) * float(self.amount), 2
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.payment_scope == 'TERM' and not self.term:
            raise ValidationError("Term is required for term-based fees")

        if self.payment_scope == 'SESSION' and self.term:
            raise ValidationError("Session-based fees must not have a term")


class FeePayment(models.Model):
    enrollment = models.ForeignKey(
        StudentEnrollment,
        on_delete=models.CASCADE,
        related_name="fee_payments"
    )

    fee = models.ForeignKey(
        SchoolFee,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Required for term-based fees"
    )

    total_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'fee', 'term'],
                name='unique_fee_payment_per_term'
            )
        ]

    def __str__(self):
        scope = self.term.term if self.term else "Session"
        return f"{self.enrollment.student.full_name} - {scope} Fee"

    @property
    def balance(self):
        return round(float(self.fee.amount) - float(self.total_paid), 2)

    @property
    def is_fully_paid(self):
        return self.balance <= 0


class InstallmentPayment(models.Model):
    payment = models.ForeignKey(
        FeePayment,
        on_delete=models.CASCADE,
        related_name="installments"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50, default="Cash")
    reference = models.CharField(
        max_length=100, blank=True, null=True
    )

    date_paid = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment.enrollment.student.full_name} - {self.amount}"

# --- Ended Payment --- 

class Lecture(models.Model):
    CONTENT_TYPES = [
        ('VIDEO', 'Video'),
        ('PDF', 'PDF'),
        ('AUDIO', 'Audio'),
        ('LINK', 'External Link'),
    ]
    STATUS_CHOICES = [
        ('LIVE', 'Live'),
        ('DRAFT', 'Draft'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lectures")
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    file = models.FileField(upload_to="lectures/files/", blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma separated tags")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="DRAFT")
    duration = models.PositiveIntegerField(blank=True, null=True, help_text="Duration in minutes")
    views = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def __str__(self):
        return f"{self.title} ({self.course})"
    

class LectureVote(models.Model):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name="votes")
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()  # 1–5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("lecture", "student")

class Teacher(models.Model):
    """Universal model for Teachers or Lecturers"""
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    full_name = models.CharField("Full Name", max_length=150)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    department = models.ManyToManyField(
    Department, 
        blank=True, 
        related_name='teachers', 
        verbose_name="Departments"
    )
    courses = models.ManyToManyField(
        Course, 
        related_name='teachers', 
        blank=True, 
        verbose_name="Courses / Subjects"
    )
    class_groups = models.ManyToManyField(
        'ClassGroup',
        blank=True,
        related_name='teachers',
        verbose_name="Classes / Levels"  # human-readable name
    )
    qualification = models.CharField("Qualification", max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='teacher_profiles/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = "Teacher / Lecturer"
        verbose_name_plural = "Teachers / Lecturers"

    def __str__(self):
        return self.full_name



class Exam(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    class_groups = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.course.title} ({self.class_groups.name})"


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D')
    ])
    term = models.CharField("Term / Semester", max_length=50, choices=[
        ('First Term', 'First Term'),
        ('Second Term', 'Second Term'),
        ('Third Term', 'Third Term'),
        ('Fourth Term', 'Fourth Term'),
        ('First Semester', 'First Semester'),
        ('Second Semester', 'Second Semester'),
        ('Third Semester', 'Third Semester'),
    ])


    def __str__(self):
        return self.question_text[:50]

# class Question(models.Model):
#     exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
#     question_text = models.TextField()
#     option_a = models.CharField(max_length=255)
#     option_b = models.CharField(max_length=255)
#     option_c = models.CharField(max_length=255)
#     option_d = models.CharField(max_length=255)
#     correct_answer = models.CharField(max_length=1, choices=[
#         ('A', 'Option A'),
#         ('B', 'Option B'),
#         ('C', 'Option C'),
#         ('D', 'Option D')
#     ])

#     def __str__(self):
#         return self.question_text[:50]


class ExamSchedule(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    class_level = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    course_name = models.ForeignKey(Course, on_delete=models.CASCADE)
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    term = models.CharField("Term / Semester", max_length=50, choices=[
        ('First Term', 'First Term'),
        ('Second Term', 'Second Term'),
        ('Third Term', 'Third Term'),
        ('Fourth Term', 'Fourth Term'),
        ('First Semester', 'First Semester'),
        ('Second Semester', 'Second Semester'),
        ('Third Semester', 'Third Semester'),
    ])
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.exam.title} - {self.department.name} ({self.class_level.name})"
    
    
    @property
    def computed_status(self):
        today = timezone.localdate()
        now = timezone.localtime().time()

        if self.scheduled_date == today and self.start_time <= now:
            return "ongoing"
        elif self.scheduled_date > today or (self.scheduled_date == today and self.start_time > now):
            return "upcoming"
        else:
            return "completed"

    
    

class MarkedExam(models.Model):
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='marked_exams')
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='marked_exams')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True)

    exam_number = models.CharField(max_length=50)
    username = models.CharField(max_length=150)
    full_name = models.CharField(max_length=150)
    total_score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    term = models.CharField("Term", max_length=50)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)

    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.exam.title} ({self.total_score}/{self.total_questions})"
    
    class Meta:
        unique_together = ('exam', 'student', 'term', 'session')


class TestScore(models.Model):
    TEST_TYPE_CHOICES = [
        ('1st Test', '1st Test'),
        ('2nd Test', '2nd Test'),
        ('3rd Test', '3rd Test'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    # class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    class_group = models.CharField(max_length=50)
    total_questions = models.PositiveIntegerField()
    total_score = models.PositiveIntegerField()
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    date_added = models.DateTimeField(auto_now_add=True)
    percentage = models.FloatField(blank=True, null=True)
    Testterm = models.CharField("Term", max_length=50)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.full_name} - {self.course.title} ({self.test_type})"

    @property
    def percentage(self):
        if self.total_questions:
            return round((self.total_score / self.total_questions) * 100, 2)
        return 0
    


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"
    
    

class SliderImage(models.Model):
    title = models.CharField(max_length=150)
    image = models.ImageField(upload_to='slider_images/')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # Latest images first

    def __str__(self):
        return self.title
    

class ResultAccessCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    students = models.ManyToManyField('Student', related_name='access_codes')
    # schedule_result_time = models.DateTimeField(null=True, blank=True)  # ✅ This field must exist

    def __str__(self):
        return self.code
    
class AgregatedPercentahe(models.Model):
    scorePercent = models.FloatField(
        unique=True,
        help_text="Enter the percentage multiplier for calculating exam scores (e.g. 100 for 100%)."
    )

    class Meta:
        verbose_name = 'Agregate Percentage'
        verbose_name = 'Agregate Percentage'
    
    
    def __str__(self):
        return f"{self.scorePercent}%"
    
    

class Day(models.Model):
    name = models.CharField(max_length=10, unique=True)  # Monday, Tuesday...

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['start_time']
        unique_together = ('start_time', 'end_time')

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"


class Classroom(models.Model):
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class Timetable(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="timetables"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="timetables"
    )
    classgroup = models.ForeignKey(
        ClassGroup, on_delete=models.CASCADE, related_name="timetables"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="timetables"
    )
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, related_name="timetables"
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.SET_NULL, null=True, related_name="timetables"
    )
    day = models.ForeignKey(
        Day, on_delete=models.CASCADE, related_name="timetables"
    )
    time_slot = models.ForeignKey(
        TimeSlot, on_delete=models.CASCADE, related_name="timetables"
    )

    class Meta:
        ordering = ['day', 'time_slot']
        unique_together = [
            # One class cannot have two courses at same time
            ('session', 'classgroup', 'day', 'time_slot'),

            # Teacher cannot teach two classes at same time
            ('session', 'teacher', 'day', 'time_slot'),

            # Room cannot be used twice at same time
            ('session', 'classroom', 'day', 'time_slot'),
        ]

    def __str__(self):
        return f"{self.classgroup} - {self.course} ({self.day})"


class Elibrary(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Either upload a PDF file OR provide a link
    pdf_file = models.FileField(
        upload_to="elibrary/pdfs/",
        blank=True,
        null=True
    )
    link = models.URLField(
        blank=True,
        null=True,
        help_text="Provide a link if no file is uploaded"
    )
    cover_image = models.ImageField( upload_to="elibrary/covers/", blank=True, null=True, help_text="Optional book cover or thumbnail" )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def source(self):
        """Return whichever source is available (file or link)."""
        if self.pdf_file:
            return self.pdf_file.url
        return self.link
    

class Assignment(models.Model):
    """Assignments given by teachers for their courses"""
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.CASCADE, 
        related_name='assignments'
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='assignments'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    attachment = models.FileField(
        upload_to="assignment_files/",
        blank=True,
        null=True
    )

    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"

    def __str__(self):
        return f"{self.title} ({self.course.title})"



class AssignmentSubmission(models.Model):

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    file = models.FileField(upload_to="submissions/")

    submitted_at = models.DateTimeField(auto_now_add=True)

    score = models.FloatField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.student} - {self.assignment}"


class TechCourse_Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tech Course Category"
        verbose_name_plural = "Tech Course Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    
class TechCourse(models.Model):
    title = models.CharField(max_length=150)
    category = models.ForeignKey(
        TechCourse_Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="techcourse"
    )
    description = models.TextField(blank=True, null=True)
    duration = models.CharField(max_length=100, help_text="e.g. 3 Months")
    price = models.TextField(blank=True, null=True)
    link = models.CharField(max_length=100, help_text="e.g. Youtube Link, Drive Link")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tech Course"
        verbose_name_plural = "Tech Courses"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
