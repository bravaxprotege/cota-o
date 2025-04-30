import sys
sys.path.append("/opt/.manus/.sandbox-runtime")
from flask import Flask, render_template, request, send_from_directory, url_for
import os
import uuid

# Importar as funções dos scripts criados
from calculo_precos import calcular_precos_planos
from preenche_cotacao import preencher_cotacao_pptx
from converte_pdf import converter_pptx_para_pdf

app = Flask(__name__)

# Configurações
UPLOAD_FOLDER = "." # Usar o diretório atual do projeto
DATABASE_FILE = "input_files/Tabela 2023.xlsx"
TEMPLATE_PPTX = "input_files/Cotação auto.pptx"
OUTPUT_DIR = "/home/ubuntu/projeto_cotacao/output" # Diretório para salvar os arquivos gerados

app.config["OUTPUT_DIR"] = OUTPUT_DIR

# Criar diretório de saída se não existir
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
            return render_template("index.html", error=error)

        # Converter valores numéricos
        try:
            ano = int(ano)
            valor_fipe = float(valor_fipe_str)
        except ValueError:
            error = "Ano e Valor FIPE devem ser valores numéricos válidos."
            return render_template("index.html", error=error)

        # Calcular preços dos planos com base no valor FIPE
        print(f"Calculando preços para valor FIPE: {valor_fipe}")
        precos_info = calcular_precos_planos(valor_fipe, DATABASE_FILE)

        if precos_info:
            # Preparar dados para preencher o PowerPoint
            dados_cotacao = {
                "nome_cliente": nome_cliente,
                "placa": placa,
                "marca": marca,
                "modelo": modelo,
                "ano": ano,
                "valor_fipe": valor_fipe,
                "categoria": categoria,
                "precos": precos_info # Passa todo o dicionário retornado
            }
            
            # Verificar se há aviso de aprovação
            if precos_info.get("sujeito_aprovacao", False):
                warning = "Atenção: Esta cotação está sujeita à aprovação da diretoria devido ao valor do veículo."

            # Gerar nomes de arquivo únicos para evitar conflitos
            unique_id = str(uuid.uuid4())[:8]  # Usar apenas os primeiros 8 caracteres do UUID
            # Corrigido: Usar aspas simples dentro do replace
            output_pptx_filename = f"cotacao_{placa.replace(' ', '_')}_{unique_id}.pptx"
            output_pdf_filename = f"cotacao_{placa.replace(' ', '_')}_{unique_id}.pdf"
            
            output_pptx_path = os.path.join(app.config["OUTPUT_DIR"], output_pptx_filename)
            output_pdf_path = os.path.join(app.config["OUTPUT_DIR"], output_pdf_filename)

            # Preencher o PowerPoint
            print(f"Preenchendo PPTX: {output_pptx_path}")
            sucesso_pptx = preencher_cotacao_pptx(TEMPLATE_PPTX, output_pptx_path, dados_cotacao)

            if sucesso_pptx:
                # Converter para PDF
                print(f"Convertendo para PDF: {output_pdf_path}")
                sucesso_pdf = converter_pptx_para_pdf(output_pptx_path, output_pdf_path)

                if sucesso_pdf:
                    success = f"Cotação para {nome_cliente} (placa {placa}) gerada com sucesso!"
                    pdf_path_relative = os.path.join("output", output_pdf_filename)
                    # Limpar o arquivo pptx intermediário (opcional)
                    try:
                        os.remove(output_pptx_path)
                        print(f"Arquivo PPTX intermediário removido: {output_pptx_path}")
                    except OSError as e:
                        print(f"Erro ao remover arquivo PPTX intermediário: {e}")
                else:
                    error = f"Erro ao converter a cotação para PDF."
            else:
                error = f"Erro ao preencher o modelo de cotação."
        else:
            error = f"Erro ao calcular os preços dos planos para o valor FIPE {valor_fipe}."

    return render_template("index.html", error=error, success=success, warning=warning, pdf_path=pdf_path_relative)

@app.route("/output/<filename>")
def download_file(filename):
    return send_from_directory(app.config["OUTPUT_DIR"], filename, as_attachment=True)

if __name__ == "__main__":
    # Ouvir em todas as interfaces de rede na porta 8080
    app.run(host="0.0.0.0", port=8080, debug=True)
