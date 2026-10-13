class HeaderLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("=" * 60)
        print("HTTP_ORIGIN:", request.META.get("HTTP_ORIGIN"))
        print("HTTP_REFERER:", request.META.get("HTTP_REFERER"))
        print("HTTP_HOST:", request.META.get("HTTP_HOST"))
        print("ALL HTTP HEADERS:")
        for k, v in request.META.items():
            if k.startswith("HTTP_"):
                print(f"{k}: {v}")
        print("=" * 60)
        return self.get_response(request)
        

class FixOriginHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        origin = request.META.get("HTTP_ORIGIN")

        if origin and "," in origin:
            request.META["HTTP_ORIGIN"] = origin.split(",")[0].strip()

        response = self.get_response(request)
        return response