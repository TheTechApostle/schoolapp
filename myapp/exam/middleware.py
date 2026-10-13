# exam/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class ExamLockMiddleware:
    """
    Prevent users from navigating away during an exam.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exam_in_progress = request.session.get('exam_in_progress')

        # Only check for authenticated users
        if request.user.is_authenticated and exam_in_progress:
            current_path = request.path
            take_exam_url = reverse('take_exam', args=[exam_in_progress])

            # Allow take_exam and (optional) submit_exam routes only
            allowed_urls = [take_exam_url]
            try:
                allowed_urls.append(reverse('submit_exam'))
            except:
                pass  # in case submit_exam isn't defined yet

            # Redirect if user tries to access any other page
            if current_path not in allowed_urls:
                return redirect('take_exam', course_id=exam_in_progress)

        response = self.get_response(request)
        return response
