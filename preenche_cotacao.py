import sys
sys.path.append("/opt/.manus/.sandbox-runtime")
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

def format_currency_manual(value):
    """Formata um valor numérico como moeda brasileira (R$) manualmente."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        # Formatação manual para R$ 1.234,56
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"

def find_shape_by_name(slide, shape_name):
    """Encontra uma forma em um slide pelo seu nome."""
    for shape in slide.shapes:
        if shape.name == shape_name:
            return shape
    return None

def fill_text_frame(shape, text, font_size=Pt(18), bold=False, color=None):
    """Preenche o frame de texto de uma forma com o texto fornecido."""
    if shape and shape.has_text_frame:
        text_frame = shape.text_frame
        text_frame.clear()
        p = text_frame.add_paragraph()
        run = p.add_run()
        run.text = str(text) # Garantir que o texto seja string
        run.font.size = font_size
        run.font.bold = bold
        if color:
            run.font.color.rgb = color
        logging.info(f"Preenchendo Forma: '{shape.name}' com texto: '{str(text)[:50]}...'" ) # Log truncado
        return True
    else:
        logging.warning(f"Forma '{shape.name if shape else 'desconhecida'}' não encontrada ou não possui frame de texto.")
        return False

def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    """Preenche um template PowerPoint com dados da cotação e salva, buscando formas por nome em slides específicos."""
    try:
        prs = Presentation(template_path)
        logging.info(f"Abrindo template: {template_path}")

        # Extrair dados do dicionário
        nome_cliente = dados_cotacao.get("nome_cliente", "Nome não informado")
        placa = dados_cotacao.get("placa", "Placa não informada")
        marca = dados_cotacao.get("marca", "")
        modelo = dados_cotacao.get("modelo", "")
        ano = dados_cotacao.get("ano", "")
        valor_fipe = dados_cotacao.get("valor_fipe")
        categoria = dados_cotacao.get("categoria", "N/A")
        precos = dados_cotacao.get("precos", {})
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)

        # --- Preenchimento por Slide e Nome da Forma --- 

        formas_a_preencher = [] # Lista para rastrear o sucesso do preenchimento

        # Slide 1 (Índice 0)
        if len(prs.slides) > 0:
            slide1 = prs.slides[0]
            shape_nome_assoc_s1 = find_shape_by_name(slide1, "Nome associado")
            formas_a_preencher.append(fill_text_frame(shape_nome_assoc_s1, nome_cliente))
        else: 
            logging.error("Template não possui Slide 1")
            formas_a_preencher.append(False)

        # Slide 4 (Índice 3)
        if len(prs.slides) > 3:
            slide4 = prs.slides[3]
            shape_nome_assoc_s4 = find_shape_by_name(slide4, "Nome associado")
            shape_placa = find_shape_by_name(slide4, "Placa")
            shape_marca = find_shape_by_name(slide4, "Marca carro")
            shape_modelo = find_shape_by_name(slide4, "modelo")
            shape_ano = find_shape_by_name(slide4, "Ano")
            shape_categoria = find_shape_by_name(slide4, "Categoria")
            shape_valor_fipe = find_shape_by_name(slide4, "Valor fipe")
            
            formas_a_preencher.append(fill_text_frame(shape_nome_assoc_s4, nome_cliente))
            formas_a_preencher.append(fill_text_frame(shape_placa, placa))
            formas_a_preencher.append(fill_text_frame(shape_marca, marca))
            formas_a_preencher.append(fill_text_frame(shape_modelo, modelo))
            formas_a_preencher.append(fill_text_frame(shape_ano, ano))
            formas_a_preencher.append(fill_text_frame(shape_categoria, categoria))
            formas_a_preencher.append(fill_text_frame(shape_valor_fipe, format_currency_manual(valor_fipe)))
        else: 
            logging.error("Template não possui Slide 4")
            formas_a_preencher.extend([False]*7) # Adiciona 7 falhas

        # Slide 5 (Índice 4)
        if len(prs.slides) > 4:
            slide5 = prs.slides[4]
            shape_adesao_s5 = find_shape_by_name(slide5, "adesão")
            shape_ouro = find_shape_by_name(slide5, "ouro")
            
            formas_a_preencher.append(fill_text_frame(shape_adesao_s5, format_currency_manual(precos.get('Adesão'))))
            formas_a_preencher.append(fill_text_frame(shape_ouro, format_currency_manual(precos.get('Plano Ouro'))))
        else: 
            logging.error("Template não possui Slide 5")
            formas_a_preencher.extend([False]*2)

        # Slide 6 (Índice 5)
        if len(prs.slides) > 5:
            slide6 = prs.slides[5]
            shape_adesao_s6 = find_shape_by_name(slide6, "adesão")
            shape_diamante = find_shape_by_name(slide6, "diamante")
            
            formas_a_preencher.append(fill_text_frame(shape_adesao_s6, format_currency_manual(precos.get('Adesão'))))
            formas_a_preencher.append(fill_text_frame(shape_diamante, format_currency_manual(precos.get('Diamante'))))
        else: 
            logging.error("Template não possui Slide 6")
            formas_a_preencher.extend([False]*2)

        # Slide 7 (Índice 6)
        if len(prs.slides) > 6:
            slide7 = prs.slides[6]
            shape_adesao_s7 = find_shape_by_name(slide7, "adesão")
            shape_platinium = find_shape_by_name(slide7, "platinium") # Confirmar nome "platinium"
            
            formas_a_preencher.append(fill_text_frame(shape_adesao_s7, format_currency_manual(precos.get('Adesão'))))
            formas_a_preencher.append(fill_text_frame(shape_platinium, format_currency_manual(precos.get('Platinum'))))
        else: 
            logging.error("Template não possui Slide 7")
            formas_a_preencher.extend([False]*2)
            
        # TODO: Adicionar lógica para "Plano Pesados" e "AvisoDiretoria" se os nomes das formas forem fornecidos
        # Exemplo:
        # if sujeito_aprovacao:
        #     slide_aviso = prs.slides[X] # Definir slide X
        #     shape_aviso = find_shape_by_name(slide_aviso, "NomeDaFormaParaAviso")
        #     fill_text_frame(shape_aviso, "*Sujeito à aprovação da diretoria*", bold=True, color=RGBColor(192, 0, 0))
        # 
        # slide_pesados = prs.slides[Y] # Definir slide Y
        # shape_pesados = find_shape_by_name(slide_pesados, "NomeDaFormaParaPesados")
        # fill_text_frame(shape_pesados, format_currency_manual(precos.get('Pesados')))

        # Verificar se todas as formas essenciais foram preenchidas
        if not all(formas_a_preencher):
             logging.warning("Nem todas as formas especificadas foram encontradas ou preenchidas. Verifique os logs e o template.")
             # Decidir se isso deve ser um erro fatal ou apenas um aviso
             # return False # Descomente se a falta de uma forma deve impedir o salvamento

        prs.save(output_path)
        logging.info(f"Cotação salva em: {output_path}")
        return True

    except FileNotFoundError:
        logging.error(f"Erro: Template não encontrado em {template_path}")
        return False
    except Exception as e:
        logging.exception(f"Erro inesperado ao preencher o PowerPoint: {e}") # Usar logging.exception para incluir traceback
        return False

# Exemplo de uso (será chamado de outro script posteriormente)
if __name__ == "__main__":
    from calculo_precos import calcular_precos_planos

    # Dados de exemplo (simulando entrada manual + cálculo)
    valores_fipe_teste = [74442.0, 105000.0]
    arquivo_tabela = "input_files/Tabela 2023.xlsx"
    template_pptx = "input_files/cotacao_auto.pptx" # Usar o nome correto
    
    for i, valor_fipe_teste in enumerate(valores_fipe_teste):
        placa_teste = f"XYZ123{i}"
        # Salvar na pasta output para consistência com app.py
        output_dir_teste = "output"
        if not os.path.exists(output_dir_teste):
             os.makedirs(output_dir_teste)
        output_pptx = os.path.join(output_dir_teste, f"cotacao_{placa_teste}_teste.pptx")

        print(f"\n--- Testando Preenchimento com FIPE: {valor_fipe_teste} ---")
        print(f"Calculando preços para FIPE: {valor_fipe_teste}")
        precos_calculados = calcular_precos_planos(valor_fipe_teste, arquivo_tabela)

        if precos_calculados:
            dados_para_preencher = {
                "nome_cliente": f"Cliente Teste {i}",
                "placa": placa_teste,
                "marca": "Marca Teste",
                "modelo": "Modelo Teste",
                "ano": 2024,
                "valor_fipe": valor_fipe_teste,
                "categoria": "PASSEIO",
                "precos": precos_calculados
            }

            print("\nIniciando preenchimento do PowerPoint...")
            sucesso = preencher_cotacao_pptx(template_pptx, output_pptx, dados_para_preencher)
            if sucesso:
                print(f"Preenchimento do PowerPoint para {placa_teste} concluído com sucesso: {output_pptx}")
                # Opcional: Testar conversão para PDF aqui também
                # from converte_pdf import converter_pptx_para_pdf
                # pdf_success = converter_pptx_para_pdf(output_pptx, output_dir_teste)
                # print(f"Conversão para PDF {'bem-sucedida' if pdf_success else 'falhou'}.")
            else:
                print(f"Falha ao preencher o PowerPoint para {placa_teste}.")
        else:
            print("Não foi possível calcular os preços para preencher o PowerPoint.")

