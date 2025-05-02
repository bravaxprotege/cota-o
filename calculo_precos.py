import pandas as pd
import sys
import numpy as np
sys.path.append("/opt/.manus/.sandbox-runtime")

def calcular_precos_planos(valor_fipe, arquivo_tabela):
    """Calcula os preços dos planos com base no valor FIPE do veículo.
    
    Args:
        valor_fipe (float): Valor FIPE do veículo.
        arquivo_tabela (str): Caminho para o arquivo Excel com a tabela de preços.
        
    Returns:
        dict: Dicionário com os valores dos diferentes planos e informações adicionais.
              Exemplo: {
                "Adesão": 300.0, 
                "Plano Ouro": 143.1, 
                "Diamante": 159.8, 
                "Platinum": 188.9, 
                "Pesados": 225.0,
                "valor_excedente": 0.0,
                "percentual_adicional": 0.0,
                "sujeito_aprovacao": False
              }
    """
    try:
        # Ler a planilha de preços
        df = pd.read_excel(arquivo_tabela)
        
        # Procurar a linha que contém "VALOR DO VEÍCULO" ou similar
        valor_veiculo_idx = None
        for idx, row in df.iterrows():
            for col in row:
                if isinstance(col, str) and "VALOR DO VEÍCULO" in col:
                    valor_veiculo_idx = idx
                    break
            if valor_veiculo_idx is not None:
                break
                
        if valor_veiculo_idx is None:
            print("Não foi possível encontrar a linha com 'VALOR DO VEÍCULO'")
            # Tentar encontrar a linha com os nomes dos planos
            for idx, row in df.iterrows():
                if "PLANO OURO" in [str(x).upper() for x in row if isinstance(x, str)]:
                    valor_veiculo_idx = idx
                    break
                    
        if valor_veiculo_idx is None:
            print("Não foi possível identificar a estrutura da tabela")
            return None
            
        # Extrair os nomes das colunas da linha identificada
        colunas = df.iloc[valor_veiculo_idx].tolist()
        
        # Criar um novo DataFrame apenas com os dados relevantes (após a linha de cabeçalho)
        dados_df = df.iloc[valor_veiculo_idx+1:].reset_index(drop=True)
        
        # Atribuir nomes às colunas
        # Identificar as colunas pelos valores na linha de cabeçalho
        col_names = []
        for col in colunas:
            if pd.isna(col):
                col_names.append("Unnamed")
            elif "VALOR" in str(col).upper() or "VEÍCULO" in str(col).upper():
                col_names.append("faixa_valor")
            elif "ADESAO" in str(col).upper() or "ADESÃO" in str(col).upper():
                col_names.append("adesao")
            elif "OURO" in str(col).upper():
                col_names.append("plano_ouro")
            elif "DIAMANTE" in str(col).upper():
                col_names.append("plano_diamante")
            elif "PLATINUM" in str(col).upper():
                col_names.append("plano_platinum")
            elif "PESADOS" in str(col).upper():
                col_names.append("pesados")
            else:
                col_names.append(str(col))
                
        # Se não temos nomes suficientes, usar nomes genéricos
        if len(col_names) < dados_df.shape[1]:
            for i in range(len(col_names), dados_df.shape[1]):
                col_names.append(f"col_{i}")
        
        # Atribuir os nomes às colunas
        dados_df.columns = col_names[:dados_df.shape[1]]
        
        # Verificar se temos as colunas necessárias
        colunas_necessarias = ["faixa_valor", "adesao", "plano_ouro", "plano_diamante", "plano_platinum", "pesados"]
        colunas_faltantes = [col for col in colunas_necessarias if col not in dados_df.columns]
        
        if colunas_faltantes:
            print(f"Colunas faltantes: {colunas_faltantes}")
            # Tentar mapear colunas por posição se os nomes não foram encontrados
            if "faixa_valor" not in dados_df.columns and dados_df.shape[1] >= 1:
                dados_df = dados_df.rename(columns={dados_df.columns[0]: "faixa_valor"})
            if "adesao" not in dados_df.columns and dados_df.shape[1] >= 3:
                dados_df = dados_df.rename(columns={dados_df.columns[2]: "adesao"})
            if "plano_ouro" not in dados_df.columns and dados_df.shape[1] >= 4:
                dados_df = dados_df.rename(columns={dados_df.columns[3]: "plano_ouro"})
            if "plano_diamante" not in dados_df.columns and dados_df.shape[1] >= 5:
                dados_df = dados_df.rename(columns={dados_df.columns[4]: "plano_diamante"})
            if "plano_platinum" not in dados_df.columns and dados_df.shape[1] >= 6:
                dados_df = dados_df.rename(columns={dados_df.columns[5]: "plano_platinum"})
            if "pesados" not in dados_df.columns and dados_df.shape[1] >= 7:
                dados_df = dados_df.rename(columns={dados_df.columns[6]: "pesados"})
        
        # Remover linhas sem dados ou com NaN na coluna de faixa de valor
        dados_df = dados_df.dropna(subset=["faixa_valor"])
        
        # Converter valores para numérico onde possível
        for col in ["adesao", "plano_ouro", "plano_diamante", "plano_platinum", "pesados"]:
            if col in dados_df.columns:
                dados_df[col] = pd.to_numeric(dados_df[col], errors='coerce')
        
        # Variáveis para lógica especial de valores acima de R$ 100.000,00
        valor_excedente = 0.0
        percentual_adicional = 0.0
        sujeito_aprovacao = False
        
        # Verificar se o valor FIPE é maior que R$ 100.000,00
        if valor_fipe > 100000.0:
            print(f"Valor FIPE {valor_fipe} é maior que R$ 100.000,00. Aplicando regra especial.")
            valor_excedente = valor_fipe - 100000.0
            # Calcular percentual adicional: 1% para cada R$ 1.000,00 excedentes
            percentual_adicional = int(valor_excedente / 1000.0)
            sujeito_aprovacao = True
            
            # Buscar a faixa mais alta da tabela (presumivelmente R$ 95.000,01 - R$ 100.000,00)
            # Ordenar o DataFrame pela faixa de valor (assumindo que a última linha tem a maior faixa)
            faixa_encontrada = dados_df.iloc[-1]
            print(f"Usando a faixa mais alta da tabela como base para o cálculo.")
        else:
            # Encontrar a faixa de valor correspondente ao valor FIPE
            faixa_encontrada = None
            
            for idx, row in dados_df.iterrows():
                faixa = row["faixa_valor"]
                if isinstance(faixa, str) and "-" in faixa:
                    # Extrair os valores mínimo e máximo da faixa
                    faixa_limpa = faixa.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    valores = faixa_limpa.split("-")
                    if len(valores) == 2:
                        try:
                            min_valor = float(valores[0].strip())
                            max_valor = float(valores[1].strip())
                            
                            if min_valor <= valor_fipe <= max_valor:
                                faixa_encontrada = row
                                print(f"Faixa encontrada: {faixa} para valor FIPE {valor_fipe}")
                                break
                        except ValueError as e:
                            print(f"Erro ao converter faixa '{faixa}': {e}")
                            continue
            
            if faixa_encontrada is None:
                # Se não encontrou uma faixa exata, usar a última faixa (maior valor)
                if not dados_df.empty:
                    faixa_encontrada = dados_df.iloc[-1]
                    print(f"Valor FIPE {valor_fipe} não encontrado em nenhuma faixa específica. Usando a última faixa.")
                else:
                    print("Não há dados disponíveis na tabela após o processamento.")
                    return None
        
        # Extrair os valores dos planos
        precos = {}
        for plano, coluna in [
            ("Adesão", "adesao"),
            ("Plano Ouro", "plano_ouro"),
            ("Diamante", "plano_diamante"),
            ("Platinum", "plano_platinum"),
            ("Pesados", "pesados")
        ]:
            if coluna in faixa_encontrada.index and not pd.isna(faixa_encontrada[coluna]):
                valor_base = float(faixa_encontrada[coluna])
                
                # Aplicar percentual adicional se necessário (exceto para Adesão)
                if sujeito_aprovacao and plano != "Adesão":
                    valor_ajustado = valor_base * (1 + percentual_adicional / 100.0)
                    print(f"{plano}: Valor base {valor_base} + {percentual_adicional}% = {valor_ajustado}")
                    precos[plano] = valor_ajustado
                else:
                    precos[plano] = valor_base
            else:
                print(f"Coluna {coluna} não encontrada ou valor nulo para o plano {plano}")
                precos[plano] = 0.0
        
        # Adicionar informações sobre valor excedente e percentual adicional
        precos["valor_excedente"] = valor_excedente
        precos["percentual_adicional"] = percentual_adicional
        precos["sujeito_aprovacao"] = sujeito_aprovacao
        
        return precos
        
    except FileNotFoundError:
        print(f"Erro: Arquivo de tabela não encontrado em {arquivo_tabela}")
        return None
    except Exception as e:
        print(f"Erro ao calcular preços dos planos: {e}")
        import traceback
        traceback.print_exc()
        return None

# Exemplo de uso
if __name__ == "__main__":
    # Testar com alguns valores FIPE
    valores_teste = [10000.0, 74442.0, 99000.0, 105000.0, 150000.0]
    arquivo_tabela = "/home/ubuntu/upload/Tabela 2023.xlsx"
    
    for valor in valores_teste:
        print(f"\n--- Testando com valor FIPE: R$ {valor:.2f} ---")
        precos = calcular_precos_planos(valor, arquivo_tabela)
        if precos:
            print("Preços calculados:")
            for plano, preco in precos.items():
                if plano not in ["valor_excedente", "percentual_adicional", "sujeito_aprovacao"]:
                    print(f"  {plano}: R$ {preco:.2f}")
            
            if precos["sujeito_aprovacao"]:
                print(f"  Valor excedente: R$ {precos['valor_excedente']:.2f}")
                print(f"  Percentual adicional: {precos['percentual_adicional']:.0f}%")
                print("  SUJEITO À APROVAÇÃO DA DIRETORIA")
        else:
            print("Falha ao calcular preços.")
