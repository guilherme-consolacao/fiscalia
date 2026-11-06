from django.contrib import admin
from django.urls import path, include

from feeds.forms.accounts import AdminLoginForm

admin.site.login_form = AdminLoginForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('feeds.urls')),
]
