import pandas as pd
import traceback
import os
import logging

log = logging.getLogger(__name__)


def calcular_precos_planos(valor_fipe, arquivo_tabela):
    """Calcula os preços dos planos com base no valor FIPE do veículo."""
    log.info(f"Iniciando cálculo para FIPE: {valor_fipe} usando Tabela: {arquivo_tabela}")
    
    try:
        # Ler a planilha de preços
        log.info(" Lendo arquivo Excel...")
        if not os.path.exists(arquivo_tabela):
             log.error(f" ERRO CRÍTICO IMEDIATO: Arquivo de tabela NÃO EXISTE em {arquivo_tabela}")
             return None # Retorna None imediatamente se o arquivo não existe
        df = pd.read_excel(arquivo_tabela)
        log.info(f" Leitura concluída. DataFrame shape: {df.shape}")
        
        # --- Lógica para encontrar cabeçalho (mantida, mas pode ser frágil) ---
        valor_veiculo_idx = None
        # Procurar a linha que contém "VALOR DO VEÍCULO" ou similar
        log.info(" Procurando linha do cabeçalho por 'VALOR DO VEÍCULO'...")
        for idx, row in df.iterrows():
            for col in row:
                # Verifica se col é string antes de chamar 'in'
                if isinstance(col, str) and "VALOR DO VEÍCULO" in col.upper(): # Comparar em maiúsculas
                    valor_veiculo_idx = idx
                    log.info(f" Encontrado 'VALOR DO VEÍCULO' na linha índice {idx}")
                    break
            if valor_veiculo_idx is not None:
                break
                
        if valor_veiculo_idx is None:
            log.info(" Não encontrou por 'VALOR DO VEÍCULO'. Procurando por 'PLANO OURO'...")
            # Tentar encontrar a linha com os nomes dos planos como fallback
            for idx, row in df.iterrows():
                # Verifica se é string antes de chamar upper()
                if "PLANO OURO" in [str(x).upper() for x in row if isinstance(x, str)]:
                    valor_veiculo_idx = idx
                    log.info(f" Fallback: Usando linha {idx} como cabeçalho (contém PLANO OURO).")
                    break
                    
        if valor_veiculo_idx is None:
            log.info(" ERRO CRÍTICO: Estrutura da tabela não identificada (cabeçalho não encontrado).")
            return None # Retorna None se não achar o cabeçalho
            
        log.info(f" Linha de cabeçalho identificada (ou fallback): Índice {valor_veiculo_idx}")
        colunas = df.iloc[valor_veiculo_idx].tolist()
        log.info(f" Nomes das colunas brutos lidos da linha {valor_veiculo_idx}: {colunas}")

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

        log.info(" Mapeando nomes das colunas por keywords...")
        for i, col_header in enumerate(colunas):
            header_str = str(col_header).upper()
            found_map = False
            for target_name, keywords in keywords_map.items():
                 if mapped_cols[target_name] is None: # Mapeia apenas uma vez
                     if any(keyword in header_str for keyword in keywords):
                         col_names.append(target_name)
                         mapped_cols[target_name] = i # Guarda o índice original
                         log.info(f"  - Mapeado '{col_header}' (Índice {i}) para '{target_name}'")
                         found_map = True
                         break
            if not found_map:
                 col_names.append(f"desconhecida_{i}")
                 log.info(f"  - Coluna '{col_header}' (Índice {i}) não mapeada.")
        
        # Aplicar nomes ao dataframe de dados
        if len(col_names) >= dados_df.shape[1]:
            dados_df.columns = col_names[:dados_df.shape[1]]
            log.info(f" Nomes das colunas aplicados: {dados_df.columns.tolist()}")
        else:
             log.error(f" ERRO: Discrepância entre número de colunas lidas ({len(colunas)}) e colunas de dados ({dados_df.shape[1]})")
             log.info(f" Colunas mapeadas: {col_names}")
             return None

        # Verificar se colunas essenciais foram mapeadas
        colunas_faltantes = [name for name, index in mapped_cols.items() if index is None]
        if colunas_faltantes:
            log.warning(f" AVISO: Colunas essenciais não encontradas pelo nome: {colunas_faltantes}. A aplicação pode falhar.")
            # Poderia retornar None aqui se colunas como 'faixa_valor' faltarem

        # Remover linhas com NaN em 'faixa_valor' (se a coluna existir)
        if "faixa_valor" in dados_df.columns:
            log.info(f" Shape antes de dropna('faixa_valor'): {dados_df.shape}")
            dados_df = dados_df.dropna(subset=["faixa_valor"])
            log.info(f" Shape depois de dropna('faixa_valor'): {dados_df.shape}")
        else:
             log.info(" ERRO: Coluna 'faixa_valor' não encontrada após mapeamento.")
             return None

        if dados_df.empty:
            log.info(" ERRO: DataFrame vazio após limpar linhas sem faixa de valor.")
            return None

        # Converter valores para numérico
        for col in ["adesao", "plano_ouro", "plano_diamante", "plano_platinum", "pesados"]:
            if col in dados_df.columns:
                log.info(f" Convertendo coluna '{col}' para numérico.")
                dados_df[col] = pd.to_numeric(dados_df[col], errors='coerce')
                # Verificar se há NaNs após conversão (indicaria texto/formato inválido na coluna)
                if dados_df[col].isnull().any():
                     log.warning(f" AVISO: Valores não numéricos encontrados na coluna '{col}' e convertidos para NaN.")
            else:
                 log.warning(f" AVISO: Coluna '{col}' esperada não encontrada para conversão numérica.")

        # --- Lógica de Cálculo ---
        valor_excedente = 0.0
        percentual_adicional = 0.0
        sujeito_aprovacao = False
        
        if valor_fipe > 100000.0:
            log.info(f" Valor FIPE {valor_fipe} > 100k. Aplicando regra especial.")
            valor_excedente = valor_fipe - 100000.0
            percentual_adicional = int(valor_excedente / 1000.0) # 1% a cada 1000
            sujeito_aprovacao = True
            log.info(f" Valor excedente: {valor_excedente}, Percentual Adicional: {percentual_adicional}%")
            
            # Usar a última linha como base
            if not dados_df.empty:
                 faixa_encontrada = dados_df.iloc[-1]
                 log.info(f" Usando última linha (Índice {faixa_encontrada.name}) como base: Faixa '{faixa_encontrada.get('faixa_valor', 'N/A')}'")
            else:
                 log.info(" ERRO: Tabela vazia, não é possível calcular para FIPE > 100k.")
                 return None 
        else:
            # --- Loop Principal para Encontrar a Faixa ---
            log.info(f" Procurando faixa para FIPE: {valor_fipe}")
            faixa_encontrada = None
            for idx, row in dados_df.iterrows():
                faixa = row["faixa_valor"]
                log.info(f"  Verificando Linha índice: {idx}, Faixa: '{faixa}'")
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
                            log.info(f"    Faixa parseada: min={min_valor}, max={max_valor}")
                        else:
                             log.warning(f"    AVISO: Faixa '{faixa}' não tem formato min-max esperado após split.")
                             continue 
                             
                    except ValueError as e:
                        log.error(f"    ERRO ao converter valores da faixa '{faixa}' para float: {e}")
                        continue 
                    except Exception as e_parse:
                         log.error(f"    ERRO inesperado ao parsear faixa '{faixa}': {e_parse}")
                         continue

                    # Comparação
                    if min_valor is not None and max_valor is not None:
                        # Ajuste pequeno para garantir inclusão correta (ex: 0.01 a 100.00 inclui 100.00)
                        # A comparação original min_valor <= valor_fipe <= max_valor ESTÁ CORRETA.
                        # Não precisa de ajuste epsilon se os limites forem xxx.01 a yyy.00
                        comparacao = min_valor <= valor_fipe <= max_valor
                        log.info(f"    Comparando: {min_valor} <= {valor_fipe} <= {max_valor} -> {comparacao}")
                        if comparacao:
                            faixa_encontrada = row
                            log.info(f"    >>> Faixa ENCONTRADA! Índice da linha no DataFrame original: {idx}")
                            break 
                    else:
                         log.info("    AVISO: min_valor ou max_valor não puderam ser definidos para comparação.")

            # Fallback se nenhuma faixa exata foi encontrada
            if faixa_encontrada is None:
                log.info(f" Nenhuma faixa exata encontrada para FIPE {valor_fipe}.")
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
                           log.error(f" ERRO: Valor FIPE {valor_fipe} é MAIOR que o limite máximo da tabela ({max_ultima_faixa}).")
                           return None # Retorna None -> Causa o erro "Não foi possível encontrar..." no app.py intencionalmente.
                     else:
                          # Se não for maior que o limite (ou não conseguimos verificar), mantém o fallback
                          faixa_encontrada = ultima_faixa_row
                          log.warning(f" ATENÇÃO: Usando a ÚLTIMA faixa da tabela como fallback: '{ultima_faixa_str}'")

                elif valor_fipe <= 0:
                     log.info(" ERRO: Valor FIPE inválido ou zero.")
                     return None
                else:
                    # Isso só aconteceria se dropna limpasse TUDO
                    log.info(" ERRO CRÍTICO: Não há faixas válidas na tabela para usar como fallback.")
                    return None 

        # --- Extração dos Preços ---
        log.info(f" Extraindo preços da linha encontrada (Índice original: {faixa_encontrada.name if faixa_encontrada is not None else 'Nenhum'})")
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
                            log.info(f"   {plano} ({coluna}): Valor base lido = {valor_base}")
                             
                            if sujeito_aprovacao and plano != "Adesão":
                                valor_ajustado = valor_base * (1 + percentual_adicional / 100.0)
                                log.info(f"     + {percentual_adicional}% = {valor_ajustado}")
                                precos[plano] = valor_ajustado
                            else:
                                precos[plano] = valor_base
                        except Exception as e_conv:
                             log.info(f"   ERRO ao converter valor para {plano} ({coluna}): '{valor_na_celula}' -> {e_conv}")
                             precos[plano] = 0.0 # Define 0.0 se a conversão falhar
                    else:
                        log.warning(f"   AVISO: Valor NULO/NaN encontrado na coluna '{coluna}' para o plano '{plano}'. Definindo preço como 0.0")
                        precos[plano] = 0.0
                else:
                    log.warning(f"   AVISO: Coluna '{coluna}' não encontrada na linha selecionada para o plano '{plano}'. Definindo preço como 0.0")
                    precos[plano] = 0.0
        else:
             log.info(" ERRO: Nenhuma linha/faixa encontrada para extrair preços (faixa_encontrada is None).")
             return None # Retorna None explicitamente

        # Adicionar informações extras
        precos["valor_excedente"] = valor_excedente
        precos["percentual_adicional"] = percentual_adicional
        precos["sujeito_aprovacao"] = sujeito_aprovacao
        
        log.info(f" Preços finais calculados: {precos}")
        log.info(" Cálculo finalizado com sucesso.")
        return precos
        
    except FileNotFoundError:
        log.error(f" ERRO CRÍTICO: Arquivo de tabela não encontrado em {arquivo_tabela}")
        return None
    except Exception as e:
        log.error(f"Erro inesperado em calcular_precos_planos: {e}")
        log.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def _fmt(value):
        if value is None or not isinstance(value, (int, float)):
            return "N/A"
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    paths_possiveis = ["input_files/Tabela 2023.xlsx", "../input_files/Tabela 2023.xlsx", "Tabela 2023.xlsx"]
    arquivo_tabela_teste = next((p for p in paths_possiveis if os.path.exists(p)), None)

    if not arquivo_tabela_teste:
        print("ERRO: 'Tabela 2023.xlsx' não encontrada.")
    else:
        for valor in [10000.0, 74442.0, 99000.0, 105000.0, 150000.0]:
            print(f"\n--- FIPE: R$ {valor:,.2f} ---")
            precos = calcular_precos_planos(valor, arquivo_tabela_teste)
            if precos:
                for plano, preco in precos.items():
                    if plano not in ("valor_excedente", "percentual_adicional", "sujeito_aprovacao"):
                        print(f"  {plano}: {_fmt(preco)}")
                if precos.get("sujeito_aprovacao"):
                    print(f"  ⚠️ Sujeito à aprovação — adicional: {precos['percentual_adicional']:.0f}%")
            else:
                print("  Falha ao calcular preços.")
