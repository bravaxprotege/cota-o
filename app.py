from flask import Flask, render_template, request, send_from_directory, url_for, abort, jsonify
import os
import uuid
import glob
import time
import threading
import logging
import requests as http_requests

# Importar módulos locais
try:
    from calculo_precos import calcular_precos_planos
    from gera_pdf import gerar_pdf_cotacao
except ImportError as import_err:
    logging.exception(f"ERRO CRÍTICO: Falha ao importar módulos locais: {import_err}")

app = Flask(__name__)
app.config["COTACAO_AJUSTE_PIN"] = os.environ.get("COTACAO_AJUSTE_PIN", "").strip()

# Configurar logging para um nível útil (INFO ou DEBUG para mais detalhes)
# A formatação ajuda a identificar a origem das mensagens
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# Obter o logger específico do Flask para mensagens do Flask/Werkzeug
# werkzeug_logger = logging.getLogger('werkzeug')
# werkzeug_logger.setLevel(logging.INFO) 

# --- Configurações ---
# Caminhos relativos ao diretório onde app.py está (/app no container Docker)
INPUT_DIR = "input_files" 
OUTPUT_DIR = "output" # Diretório relativo para salvar os arquivos gerados
DATABASE_FILE = os.path.join(INPUT_DIR, "Tabela 2023.xlsx")
# Usar o nome de arquivo padronizado (sem acentos, definido anteriormente)
TEMPLATE_PPTX = os.path.join(INPUT_DIR, "cotacao_auto.pptx") 

# Guarda o diretório de saída na configuração do Flask para fácil acesso
app.config["OUTPUT_DIR"] = OUTPUT_DIR
# Guarda o diretório de input também (pode ser útil)
app.config["INPUT_DIR"] = INPUT_DIR 

# --- Criação de Diretórios na Inicialização ---
# Garante que o diretório de saída exista DENTRO do container
# É executado apenas uma vez quando a aplicação inicia
if not os.path.exists(OUTPUT_DIR):
    try:
        os.makedirs(OUTPUT_DIR)
        logging.info(f"Diretório de saída criado com sucesso: {OUTPUT_DIR}")
    except OSError as e:
        logging.error(f"ERRO CRÍTICO ao criar diretório de saída '{OUTPUT_DIR}': {e}")
        # Se não conseguir criar o diretório de saída, a aplicação não funcionará
        raise OSError(f"Não foi possível criar o diretório de saída necessário: {e}") from e

# --- Limpeza de PDFs antigos ---

def limpar_pdfs_antigos(diretorio, max_arquivos=50, max_idade_horas=24):
    """Remove PDFs mais antigos quando o número excede max_arquivos ou têm mais de max_idade_horas."""
    arquivos = sorted(glob.glob(os.path.join(diretorio, "cotacao_*.pdf")), key=os.path.getmtime)
    agora = time.time()
    removidos = 0
    for arq in arquivos:
        idade_horas = (agora - os.path.getmtime(arq)) / 3600
        if len(arquivos) - removidos > max_arquivos or idade_horas > max_idade_horas:
            try:
                os.remove(arq)
                removidos += 1
                logging.info(f"PDF antigo removido: {os.path.basename(arq)}")
            except OSError:
                pass
    if removidos:
        logging.info(f"Limpeza: {removidos} PDF(s) removido(s) de {diretorio}")


# --- Helpers para busca FIPE ---

FIPE_BASE = "https://fipe.parallelum.com.br/api/v2"
FIPE_VEHICLE_TYPES = {"carros": "cars", "motos": "motorcycles", "caminhoes": "trucks"}
FIPE_CACHE_TTL = 6 * 60 * 60
_fipe_cache = {}
_fipe_cache_lock = threading.Lock()
_fipe_thread_local = threading.local()


class FipeApiError(Exception):
    """Erro controlado ao consultar a API FIPE."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def _fipe_session():
    session = getattr(_fipe_thread_local, "session", None)
    if session is None:
        session = http_requests.Session()
        session.headers.update({"Accept": "application/json", "User-Agent": "BravaxCotacao/2.0"})
        token = os.environ.get("FIPE_API_TOKEN", "").strip()
        if token:
            session.headers["X-Subscription-Token"] = token
        _fipe_thread_local.session = session
    return session


def _fipe_get(path, params=None):
    """Faz GET reutilizando conexão e resposta em cache curto por caminho/referência."""
    params = dict(params or {})
    cache_key = (path, tuple(sorted(params.items())))
    now = time.monotonic()
    with _fipe_cache_lock:
        cached = _fipe_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]
        if cached:
            _fipe_cache.pop(cache_key, None)

    try:
        response = _fipe_session().get(f"{FIPE_BASE}{path}", params=params, timeout=(3, 8))
    except http_requests.Timeout as exc:
        raise FipeApiError("A consulta FIPE demorou demais. Tente novamente.", 504) from exc
    except http_requests.RequestException as exc:
        raise FipeApiError("Não foi possível conectar à tabela FIPE. Tente novamente.", 502) from exc

    if response.status_code == 429:
        raise FipeApiError("A consulta FIPE atingiu o limite temporário. Tente novamente mais tarde.", 429)
    if response.status_code >= 500:
        raise FipeApiError("A tabela FIPE está temporariamente indisponível.", 502)
    if response.status_code >= 400:
        raise FipeApiError("Não encontramos essa combinação na tabela FIPE.", 404)
    try:
        data = response.json()
    except ValueError as exc:
        raise FipeApiError("A tabela FIPE retornou uma resposta inválida.", 502) from exc

    with _fipe_cache_lock:
        _fipe_cache[cache_key] = (now + FIPE_CACHE_TTL, data)
    return data


def _fipe_reference():
    references = _fipe_get("/references")
    if not references:
        raise FipeApiError("Não foi possível identificar a referência FIPE atual.", 502)
    return references[0]


def _fipe_price(vehicle_type, brand_id, model_id, year_id, reference):
    detail = _fipe_get(
        f"/{vehicle_type}/brands/{brand_id}/models/{model_id}/years/{year_id}",
        {"reference": reference["code"]},
    )
    price = detail.get("price", "")
    try:
        price_number = float(price.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except (AttributeError, ValueError):
        raise FipeApiError("A API FIPE retornou um valor que não conseguimos interpretar.", 502)
    return {
        "marca": detail.get("brand"),
        "modelo": detail.get("model"),
        "ano": detail.get("modelYear"),
        "combustivel": detail.get("fuel"),
        "valor_fipe_formatado": price,
        "valor_fipe": price_number,
        "codigo_fipe": detail.get("codeFipe"),
        "referencia": detail.get("referenceMonth") or reference.get("month"),
        "referencia_codigo": reference["code"],
        "marca_codigo": str(brand_id),
        "modelo_codigo": str(model_id),
        "ano_codigo": str(year_id),
    }


def _parse_currency(value):
    """Aceita valor numérico HTML (75000.50) ou formato brasileiro (75.000,50)."""
    normalized = str(value or "").replace("R$", "").replace(" ", "").strip()
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    return float(normalized)


def _melhor_match(query, items, campo):
    """Retorna o item da lista cujo campo melhor corresponde ao query."""
    q = query.upper().strip()
    # 1. Match exato
    for item in items:
        if str(item.get(campo, "")).upper() == q:
            return item
    # 2. Query contida no campo
    for item in items:
        if q in str(item.get(campo, "")).upper():
            return item
    # 3. Todas as palavras do query no campo
    palavras = q.split()
    for item in items:
        campo_upper = str(item.get(campo, "")).upper()
        if all(p in campo_upper for p in palavras):
            return item
    return None


def _coincidencias(query, items, campo):
    """Retorna todos os resultados do melhor nível de correspondência."""
    q = query.upper().strip()
    exactos = [item for item in items if str(item.get(campo, "")).upper() == q]
    if exactos:
        return exactos
    contidos = [item for item in items if q in str(item.get(campo, "")).upper()]
    if contidos:
        return contidos
    palavras = q.split()
    return [item for item in items if all(p in str(item.get(campo, "")).upper() for p in palavras)]


@app.route("/api/buscar-fipe")
def api_buscar_fipe():
    """Busca preço FIPE atual pela API v2 com cache e referência explícita."""
    marca = request.args.get("marca", "").strip()
    modelo = request.args.get("modelo", "").strip()
    ano = request.args.get("ano", "").strip()

    if not all([marca, modelo, ano]):
        return jsonify({"erro": "Marca, modelo e ano são obrigatórios"}), 400

    tipo = request.args.get("tipo", "carros")
    vehicle_type = FIPE_VEHICLE_TYPES.get(tipo)
    if not vehicle_type:
        return jsonify({"erro": "Tipo de veículo inválido"}), 400

    try:
        reference = _fipe_reference()
        params = {"reference": reference["code"]}
        # A hierarquia é armazenada por referência; apenas preço/combustível pode variar por versão.
        brands = _fipe_get(f"/{vehicle_type}/brands", params)
        marca_match = _melhor_match(marca, brands, "name")
        if not marca_match:
            return jsonify({"erro": f"Marca '{marca}' não encontrada na tabela FIPE"}), 404

        models = _fipe_get(f"/{vehicle_type}/brands/{marca_match['code']}/models", params)
        modelo_codigo = request.args.get("modelo_codigo", "").strip()
        modelo_match = next((item for item in models if item.get("code") == modelo_codigo), None) if modelo_codigo else None
        if modelo_codigo and not modelo_match:
            return jsonify({"erro": "O modelo selecionado não está disponível. Consulte novamente."}), 404
        if not modelo_codigo:
            modelos = _coincidencias(modelo, models, "name")
            if len(modelos) > 1:
                return jsonify({
                    "erro": "Há mais de uma versão de modelo correspondente. Escolha o modelo correto.",
                    "modelos": [{"codigo": item["code"], "nome": item["name"]} for item in modelos],
                }), 409
            modelo_match = modelos[0] if modelos else None
        if not modelo_match:
            return jsonify({"erro": f"Modelo '{modelo}' não encontrado para a marca '{marca_match['name']}'"}), 404

        years = _fipe_get(
            f"/{vehicle_type}/brands/{marca_match['code']}/models/{modelo_match['code']}/years",
            params,
        )
        codigo_ano = request.args.get("ano_codigo", "").strip()
        ano_match = next((item for item in years if item.get("code") == codigo_ano), None) if codigo_ano else None
        if codigo_ano and not ano_match:
            return jsonify({"erro": "A versão selecionada não está disponível na referência FIPE atual. Consulte novamente."}), 404
        if not codigo_ano:
            anos = [item for item in years if str(ano) in str(item.get("name", ""))]
            if len(anos) > 1:
                return jsonify({
                    "erro": "Há mais de uma versão/combustível para esse ano. Escolha a versão FIPE.",
                    "versoes": [{"codigo": item["code"], "nome": item["name"]} for item in anos],
                }), 409
            ano_match = anos[0] if anos else None
        if not ano_match:
            return jsonify({"erro": f"Ano '{ano}' não encontrado para o modelo '{modelo_match['name']}'"}), 404

        return jsonify(_fipe_price(vehicle_type, marca_match["code"], modelo_match["code"], ano_match["code"], reference))

    except FipeApiError as e:
        return jsonify({"erro": str(e)}), e.status_code
    except Exception:
        logging.exception("Erro em api_buscar_fipe:")
        return jsonify({"erro": "Erro interno ao consultar FIPE"}), 500


# --- Rotas da Aplicação ---

@app.route("/", methods=["GET", "POST"])
def index():
    """ Rota principal que exibe o formulário e processa a geração da cotação. """
    error = None
    success = None
    pdf_filename = None # Apenas o NOME do arquivo PDF para gerar o link
    warning = None 
    fipe_dados = None

    if request.method == "POST":
        logging.info("Recebida requisição POST para /")
        # Capturar dados do formulário
        nome_cliente = request.form.get("nome")
        placa = request.form.get("placa")
        marca = request.form.get("marca")
        modelo = request.form.get("modelo")
        ano = request.form.get("ano")
        valor_fipe_str = request.form.get("valor_fipe")
        fipe_tipo = request.form.get("fipe_tipo", "carros")
        fipe_marca_codigo = request.form.get("fipe_marca_codigo", "").strip()
        fipe_modelo_codigo = request.form.get("fipe_modelo_codigo", "").strip()
        fipe_ano_codigo = request.form.get("fipe_ano_codigo", "").strip()
        fipe_referencia_codigo = request.form.get("fipe_referencia_codigo", "").strip()
        categoria = request.form.get("categoria", "")
        veiculo_pesado = request.form.get("veiculo_pesado") == "on"

        # Desconto / Acréscimo (protegido por PIN)
        desconto_pin   = request.form.get("desconto_pin", "")
        desconto_tipo  = request.form.get("desconto_tipo", "")   # "desconto" ou "acrescimo"
        desconto_valor = 0.0
        try:
            desconto_valor = float(request.form.get("desconto_valor", "0") or 0)
        except ValueError:
            desconto_valor = 0.0

        logging.info("Recebida cotação; dados pessoais e placa omitidos do log.")

        # Validar dados obrigatórios
        if not all([nome_cliente, placa, marca, modelo, ano, valor_fipe_str]):
            error = "Por favor, preencha todos os campos obrigatórios."
            logging.warning("Tentativa de cotação com campos obrigatórios faltando.")
            # Retorna imediatamente se faltar dados
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Quando a busca FIPE foi confirmada na tela, refazemos a consulta no servidor.
        # Assim o valor submetido pelo navegador não substitui o preço retornado pela API.
        if all([fipe_marca_codigo, fipe_modelo_codigo, fipe_ano_codigo, fipe_referencia_codigo]):
            vehicle_type = FIPE_VEHICLE_TYPES.get(fipe_tipo)
            if not vehicle_type:
                error = "Tipo de veículo FIPE inválido. Faça a consulta novamente."
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)
            try:
                reference = _fipe_reference()
                if str(reference.get("code")) != fipe_referencia_codigo:
                    raise FipeApiError("A referência FIPE mudou. Faça a consulta novamente.", 409)
                fipe_dados = _fipe_price(vehicle_type, fipe_marca_codigo, fipe_modelo_codigo, fipe_ano_codigo, reference)
                marca = fipe_dados["marca"] or marca
                modelo = fipe_dados["modelo"] or modelo
                ano = fipe_dados["ano"] or ano
                valor_fipe_str = str(fipe_dados["valor_fipe"])
            except FipeApiError as e:
                error = str(e)
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Converter valores numéricos
        try:
            ano_int = int(ano)
            valor_fipe = fipe_dados["valor_fipe"] if fipe_dados else _parse_currency(valor_fipe_str)
        except ValueError:
            error = "Ano e Valor FIPE devem ser valores numéricos válidos (ex: 2023, 75000.50 ou 75.000,50)."
            logging.warning(f"Erro ao converter Ano ('{ano}') ou Valor FIPE ('{valor_fipe_str}').")
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        if valor_fipe <= 0:
            error = "Informe um valor FIPE maior que zero."
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        if categoria not in {"PASSEIO", "SUV", "PICKUP", "UTILITÁRIO", "VAN", "MOTO"}:
            error = "Selecione uma categoria válida para o veículo."
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Calcular preços dos planos
        logging.info(f"Chamando calcular_precos_planos para FIPE: {valor_fipe} usando DB: {DATABASE_FILE}")
        precos_info = None # Inicializa como None
        try:
            # Verifica se o arquivo DB existe antes de chamar
            if not os.path.exists(DATABASE_FILE):
                 error = f"Erro interno: Arquivo da tabela de preços ({DATABASE_FILE}) não encontrado no servidor."
                 logging.error(error)
            else:
                 precos_info = calcular_precos_planos(valor_fipe, DATABASE_FILE)

        except Exception as e:
             error = f"Erro inesperado ao calcular preços: {e}"
             logging.exception(f"Exceção em calcular_precos_planos:") # Loga o traceback completo
             # Garante que precos_info é None se houve exceção
             precos_info = None 

        # Verifica se o cálculo retornou preços ou se houve erro antes
        if error:
             # Se já houve erro (ex: DB não encontrado, exceção no cálculo), retorna agora
             return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)
        elif not precos_info:
             # Se não houve exceção mas precos_info é None/vazio (lógica não achou faixa)
             error = f"Não foi possível encontrar uma faixa de preço para o valor FIPE informado ({valor_fipe}). Verifique a tabela de preços."
             logging.warning(error)
             return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Se chegou aqui, precos_info contém os dados calculados
        logging.info(f"Preços calculados com sucesso: {precos_info}")

        # Aplicar desconto ou acréscimo (somente com PIN correto e valor válido)
        ajuste_solicitado = bool(desconto_tipo or desconto_valor > 0)
        if ajuste_solicitado:
            pin_configurado = app.config["COTACAO_AJUSTE_PIN"]
            if not pin_configurado:
                error = "O ajuste de valores está temporariamente desativado."
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)
            if desconto_pin != pin_configurado:
                error = "PIN inválido. O ajuste não foi aplicado."
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)
            if desconto_tipo not in ("desconto", "acrescimo") or not 0 < desconto_valor <= 99:
                error = "Informe um tipo de ajuste e percentual entre 0,1% e 99%."
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)
            mult = (1 - desconto_valor / 100) if desconto_tipo == "desconto" else (1 + desconto_valor / 100)
            for plano in ["Plano Ouro", "Diamante", "Platinum", "Pesados"]:
                if plano in precos_info and isinstance(precos_info[plano], (int, float)):
                    precos_info[plano] = round(precos_info[plano] * mult, 2)
            sinal = "−" if desconto_tipo == "desconto" else "+"
            logging.info(f"Ajuste aplicado: {sinal}{desconto_valor}% nos preços.")

        # Preparar dados para preencher o PowerPoint
        dados_cotacao = {
            "nome_cliente": nome_cliente,
            "placa": placa,
            "marca": marca,
            "modelo": modelo,
            "ano": ano_int,
            "valor_fipe": valor_fipe,
            "categoria": categoria,
            "veiculo_pesado": veiculo_pesado,
            "codigo_fipe": fipe_dados["codigo_fipe"] if fipe_dados else "",
            "referencia_fipe": fipe_dados["referencia"] if fipe_dados else "",
            "precos": precos_info
        }

        # Verificar aviso de aprovação
        if precos_info.get("sujeito_aprovacao", False):
            warning = "Atenção: Esta cotação está sujeita à aprovação da diretoria devido ao valor do veículo."
            logging.info(f"Cotação para FIPE {valor_fipe} sujeita à aprovação.")

        # Limpar PDFs antigos antes de gerar novo
        limpar_pdfs_antigos(app.config["OUTPUT_DIR"])

        # Gerar nomes de arquivo únicos
        unique_id = str(uuid.uuid4())
        output_pdf_filename = f"cotacao_{unique_id}.pdf"
        output_pdf_path    = os.path.join(app.config["OUTPUT_DIR"], output_pdf_filename)

        # ── Geração do PDF via HTML + WeasyPrint ──────────────────────────
        try:
            logging.info(f"Gerando PDF HTML para {output_pdf_path}")
            sucesso = gerar_pdf_cotacao(dados_cotacao, output_pdf_path)

            if sucesso and os.path.exists(output_pdf_path):
                success      = f"Cotação para {nome_cliente} (placa {placa}) gerada com sucesso!"
                pdf_filename = output_pdf_filename
                logging.info(f"PDF gerado: {output_pdf_path}")
            else:
                error = "Erro ao gerar o PDF da cotação. Verifique os logs do servidor."
                logging.error("gerar_pdf_cotacao retornou False ou arquivo não foi criado.")

        except Exception as e:
            error = "Ocorreu um erro inesperado durante a geração da cotação."
            logging.exception("Exceção em gerar_pdf_cotacao:")

    # Fim do 'if request.method == "POST":'
    # O return abaixo será executado para GET ou após o POST (com ou sem erro/success)

    # Preserva os dados do formulário para repopular após POST
    form_data = None
    if request.method == "POST":
        form_data = {
            "nome":           request.form.get("nome", ""),
            "placa":          request.form.get("placa", "").upper(),
            "marca":          request.form.get("marca", ""),
            "modelo":         request.form.get("modelo", ""),
            "ano":            request.form.get("ano", ""),
            "valor_fipe":     request.form.get("valor_fipe", ""),
            "categoria":      request.form.get("categoria", ""),
            "veiculo_pesado": request.form.get("veiculo_pesado") == "on",
        }

# Renderiza o template no final, seja GET ou POST, com as variáveis de estado
    return render_template("index.html",
                           error=error,
                           success=success,
                           warning=warning,
                           pdf_filename=pdf_filename,
                           form_data=form_data)


@app.route("/output/<path:filename>") 
def download_file(filename):
    """ Rota para servir os arquivos PDF gerados. """
    directory = app.config["OUTPUT_DIR"]
    logging.info(f"Requisição de download para: {filename} de {directory}")
    try:
        # Verifica se o arquivo existe antes de tentar servir
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
             logging.error(f"Tentativa de download de arquivo inexistente: {file_path}")
             abort(404, description="Arquivo não encontrado") # Retorna erro 404

        logging.info(f"Servindo arquivo: {file_path}")
        return send_from_directory(directory, filename, as_attachment=True)

    except FileNotFoundError:
        # Segurança extra, embora o check acima deva pegar
        logging.error(f"Exceção FileNotFoundError ao servir: {filename} de {directory}")
        abort(404, description="Recurso não encontrado")
    except Exception as e:
        logging.exception(f"Erro inesperado ao servir arquivo '{filename}':")
        abort(500, description="Erro interno ao servir arquivo")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
