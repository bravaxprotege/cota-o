# ----- INÍCIO DO CÓDIGO COMPLETO E FINAL PARA preenche_cotacao.py -----
import sys
# sys.path.append("/opt/.manus/.sandbox-runtime") 
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
# Importa APENAS o alinhamento HORIZONTAL
from pptx.enum.text import PP_ALIGN 
import traceback 
import os 
import logging 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log_prefix = "[preenche_cotacao]" 

# --- Função Auxiliar para Formatar Moeda COMPLETA ---
def format_currency_manual(value):
    """Formata um valor numérico como moeda brasileira (R$ XXX.XXX,XX) manualmente."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"

# --- Função Auxiliar para Formatar SÓ O VALOR ---
def format_currency_value_only(value):
    """Formata um valor numérico, retornando APENAS O NÚMERO (XXX.XXX,XX)."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        # Formata e remove o "R$ "
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


# --- Função set_text FINAL (Tamanho 22pt, Align Left, Fonte Liberation Sans) ---
def set_text(text_frame, text_value, 
             font_size=Pt(22),            # <<< TAMANHO PADRÃO 22pt <<<
             font_name='Liberation Sans', # <<< FONTE PADRÃO <<<
             alignment=PP_ALIGN.LEFT,     # <<< ALINHAMENTO PADRÃO ESQUERDA <<<
             is_warning=False):
    """Define o texto em um text_frame, limpando, aplicando formatação e alinhamento HORIZONTAL."""
    if text_frame is None:
        return 
        
    # REMOVIDA a tentativa de definir alinhamento vertical
        
    logging.info(f"  Tentando definir texto: '{text_value}'...") 

    text_frame.clear() 
    p = text_frame.add_paragraph() 
        
    # Define o alinhamento HORIZONTAL do parágrafo
    try:
         p.alignment = alignment  
         # logging.info(f"  Alinhamento horizontal definido para: {alignment}") # Log Opcional
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
        font_final_name = p.font.name # Loga qual fonte ficou como padrão

    p.font.size = font_size 
    if is_warning:
        p.font.bold = True
        p.font.color.rgb = RGBColor(192, 0, 0)
    else:
         p.font.bold = False 

    # Log final SEM VAlign e SEM usar '.parent'
    logging.info(f"  Texto definido. Fonte Aplicada: {font_final_name}, Tamanho: {font_size.pt}pt, HAlign: {p.alignment}") 


# --- Função Principal preencher_cotacao_pptx (COM CHAMADAS AJUSTADAS para formato e tamanho de preço) ---
def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    logging.info(f"{log_prefix} Iniciando preenchimento com template: {template_path}")
    logging.info(f"{log_prefix} Dados recebidos: {dados_cotacao}")
    try:
        # Tenta abrir a apresentação ANTES da função auxiliar
        logging.info(f"{log_prefix} Abrindo apresentação: {template_path}")
        prs = Presentation(template_path)
        logging.info(f"{log_prefix} Template aberto com sucesso.")
        
        # --- Função Auxiliar Interna find_shape (sem alterações) ---
        def find_shape(slide_index, shape_name_to_find):
            if slide_index < 0 or slide_index >= len(prs.slides):
                logging.warning(f"{log_prefix} AVISO: Slide índice {slide_index} (página {slide_index+1}) não existe.")
                return None
            slide = prs.slides[slide_index]
            shape_found = None
            logging.info(f"{log_prefix} Procurando shape '{shape_name_to_find}' no slide {slide_index+1}...")
            for shape in slide.shapes:
                # Comparação case-insensitive e removendo espaços extras do nome da shape
                if shape.name.strip().lower() == shape_name_to_find.strip().lower(): 
                    shape_found = shape
                    break # Encontrou, pode parar de procurar neste slide

            if shape_found:
                if shape_found.has_text_frame:
                    logging.info(f"{log_prefix}   Encontrada forma '{shape_found.name}' (buscando por '{shape_name_to_find}').")
                    return shape_found.text_frame
                else:
                    logging.warning(f"{log_prefix} AVISO: Forma '{shape_found.name}' encontrada mas não tem frame de texto.")
                    return None
            else:
                logging.warning(f"{log_prefix} AVISO: Forma com nome parecido com '{shape_name_to_find}' NÃO encontrada no slide {slide_index+1}.")
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

        # Definir tamanho GRANDE para mensalidades (Ajuste aqui se 36 for muito/pouco)
        TAMANHO_FONTE_MENSALIDADE = Pt(36) 

        # --- Preenchimento Slide por Slide ---
        
        logging.info(f"{log_prefix} Preenchendo Slide 1 (Índice 0)")
        tf = find_shape(0, "Nome associado") 
        # Usa padrões de set_text: Pt(22), Liberation Sans, LEFT
        set_text(tf, nome_cliente) 

        logging.info(f"{log_prefix} Preenchendo Slide 4 (Índice 3)")
        tf = find_shape(3, "Nome associado") 
        set_text(tf, nome_cliente) # Usa padrões (Left, 22pt)
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
        # Para o valor FIPE, manter R$ mas usar formatação padrão (Left, 22pt)
        set_text(tf, format_currency_manual(valor_fipe)) 

        logging.info(f"{log_prefix} Preenchendo Slide 5 (Índice 4) - Ouro")
        tf_adesao_ouro = find_shape(4, "adesão") 
        # Usa formatador SEM R$, alinhamento padrão (LEFT), mas TAMANHO GRANDE
        set_text(tf_adesao_ouro, adesao_valor_str, font_size=TAMANHO_FONTE_MENSALIDADE) 
        tf_mensal_ouro = find_shape(4, "ouro") 
        set_text(tf_mensal_ouro, format_currency_value_only(precos.get('Plano Ouro')), font_size=TAMANHO_FONTE_MENSALIDADE) 

        logging.info(f"{log_prefix} Preenchendo Slide 6 (Índice 5) - Diamante")
        tf_adesao_diamante = find_shape(5, "adesão") 
        set_text(tf_adesao_diamante, adesao_valor_str, font_size=TAMANHO_FONTE_MENSALIDADE) 
        tf_mensal_diamante = find_shape(5, "diamante") 
        set_text(tf_mensal_diamante, format_currency_value_only(precos.get('Diamante')), font_size=TAMANHO_FONTE_MENSALIDADE) 

        logging.info(f"{log_prefix} Preenchendo Slide 7 (Índice 6) - Platinum")
        tf_adesao_platinum = find_shape(6, "adesão") 
        set_text(tf_adesao_platinum, adesao_valor_str, font_size=TAMANHO_FONTE_MENSALIDADE) 
        tf_mensal_platinum = find_shape(6, "platinium") # Confirmar se o nome da shape é 'platinium' mesmo
        set_text(tf_mensal_platinum, format_currency_value_only(precos.get('Platinum')), font_size=TAMANHO_FONTE_MENSALIDADE) 
        
        # --- PONTOS FALTANDO (Onde colocar estes?) ---
        preco_pesados_str = format_currency_value_only(precos.get('Pesados'))
        if preco_pesados_str != "N/A":
             logging.warning(f"{log_prefix} Valor Pesados ({preco_pesados_str}) NÃO INSERIDO - Definir Slide/Shape.")
        if sujeito_aprovacao:
             logging.warning(f"{log_prefix} AVISO Sujeito à Aprovação NÃO INSERIDO - Definir Slide/Shape.")

        # --- Salvando e Retornando ---
        logging.info(f"{log_prefix} Salvando apresentação em {output_path}")
        prs.save(output_path)
        logging.info(f"{log_prefix} Cotação salva com sucesso.")
        return True

    # --- Tratamento de Erros ---
    except Presentation.PackageNotFoundError as pe: # Erro específico para arquivo corrompido/inválido
         logging.error(f"{log_prefix} ERRO AO ABRIR/LER O TEMPLATE: {pe}")
         logging.error(f"{log_prefix} Verifique se o arquivo '{template_path}' não está corrompido ou se é um formato PPTX válido.")
         traceback.print_exc()
         return False
    except Exception as e: # Outros erros durante o processo
        logging.error(f"{log_prefix} ERRO GERAL DURANTE O PREENCHIMENTO do PowerPoint: {e}")
        traceback.print_exc() 
        return False

# --- Bloco de Teste Local (Mantido igual) ---
if __name__ == "__main__":
    # ... (código de teste local igual ao anterior) ...
    pass # Adicionado pass para garantir que bloco não fique vazio se código for removido

# ----- FIM DO CÓDIGO -----
