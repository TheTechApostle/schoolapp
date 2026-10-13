from django.core.management.base import BaseCommand
from myapp.models import Student, Session, StudentEnrollment, CourseRegistration   # Update to your app names

class Command(BaseCommand):
    help = "Migrates old Student model data into new dynamic tables"

    def handle(self, *args, **kwargs):
        current_session = Session.objects.get(is_current=True)

        self.stdout.write(self.style.WARNING("Migrating student enrollment..."))

        for s in Student.objects.all():
            enroll, created = StudentEnrollment.objects.get_or_create(
                student=s,
                session=current_session,
                defaults={
                    'department': s.department,
                    'classgroup': s.level_or_class,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Enrollment created for {s.full_name}"))

            # Register old courses
            for c in s.courses.all():
                CourseRegistration.objects.get_or_create(
                    enrollment=enroll,
                    course=c
                )

        self.stdout.write(self.style.SUCCESS("Migration complete!"))
