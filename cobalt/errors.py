from django.shortcuts import render


def not_found_404(request, exception=None):
    return render(request, "errors/404.html", {}, status=404)


def server_error_500(request):
    response = render(request, "errors/500.html")
    response.status_code = 500
    return response


def permission_denied_403(request, exception):
    return render(request, "errors/500.html")


def bad_request_400(request, exception):
    return render(request, "errors/500.html")
