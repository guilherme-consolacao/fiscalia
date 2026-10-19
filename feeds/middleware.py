from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from feeds.models import Membership
from feeds.tenancy import workspace_scope
from django.core.exceptions import PermissionDenied


class WorkspaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        membership = None
        request.workspace = None
        request.membership = None
        if request.user.is_authenticated:
            memberships = Membership.objects.filter(user=request.user, active=True).select_related('workspace')
            membership = memberships.filter(workspace_id=request.session.get('workspace_id')).first()
            if membership is None:
                membership = memberships.order_by('pk').first()
            if membership:
                request.workspace = membership.workspace
                request.membership = membership
                request.session['workspace_id'] = membership.workspace_id
        with workspace_scope(membership.workspace_id if membership else -1, request.user.pk if request.user.is_authenticated else None):
            response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'private, no-store'
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        namespace = request.resolver_match.namespace
        name = request.resolver_match.url_name
        if namespace == 'admin':
            if request.user.is_authenticated and not request.user.is_superuser:
                raise PermissionDenied('Administração da plataforma restrita.')
            if name == 'login' and request.method == 'POST':
                from feeds.services.auth_rate_limit import allow_auth_attempt
                if not allow_auth_attempt(request, 'admin-login', 10, 900):
                    return JsonResponse({'message':'Muitas tentativas. Aguarde 15 minutos.'}, status=429)
        if namespace != 'feeds' or name in {'login', 'signup', 'logout', 'no_workspace'}:
            return None
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.endswith('/status/'):
                return JsonResponse({'message': 'Sua sessão expirou. Entre novamente.'}, status=401)
            return redirect_to_login(request.get_full_path(), reverse('feeds:login'))
        if request.membership is None:
            return redirect('feeds:no_workspace')


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        # The official VLibras host redirects its versioned assets to this CDN.
        libras_assets = 'https://cdn.jsdelivr.net/gh/spbgovbr-vlibras/vlibras-portal@v7.12.2/'
        response['Content-Security-Policy'] = "; ".join([
            "default-src 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "script-src 'self' https://vlibras.gov.br https://*.vlibras.gov.br 'wasm-unsafe-eval' " + libras_assets,
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com " + libras_assets,
            "font-src 'self' https://fonts.gstatic.com https://vlibras.gov.br data: " + libras_assets,
            "img-src 'self' data: blob: https://vlibras.gov.br https://*.vlibras.gov.br " + libras_assets,
            "connect-src 'self' https://vlibras.gov.br https://*.vlibras.gov.br https://*.lavid.ufpb.br " + libras_assets,
            "worker-src 'self' blob:",
            "frame-src 'self' https://vlibras.gov.br https://*.vlibras.gov.br " + libras_assets,
        ])
        return response
