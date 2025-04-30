# ----- INÍCIO DO CÓDIGO PARA preenche_cotacao.py -----
import sys
# Linha específica do ambiente Render/Manus, pode manter se necessário
sys.path.append("/opt/.manus/.sandbox-runtime") 
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import traceback # Importar para log de erros
import os # Importar OS para o bloco de teste funcionar

# --- Função Auxiliar para Formatar Moeda ---
def format_currency_manual(value):
    """Formata um valor numérico como moeda brasileira (R$) manualmente."""
    if value is None or not isinstance(value, (int, float)):
        return "N/A"
    try:
        # Formatação manual para R$ 1.234,56
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "Valor inválido"

# --- Função Principal Modificada ---
def preencher_cotacao_pptx(template_path, output_path, dados_cotacao):
    """Preenche um template PowerPoint com dados da cotação em slides específicos e salva."""
    
    print(f"Iniciando preenchimento com template: {template_path}")
    print(f"Dados recebidos: {dados_cotacao}")

    try:
        prs = Presentation(template_path)
        
        # --- Funções Auxiliares Internas ---
        def find_shape(slide_index, shape_name_to_find):
            """Encontra uma forma pelo nome em um slide específico."""
            if slide_index < 0 or slide_index >= len(prs.slides):
                print(f"AVISO: Slide com índice {slide_index} (número {slide_index+1}) não existe no template.")
                return None
            slide = prs.slides[slide_index]
            for shape in slide.shapes:
                # Comparar nomes ignorando maiúsculas/minúsculas e espaços extras? (Mais robusto)
                if shape.name.strip().lower() == shape_name_to_find.strip().lower(): 
                    if shape.has_text_frame:
                        print(f"  Encontrada forma '{shape.name}' (buscando por '{shape_name_to_find}') no slide {slide_index+1}.")
                        return shape.text_frame
                    else:
                        print(f"AVISO: Forma '{shape.name}' no slide {slide_index+1} não tem frame de texto.")
                        return None
            print(f"AVISO: Forma com nome parecido com '{shape_name_to_find}' não encontrada no slide {slide_index+1}.")
            return None

        def set_text(text_frame, text_value, font_size=Pt(10), is_warning=False):
             """Define o texto em um text_frame, limpando o anterior."""
             if text_frame is None:
                 # O Aviso já foi dado por find_shape, não precisa repetir aqui
                 # Apenas não faz nada se a forma não foi encontrada
                 return 
             
             print(f"  Definindo texto '{text_value}' na forma '{text_frame.parent.name}'...") # Log um pouco melhor
             text_frame.clear()
             p = text_frame.add_paragraph()
              # Define o texto diretamente no parágrafo (melhor para formatação geral)
             p.text = str(text_value)
             # Ajusta a fonte para todo o parágrafo
             p.font.size = font_size
             if is_warning:
                 p.font.bold = True
                 p.font.color.rgb = RGBColor(192, 0, 0) # Vermelho escuro


        # --- Extração dos Dados ---
        nome_cliente = dados_cotacao.get("nome_cliente", "N/A")
        placa = dados_cotacao.get("placa", "N/A")
        marca = dados_cotacao.get("marca", "N/A")
        modelo = dados_cotacao.get("modelo", "N/A")
        ano = dados_cotacao.get("ano", "N/A")
        valor_fipe = dados_cotacao.get("valor_fipe")
        categoria = dados_cotacao.get("categoria", "N/A")
        precos = dados_cotacao.get("precos", {})
        sujeito_aprovacao = precos.get("sujeito_aprovacao", False)

        # --- Preenchimento Slide por Slide (Usando os nomes que você passou) ---
        
        # Slide 1 (Índice 0)
        print("\n--- Preenchendo Slide 1 (Índice 0) ---")
        tf = find_shape(0, "Nome associado") 
        set_text(tf, nome_cliente) 

        # Slide 4 (Índice 3)
        print("\n--- Preenchendo Slide 4 (Índice 3) ---")
        tf = find_shape(3, "Nome associado") 
        set_text(tf, nome_cliente)
        tf = find_shape(3, "Placa") 
        set_text(tf, placa)
        tf = find_shape(3, "Marca carro") # Confirmar nome exato da shape
        set_text(tf, marca)
        tf = find_shape(3, "modelo") # Confirmar nome exato da shape (está minúsculo?)
        set_text(tf, modelo)
        tf = find_shape(3, "Ano") # Confirmar nome exato da shape
        set_text(tf, str(ano)) 
        tf = find_shape(3, "Categoria") # Confirmar nome exato da shape
        set_text(tf, categoria)
        tf = find_shape(3, "Valor fipe") # Confirmar nome exato da shape (tem espaço?)
        set_text(tf, format_currency_manual(valor_fipe))

        # OBS: ASSUMINDO que a chave para o preço da Adesão nos dados é 'Adesão'
        adesao_valor = format_currency_manual(precos.get('Adesão'))
        
        # Slide 5 (Índice 4) - Plano Ouro 
        print("\n--- Preenchendo Slide 5 (Índice 4) - Plano Ouro ---")
        # ASSUMINDO que a chave para o preço do Plano Ouro nos dados é 'Plano Ouro'
        tf = find_shape(4, "adesão") # Confirmar nome exato da shape (está minúsculo?)
        set_text(tf, adesao_valor) 
        tf = find_shape(4, "ouro") # Confirmar nome exato da shape (está minúsculo?)
        set_text(tf, format_currency_manual(precos.get('Plano Ouro'))) 

        # Slide 6 (Índice 5) - Plano Diamante
        print("\n--- Preenchendo Slide 6 (Índice 5) - Plano Diamante ---")
        # ASSUMINDO que a chave para o preço do Plano Diamante nos dados é 'Diamante'
        tf = find_shape(5, "adesão") # Confirmar nome exato da shape (está minúsculo?)
        set_text(tf, adesao_valor) 
        tf = find_shape(5, "diamante") # Confirmar nome exato da shape (está minúsculo?)
        set_text(tf, format_currency_manual(precos.get('Diamante')))

        # Slide 7 (Índice 6) - Plano Platinum
        print("\n--- Preenchendo Slide 7 (Índice 6) - Plano Platinum ---")
        # ASSUMINDO que a chave para o preço do Plano Platinum nos dados é 'Platinum'
        tf = find_shape(6, "adesão") # Confirmar nome exato da shape (está minúsculo?)
        set_text(tf, adesao_valor) 
        tf = find_shape(6, "platinium") # Confirmar nome exato da shape (é 'platinium' ou 'platinum'?)
        set_text(tf, format_currency_manual(precos.get('Platinum'))) 
        
        # --- PONTOS FALTANDO ---
        # 1. Plano Pesados: Onde ele deve ir (slide e nome da shape)?
        preco_pesados = format_currency_manual(precos.get('Pesados'))
        print(f"Valor Pesados (não inserido): {preco_pesados}")
        # Exemplo: tf_pesados = find_shape(INDICE_SLIDE_PESADOS, "NOME_SHAPE_PESADOS")
        #         set_text(tf_pesados, preco_pesados)
        
        # 2. Aviso de Aprovação: Onde ele deve ir (slide e nome da shape)?
        if sujeito_aprovacao:
             print("AVISO: Cotação sujeita à aprovação (local para inserir não definido).")
             # Exemplo: tf_aviso = find_shape(INDICE_SLIDE_AVISO, "NOME_SHAPE_AVISO")
             #         set_text(tf_aviso, "*Sujeito à aprovação da diretoria*", is_warning=True)


        print("\n--- Salvando apresentação ---")
        prs.save(output_path)
        print(f"Cotação salva com sucesso em: {output_path}")
        return True

    # except FileNotFoundError: # Não deve mais ocorrer se o path e nome estiverem certos
    #     print(f"Erro CRÍTICO: Template não encontrado em {template_path}")
    #     return False
    except Exception as e:
        print(f"ERRO GERAL ao preencher o PowerPoint: {e}")
        traceback.print_exc() # Imprime o traceback detalhado no log
        return False

# --- Bloco de Teste (Não essencial para o Render, mas útil para teste local) ---
if __name__ == "__main__":
    try:
        # Tenta importar a função de cálculo de preços que deve estar no mesmo nível
        from calculo_precos import calcular_precos_planos 
        print("INFO: Função calcular_precos_planos importada para teste.")
    except ImportError:
         print("AVISO: calculo_precos.py não encontrado ou erro na importação para teste local.")
         calcular_precos_planos = None # Define como None para evitar erro abaixo

    if calcular_precos_planos: # Só executa se conseguiu importar
         # Dados de exemplo 
         valores_fipe_teste = [74442.0, 105000.0]
         # Caminhos relativos ao script preenche_cotacao.py se executado diretamente
         # Assume que input_files está um nível ACIMA de onde este script está, 
         # ou no mesmo nível se você rodar da raiz do projeto. 
         # Ajuste se necessário para seu teste local.
         arquivo_tabela = os.path.join("..", "input_files", "Tabela 2023.xlsx") 
         template_pptx = os.path.join("..", "input_files", "cotacao_auto.pptx") # Usar o nome SEM acento

         # Tenta criar uma pasta output no diretório atual para os testes
         output_dir_teste = "./output_teste_local"
         os.makedirs(output_dir_teste, exist_ok=True)
         
         for i, valor_fipe_teste in enumerate(valores_fipe_teste):
             placa_teste = f"XYZ123{i}"
             # Salvar output na pasta de teste criada
             output_pptx = os.path.join(output_dir_teste, f"cotacao_{placa_teste}_teste.pptx") 

             print(f"\n--- Testando Preenchimento com FIPE: {valor_fipe_teste} ---")
             
             # Verifica se arquivos de teste existem ANTES de calcular
             if not os.path.exists(arquivo_tabela):
                 print(f"ERRO no teste: Arquivo Tabela não encontrado em {arquivo_tabela}")
                 continue
             if not os.path.exists(template_pptx):
                  print(f"ERRO no teste: Arquivo Template não encontrado em {template_pptx}")
                  continue

             print(f"Calculando preços para FIPE: {valor_fipe_teste}")
             precos_calculados = calcular_precos_planos(valor_fipe_teste, arquivo_tabela)

            # (Isso ainda está dentro do 'for i, valor_fipe_teste...' no seu código)
            # Certifique-se que a linha abaixo está com 2 níveis de indentação (8 espaços)
            if precos_calculados: 
                # As linhas abaixo devem ter 3 níveis de indentação (12 espaços)
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
                # Este 'if' deve ter 3 níveis de indentação (12 espaços)
                if sucesso: 
                    # As linhas abaixo devem ter 4 níveis de indentação (16 espaços)
                    print(f"Preenchimento do PowerPoint para {placa_teste} concluído com sucesso.") 
                    print(f"Arquivo de teste salvo em: {os.path.abspath(output_pptx)}") 
                # Este 'else' deve estar alinhado com o 'if sucesso:' (3 níveis / 12 espaços)
                else: 
                    # A linha abaixo deve ter 4 níveis de indentação (16 espaços)
                    print(f"Falha ao preencher o PowerPoint para {placa_teste}.") 
            # Este 'else' deve estar alinhado com o 'if precos_calculados:' (2 níveis / 8 espaços)
            else: 
                # A linha abaixo deve ter 3 níveis de indentação (12 espaços)
                print("Não foi possível calcular os preços para preencher o PowerPoint.") 

    # Este 'else' final deve estar alinhado com 'if calcular_precos_planos:' lá do início do bloco __main__ (1 nível / 4 espaços)
    else: 
        # A linha abaixo deve ter 2 níveis de indentação (8 espaços)
        print("Pular teste local pois calculo_precos não foi importado.")

# ----- FIM DO CÓDIGO PARA preenche_cotacao.py ----- 
# !!! APAGUE QUALQUER LINHA DE CÓDIGO QUE ESTIVER ABAIXO DESTE COMENTÁRIO !!!
