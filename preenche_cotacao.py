import sys
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import traceback
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log_prefix = "[preenche_cotacao]"


def format_currency_manual(value):
    """Formata valor numérico como moeda brasileira (R$ XXX.XXX,XX)."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


def format_currency_value_only(value):
    """Formata valor numérico retornando apenas o número (XXX.XXX,XX)."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


def set_text(text_frame, text_value, font_size=None, is_warning=False):
    """
    Define o texto preservando a fonte e formatação originais do template.
    Só sobrescreve font_size se explicitamente fornecido.
    """
    if text_frame is None:
        return

    # Captura formatação do template ANTES de limpar
    tmpl_font_name = None
    tmpl_font_size = None
    tmpl_bold      = None
    tmpl_alignment = None

    if text_frame.paragraphs:
        para = text_frame.paragraphs[0]
        tmpl_alignment = para.alignment
        if para.font.name:  tmpl_font_name = para.font.name
        if para.font.size:  tmpl_font_size = para.font.size
        if para.font.bold is not None: tmpl_bold = para.font.bold
        if para.runs:
            run = para.runs[0]
            if run.font.name:  tmpl_font_name = run.font.name
            if run.font.size:  tmpl_font_size = run.font.size
            if run.font.bold is not None: tmpl_bold = run.font.bold

    text_frame.clear()
    p = text_frame.add_paragraph()

    if tmpl_alignment is not None:
        try:
            p.alignment = tmpl_alignment
        except Exception as e:
            logging.error(f"  Erro ao definir alinhamento: {e}")

    p.text = str(text_value)

    if tmpl_font_name:
        p.font.name = tmpl_font_name
    if font_size is not None:
        p.font.size = font_size
    elif tmpl_font_size is not None:
        p.font.size = tmpl_font_size

    if is_warning:
        p.font.bold = True
        p.font.color.rgb = RGBColor(192, 0, 0)
    elif tmpl_bold is not None:
        p.font.bold = tmpl_bold

    logging.info(f"  '{text_value}' → fonte='{p.font.name}' tamanho={p.font.size}")


def remover_slide(prs, slide_index):
    """
    Remove um slide da apresentação pelo índice.
    Sempre remova do índice MAIOR para o MENOR para não bagunçar os índices.
    """
    xml_slides = prs.slides._sldIdLst
    # O atributo r:id aponta para o relacionamento do slide
    rId = xml_slides[slide_index].get(
        '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    )
    prs.part.drop_rel(rId)
    del xml_slides[slide_index]
    logging.info(f"{log_prefix} Slide índice {slide_index} removido.")


def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    logging.info(f"{log_prefix} Iniciando preenchimento: {template_path}")
    logging.info(f"{log_prefix} Dados: {dados_cotacao}")
    try:
        prs = Presentation(template_path)
        logging.info(f"{log_prefix} Template aberto com sucesso. Total de slides: {len(prs.slides)}")

        def find_shape(slide_index, shape_name_to_find):
            if slide_index < 0 or slide_index >= len(prs.slides):
                logging.warning(f"{log_prefix} Slide {slide_index} não existe.")
                return None
            slide = prs.slides[slide_index]
            for shape in slide.shapes:
                if shape.name.strip().lower() == shape_name_to_find.strip().lower():
                    if shape.has_text_frame:
                        return shape.text_frame
                    logging.warning(f"{log_prefix} Shape '{shape.name}' sem text frame.")
                    return None
            logging.warning(f"{log_prefix} Shape '{shape_name_to_find}' não encontrada no slide {slide_index+1}.")
            return None

        # Extração de dados
        nome_cliente   = dados_cotacao.get("nome_cliente", "N/A")
        placa          = dados_cotacao.get("placa", "N/A")
        marca          = dados_cotacao.get("marca", "N/A")
        modelo         = dados_cotacao.get("modelo", "N/A")
        ano            = dados_cotacao.get("ano", "N/A")
        valor_fipe     = dados_cotacao.get("valor_fipe")
        categoria      = dados_cotacao.get("categoria", "N/A")
        precos         = dados_cotacao.get("precos", {})
        veiculo_pesado = dados_cotacao.get("veiculo_pesado", False)
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)
        adesao_valor_str  = format_currency_value_only(precos.get('Adesão'))

        TAMANHO_FONTE_MENSALIDADE = Pt(36)

        # ── SLIDE 1 (índice 0): Nome na capa ──
        logging.info(f"{log_prefix} Preenchendo Slide 1 (índice 0)")
        set_text(find_shape(0, "Nome associado"), nome_cliente)

        # ── SLIDE 4 (índice 3): Dados do veículo ──
        logging.info(f"{log_prefix} Preenchendo Slide 4 (índice 3)")
        set_text(find_shape(3, "Nome associado"), nome_cliente)
        set_text(find_shape(3, "Placa"),          placa)
        set_text(find_shape(3, "Marca carro"),    marca)
        set_text(find_shape(3, "modelo"),         modelo)
        set_text(find_shape(3, "Ano"),            str(ano))
        set_text(find_shape(3, "Categoria"),      categoria)
        set_text(find_shape(3, "Valor fipe"),     format_currency_manual(valor_fipe))

        if veiculo_pesado:
            # ═══════════════════════════════════════════════
            # VEÍCULO PESADO: preenche só o slide Diamante
            # (índice 5) com o valor de Pesados, depois
            # remove os slides Ouro (índice 4) e Platinum
            # (índice 6) — do maior para o menor.
            # ═══════════════════════════════════════════════
            logging.info(f"{log_prefix} Modo PESADO: preenchendo slide Diamante com valores de Pesados")

            preco_pesado_str = format_currency_value_only(precos.get('Pesados'))

            # Slide 6 / índice 5 — Diamante (usado para Pesado)
            set_text(find_shape(5, "adesão"),   adesao_valor_str,   font_size=TAMANHO_FONTE_MENSALIDADE)
            set_text(find_shape(5, "diamante"), preco_pesado_str,   font_size=TAMANHO_FONTE_MENSALIDADE)

            # Remove slides indesejados do maior índice para o menor
            # para não bagunçar os índices durante a remoção
            total = len(prs.slides)
            if total > 6:
                remover_slide(prs, 6)  # Platinum (índice 6)
            if total > 4:
                remover_slide(prs, 4)  # Ouro (índice 4)

        else:
            # ═══════════════════════════════════════════════
            # VEÍCULO NORMAL: preenche os 3 planos
            # ═══════════════════════════════════════════════
            logging.info(f"{log_prefix} Modo NORMAL: preenchendo slides Ouro, Diamante e Platinum")

            # Slide 5 / índice 4 — Ouro
            set_text(find_shape(4, "adesão"), adesao_valor_str,
                     font_size=TAMANHO_FONTE_MENSALIDADE)
            set_text(find_shape(4, "ouro"), format_currency_value_only(precos.get('Plano Ouro')),
                     font_size=TAMANHO_FONTE_MENSALIDADE)

            # Slide 6 / índice 5 — Diamante
            set_text(find_shape(5, "adesão"), adesao_valor_str,
                     font_size=TAMANHO_FONTE_MENSALIDADE)
            set_text(find_shape(5, "diamante"), format_currency_value_only(precos.get('Diamante')),
                     font_size=TAMANHO_FONTE_MENSALIDADE)

            # Slide 7 / índice 6 — Platinum
            set_text(find_shape(6, "adesão"), adesao_valor_str,
                     font_size=TAMANHO_FONTE_MENSALIDADE)
            set_text(find_shape(6, "platinium"), format_currency_value_only(precos.get('Platinum')),
                     font_size=TAMANHO_FONTE_MENSALIDADE)

        if sujeito_aprovacao:
            logging.warning(f"{log_prefix} AVISO: Cotação sujeita à aprovação — definir onde exibir no PPTX.")

        logging.info(f"{log_prefix} Salvando em {output_path}")
        prs.save(output_path)
        logging.info(f"{log_prefix} Salvo com sucesso.")
        return True

    except Exception as e:
        logging.error(f"{log_prefix} ERRO durante o preenchimento: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    pass
