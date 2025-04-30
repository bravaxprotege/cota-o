import sys
# Linha específica do ambiente Render/Manus, pode manter se necessário
sys.path.append("/opt/.manus/.sandbox-runtime") 

import os
import uuid
from flask import Flask, render_template, request, send_from_directory, url_for, abort

# Importar as funções dos scripts criados (assumindo que estão na mesma pasta 'app/')
try:
    from calculo_precos import calcular_precos_planos
    from preenche_cotacao import preencher_cotacao_pptx
    from converte_pdf import converter_pptx_para_pdf
except ImportError as e:
    print(f"Erro ao importar módulos locais: {e}")
    # Você pode querer lançar um erro aqui ou lidar de outra forma
    # raise ImportError(f"Verifique se os arquivos .py auxiliares estão na pasta 'app/': {e}") from e

# Inicializa a aplicação Flask
app = Flask(__name__) # '__name__' ajuda o Flask a encontrar recursos como templates

# --- Configurações ---

# Diretório base da aplicação (onde este arquivo app.py está)
APP_ROOT = os.path.dirname(os.path.abspath(__file__)) 

# Diretório para arquivos de entrada (ASSUMINDO QUE 'input_files' ESTÁ DENTRO DE 'app/')
# Se 'input_files' estiver na raiz do projeto (fora de 'app/'), ajuste o path:
# INPUT_FILES_DIR = os.path.join(os.path.dirname(APP_ROOT), 'input_files') 
INPUT_FILES_DIR = os.path.join(APP_ROOT, 'input_files')

# Diretório para salvar arquivos gerados (relativo à pasta 'app/')
OUTPUT_DIR_NAME = 'generated_files'
OUTPUT_DIR = os.path.join(APP_ROOT, OUTPUT_DIR_NAME)

# Arquivos específicos de entrada (usando o diretório configurado)
DATABASE_FILE = os.path.join(INPUT_FILES_DIR, "Tabela 2023.xlsx")
TEMPLATE_PPTX = os.path.join(INPUT_FILES_DIR, "cotacao_auto.pptx")

# Guarda o diretório de saída na configuração do Flask (boa prática)
app.config["OUTPUT_DIR"] = OUTPUT_DIR

# --- Criação de Diretórios ---

# Criar diretório de saída se não existir
# Usar o caminho relativo definido acima
try:
    print(f"Tentando criar diretório de saída em: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Diretório de saída verificado/criado com sucesso.")
except OSError as e:
    print(f"ERRO CRÍTICO ao criar diretório de saída '{OUTPUT_DIR}': {e}")
    # Considerar lançar um erro aqui, pois a aplicação não funcionará sem ele.
    raise OSError(f"Não foi possível criar o diretório de saída necessário: {e}") from e


# --- Rotas da Aplicação ---

@app.route("/", methods=["GET", "POST"])
def index():
    """ Rota principal que exibe o formulário e processa a geração da cotação. """
    error = None
    success = None
    pdf_filename = None # Apenas o nome do arquivo para usar com url_for
    warning = None # Para avisos como "sujeito à aprovação"

    if request.method == "POST":
        # Capturar todos os dados do formulário
        nome_cliente = request.form.get("nome")
        placa = request.form.get("placa")
        marca = request.form.get("marca")
        modelo = request.form.get("modelo")
        ano = request.form.get("ano")
        valor_fipe_str = request.form.get("valor_fipe")
        categoria = request.form.get("categoria", "") # Campo opcional

        # Validar dados obrigatórios
        if not all([nome_cliente, placa, marca, modelo, ano, valor_fipe_str]):
            error = "Por favor, preencha todos os campos obrigatórios."
            # Retorna o template imediatamente com o erro
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Converter valores numéricos
        try:
            ano = int(ano)
            valor_fipe = float(valor_fipe_str.replace('.', '').replace(',', '.')) # Lidar com formato brasileiro
        except ValueError:
            error = "Ano e Valor FIPE devem ser valores numéricos válidos."
            return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

        # Calcular preços dos planos com base no valor FIPE
        print(f"Calculando preços para valor FIPE: {valor_fipe} usando DB: {DATABASE_FILE}")
        if not os.path.exists(DATABASE_FILE):
             print(f"ERRO: Arquivo de banco de dados não encontrado em: {DATABASE_FILE}")
             error = "Erro interno: Arquivo de dados da tabela não encontrado."
             return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)
        
        try:
            precos_info = calcular_precos_planos(valor_fipe, DATABASE_FILE)
        except Exception as e:
            print(f"Erro ao chamar calcular_precos_planos: {e}")
            error = f"Erro ao calcular os preços: {e}"
            precos_info = None # Garante que não continue se houver erro

        if precos_info:
            # Preparar dados para preencher o PowerPoint
            dados_cotacao = {
                "nome_cliente": nome_cliente, "placa": placa, "marca": marca,
                "modelo": modelo, "ano": ano, "valor_fipe": valor_fipe,
                "categoria": categoria, "precos": precos_info
            }
            
            # Verificar se há aviso de aprovação
            if precos_info.get("sujeito_aprovacao", False):
                warning = "Atenção: Esta cotação está sujeita à aprovação da diretoria devido ao valor do veículo."

            # Gerar nomes de arquivo únicos para evitar conflitos
            unique_id = str(uuid.uuid4())[:8]
            safe_placa = placa.replace(' ', '_').replace('-', '') # Deixar nome mais seguro
            output_pptx_filename = f"cotacao_{safe_placa}_{unique_id}.pptx"
            output_pdf_filename = f"cotacao_{safe_placa}_{unique_id}.pdf"
            
            # Caminhos completos usando o OUTPUT_DIR relativo configurado
            output_pptx_path = os.path.join(app.config["OUTPUT_DIR"], output_pptx_filename)
            output_pdf_path = os.path.join(app.config["OUTPUT_DIR"], output_pdf_filename)

            # Verificar se template PPTX existe
            print(f"Verificando template PPTX em: {TEMPLATE_PPTX}")
            if not os.path.exists(TEMPLATE_PPTX):
                print(f"ERRO: Arquivo de template PPTX não encontrado em: {TEMPLATE_PPTX}")
                error = "Erro interno: Arquivo modelo de cotação não encontrado."
                return render_template("index.html", error=error, success=success, warning=warning, pdf_filename=pdf_filename)

            # Preencher o PowerPoint
            print(f"Preenchendo PPTX: {output_pptx_path} a partir de {TEMPLATE_PPTX}")
            try:
                sucesso_pptx = preencher_cotacao_pptx(TEMPLATE_PPTX, output_pptx_path, dados_cotacao)
            except Exception as e:
                 print(f"Erro ao chamar preencher_cotacao_pptx: {e}")
                 error = f"Erro ao gerar o arquivo de cotação: {e}"
                 sucesso_pptx = False

            if sucesso_pptx:
                # Converter para PDF
                print(f"Convertendo para PDF: {output_pptx_path} -> {output_pdf_path}")
                try:
                    sucesso_pdf = converter_pptx_para_pdf(output_pptx_path, output_pdf_path)
                except Exception as e:
                    print(f"Erro ao chamar converter_pptx_para_pdf: {e}")
                    # Informar o usuário, mas talvez manter o PPTX? Ou dar erro total?
                    # Aqui, vamos dar erro total na conversão.
                    error = f"Erro ao converter a cotação para PDF: {e}. Verifique as dependências de conversão."
                    sucesso_pdf = False

                if sucesso_pdf:
                    success = f"Cotação para {nome_cliente} (placa {placa}) gerada com sucesso!"
                    pdf_filename = output_pdf_filename # Guarda apenas o nome para url_for
                    print(f"Sucesso! PDF gerado: {pdf_filename}")
                    
                    # Limpar o arquivo pptx intermediário (opcional)
                    try:
                        os.remove(output_pptx_path)
                        print(f"Arquivo PPTX intermediário removido: {output_pptx_path}")
                    except OSError as e:
                        # Não é um erro fatal se não conseguir remover
                        print(f"Aviso: Erro não-fatal ao remover arquivo PPTX intermediário: {e}")
                # else: (Erro na conversão PDF já tratado acima)
                #    error = error # Mantém o erro da conversão   
            # else: (Erro no preenchimento PPTX já tratado acima)
            #    error = error # Mantém o erro do preenchimento
        # else: (Erro no cálculo de preços já tratado acima)
        #    error = error # Mantém o erro do cálculo

    # Renderiza o template passando todas as variáveis necessárias
    return render_template("index.html", 
                           error=error, 
                           success=success, 
                           warning=warning, 
                           pdf_filename=pdf_filename)


@app.route("/output/<filename>")
def download_file(filename):
    """ Rota para servir os arquivos PDF gerados a partir do diretório de saída. """
    directory = app.config["OUTPUT_DIR"]
    print(f"Tentando servir arquivo '{filename}' do diretório '{directory}'")
    try:
        # Verifica se o arquivo realmente existe antes de tentar servir
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
             print(f"Erro 404: Arquivo não encontrado em: {file_path}")
             abort(404, description="Arquivo solicitado não encontrado no servidor.")

        return send_from_directory(directory, filename, as_attachment=True)
    
    except FileNotFoundError:
        # Segurança extra, embora o check acima deva pegar antes
        print(f"Erro 404: send_from_directory não encontrou o arquivo: {filename}")
        abort(404, description="Recurso não encontrado.")
    except Exception as e:
        # Captura outros erros inesperados ao tentar servir o arquivo
        print(f"Erro 500 ao tentar servir o arquivo '{filename}': {e}")
        abort(500, description="Erro interno do servidor ao tentar acessar o arquivo.")


# --- Execução da Aplicação ---

if __name__ == "__main__":
    # Pega a porta da variável de ambiente PORT (usada pelo Render)
    # Usa 8080 como padrão se PORT não estiver definida (para testes locais)
    port = int(os.environ.get("PORT", 8080))
    
    # Executa a aplicação Flask
    # host='0.0.0.0' permite acesso de fora do container/máquina
    # debug=False é ESSENCIAL para produção (segurança e performance)
    print(f"Iniciando servidor Flask em host 0.0.0.0 na porta {port} com debug=False")
    app.run(host="0.0.0.0", port=port, debug=False)
