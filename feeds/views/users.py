from django.contrib import messages
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from feeds.forms.users import AddMemberForm, EditMemberForm
from feeds.models import Membership, Workspace
from feeds.permissions import admin_required


@admin_required
def index(request):
    form = AddMemberForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            _, created = Membership.objects.get_or_create(workspace=request.workspace, user=form.member_user, defaults={'role':form.cleaned_data['role']})
        except IntegrityError:
            created = False
        if created:
            messages.success(request, 'Pessoa adicionada à equipe. Ela entra com a própria conta e pode escolher esta equipe no cabeçalho.')
            return redirect('feeds:users')
        form.add_error('email', 'Esta pessoa já pertence à equipe. Edite o acesso na lista.')
    members = Membership.objects.filter(workspace=request.workspace).select_related('user').order_by('user__first_name', 'pk')
    return render(request, 'pages/users/index.html', {'members':members, 'form':form})


@admin_required
def edit(request, membership_id):
    member = get_object_or_404(Membership.objects.select_related('user'), workspace=request.workspace, pk=membership_id)
    form = EditMemberForm(request.POST or None, instance=member)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Serialize changes on a stable row even when two admins demote
            # different memberships concurrently.
            Workspace.objects.select_for_update().get(pk=request.workspace.pk)
            current = Membership.objects.get(pk=member.pk, workspace=request.workspace)
            admins = Membership.objects.filter(workspace=request.workspace, active=True, role=Membership.ADMIN, user__is_active=True)
            if current.role == Membership.ADMIN and current.active and (not form.cleaned_data['active'] or form.cleaned_data['role'] != Membership.ADMIN) and admins.count() <= 1:
                form.add_error(None, 'Mantenha pelo menos um administrador ativo na equipe.')
            else:
                form.save()
                messages.success(request, 'Acesso atualizado nesta equipe. A alteração vale imediatamente para as sessões abertas.')
                return redirect('feeds:users')
    return render(request, 'pages/users/edit.html', {'form':form, 'member':member})


@require_POST
def switch_workspace(request):
    try:
        workspace_id = int(request.POST.get('workspace_id', ''))
    except (ValueError, TypeError):
        return HttpResponseBadRequest('Selecione um espaço válido.')
    member = get_object_or_404(Membership, user=request.user, active=True, workspace_id=workspace_id)
    request.session['workspace_id'] = member.workspace_id
    return redirect('feeds:index')
