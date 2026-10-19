import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST


@require_POST
def exemplo_post(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict):
                return JsonResponse({'status':'erro', 'mensagem':'Envie um objeto JSON.'}, status=400)
            mensagem = data.get('mensagem', 'Nenhuma mensagem recebida')
            return JsonResponse({
                'status': 'sucesso',
                'dados_recebidos': mensagem,
            })
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'status': 'erro', 'mensagem': 'JSON inválido'}, status=400)

    return JsonResponse({'status': 'erro', 'mensagem': 'Apenas requisições POST são permitidas'}, status=405)
