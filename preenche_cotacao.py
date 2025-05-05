# ----- INÍCIO DO CÓDIGO COMPLETO E ATUALIZADO PARA preenche_cotacao.py -----
import sys
# sys.path.append("/opt/.manus/.sandbox-runtime") 
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN # Importar enumeração para alinhamento HORIZONTAL
from pptx.enum.shapes import MSO_ANCHOR # Importar enumeração para alinhamento VERTICAL
import traceback 
import os 
import logging 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log_prefix = "[preenche_cotacao]" 

# --- Funções Auxiliares para Formatar Moeda ---
def format_currency_manual(value):
    """Formata um valor numérico como moeda brasileira (R$ XXX.XXX,XX) manualmente."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"

# --- NOVA Função Auxiliar para Formatar SÓ O VALOR ---
def format_currency_value_only(value):
    """Formata um valor numérico, retornando APENAS O NÚMERO (XXX.XXX,XX)."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        # Formata e remove o "R$ "
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


# --- Função set_text MODIFICADA ---
def set_text(text_frame, text_value, 
             font_size=Pt(22),           # Tamanho padrão (pode ser sobrescrito na chamada)
             font_name='Liberation Sans',# Fonte padrão
             alignment=PP_ALIGN.LEFT,    # <<< Alinhamento padrão Horizontal: ESQUERDA
             vertical_anchor=MSO_ANCHOR.TOP, # <<< Alinhamento padrão Vertical: TOPO
             is_warning=False):
    """Define o texto em um text_frame, limpando, aplicando formatação e alinhamento."""
    if text_frame is None:
        return 
    
    logging.info(f"  Tentando definir texto: '{text_value}'...") 

    # Define alinhamento vertical ANTES de limpar (pode preservar melhor)
    try:
        text_frame.vertical_anchor = vertical_anchor
        logging.info(f"  Alinhamento vertical definido para: {vertical_anchor}")
    except Exception as va_err:
         logging.error(f"  ERRO ao definir alinhamento vertical: {va_err}")

    text_frame.clear() 
    p = text_frame.add_paragraph() 
    
    # Define alinhamento horizontal do parágrafo
    try:
         p.alignment = alignment  
         logging.info(f"  Alinhamento horizontal definido para: {alignment}")
    except AttributeError as align_err:
         logging.error(f"  ERRO ao definir alinhamento horizontal: {align_err}")
    except Exception as general_align_err:
         logging.error(f"  ERRO GERAL ao definir alinhamento horizontal: {general_align_err}")

    # Define o texto
    p.text = str(text_value) 
    
    # Define fonte e tamanho
    font_final_name = None 
    try:
        p.font.name = font_name
        font_final_name = p.font.name
    except Exception as font_err:
        logging.error(f"  ERRO ao definir nome da fonte '{font_name}': {font_err}. Usando fonte padrão.")
        font_final_name = p.font.name 

    p.font.size = font_size 
    if is_warning:
        p.font.bold = True
        p.font.color.rgb = RGBColor(192, 0, 0)
    else:
         p.font.bold = False 

    logging.info(f"  Texto definido. Fonte: {font_final_name}, Tamanho: {font_size.pt}pt, HAlign: {p.alignment}, VAlign: {text_frame.vertical_anchor}") 


# --- Função Principal preencher_cotacao_pptx (COM CHAMADAS AJUSTADAS) ---
def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    logging.info(f"{log_prefix} Iniciando preenchimento com template: {template_path}")
    logging.info(f"{log_prefix} Dados recebidos: {dados_cotacao}")
    try:
        prs = Presentation(template_path)
        
        def find_shape(slide_index, shape_name_to_find):
            # ... (código da função find_shape igual ao anterior) ...
             if slide_index < 0 or slide_index >= len(prs.slides):
                logging.warning(f"{log_prefix} AVISO: Slide índice {slide_index} não existe.")
                return None
             slide = prs.slides[slide_index]
             for shape in slide.shapes:
                if shape.name.strip().lower() == shape_name_to_find.strip().lower(): 
                    if shape.has_text_frame:
                        logging.info(f"{log_prefix}   Encontrada forma '{shape.name}' (buscando por '{shape_name_to_find}') no slide {slide_index+1}.")
                        return shape.text_frame
                    else:
                        logging.warning(f"{log_prefix} AVISO: Forma '{shape.name}' no slide {slide_index+1} não tem frame de texto.")
                        return None
             logging.warning(f"{log_prefix} AVISO: Forma com nome parecido com '{shape_name_to_find}' não encontrada no slide {slide_index+1}.")
             return None

        # Extração de dados
        nome_cliente = dados_cotacao.get("nome_cliente", "N/A")
        placa = dados_cotacao.get("placa", "N/A")
        marca = dados_cotacao.get("marca", "N/A")
        modelo = dados_cotacao.get("modelo", "N/A")
        ano = dados_cotacao.get("ano", "N/A")
        valor_fipe = dados_cotacao.get("valor_fipe")
        categoria = dados_cotacao.get("categoria", "N/A")
        precos = dados_cotacao.get("precos", {})
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)
        # Formata adesão UMA VEZ e SEM R$
        adesao_valor_str = format_currency_value_only(precos.get('Adesão')) 

        # --- Preenchimento Slide por Slide ---
        
        logging.info(f"{log_prefix} Preenchendo Slide 1 (Índice 0)")
        tf = find_shape(0, "Nome associado") 
        # Usará padrões de set_text: Pt(22), Liberation Sans, LEFT, TOP
        set_text(tf, nome_cliente) 

        logging.info(f"{log_prefix} Preenchendo Slide 4 (Índice 3)")
        tf = find_shape(3, "Nome associado") 
        set_text(tf, nome_cliente) # Usa padrões
        tf = find_shape(3, "Placa") 
        set_text(tf, placa) # Usa padrões
        tf = find_shape(3, "Marca carro") 
        set_text(tf, marca) # Usa padrões
        tf = find_shape(3, "modelo") 
        set_text(tf, modelo) # Usa padrões
        tf = find_shape(3, "Ano") 
        set_text(tf, str(ano)) # Usa padrões
        tf = find_shape(3, "Categoria") 
        set_text(tf, categoria) # Usa padrões
        tf = find_shape(3, "Valor fipe") 
        # Para o valor FIPE, manter R$ mas usar formatação padrão (Left, Top, 22pt)
        set_text(tf, format_currency_manual(valor_fipe)) 

        # Definir tamanho GRANDE para mensalidades
        TAMANHO_FONTE_MENSALIDADE = Pt(36) # <-- Ajuste este valor se necessário

        logging.info(f"{log_prefix} Preenchendo Slide 5 (Índice 4) - Ouro")
        tf_adesao_ouro = find_shape(4, "adesão") 
        set_text(tf_adesao_ouro, adesao_valor_str, font_size=TAMANHO_FONTE_MENSALIDADE) # Sem R$, tamanho grande
        tf_mensal_ouro = find_shape(4, "ouro") 
        set_text(tf_mensal_ouro, format_currency_value_only(precos.get('Plano Ouro')), font_size=TAMANHO_FONTE_MENSALIDADE) # Sem R$, tamanho grande

        logging.info(f"{log_prefix} Preenchendo Slide 6 (Índice 5) - Diamante")
        tf_adesao_diamante = find_shape(5, "adesão") 
        set_text(tf_adesao_diamante, adesao_valor_str, font_size=TAMANHO_FONTE_MENSALIDADE) # Sem R$, tamanho grande
        tf_mensal_diamante = find_shape(5, "diamante") 
        set_text(tf_mensal_diamante, format_currency_value_only(precos.get('Diamante')), font_size=TAMANHO_FONTE_MENSALIDADE) # Sem R$, tamanho grande

        logging.info(f"{log_prefix} Preenchendo Slide 7 (Índice 6) - Platinum")
        tf_adesao_platinum = find_shape(6, "adesão") 
        set_text(tf_adesao_platinum, adesao_valor_str, font_size=TAMANHO_FONTE_MENSALIDADE) # Sem R$, tamanho grande
        tf_mensal_platinum = find_shape(6, "platinium") # Confirmar se o nome da shape é 'platinium' mesmo
        set_text(tf_mensal_platinum, format_currency_value_only(precos.get('Platinum')), font_size=TAMANHO_FONTE_MENSALIDADE) # Sem R$, tamanho grande
        
        # --- PONTOS FALTANDO ---
        preco_pesados_str = format_currency_value_only(precos.get('Pesados'))
        if preco_pesados_str != "N/A":
             logging.warning(f"{log_prefix} Valor Pesados ({preco_pesados_str}) NÃO INSERIDO - Definir Slide/Shape.")
             # Adicionar chamada a set_text aqui quando souber onde colocar
        if sujeito_aprovacao:
             logging.warning(f"{log_prefix} AVISO Sujeito à Aprovação NÃO INSERIDO - Definir Slide/Shape.")
             # Adicionar chamada a set_text aqui quando souber onde colocar

        logging.info(f"{log_prefix} Salvando apresentação em {output_path}")
        prs.save(output_path)
        logging.info(f"{log_prefix} Cotação salva com sucesso.")
        return True

    except Presentation.PackageNotFoundError as pe:
         logging.error(f"{log_prefix} ERRO ao ABRIR/LER o template PowerPoint: {pe}")
         traceback.print_exc()
         return False
    except Exception as e:
        logging.error(f"{log_prefix} ERRO GERAL ao preencher o PowerPoint: {e}")
        traceback.print_exc() 
        return False

# --- Bloco de Teste Local (Mantido igual) ---
# if __name__ == "__main__":
#    # ... (código de teste local) ...
#    pass

# ----- FIM DO CÓDIGO -----
