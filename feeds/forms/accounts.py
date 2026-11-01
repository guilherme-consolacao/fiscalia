from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='E-mail ou usuário', max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}))

    def clean_username(self):
        value = self.cleaned_data['username'].strip()
        return value.casefold() if '@' in value else value

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.memberships.filter(active=True).exists():
            raise forms.ValidationError('Esta conta está sem acesso ativo. Fale com o administrador do seu espaço.', code='inactive')


class SignupForm(UserCreationForm):
    first_name = forms.CharField(label='Seu nome', max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'given-name'}))
    email = forms.EmailField(label='Seu e-mail', max_length=150, help_text='Você usará este e-mail para entrar em todas as suas equipes.', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    workspace_name = forms.CharField(label='Nome da equipe inicial', max_length=120, help_text='Esta equipe começa privada, com você como administrador.')

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'email', 'workspace_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().casefold()
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username=email).exists():
            raise forms.ValidationError('Não foi possível usar este e-mail. Entre na sua conta ou utilize outro endereço.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user
