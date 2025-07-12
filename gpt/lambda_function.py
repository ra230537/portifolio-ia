import json
import os
import urllib.request
import traceback

SYSTEM_CONTEXT = "Você é um assistente chamado GPT. Seja claro e objetivo."
openai_api_key = os.environ.get('OPENAI_API_KEY')


def lambda_handler(event, context):
    print("Event received:", json.dumps(event))  # Log para debug

    req = event.get('request', {})
    req_type = req.get('type')

    if req_type == 'LaunchRequest':
        return _build_response(
            text="Olá! Pergunte algo ao ChatGPT!",
            should_end_session=False
        )

    elif req_type == 'IntentRequest':
        intent = req.get('intent', {})
        intent_name = intent.get('name')

        if intent_name == 'AMAZON.FallbackIntent':
            try:
                # Extrai a pergunta do usuário de forma robusta
                user_input = _extract_user_query(event)

                if not user_input:
                    return _build_response(
                        text="Não consegui identificar sua pergunta. Poderia reformular?",
                        should_end_session=False
                    )

                print("User query:", user_input)  # Log para debug

                # Prepara mensagem para a OpenAI
                messages = [
                    {"role": "system", "content": SYSTEM_CONTEXT},
                    {"role": "user", "content": user_input}
                ]

                # Chama API OpenAI
                resposta = _call_openai(messages)
                return _build_response(text=resposta, should_end_session=True)

            except Exception as e:
                print("Error:", str(e))
                traceback.print_exc()
                return _build_response(
                    text="Desculpe, ocorreu um erro. Tente novamente.",
                    should_end_session=True
                )

        # Outros intents...
        return _build_response(text="Comando não reconhecido", should_end_session=True)

    return _build_response(text="Sessão encerrada", should_end_session=True)


def _extract_user_query(event):
    """Extrai a pergunta do usuário de múltiplas fontes possíveis"""
    try:
        # 1. Tenta pegar do input direto do FallbackIntent
        intent = event.get('request', {}).get('intent', {})
        if 'input' in intent:
            return intent['input'].strip()

        # 2. Tenta pegar do contexto da sessão (para dispositivos mais antigos)
        session = event.get('session', {})
        if 'lastQuery' in session.get('attributes', {}):
            return session['attributes']['lastQuery']

        # 3. Fallback para o raw request (último recurso)
        raw_request = event.get('request', {}).get('rawQuery', '')
        if raw_request:
            return raw_request.strip()

    except Exception:
        pass

    return ""


def _call_openai(messages):
    """Faz a chamada à API OpenAI"""
    url = 'https://api.openai.com/v1/chat/completions'
    payload = {
        "model": "gpt-4-turbo",
        "messages": messages,
        "max_tokens": 500
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp_data = json.loads(resp.read())

    return resp_data['choices'][0]['message']['content']


def _build_response(text: str, should_end_session: bool):
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": text},
            "card": {
                "type": "Simple",
                "title": "GPT Responde",
                "content": text[:8000]
            },
            "shouldEndSession": should_end_session
        }
    }