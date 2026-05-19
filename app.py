# ----- INÍCIO DO CÓDIGO COMPLETO E CORRIGIDO PARA app.py -----
import sys
# Linha específica do ambiente Render/Manus, pode manter se necessário
# sys.path.append("/opt/.manus/.sandbox-runtime") 

from flask import Flask, render_template, request, send_from_directory, url_for, abort, jsonify
import os
import uuid
import logging
import traceback
import requests as http_requests

# Importar módulos locais
try:
    from calculo_precos import calcular_precos_planos
    from gera_pdf import gerar_pdf_cotacao
except ImportError as import_err:
    logging.exception(f"ERRO CRÍTICO: Falha ao importar módulos locais: {import_err}")

app = Flask(__name__)

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

# --- Helpers para busca FIPE ---

FIPE_BASE = "https://parallelum.com.br/fipe/api/v1/carros"

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


def _melhor_ano(ano_str, anos):
    """Retorna o item de ano que melhor corresponde ao ano fornecido."""
    for item in anos:
        if str(ano_str) in str(item.get("nome", "")):
            return item
    return None


@app.route("/api/buscar-fipe")
def api_buscar_fipe():
    """Busca o valor FIPE via API pública (parallelum) dado marca, modelo e ano."""
    marca = request.args.get("marca", "").strip()
    modelo = request.args.get("modelo", "").strip()
    ano = request.args.get("ano", "").strip()

    if not all([marca, modelo, ano]):
        return jsonify({"erro": "Marca, modelo e ano são obrigatórios"}), 400

    try:
        # 1. Busca marcas
        r = http_requests.get(f"{FIPE_BASE}/marcas", timeout=10)
        r.raise_for_status()
        marca_match = _melhor_match(marca, r.json(), "nome")
        if not marca_match:
            return jsonify({"erro": f"Marca '{marca}' não encontrada na tabela FIPE"}), 404

        # 2. Busca modelos da marca
        r = http_requests.get(f"{FIPE_BASE}/marcas/{marca_match['codigo']}/modelos", timeout=10)
        r.raise_for_status()
        modelos = r.json().get("modelos", [])
        modelo_match = _melhor_match(modelo, modelos, "nome")
        if not modelo_match:
            return jsonify({"erro": f"Modelo '{modelo}' não encontrado para a marca '{marca_match['nome']}'"}), 404

        # 3. Busca anos do modelo
        r = http_requests.get(
            f"{FIPE_BASE}/marcas/{marca_match['codigo']}/modelos/{modelo_match['codigo']}/anos",
            timeout=10
        )
        r.raise_for_status()
        anos = r.json()
        ano_match = _melhor_ano(ano, anos)
        if not ano_match:
            return jsonify({"erro": f"Ano '{ano}' não encontrado para o modelo '{modelo_match['nome']}'"}), 404

        # 4. Busca valor FIPE
        r = http_requests.get(
            f"{FIPE_BASE}/marcas/{marca_match['codigo']}/modelos/{modelo_match['codigo']}/anos/{ano_match['codigo']}",
            timeout=10
        )
        r.raise_for_status()
        dados = r.json()

        # Converte "R$ 74.442,00" para float 74442.0
        valor_str = dados.get("Valor", "")
        valor_num = None
        try:
            valor_num = float(valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip())
        except Exception:
            pass

        return jsonify({
            "marca": dados.get("Marca"),
            "modelo": dados.get("Modelo"),
            "ano": dados.get("AnoModelo"),
            "valor_fipe_formatado": valor_str,
            "valor_fipe": valor_num,
            "codigo_fipe": dados.get("CodigoFipe"),
        })

    except http_requests.Timeout:
        return jsonify({"erro": "Timeout ao consultar a tabela FIPE. Tente novamente."}), 504
    except Exception as e:
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

    if request.method == "POST":
        logging.info("Recebida requisição POST para /")
        # Capturar dados do formulário
        nome_cliente = request.form.get("nome")
        placa = request.form.get("placa")
        marca = request.form.get("marca")
        modelo = request.form.get("modelo")
        ano = request.form.get("ano")
        valor_fipe_str = request.form.get("valor_fipe")
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

        logging.info(f"Dados recebidos: Nome='{nome_cliente}', Placa='{placa}', FIPE='{valor_fipe_str}', Pesado={veiculo_pesado}")

        # Validar dados obrigatórios
        if not all([nome_cliente, placa, marca, modelo, ano, valor_fipe_str]):
            error = "Por favor, preencha todos os campos obrigatórios."
            logging.warning(f"Tentativa de submissão com campos obrigatórios faltando. Dados: {request.form}")
            # Retorna imediatamente se faltar dados
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Converter valores numéricos
        try:
            ano_int = int(ano)
            # Tratar formato brasileiro (remove '.' de milhar, troca ',' decimal por '.')
            valor_fipe_str_limpo = valor_fipe_str.replace('.', '').replace(',', '.')
            valor_fipe = float(valor_fipe_str_limpo) 
        except ValueError:
            error = "Ano e Valor FIPE devem ser valores numéricos válidos (ex: 2023, 75000.50 ou 75.000,50)."
            logging.warning(f"Erro ao converter Ano ('{ano}') ou Valor FIPE ('{valor_fipe_str}').")
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
        PIN_VALIDO = "2019"
        if desconto_pin == PIN_VALIDO and desconto_tipo in ("desconto", "acrescimo") and desconto_valor > 0:
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
            "precos": precos_info
        }

        # Verificar aviso de aprovação
        if precos_info.get("sujeito_aprovacao", False):
            warning = "Atenção: Esta cotação está sujeita à aprovação da diretoria devido ao valor do veículo."
            logging.info(f"Cotação para FIPE {valor_fipe} sujeita à aprovação.")

        # Gerar nomes de arquivo únicos
        unique_id = str(uuid.uuid4())[:8]
        safe_placa = placa.replace(' ', '_').replace('/', '_').replace('-', '') # Mais sanitização
        output_pdf_filename = f"cotacao_{safe_placa}_{unique_id}.pdf"
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
    # Define a porta baseado na variável de ambiente ou usa 8080 como padrão
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Iniciando servidor de desenvolvimento Flask em host 0.0.0.0 na porta {port}")
    # Executa o servidor de desenvolvimento do Flask
    # debug=True é útil para desenvolvimento local, mas NUNCA em produção
    # host='0.0.0.0' permite acesso na rede local
    # No Render, o Gunicorn definido no Start Command é que será usado.
    app.run(host="0.0.0.0", port=port, debug=True) # Deixei debug=True para facilitar teste local, mas lembre-se de desativar ou usar Gunicorn para produção real

# ----- FIM DO CÓDIGO PARA app.py -----
