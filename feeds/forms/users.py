from django import forms
from django.contrib.auth import get_user_model
from feeds.models import Membership


class AddMemberForm(forms.Form):
    email = forms.EmailField(label='E-mail da conta existente', max_length=150, help_text='Use o mesmo e-mail que a pessoa cadastrou no Fiscalia.')
    role = forms.ChoiceField(label='Papel nesta equipe', choices=Membership.ROLE_CHOICES, initial=Membership.READER, help_text='A permissão escolhida vale somente para a equipe atual.')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().casefold()
        user = get_user_model().objects.filter(username=email, is_active=True).first()
        if not user:
            raise forms.ValidationError('Não foi possível adicionar esta conta. Verifique o e-mail e se ela está cadastrada e ativa.')
        self.member_user = user
        return email


class EditMemberForm(forms.ModelForm):
    confirm = forms.BooleanField(label='Confirmo a alteração do acesso desta pessoa', required=True)

    class Meta:
        model = Membership
        fields = ['role', 'active']
        labels = {'role': 'Papel nesta equipe', 'active': 'Acesso ativo nesta equipe'}
        help_texts = {'active': 'Desativar este acesso não desativa a conta nem o acesso às outras equipes.'}
