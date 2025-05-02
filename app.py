import sys
sys.path.append("/opt/.manus/.sandbox-runtime")
from flask import Flask, render_template, request, send_from_directory, url_for
import os
import uuid
import logging # Adicionado para logs mais detalhados

# Importar as funções dos scripts criados
from calculo_precos import calcular_precos_planos
from preenche_cotacao import preencher_cotacao_pptx
from converte_pdf import converter_pptx_para_pdf

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Configurações
# Corrigido: Usar caminhos relativos que funcionarão dentro do container Docker
INPUT_DIR = "input_files"
OUTPUT_DIR = "output" # Diretório relativo para salvar os arquivos gerados
DATABASE_FILE = os.path.join(INPUT_DIR, "Tabela 2023.xlsx")
# Corrigido: Usar o nome de arquivo padronizado mencionado nos logs
TEMPLATE_PPTX = os.path.join(INPUT_DIR, "cotacao_auto.pptx")

app.config["OUTPUT_DIR"] = OUTPUT_DIR

# Criar diretório de saída se não existir
# Isso garante que o diretório exista dentro do container
if not os.path.exists(OUTPUT_DIR):
    try:
        os.makedirs(OUTPUT_DIR)
        logging.info(f"Diretório de saída criado: {OUTPUT_DIR}")
    except OSError as e:
        logging.error(f"Erro ao criar diretório de saída {OUTPUT_DIR}: {e}")
        # Considerar lançar uma exceção ou tratar o erro de forma adequada

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    success = None
    pdf_path_relative = None
    warning = None # Para avisos como "sujeito à aprovação"

    if request.method == "POST":
        # Capturar todos os dados do formulário
        nome_cliente = request.form.get("nome")
        placa = request.form.get("placa")
        marca = request.form.get("marca")
        modelo = request.form.get("modelo")
        ano = request.form.get("ano")
        valor_fipe_str = request.form.get("valor_fipe")
        categoria = request.form.get("categoria", "")  # Campo opcional

        # Validar dados obrigatórios
        if not all([nome_cliente, placa, marca, modelo, ano, valor_fipe_str]):
            error = "Por favor, preencha todos os campos obrigatórios."
            logging.warning("Tentativa de submissão com campos obrigatórios faltando.")
            return render_template("index.html", error=error)

        # Converter valores numéricos
        try:
            ano_int = int(ano)
            valor_fipe = float(valor_fipe_str.replace('.', '').replace(',', '.')) # Tratar formato brasileiro
        except ValueError:
            error = "Ano e Valor FIPE devem ser valores numéricos válidos (ex: 2023, 75000.50)."
            logging.warning(f"Erro ao converter Ano ({ano}) ou Valor FIPE ({valor_fipe_str}).")
            return render_template("index.html", error=error)

        # Calcular preços dos planos com base no valor FIPE
        logging.info(f"Calculando preços para valor FIPE: {valor_fipe}")
        try:
            precos_info = calcular_precos_planos(valor_fipe, DATABASE_FILE)
        except FileNotFoundError:
             error = f"Erro interno: Arquivo da tabela de preços ({DATABASE_FILE}) não encontrado."
             logging.error(error)
             return render_template("index.html", error=error)
        except Exception as e:
             error = f"Erro ao calcular preços: {e}"
             logging.error(error)
             return render_template("index.html", error=error)

        if precos_info:
            # Preparar dados para preencher o PowerPoint
            dados_cotacao = {
                "nome_cliente": nome_cliente,
                "placa": placa,
                "marca": marca,
                "modelo": modelo,
                "ano": ano_int, # Usar o valor convertido
                "valor_fipe": valor_fipe,
                "categoria": categoria,
                "precos": precos_info # Passa todo o dicionário retornado
            }

            # Verificar se há aviso de aprovação
            if precos_info.get("sujeito_aprovacao", False):
                warning = "Atenção: Esta cotação está sujeita à aprovação da diretoria devido ao valor do veículo."
                logging.info(f"Cotação para veículo com valor {valor_fipe} sujeita à aprovação.")

            # Gerar nomes de arquivo únicos para evitar conflitos
            unique_id = str(uuid.uuid4())[:8]
            safe_placa = placa.replace(' ', '_').replace('/', '_') # Sanitizar placa para nome de arquivo
            output_pptx_filename = f"cotacao_{safe_placa}_{unique_id}.pptx"
            output_pdf_filename = f"cotacao_{safe_placa}_{unique_id}.pdf"

            output_pptx_path = os.path.join(app.config["OUTPUT_DIR"], output_pptx_filename)
            output_pdf_path = os.path.join(app.config["OUTPUT_DIR"], output_pdf_filename)

            # ---- Início da Verificação e Preenchimento do PPTX ----
            logging.info(f"Verificando existência do template: {TEMPLATE_PPTX}")
            # Adicionado log para listar diretório (conforme sugerido nos seus logs)
            try:
                input_files_list = os.listdir(INPUT_DIR)
                logging.info(f"Conteúdo de {INPUT_DIR}: {input_files_list}")
            except Exception as e:
                logging.error(f"Erro ao listar diretório {INPUT_DIR}: {e}")

            if not os.path.exists(TEMPLATE_PPTX):
                error = f"Erro interno: Arquivo modelo de cotação ({TEMPLATE_PPTX}) não encontrado."
                logging.error(error)
                return render_template("index.html", error=error, warning=warning) # Manter warning se houver
            # ---- Fim da Verificação ----

            try:
                # Preencher o PowerPoint
                logging.info(f"Preenchendo PPTX: {output_pptx_path} usando template {TEMPLATE_PPTX}")
                sucesso_pptx = preencher_cotacao_pptx(TEMPLATE_PPTX, output_pptx_path, dados_cotacao)

                if sucesso_pptx:
                    # Converter para PDF
                    logging.info(f"Convertendo para PDF: {output_pdf_path}")
                    sucesso_pdf = converter_pptx_para_pdf(output_pptx_path, app.config["OUTPUT_DIR"]) # Passar diretório de saída

                    if sucesso_pdf:
                        success = f"Cotação para {nome_cliente} (placa {placa}) gerada com sucesso!"
                        pdf_path_relative = os.path.join("output", output_pdf_filename) # Usar nome de arquivo PDF correto
                        logging.info(f"PDF gerado com sucesso: {pdf_path_relative}")
                        # Limpar o arquivo pptx intermediário (opcional)
                        try:
                            os.remove(output_pptx_path)
                            logging.info(f"Arquivo PPTX intermediário removido: {output_pptx_path}")
                        except OSError as e:
                            logging.warning(f"Erro ao remover arquivo PPTX intermediário: {e}")
                    else:
                        error = f"Erro ao converter a cotação para PDF. Verifique os logs do servidor."
                        logging.error(f"Falha na conversão para PDF para {output_pptx_path}")
                else:
                    error = f"Erro ao preencher o modelo de cotação. Verifique os logs do servidor."
                    logging.error(f"Falha ao preencher PPTX {output_pptx_path}")

            except Exception as e:
                error = f"Ocorreu um erro inesperado durante a geração da cotação: {e}"
                logging.exception("Erro inesperado no processo de geração de cotação:") # Log completo do erro

        else:
            error = f"Não foi possível encontrar uma faixa de preço para o valor FIPE informado ({valor_fipe}). Verifique a tabela de preços."
            logging.warning(error)

    return render_template("index.html", error=error, success=success, warning=warning, pdf_path=pdf_path_relative)

@app.route("/output/<path:filename>") # Adicionado <path:> para suportar subdiretórios se necessário
def download_file(filename):
    logging.info(f"Tentando servir arquivo para download: {filename} de {app.config['OUTPUT_DIR']}")
    try:
        return send_from_directory(app.config["OUTPUT_DIR"], filename, as_attachment=True)
    except FileNotFoundError:
        logging.error(f"Arquivo para download não encontrado: {filename} em {app.config['OUTPUT_DIR']}")
        return "Arquivo não encontrado.", 404

if __name__ == "__main__":
    # Ouvir em todas as interfaces de rede na porta definida pelo Render (ou 8080 como padrão)
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Iniciando aplicação Flask na porta {port}")
    # Usar debug=False para produção, True para desenvolvimento
    # O Dockerfile já usa Gunicorn, então este app.run() é mais para teste local
    app.run(host="0.0.0.0", port=port, debug=False)

