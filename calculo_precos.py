# ----- INÍCIO DO CÓDIGO PARA calculo_precos.py COM LOGS ADICIONAIS -----
import pandas as pd
import sys
import numpy as np # numpy não parece ser usado, mas mantido por enquanto
import traceback # Para log de erro
import os # Importar OS para o bloco de teste funcionar

# sys.path.append("/opt/.manus/.sandbox-runtime") # Remover ou comentar se não for necessário

def calcular_precos_planos(valor_fipe, arquivo_tabela):
    """Calcula os preços dos planos com base no valor FIPE do veículo."""
    print(f"\n[calculo_precos] Iniciando cálculo para FIPE: {valor_fipe} usando Tabela: {arquivo_tabela}")
    
    try:
        # Ler a planilha de preços
        print("[calculo_precos] Lendo arquivo Excel...")
        if not os.path.exists(arquivo_tabela):
             print(f"[calculo_precos] ERRO CRÍTICO IMEDIATO: Arquivo de tabela NÃO EXISTE em {arquivo_tabela}")
             return None # Retorna None imediatamente se o arquivo não existe
        df = pd.read_excel(arquivo_tabela)
        print(f"[calculo_precos] Leitura concluída. DataFrame shape: {df.shape}")
        
        # --- Lógica para encontrar cabeçalho (mantida, mas pode ser frágil) ---
        valor_veiculo_idx = None
        # Procurar a linha que contém "VALOR DO VEÍCULO" ou similar
        print("[calculo_precos] Procurando linha do cabeçalho por 'VALOR DO VEÍCULO'...")
        for idx, row in df.iterrows():
            for col in row:
                # Verifica se col é string antes de chamar 'in'
                if isinstance(col, str) and "VALOR DO VEÍCULO" in col.upper(): # Comparar em maiúsculas
                    valor_veiculo_idx = idx
                    print(f"[calculo_precos] Encontrado 'VALOR DO VEÍCULO' na linha índice {idx}")
                    break
            if valor_veiculo_idx is not None:
                break
                
        if valor_veiculo_idx is None:
            print("[calculo_precos] Não encontrou por 'VALOR DO VEÍCULO'. Procurando por 'PLANO OURO'...")
            # Tentar encontrar a linha com os nomes dos planos como fallback
            for idx, row in df.iterrows():
                # Verifica se é string antes de chamar upper()
                if "PLANO OURO" in [str(x).upper() for x in row if isinstance(x, str)]:
                    valor_veiculo_idx = idx
                    print(f"[calculo_precos] Fallback: Usando linha {idx} como cabeçalho (contém PLANO OURO).")
                    break
                    
        if valor_veiculo_idx is None:
            print("[calculo_precos] ERRO CRÍTICO: Estrutura da tabela não identificada (cabeçalho não encontrado).")
            return None # Retorna None se não achar o cabeçalho
            
        print(f"[calculo_precos] Linha de cabeçalho identificada (ou fallback): Índice {valor_veiculo_idx}")
        colunas = df.iloc[valor_veiculo_idx].tolist()
        print(f"[calculo_precos] Nomes das colunas brutos lidos da linha {valor_veiculo_idx}: {colunas}")

        # --- Processamento do DataFrame ---
        dados_df = df.iloc[valor_veiculo_idx+1:].reset_index(drop=True)
        
        # Mapear nomes das colunas
        colunas_necessarias = ["faixa_valor", "adesao", "plano_ouro", "plano_diamante", "plano_platinum", "pesados"]
        col_names = []
        keywords_map = {
            "faixa_valor": ["VALOR", "VEÍCULO"],
            "adesao": ["ADESAO", "ADESÃO"],
            "plano_ouro": ["OURO"],
            "plano_diamante": ["DIAMANTE"],
            "plano_platinum": ["PLATINUM"],
            "pesados": ["PESADOS"]
        }
        mapped_cols = {name: None for name in colunas_necessarias}

        print("[calculo_precos] Mapeando nomes das colunas por keywords...")
        for i, col_header in enumerate(colunas):
            header_str = str(col_header).upper()
            found_map = False
            for target_name, keywords in keywords_map.items():
                 if mapped_cols[target_name] is None: # Mapeia apenas uma vez
                     if any(keyword in header_str for keyword in keywords):
                         col_names.append(target_name)
                         mapped_cols[target_name] = i # Guarda o índice original
                         print(f"  - Mapeado '{col_header}' (Índice {i}) para '{target_name}'")
                         found_map = True
                         break
            if not found_map:
                 col_names.append(f"desconhecida_{i}")
                 print(f"  - Coluna '{col_header}' (Índice {i}) não mapeada.")
        
        # Aplicar nomes ao dataframe de dados
        if len(col_names) >= dados_df.shape[1]:
            dados_df.columns = col_names[:dados_df.shape[1]]
            print(f"[calculo_precos] Nomes das colunas aplicados: {dados_df.columns.tolist()}")
        else:
             print(f"[calculo_precos] ERRO: Discrepância entre número de colunas lidas ({len(colunas)}) e colunas de dados ({dados_df.shape[1]})")
             print(f"[calculo_precos] Colunas mapeadas: {col_names}")
             return None

        # Verificar se colunas essenciais foram mapeadas
        colunas_faltantes = [name for name, index in mapped_cols.items() if index is None]
        if colunas_faltantes:
            print(f"[calculo_precos] AVISO: Colunas essenciais não encontradas pelo nome: {colunas_faltantes}. A aplicação pode falhar.")
            # Poderia retornar None aqui se colunas como 'faixa_valor' faltarem

        # Remover linhas com NaN em 'faixa_valor' (se a coluna existir)
        if "faixa_valor" in dados_df.columns:
            print(f"[calculo_precos] Shape antes de dropna('faixa_valor'): {dados_df.shape}")
            dados_df = dados_df.dropna(subset=["faixa_valor"])
            print(f"[calculo_precos] Shape depois de dropna('faixa_valor'): {dados_df.shape}")
        else:
             print("[calculo_precos] ERRO: Coluna 'faixa_valor' não encontrada após mapeamento.")
             return None

        if dados_df.empty:
            print("[calculo_precos] ERRO: DataFrame vazio após limpar linhas sem faixa de valor.")
            return None

        # Converter valores para numérico
        for col in ["adesao", "plano_ouro", "plano_diamante", "plano_platinum", "pesados"]:
            if col in dados_df.columns:
                print(f"[calculo_precos] Convertendo coluna '{col}' para numérico.")
                dados_df[col] = pd.to_numeric(dados_df[col], errors='coerce')
                # Verificar se há NaNs após conversão (indicaria texto/formato inválido na coluna)
                if dados_df[col].isnull().any():
                     print(f"[calculo_precos] AVISO: Valores não numéricos encontrados na coluna '{col}' e convertidos para NaN.")
            else:
                 print(f"[calculo_precos] AVISO: Coluna '{col}' esperada não encontrada para conversão numérica.")

        # --- Lógica de Cálculo ---
        valor_excedente = 0.0
        percentual_adicional = 0.0
        sujeito_aprovacao = False
        
        if valor_fipe > 100000.0:
            print(f"[calculo_precos] Valor FIPE {valor_fipe} > 100k. Aplicando regra especial.")
            valor_excedente = valor_fipe - 100000.0
            percentual_adicional = int(valor_excedente / 1000.0) # 1% a cada 1000
            sujeito_aprovacao = True
            print(f"[calculo_precos] Valor excedente: {valor_excedente}, Percentual Adicional: {percentual_adicional}%")
            
            # Usar a última linha como base
            if not dados_df.empty:
                 faixa_encontrada = dados_df.iloc[-1]
                 print(f"[calculo_precos] Usando última linha (Índice {faixa_encontrada.name}) como base: Faixa '{faixa_encontrada.get('faixa_valor', 'N/A')}'")
            else:
                 print("[calculo_precos] ERRO: Tabela vazia, não é possível calcular para FIPE > 100k.")
                 return None 
        else:
            # --- Loop Principal para Encontrar a Faixa ---
            print(f"[calculo_precos] Procurando faixa para FIPE: {valor_fipe}")
            faixa_encontrada = None
            for idx, row in dados_df.iterrows():
                faixa = row["faixa_valor"]
                print(f"[calculo_precos]  Verificando Linha índice: {idx}, Faixa: '{faixa}'")
                if isinstance(faixa, str) and "-" in faixa:
                    min_valor, max_valor = None, None
                    try:
                        # Limpeza mais robusta
                        faixa_limpa = str(faixa).replace("R$", "").strip()
                        valores = faixa_limpa.split("-")
                        if len(valores) == 2:
                            # Limpa pontos de milhar e troca vírgula decimal por ponto
                            min_valor_str = valores[0].replace(".", "").replace(",", ".").strip()
                            max_valor_str = valores[1].replace(".", "").replace(",", ".").strip()
                            min_valor = float(min_valor_str)
                            max_valor = float(max_valor_str)
                            print(f"[calculo_precos]    Faixa parseada: min={min_valor}, max={max_valor}")
                        else:
                             print(f"[calculo_precos]    AVISO: Faixa '{faixa}' não tem formato min-max esperado após split.")
                             continue 
                             
                    except ValueError as e:
                        print(f"[calculo_precos]    ERRO ao converter valores da faixa '{faixa}' para float: {e}")
                        continue 
                    except Exception as e_parse:
                         print(f"[calculo_precos]    ERRO inesperado ao parsear faixa '{faixa}': {e_parse}")
                         continue

                    # Comparação
                    if min_valor is not None and max_valor is not None:
                        # Ajuste pequeno para garantir inclusão correta (ex: 0.01 a 100.00 inclui 100.00)
                        # A comparação original min_valor <= valor_fipe <= max_valor ESTÁ CORRETA.
                        # Não precisa de ajuste epsilon se os limites forem xxx.01 a yyy.00
                        comparacao = min_valor <= valor_fipe <= max_valor
                        print(f"[calculo_precos]    Comparando: {min_valor} <= {valor_fipe} <= {max_valor} -> {comparacao}")
                        if comparacao:
                            faixa_encontrada = row
                            print(f"[calculo_precos]    >>> Faixa ENCONTRADA! Índice da linha no DataFrame original: {idx}")
                            break 
                    else:
                         print("[calculo_precos]    AVISO: min_valor ou max_valor não puderam ser definidos para comparação.")

            # Fallback se nenhuma faixa exata foi encontrada
            if faixa_encontrada is None:
                print(f"[calculo_precos] Nenhuma faixa exata encontrada para FIPE {valor_fipe}.")
                # Manter fallback para última linha, mas só se valor > 0
                if not dados_df.empty and valor_fipe > 0:
                     # Verificar se o valor FIPE é MAIOR que o máximo da última faixa?
                     # Isso pode indicar que ele realmente não deveria ter preço.
                     # Vamos pegar a última faixa para análise:
                     ultima_faixa_row = dados_df.iloc[-1]
                     ultima_faixa_str = ultima_faixa_row.get("faixa_valor", "")
                     max_ultima_faixa = None
                     try:
                         if isinstance(ultima_faixa_str, str) and "-" in ultima_faixa_str:
                             max_str = ultima_faixa_str.split("-")[1].replace("R$", "").replace(".", "").replace(",", ".").strip()
                             max_ultima_faixa = float(max_str)
                     except: 
                         pass # Ignora erro ao parsear a última faixa para este check

                     # Se o valor FIPE for maior que o limite máximo da tabela, retornar erro?
                     if max_ultima_faixa is not None and valor_fipe > max_ultima_faixa:
                           print(f"[calculo_precos] ERRO: Valor FIPE {valor_fipe} é MAIOR que o limite máximo da tabela ({max_ultima_faixa}).")
                           return None # Retorna None -> Causa o erro "Não foi possível encontrar..." no app.py intencionalmente.
                     else:
                          # Se não for maior que o limite (ou não conseguimos verificar), mantém o fallback
                          faixa_encontrada = ultima_faixa_row
                          print(f"[calculo_precos] ATENÇÃO: Usando a ÚLTIMA faixa da tabela como fallback: '{ultima_faixa_str}'")

                elif valor_fipe <= 0:
                     print("[calculo_precos] ERRO: Valor FIPE inválido ou zero.")
                     return None
                else:
                    # Isso só aconteceria se dropna limpasse TUDO
                    print("[calculo_precos] ERRO CRÍTICO: Não há faixas válidas na tabela para usar como fallback.")
                    return None 

        # --- Extração dos Preços ---
        print(f"[calculo_precos] Extraindo preços da linha encontrada (Índice original: {faixa_encontrada.name if faixa_encontrada is not None else 'Nenhum'})")
        precos = {}
        if faixa_encontrada is not None:
            for plano, coluna in [
                ("Adesão", "adesao"),
                ("Plano Ouro", "plano_ouro"),
                ("Diamante", "plano_diamante"),
                ("Platinum", "plano_platinum"),
                ("Pesados", "pesados")
            ]:
                # Verifica se a coluna realmente existe ANTES de tentar acessá-la
                if coluna in faixa_encontrada.index:
                    valor_na_celula = faixa_encontrada[coluna]
                    # Verifica se não é NaN (resultado de to_numeric com erro ou célula vazia)
                    if not pd.isna(valor_na_celula):
                        try:
                            valor_base = float(valor_na_celula)
                            print(f"[calculo_precos]   {plano} ({coluna}): Valor base lido = {valor_base}")
                             
                            if sujeito_aprovacao and plano != "Adesão":
                                valor_ajustado = valor_base * (1 + percentual_adicional / 100.0)
                                print(f"[calculo_precos]     + {percentual_adicional}% = {valor_ajustado}")
                                precos[plano] = valor_ajustado
                            else:
                                precos[plano] = valor_base
                        except Exception as e_conv:
                             print(f"[calculo_precos]   ERRO ao converter valor para {plano} ({coluna}): '{valor_na_celula}' -> {e_conv}")
                             precos[plano] = 0.0 # Define 0.0 se a conversão falhar
                    else:
                        print(f"[calculo_precos]   AVISO: Valor NULO/NaN encontrado na coluna '{coluna}' para o plano '{plano}'. Definindo preço como 0.0")
                        precos[plano] = 0.0
                else:
                    print(f"[calculo_precos]   AVISO: Coluna '{coluna}' não encontrada na linha selecionada para o plano '{plano}'. Definindo preço como 0.0")
                    precos[plano] = 0.0
        else:
             print("[calculo_precos] ERRO: Nenhuma linha/faixa encontrada para extrair preços (faixa_encontrada is None).")
             return None # Retorna None explicitamente

        # Adicionar informações extras
        precos["valor_excedente"] = valor_excedente
        precos["percentual_adicional"] = percentual_adicional
        precos["sujeito_aprovacao"] = sujeito_aprovacao
        
        print(f"[calculo_precos] Preços finais calculados: {precos}")
        print("[calculo_precos] Cálculo finalizado com sucesso.")
        return precos
        
    except FileNotFoundError:
        print(f"[calculo_precos] ERRO CRÍTICO: Arquivo de tabela não encontrado em {arquivo_tabela}")
        return None
    except Exception as e:
        print(f"[calculo_precos] ERRO GERAL INESPERADO em calcular_precos_planos: {e}")
        traceback.print_exc() # Imprime traceback completo no log
        return None

# Exemplo de uso (mantido para teste local, mas ajustar path se necessário)
if __name__ == "__main__":
    # ... (Bloco __main__ mantido como estava na versão anterior, 
    #      mas com caminhos de teste ajustados e verificação de existência de arquivos) ...
    # Tenta encontrar o arquivo em locais comuns para teste local
    arquivo_tabela_teste = None
    # Adiciona mais um path comum
    paths_possiveis = ["input_files/Tabela 2023.xlsx", "../input_files/Tabela 2023.xlsx", "Tabela 2023.xlsx"]
    for path_t in paths_possiveis:
        if os.path.exists(path_t):
            arquivo_tabela_teste = path_t
            print(f"INFO Teste Local: Usando tabela em '{arquivo_tabela_teste}'")
            break
            
    if not arquivo_tabela_teste:
         print("ERRO Teste Local: 'Tabela 2023.xlsx' não encontrada nos caminhos padrão. Defina 'arquivo_tabela_teste' manualmente.")
    else:
        valores_teste = [10000.0, 74442.0, 75666.0, 99000.0, 105000.0, 150000.0]
        for valor in valores_teste:
            print(f"\n--- Testando com valor FIPE: R$ {valor:.2f} ---")
            precos = calcular_precos_planos(valor, arquivo_tabela_teste)
            if precos:
                print("  Preços calculados:")
                for plano, preco in precos.items():
                    if plano not in ["valor_excedente", "percentual_adicional", "sujeito_aprovacao"]:
                        print(f"    {plano}: {format_currency_manual(preco)}")
                
                if precos["sujeito_aprovacao"]:
                    print(f"    Valor excedente: {format_currency_manual(precos['valor_excedente'])}")
                    print(f"    Percentual adicional: {precos['percentual_adicional']:.0f}%")
                    print("    SUJEITO À APROVAÇÃO DA DIRETORIA")
            else:
                print("  Falha ao calcular preços.")

# ----- FIM DO CÓDIGO -----
