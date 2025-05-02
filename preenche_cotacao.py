import sys
sys.path.append("/opt/.manus/.sandbox-runtime")
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

def format_currency_manual(value):
    """Formata um valor numérico como moeda brasileira (R$) manualmente."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        # Formatação manual para R$ 1.234,56
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"

def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    """Preenche um template PowerPoint com dados da cotação e salva.

    Args:
        template_path (str): Caminho para o arquivo de template .pptx.
        output_path (str): Caminho para salvar o arquivo .pptx preenchido.
        dados_cotacao (dict): Dicionário contendo os dados da cotação, incluindo:
            - nome_cliente (str)
            - placa (str)
            - marca (str)
            - modelo (str)
            - ano (int or str)
            - valor_fipe (float)
            - categoria (str, opcional)
            - precos (dict): Dicionário com os preços calculados dos planos 
                             (e.g., {"Adesão": 150.0, "Plano Ouro": 87.1, ..., "sujeito_aprovacao": False})
    """
    try:
        prs = Presentation(template_path)
        
        if len(prs.slides) < 8:
            print("Erro: O template não tem 8 slides.")
            return False
            
        slide = prs.slides[7] # Slide 8 (índice 7)
        
        # Extrair dados do dicionário
        nome_cliente = dados_cotacao.get("nome_cliente", "Nome não informado")
        placa = dados_cotacao.get("placa", "Placa não informada")
        marca = dados_cotacao.get("marca", "")
        modelo = dados_cotacao.get("modelo", "")
        ano = dados_cotacao.get("ano", "")
        valor_fipe = dados_cotacao.get("valor_fipe")
        categoria = dados_cotacao.get("categoria", "N/A") # Categoria pode não ser fornecida
        precos = dados_cotacao.get("precos", {})
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)
        
        # Construir texto dos preços (Corrigido: usar aspas simples para chaves do dicionário)
        texto_precos = (
            f"Adesão: {format_currency_manual(precos.get('Adesão'))}\n"
            f"Plano Ouro: {format_currency_manual(precos.get('Plano Ouro'))}\n"
            f"Plano Diamante: {format_currency_manual(precos.get('Diamante'))}\n"
            f"Plano Platinum: {format_currency_manual(precos.get('Platinum'))}\n"
            f"Plano Pesados: {format_currency_manual(precos.get('Pesados'))}"
        )
        
        # Adicionar aviso se necessário
        aviso_aprovacao = "\n\n*Sujeito à aprovação da diretoria*" if sujeito_aprovacao else ""
        
        # Mapeamento de nomes de formas para dados
        mapeamento = {
            "CaixaDeTexto 6": nome_cliente,
            "CaixaDeTexto 7": placa,
            "CaixaDeTexto 8": f"{marca} {modelo} {ano}".strip(),
            "CaixaDeTexto 9": f"Valor FIPE: {format_currency_manual(valor_fipe)} | Categoria: {categoria}",
            "CaixaDeTexto 10": texto_precos + aviso_aprovacao
        }

        formas_encontradas = {shape.name: False for shape in slide.shapes if shape.name in mapeamento}

        for shape in slide.shapes:
            if shape.name in mapeamento:
                if shape.has_text_frame:
                    text_frame = shape.text_frame
                    text_frame.clear()
                    p = text_frame.add_paragraph()
                    
                    # Dividir o texto em linhas se contiver \n
                    lines = mapeamento[shape.name].split("\n")
                    first_line = True
                    for line in lines:
                        run = p.add_run()
                        run.text = line
                        # Definir tamanho da fonte (ajustar conforme necessário)
                        run.font.size = Pt(10)
                        
                        # Colocar aviso em vermelho e negrito
                        if sujeito_aprovacao and line.startswith("*Sujeito"):
                            run.font.bold = True
                            run.font.color.rgb = RGBColor(192, 0, 0) # Vermelho escuro
                            
                        # Adicionar quebra de linha (exceto para a última linha)
                        if line != lines[-1]:
                             run.text += "\n"
                             
                    formas_encontradas[shape.name] = True
                    print(f"Preenchendo Forma: {shape.name}")
                else:
                    print("Aviso: Forma encontrada, mas não possui frame de texto.")

        for nome, encontrada in formas_encontradas.items():
            if not encontrada:
                print("Aviso: Forma não encontrada ou não preenchida no slide 8.")

        prs.save(output_path)
        print(f"Cotação salva em: {output_path}")
        return True

    except FileNotFoundError:
        print(f"Erro: Template não encontrado em {template_path}")
        return False
    except Exception as e:
        print(f"Erro ao preencher o PowerPoint: {e}")
        import traceback
        traceback.print_exc()
        return False

# Exemplo de uso (será chamado de outro script posteriormente)
if __name__ == "__main__":
    from calculo_precos import calcular_precos_planos

    # Dados de exemplo (simulando entrada manual + cálculo)
    valores_fipe_teste = [74442.0, 105000.0]
    arquivo_tabela = "input_files/Tabela 2023.xlsx" # Ajustado para usar input_files
    template_pptx = "input_files/Cotação auto.pptx" # Ajustado para usar input_files
    
    for i, valor_fipe_teste in enumerate(valores_fipe_teste):
        placa_teste = f"XYZ123{i}"
        output_pptx = f"/home/ubuntu/projeto_cotacao/cotacao_{placa_teste}_teste.pptx"

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
                print(f"Preenchimento do PowerPoint para {placa_teste} concluído com sucesso.")
            else:
                print(f"Falha ao preencher o PowerPoint para {placa_teste}.")
        else:
            print("Não foi possível calcular os preços para preencher o PowerPoint.")
