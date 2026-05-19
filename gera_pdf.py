"""
gera_pdf.py
-----------
Gera o PDF de cotação diretamente de um template HTML usando WeasyPrint.
Substitui o pipeline PPTX → LibreOffice → PDF.

Vantagens:
  - Fontes renderizadas com precisão (Arial Black via @font-face)
  - Posicionamento exato em cm (mesmos valores extraídos do PPTX)
  - Sem conversão intermediária, sem artefatos do LibreOffice
"""

import os
import glob
import logging
from jinja2 import Environment, FileSystemLoader

log = logging.getLogger(__name__)

# Diretório raiz do projeto (onde este arquivo está)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _bg_images():
    """
    Escaneia static/slides/ e retorna um dict {numero_slide: caminho_relativo}.
    Ex: {1: 'static/slides/slide1_Imagem_1_xxxx.png', ...}
    """
    slides_dir = os.path.join(BASE_DIR, 'static', 'slides')
    mapping = {}
    for ext in ('*.png', '*.jpg', '*.jpeg'):
        for fpath in glob.glob(os.path.join(slides_dir, ext)):
            name = os.path.basename(fpath)
            try:
                num = int(name.split('_')[0].replace('slide', ''))
                mapping[num] = f'static/slides/{name}'
            except (ValueError, IndexError):
                pass
    return mapping


def _fmt_valor(value):
    """R$ X.XXX,XX"""
    if value is None or not isinstance(value, (int, float)):
        return 'N/A'
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_preco(value):
    """X.XXX,XX (sem R$)"""
    if value is None or not isinstance(value, (int, float)):
        return 'N/A'
    return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def gerar_pdf_cotacao(dados_cotacao, output_path):
    """
    Recebe os dados da cotação (mesmo dict usado antes no preenche_cotacao.py)
    e gera o PDF em output_path via WeasyPrint.

    Retorna True em caso de sucesso, False em caso de erro.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        log.error("WeasyPrint não instalado. Execute: pip install weasyprint")
        return False

    try:
        # ── Extrai dados ──────────────────────────────────────────────────
        nome_cliente   = dados_cotacao.get('nome_cliente', 'N/A')
        placa          = dados_cotacao.get('placa', 'N/A').upper()
        marca          = dados_cotacao.get('marca', 'N/A').upper()
        modelo         = dados_cotacao.get('modelo', 'N/A').upper()
        ano            = str(dados_cotacao.get('ano', 'N/A'))
        valor_fipe     = dados_cotacao.get('valor_fipe')
        categoria      = dados_cotacao.get('categoria', 'PASSEIO') or 'PASSEIO'
        veiculo_pesado = dados_cotacao.get('veiculo_pesado', False)
        precos         = dados_cotacao.get('precos', {})

        adesao         = _fmt_preco(precos.get('Adesão'))
        preco_ouro     = _fmt_preco(precos.get('Plano Ouro'))
        preco_diamante = _fmt_preco(precos.get('Diamante'))
        preco_platinum = _fmt_preco(precos.get('Platinum'))
        preco_pesado   = _fmt_preco(precos.get('Pesados'))
        valor_fipe_fmt = _fmt_valor(valor_fipe)

        bg = _bg_images()
        if not bg:
            log.error("Imagens de fundo não encontradas em static/slides/. "
                      "Execute o extrator de imagens do PPTX.")
            return False

        # ── Renderiza o template Jinja2 ───────────────────────────────────
        env = Environment(
            loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')),
            autoescape=False,
        )
        template = env.get_template('cotacao_pdf.html')

        html_str = template.render(
            nome_cliente   = nome_cliente.title(),
            placa          = placa,
            marca          = marca,
            modelo         = modelo,
            ano            = ano,
            categoria      = categoria.upper(),
            valor_fipe_fmt = valor_fipe_fmt,
            veiculo_pesado = veiculo_pesado,
            adesao         = adesao,
            preco_ouro     = preco_ouro,
            preco_diamante = preco_diamante,
            preco_platinum = preco_platinum,
            preco_pesado   = preco_pesado,
            bg             = bg,
        )

        # ── Converte para PDF ─────────────────────────────────────────────
        # base_url aponta para BASE_DIR para que caminhos relativos
        # (static/slides/..., fonts/...) sejam resolvidos corretamente.
        base_url = f'file://{BASE_DIR}/'
        HTML(string=html_str, base_url=base_url).write_pdf(output_path)

        if os.path.exists(output_path):
            log.info(f"[gera_pdf] PDF gerado com sucesso: {output_path}")
            return True
        else:
            log.error("[gera_pdf] WeasyPrint não gerou o arquivo.")
            return False

    except Exception as e:
        log.exception(f"[gera_pdf] Erro ao gerar PDF: {e}")
        return False
