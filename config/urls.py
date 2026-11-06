from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.views.decorators.http import require_safe

from feeds.forms.accounts import AdminLoginForm

admin.site.login_form = AdminLoginForm


@require_safe
def health(request):
    return HttpResponse(status=204)


urlpatterns = [
    path('saude/', health, name='health'),
    path('admin/', admin.site.urls),
    path('', include('feeds.urls')),
]
