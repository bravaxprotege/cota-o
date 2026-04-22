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

# ── Fontes e tamanhos padronizados ──────────────────────────────────────────
FONTE_PADRAO   = 'Liberation Sans'   # disponível no servidor (instalado no Docker)
TAMANHO_DADOS  = Pt(14)              # campos de texto da ficha do veículo
TAMANHO_PRECO  = Pt(36)              # valores de mensalidade nos slides de planos


def format_currency_manual(value):
    """R$ XXX.XXX,XX"""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


def format_currency_value_only(value):
    """XXX.XXX,XX  (sem R$)"""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"


def set_text(text_frame, text_value,
             font_size=None,
             bold=False,
             alignment=None,
             is_warning=False):
    """
    Escreve texto no campo com formatação 100% uniforme.

    - Usa Liberation Sans como fonte padrão (garantida no servidor).
    - Reseta o espaçamento de caracteres via XML para evitar
      o problema de "M at h e u s" com letras separadas.
    - font_size: usa TAMANHO_DADOS por padrão; pode ser sobrescrito.
    - alignment: preserva o alinhamento do template se não informado.
    """
    if text_frame is None:
        return

    # Lê o alinhamento do template antes de apagar
    tmpl_alignment = alignment
    if tmpl_alignment is None and text_frame.paragraphs:
        tmpl_alignment = text_frame.paragraphs[0].alignment

    tamanho = font_size if font_size is not None else TAMANHO_DADOS

    text_frame.clear()
    p = text_frame.add_paragraph()

    # Alinhamento
    if tmpl_alignment is not None:
        try:
            p.alignment = tmpl_alignment
        except Exception as e:
            logging.warning(f"  Alinhamento não aplicado: {e}")

    # Cria um run explícito para ter controle total da formatação
    run = p.add_run()
    run.text = str(text_value)
    run.font.name  = FONTE_PADRAO
    run.font.size  = tamanho
    run.font.bold  = bold

    if is_warning:
        run.font.bold = True
        run.font.color.rgb = RGBColor(192, 0, 0)

    # ── Reset do espaçamento de caracteres via XML ──────────────────────────
    # Isso corrige o bug de espaços estranhos entre letras ("M at h e u s")
    # que vem de configurações de kerning/tracking herdadas do template.
    try:
        rPr = run._r.get_or_add_rPr()
        rPr.set('spc', '0')          # espaçamento entre caracteres = 0
        rPr.attrib.pop('kern', None)  # remove kerning automático se existir
    except Exception as e:
        logging.warning(f"  Não foi possível resetar espaçamento: {e}")

    logging.info(f"  '{text_value}' → {FONTE_PADRAO} {tamanho.pt}pt bold={bold}")


def remover_slide(prs, slide_index):
    """Remove um slide pelo índice. Sempre remova do maior para o menor."""
    xml_slides = prs.slides._sldIdLst
    rId = xml_slides[slide_index].get(
        '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    )
    prs.part.drop_rel(rId)
    del xml_slides[slide_index]
    logging.info(f"{log_prefix} Slide índice {slide_index} removido.")


def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    logging.info(f"{log_prefix} Iniciando: {template_path}")
    try:
        prs = Presentation(template_path)
        logging.info(f"{log_prefix} Template aberto. Slides: {len(prs.slides)}")

        def find_shape(slide_index, shape_name):
            if slide_index < 0 or slide_index >= len(prs.slides):
                logging.warning(f"{log_prefix} Slide {slide_index} não existe.")
                return None
            for shape in prs.slides[slide_index].shapes:
                if shape.name.strip().lower() == shape_name.strip().lower():
                    if shape.has_text_frame:
                        return shape.text_frame
                    logging.warning(f"{log_prefix} '{shape.name}' sem text frame.")
                    return None
            logging.warning(f"{log_prefix} Shape '{shape_name}' não encontrada no slide {slide_index+1}.")
            return None

        # ── Dados ───────────────────────────────────────────────────────────
        nome_cliente      = dados_cotacao.get("nome_cliente", "N/A")
        placa             = dados_cotacao.get("placa", "N/A").upper()
        marca             = dados_cotacao.get("marca", "N/A").upper()
        modelo            = dados_cotacao.get("modelo", "N/A").upper()
        ano               = dados_cotacao.get("ano", "N/A")
        valor_fipe        = dados_cotacao.get("valor_fipe")
        categoria         = dados_cotacao.get("categoria", "N/A").upper()
        precos            = dados_cotacao.get("precos", {})
        veiculo_pesado    = dados_cotacao.get("veiculo_pesado", False)
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)
        adesao_str        = format_currency_value_only(precos.get('Adesão'))

        # ── Slide 1 / índice 0 — Capa ───────────────────────────────────────
        logging.info(f"{log_prefix} Slide 1 (capa)")
        set_text(find_shape(0, "Nome associado"), nome_cliente)

        # ── Slide 4 / índice 3 — Ficha do veículo ───────────────────────────
        logging.info(f"{log_prefix} Slide 4 (ficha)")
        set_text(find_shape(3, "Nome associado"), nome_cliente.title())
        set_text(find_shape(3, "Placa"),          placa)
        set_text(find_shape(3, "Marca carro"),    marca)
        set_text(find_shape(3, "modelo"),         modelo)
        set_text(find_shape(3, "Ano"),            str(ano))
        set_text(find_shape(3, "Categoria"),      categoria)
        set_text(find_shape(3, "Valor fipe"),     format_currency_manual(valor_fipe), bold=True)

        if veiculo_pesado:
            # ── PESADO: apenas slide Diamante (índice 5) ────────────────────
            logging.info(f"{log_prefix} Modo PESADO")
            preco_pesado_str = format_currency_value_only(precos.get('Pesados'))
            set_text(find_shape(5, "adesão"),   adesao_str,       font_size=TAMANHO_PRECO, bold=True)
            set_text(find_shape(5, "diamante"), preco_pesado_str, font_size=TAMANHO_PRECO, bold=True)
            # Remove Platinum (índice 6) e Ouro (índice 4) — maior primeiro
            total = len(prs.slides)
            if total > 6: remover_slide(prs, 6)
            if total > 4: remover_slide(prs, 4)

        else:
            # ── NORMAL: 3 planos ────────────────────────────────────────────
            logging.info(f"{log_prefix} Modo NORMAL")

            # Ouro — índice 4
            set_text(find_shape(4, "adesão"), adesao_str,
                     font_size=TAMANHO_PRECO, bold=True)
            set_text(find_shape(4, "ouro"),
                     format_currency_value_only(precos.get('Plano Ouro')),
                     font_size=TAMANHO_PRECO, bold=True)

            # Diamante — índice 5
            set_text(find_shape(5, "adesão"), adesao_str,
                     font_size=TAMANHO_PRECO, bold=True)
            set_text(find_shape(5, "diamante"),
                     format_currency_value_only(precos.get('Diamante')),
                     font_size=TAMANHO_PRECO, bold=True)

            # Platinum — índice 6
            set_text(find_shape(6, "adesão"), adesao_str,
                     font_size=TAMANHO_PRECO, bold=True)
            set_text(find_shape(6, "platinium"),
                     format_currency_value_only(precos.get('Platinum')),
                     font_size=TAMANHO_PRECO, bold=True)

        if sujeito_aprovacao:
            logging.warning(f"{log_prefix} Cotação sujeita à aprovação — shape não definida.")

        prs.save(output_path)
        logging.info(f"{log_prefix} Salvo em {output_path}")
        return True

    except Exception as e:
        logging.error(f"{log_prefix} ERRO: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    pass
