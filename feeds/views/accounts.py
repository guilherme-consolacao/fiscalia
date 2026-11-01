from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from feeds.forms.accounts import LoginForm, SignupForm
from feeds.models import Workspace, Membership
from feeds.services.auth_rate_limit import allow_auth_attempt


class PortalLoginView(LoginView):
    template_name = 'pages/accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if not allow_auth_attempt(request, 'login', 10, 900):
            form = self.authentication_form(request=request)
            response = self.render_to_response(self.get_context_data(form=form, rate_limit_message='Muitas tentativas de entrada. Aguarde 15 minutos e tente novamente.'), status=429)
            response['Retry-After'] = '900'
            return response
        return super().post(request, *args, **kwargs)


def signup(request):
    if request.user.is_authenticated:
        return redirect('feeds:index')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and not allow_auth_attempt(request, 'signup', 10, 3600):
        return render(request, 'pages/accounts/signup.html', {'form': SignupForm(), 'rate_limit_message':'Muitas tentativas de cadastro. Tente novamente em uma hora.'}, status=429)
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
            messages.success(request, 'Sua conta e sua equipe privada inicial foram criadas.')
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
