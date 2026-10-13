from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from .models import *


class StudentRegistrationForm(UserCreationForm):
    gender = forms.ChoiceField(
        choices=Student.GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Department dropdown
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Department",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Class dropdown (linked to Department or general list)
    classgroup = forms.ModelChoiceField(
        queryset=ClassGroup.objects.all(),
        label="Class / Level",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        
    )

    admission_number = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admission / Matric No'
        })
    )

    guardian_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parent / Guardian Name'
        })
    )
    guardian_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parent / Guardian Phone'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    profile_picture = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure dropdowns load dynamically
        self.fields['department'].queryset = Department.objects.all()
        self.fields['classgroup'].queryset = ClassGroup.objects.all()
        self.fields['courses'].queryset = Course.objects.all()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            student = Student.objects.create(
                user=user,
                full_name = f"{user.first_name} {user.last_name}",
                gender=self.cleaned_data['gender'],
                department=self.cleaned_data['department'],
                level_or_class=self.cleaned_data.get('classgroup'),
                admission_number=self.cleaned_data['admission_number'],
                guardian_name=self.cleaned_data.get('guardian_name'),
                guardian_phone=self.cleaned_data.get('guardian_phone'),
                profile_picture=self.cleaned_data.get('profile_picture'),
            )
            student.courses.set(self.cleaned_data['courses'])
        return user



class TeacherRegistrationForm(forms.ModelForm):
    # User fields
    first_name = forms.CharField(
        label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        label="Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'})
    )
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'})
    )

    class Meta:
        model = Teacher
        fields = [
            'first_name', 'last_name', 'username', 'password', 'email',  # from User
            'gender', 'department', 'courses', 'class_groups',
            'qualification', 'profile_picture', 'phone',
        ]

        widgets = {
            # 'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'courses': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'class_groups': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. B.Sc, M.Sc, PhD'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +234 8012345678'}),
        }

    def save(self, commit=True):
        """Create linked User + Teacher"""
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
        )

        teacher = super().save(commit=False)
        teacher.user = user  # link the teacher to the created user
        
        teacher.full_name = f"{user.first_name} {user.last_name}".strip()
        if commit:
            teacher.save()
            self.save_m2m()  # for many-to-many relationships

        return teacher

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'term']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control question-input', 'rows': 3}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_answer': forms.Select(attrs={'class': 'form-select'}),
            'term': forms.Select(attrs={'class': 'form-select'}),
        }


class ResultCheckForm(forms.Form):
    TERM_CHOICES = [
        ('First Term', 'First Term'),
        ('Second Term', 'Second Term'),
        ('Third Term', 'Third Term'),
        ('Fourth Term', 'Fourth Term'),
    ]
    admission_number = forms.CharField(
        label="Admission Number",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Admission / Matric Number'})
    )
    access_code = forms.CharField(
        label="Access Code",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Access Code (e.g. 12345Hero)'})
    )
    
    term = forms.ChoiceField(
        label="Choose Term",
        choices=TERM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    session = forms.ModelChoiceField(
        queryset=Session.objects.all(),
        empty_label="Select a Session",
        widget=forms.Select(attrs={"class":"form-control"})
    )




class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = [
            'session',
            'department',
            'classgroup',
            'course',
            'teacher',
            'classroom',
            'day',
            'time_slot'
        ]

        widgets = {
            'session': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'classgroup': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'classroom': forms.Select(attrs={'class': 'form-control'}),
            'day': forms.Select(attrs={'class': 'form-control'}),
            'time_slot': forms.Select(attrs={'class': 'form-control'}),
        }

class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['file']

        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'required': True
            })
        }
