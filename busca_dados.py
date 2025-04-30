import pandas as pd
import sys
sys.path.append("/opt/.manus/.sandbox-runtime")

def buscar_dados_veiculo(placa, arquivo_excel):
    """Busca dados de um veículo pela placa em um arquivo Excel.

    Args:
        placa (str): A placa do veículo a ser buscada.
        arquivo_excel (str): O caminho para o arquivo Excel.

    Returns:
        dict: Um dicionário com os dados do veículo se encontrado, None caso contrário.
    """
    try:
        # Ler a planilha, assumindo que o cabeçalho está na primeira linha (índice 0)
        # A planilha 'Consulta fipe aut.xlsx' parece ter o cabeçalho real na linha 1 (índice 0)
        # e os dados começam na linha 2 (índice 1)
        df = pd.read_excel(arquivo_excel, header=0) 
        
        # Renomear colunas para facilitar o acesso (baseado na visualização anterior)
        # Colunas originais: Unnamed: 0, Consultar, Unnamed: 2, Unnamed: 3, nome, placa, marca, modelo, ano, categoria, valor, Adesão, Plano Ouro, Diamante, Platinum, Pesados
        # Vamos usar os nomes da linha 1 como referência, ajustando onde necessário
        df.columns = [ # Mapeamento manual baseado na inspeção do head()
            'col_0', 'col_1', 'col_2', 'col_3', 'nome', 'placa', 'marca', 
            'modelo', 'ano', 'categoria', 'valor', 'Adesão', 'Plano Ouro', 
            'Diamante', 'Platinum', 'Pesados'
        ]

        # Converter a coluna 'placa' para string para garantir a comparação correta
        df['placa'] = df['placa'].astype(str)
        placa_busca = str(placa).upper() # Normalizar a placa buscada
        df['placa'] = df['placa'].str.upper() # Normalizar a coluna de placas

        # Buscar a linha correspondente à placa
        veiculo_encontrado = df[df['placa'] == placa_busca]

        if not veiculo_encontrado.empty:
            # Retornar a primeira linha encontrada como um dicionário
            dados = veiculo_encontrado.iloc[0].to_dict()
            # Converter valores numéricos para tipos apropriados, tratando NaNs
            for key, value in dados.items():
                if pd.isna(value):
                    dados[key] = None
                elif isinstance(value, (int, float)):
                    # Manter como float para valores monetários, converter ano para int se possível
                    if key == 'ano' and value == int(value):
                         dados[key] = int(value)
                    # Arredondar valores monetários para 2 casas decimais
                    elif key in ['valor', 'Adesão', 'Plano Ouro', 'Diamante', 'Platinum', 'Pesados']:
                         dados[key] = round(float(value), 2)
                    else:
                         dados[key] = float(value)
            return dados
        else:
            return None

    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em {arquivo_excel}")
        return None
    except Exception as e:
        print(f"Erro ao processar o arquivo Excel: {e}")
        return None

# Exemplo de uso (será chamado de outro script posteriormente)
if __name__ == '__main__':
    # Teste com a placa do exemplo
    placa_teste = 'PGX9873'
    arquivo_db = '/home/ubuntu/upload/Consulta fipe aut.xlsx'
    
    dados = buscar_dados_veiculo(placa_teste, arquivo_db)
    
    if dados:
        print("Dados encontrados:")
        for chave, valor in dados.items():
            print(f"  {chave}: {valor}")
    else:
        print(f"Placa {placa_teste} não encontrada no arquivo {arquivo_db}.")

    # Teste com uma placa inexistente
    placa_teste_inexistente = 'ABC1234'
    dados_inexistente = buscar_dados_veiculo(placa_teste_inexistente, arquivo_db)
    if not dados_inexistente:
        print(f"\nTeste com placa inexistente ({placa_teste_inexistente}) passou: Placa não encontrada.")
    else:
        print(f"\nErro no teste: Placa inexistente ({placa_teste_inexistente}) foi encontrada.")

