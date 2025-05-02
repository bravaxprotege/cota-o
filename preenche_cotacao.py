# ----- INÍCIO DO CÓDIGO COMPLETO E ATUALIZADO PARA preenche_cotacao.py -----
import sys
# Linha específica do ambiente Render/Manus, pode manter se necessário
# sys.path.append("/opt/.manus/.sandbox-runtime") 
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN # Importar enumeração para alinhamento
import traceback # Importar para log de erros
import os # Importar OS para o bloco de teste funcionar
import logging # Importar logging

# Configurar logging básico (app.py também configura, mas é seguro ter aqui)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log_prefix = "[preenche_cotacao]" # Prefixo para logs deste arquivo

# --- Função Auxiliar para Formatar Moeda (sem alterações) ---
def format_currency_manual(value):
    """Formata um valor numérico como moeda brasileira (R$) manualmente."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"

# --- Função set_text ATUALIZADA ---
def set_text(text_frame, text_value, 
             font_size=Pt(22),           # <<< ALTERADO AQUI PARA 22pt <<<
             font_name='Liberation Sans',        # Mantido Calibri (pode mudar)
             alignment=PP_ALIGN.CENTER,  # Mantido Centralizado (pode mudar)
             is_warning=False):
    """Define o texto em um text_frame, limpando o anterior e aplicando formatação."""
    if text_frame is None:
        return 
    
    # Limpa o frame de texto completamente
    text_frame.clear() 
    # Adiciona um novo parágrafo
    p = text_frame.add_paragraph() 
      
    # Define o texto diretamente no parágrafo
    p.text = str(text_value) 
     
    # Aplica o ALINHAMENTO e a FONTE ao parágrafo
    p.alignment = alignment  # Define o alinhamento 
    p.font.name = font_name  # Define o nome da fonte 
    p.font.size = font_size  # Define o tamanho da fonte 
    
    # Formatação de aviso 
    if is_warning:
        p.font.bold = True
        p.font.color.rgb = RGBColor(192, 0, 0)
    else:
         p.font.bold = False 

    logging.info(f"  Definido texto '{text_value}' na forma '{text_frame.parent.name}' | Fonte: {font_name}, Tamanho: {font_size.pt}pt, Align: {alignment}") 


# --- Função Principal preencher_cotacao_pptx (sem alterações na lógica principal) ---
def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    """Preenche um template PowerPoint com dados da cotação em slides específicos e salva."""
    
    logging.info(f"{log_prefix} Iniciando preenchimento com template: {template_path}")
    logging.info(f"{log_prefix} Dados recebidos: {dados_cotacao}")

    try:
        prs = Presentation(template_path)
        
        # --- Função Auxiliar Interna find_shape (sem alterações) ---
        def find_shape(slide_index, shape_name_to_find):
            if slide_index < 0 or slide_index >= len(prs.slides):
                logging.warning(f"{log_prefix} AVISO: Slide índice {slide_index} não existe.")
                return None
            slide = prs.slides[slide_index]
            for shape in slide.shapes:
                # Comparação case-insensitive
                if shape.name.strip().lower() == shape_name_to_find.strip().lower(): 
                    if shape.has_text_frame:
                        logging.info(f"{log_prefix}   Encontrada forma '{shape.name}' (buscando por '{shape_name_to_find}') no slide {slide_index+1}.")
                        return shape.text_frame
                    else:
                        logging.warning(f"{log_prefix} AVISO: Forma '{shape.name}' no slide {slide_index+1} não tem frame de texto.")
                        return None
            logging.warning(f"{log_prefix} AVISO: Forma com nome parecido com '{shape_name_to_find}' não encontrada no slide {slide_index+1}.")
            return None

        # --- Extração dos Dados (sem alterações) ---
        nome_cliente = dados_cotacao.get("nome_cliente", "N/A")
        placa = dados_cotacao.get("placa", "N/A")
        marca = dados_cotacao.get("marca", "N/A")
        modelo = dados_cotacao.get("modelo", "N/A")
        ano = dados_cotacao.get("ano", "N/A")
        valor_fipe = dados_cotacao.get("valor_fipe")
        categoria = dados_cotacao.get("categoria", "N/A")
        precos = dados_cotacao.get("precos", {})
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)
        adesao_valor = format_currency_manual(precos.get('Adesão'))


        # --- Preenchimento Slide por Slide (As chamadas a set_text usam os novos padrões) ---
        
        logging.info(f"{log_prefix} Preenchendo Slide 1 (Índice 0)")
        tf = find_shape(0, "Nome associado") 
        set_text(tf, nome_cliente) # Usará Pt(22), Calibri, Center por padrão

        logging.info(f"{log_prefix} Preenchendo Slide 4 (Índice 3)")
        tf = find_shape(3, "Nome associado") 
        set_text(tf, nome_cliente)
        tf = find_shape(3, "Placa") 
        set_text(tf, placa)
        tf = find_shape(3, "Marca carro") 
        set_text(tf, marca)
        tf = find_shape(3, "modelo") 
        set_text(tf, modelo)
        tf = find_shape(3, "Ano") 
        set_text(tf, str(ano)) 
        tf = find_shape(3, "Categoria") 
        set_text(tf, categoria)
        tf = find_shape(3, "Valor fipe") 
        set_text(tf, format_currency_manual(valor_fipe))

        logging.info(f"{log_prefix} Preenchendo Slide 5 (Índice 4) - Ouro")
        tf = find_shape(4, "adesão") 
        set_text(tf, adesao_valor) 
        tf = find_shape(4, "ouro") 
        set_text(tf, format_currency_manual(precos.get('Plano Ouro'))) 

        logging.info(f"{log_prefix} Preenchendo Slide 6 (Índice 5) - Diamante")
        tf = find_shape(5, "adesão") 
        set_text(tf, adesao_valor) 
        tf = find_shape(5, "diamante") 
        set_text(tf, format_currency_manual(precos.get('Diamante')))

        logging.info(f"{log_prefix} Preenchendo Slide 7 (Índice 6) - Platinum")
        tf = find_shape(6, "adesão") 
        set_text(tf, adesao_valor) 
        tf = find_shape(6, "platinium") # Confirmar se o nome da shape é 'platinium' mesmo
        set_text(tf, format_currency_manual(precos.get('Platinum'))) 
        
        # --- PONTOS FALTANDO (Onde colocar estes? Sem alterações aqui) ---
        preco_pesados = format_currency_manual(precos.get('Pesados'))
        if preco_pesados != "N/A":
             logging.warning(f"{log_prefix} Valor Pesados ({preco_pesados}) NÃO INSERIDO - Definir Slide/Shape.")
        if sujeito_aprovacao:
             logging.warning(f"{log_prefix} AVISO Sujeito à Aprovação NÃO INSERIDO - Definir Slide/Shape.")

        # --- Salvando e Retornando (sem alterações) ---
        logging.info(f"{log_prefix} Salvando apresentação em {output_path}")
        prs.save(output_path)
        logging.info(f"{log_prefix} Cotação salva com sucesso.")
        return True

    # --- Tratamento de Erros (sem alterações) ---
    except Presentation.PackageNotFoundError as pe:
         logging.error(f"{log_prefix} ERRO ao ABRIR/LER o template PowerPoint: {pe}")
         logging.error(f"{log_prefix} Verifique se o arquivo .pptx não está corrompido ou se é um formato válido.")
         traceback.print_exc()
         return False
    except Exception as e:
        logging.error(f"{log_prefix} ERRO GERAL ao preencher o PowerPoint: {e}")
        traceback.print_exc() 
        return False

# --- Bloco de Teste Local (sem alterações) ---
if __name__ == "__main__":
    # ... (código de teste local igual ao anterior) ...
    pass # Adicionado pass para caso o bloco if/else seja removido ou comentado

# ----- FIM DO CÓDIGO -----
