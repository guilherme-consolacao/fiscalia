from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from feeds.forms.accounts import LoginForm, SignupForm
from feeds.models import Workspace, Membership


class PortalLoginView(LoginView):
    template_name = 'pages/accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


def signup(request):
    if request.user.is_authenticated:
        return redirect('feeds:index')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                workspace = Workspace.objects.create(name=form.cleaned_data['workspace_name'])
                Membership.objects.create(user=user, workspace=workspace, role=Membership.ADMIN)
        except IntegrityError:
            form.add_error('email', 'Não foi possível cadastrar. Revise os dados e tente novamente.')
        else:
            login(request, user)
            request.session['workspace_id'] = workspace.pk
            messages.success(request, 'Sua conta e seu espaço privado foram criados.')
            return redirect('feeds:index')
    return render(request, 'pages/accounts/signup.html', {'form': form})


@require_POST
def signout(request):
    logout(request)
    return redirect('feeds:login')


def no_workspace(request):
    if not request.user.is_authenticated:
        return redirect('feeds:login')
    if request.membership:
        return redirect('feeds:index')
    return render(request, 'pages/accounts/no_workspace.html', status=403)
