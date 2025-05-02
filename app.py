# ----- INÍCIO DO CÓDIGO COMPLETO E CORRIGIDO PARA app.py -----
import sys
# Linha específica do ambiente Render/Manus, pode manter se necessário
# sys.path.append("/opt/.manus/.sandbox-runtime") 

from flask import Flask, render_template, request, send_from_directory, url_for, abort
import os
import uuid
import logging # Adicionado para logs mais detalhados
import traceback # Para log de erros detalhado

# Importar as funções dos scripts criados (Garante que os .py estejam no mesmo nível)
try:
    from calculo_precos import calcular_precos_planos
    from preenche_cotacao import preencher_cotacao_pptx
    from converte_pdf import converter_pptx_para_pdf
except ImportError as import_err:
     # Logar erro crítico se módulos essenciais não forem encontrados
     logging.exception(f"ERRO CRÍTICO: Falha ao importar módulos locais necessários: {import_err}")
     # Poderia até levantar o erro para impedir a aplicação de iniciar incorretamente
     # raise import_err 

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

        logging.info(f"Dados recebidos do formulário: Nome='{nome_cliente}', Placa='{placa}', FIPE_str='{valor_fipe_str}'")

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

        # Preparar dados para preencher o PowerPoint
        dados_cotacao = {
            "nome_cliente": nome_cliente,
            "placa": placa,
            "marca": marca,
            "modelo": modelo,
            "ano": ano_int, 
            "valor_fipe": valor_fipe,
            "categoria": categoria,
            "precos": precos_info 
        }

        # Verificar aviso de aprovação
        if precos_info.get("sujeito_aprovacao", False):
            warning = "Atenção: Esta cotação está sujeita à aprovação da diretoria devido ao valor do veículo."
            logging.info(f"Cotação para FIPE {valor_fipe} sujeita à aprovação.")

        # Gerar nomes de arquivo únicos
        unique_id = str(uuid.uuid4())[:8]
        safe_placa = placa.replace(' ', '_').replace('/', '_').replace('-', '') # Mais sanitização
        output_pptx_filename = f"cotacao_{safe_placa}_{unique_id}.pptx"
        output_pdf_filename = f"cotacao_{safe_placa}_{unique_id}.pdf" # Nome esperado do PDF

        # Caminhos completos dentro do diretório de saída configurado
        output_pptx_path = os.path.join(app.config["OUTPUT_DIR"], output_pptx_filename)
        # O caminho completo do PDF será determinado pela função de conversão

        # ---- Bloco Principal: Preencher, Converter, Limpar ----
        # Este bloco try...except engloba todo o processo de geração
        try: 
            # 1. Verificar Template PPTX (os.path.exists)
            logging.info(f"Verificando existência do template: {TEMPLATE_PPTX}")
            # Log extra para listar conteúdo (ajuda a depurar se o arquivo está lá)
            try:
                input_files_list = os.listdir(INPUT_DIR)
                logging.info(f"Conteúdo de {INPUT_DIR}: {input_files_list}")
            except Exception as list_e:
                logging.error(f"Erro ao listar diretório {INPUT_DIR}: {list_e}")

            if not os.path.exists(TEMPLATE_PPTX):
                error = f"Erro interno: Arquivo modelo de cotação ({TEMPLATE_PPTX}) não encontrado."
                logging.error(error)
                # Retorna o template mostrando o erro (importante retornar DENTRO do try neste caso)
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename) 

            # 2. Preencher o PowerPoint
            logging.info(f"Chamando preencher_cotacao_pptx para salvar em: {output_pptx_path}")
            sucesso_pptx = preencher_cotacao_pptx(TEMPLATE_PPTX, output_pptx_path, dados_cotacao)

            if sucesso_pptx:
                logging.info(f"PPTX preenchido com sucesso: {output_pptx_path}. Tentando converter para PDF...")

                # 3. Converter para PDF
                caminho_pdf_gerado = converter_pptx_para_pdf(output_pptx_path, app.config["OUTPUT_DIR"]) 

                if caminho_pdf_gerado and os.path.exists(caminho_pdf_gerado): 
                    output_pdf_filename = os.path.basename(caminho_pdf_gerado) 
                    success = f"Cotação para {nome_cliente} (placa {placa}) gerada com sucesso!"
                    pdf_filename = output_pdf_filename 
                    logging.info(f"PDF gerado com sucesso: {caminho_pdf_gerado}. Nome relativo para link: {pdf_filename}")

                    # 4. Limpar o arquivo pptx intermediário (opcional)
                    try:
                        os.remove(output_pptx_path)
                        logging.info(f"Arquivo PPTX intermediário removido: {output_pptx_path}")
                    except OSError as e:
                        logging.warning(f"Não foi possível remover arquivo PPTX intermediário: {e}")
                else:
                    # Se caminho_pdf_gerado for None ou o arquivo não existir, a conversão falhou
                    error = f"Erro ao converter a cotação para PDF. Verifique os logs do servidor."
                    logging.error(f"Falha na conversão para PDF (função retornou '{caminho_pdf_gerado}' ou arquivo não existe) para {output_pptx_path}")
                    # Tenta limpar PPTX mesmo se PDF falhou? É seguro pois ele foi gerado.
                    if os.path.exists(output_pptx_path):
                        try:
                            os.remove(output_pptx_path)
                            logging.info(f"Limpando PPTX intermediário após falha no PDF: {output_pptx_path}")
                        except:
                            pass 
            else: 
                # Se preencher_cotacao_pptx retornou False
                error = f"Erro ao preencher o modelo de cotação. Verifique os logs do servidor."
                logging.error(f"Falha reportada por preencher_cotacao_pptx para {output_pptx_path}")

        # Este except corresponde ao 'try' que engloba Preencher/Converter/Limpar
        except Exception as e:
            error = f"Ocorreu um erro inesperado durante a geração da cotação."
            logging.exception(f"Exceção durante preenchimento/conversão:") 
            # Tenta limpar arquivos intermediários se possível em caso de erro
            if 'output_pptx_path' in locals() and os.path.exists(output_pptx_path):
                 try:
                      os.remove(output_pptx_path)
                      logging.info(f"Limpando PPTX intermediário após erro: {output_pptx_path}")
                 except:
                      pass 

    # Fim do 'if request.method == "POST":'
    # O return abaixo será executado para GET ou após o POST (com ou sem erro/success)

# Renderiza o template no final, seja GET ou POST, com as variáveis de estado
return render_template("index.html", 
                       error=error, 
                       success=success, 
                       warning=warning, 
                       pdf_filename=pdf_filename) # Passa o nome do arquivo PDF


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
