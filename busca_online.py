#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.append("/opt/.manus/.sandbox-runtime")
import requests
from bs4 import BeautifulSoup
import re
import json

def buscar_dados_placa_online(placa):
    """Busca dados de um veículo pela placa no site placafipe.com.br.

    Args:
        placa (str): A placa do veículo a ser buscada (formato AAA1234 ou AAA1A23).

    Returns:
        dict: Um dicionário com os dados do veículo se encontrado, None caso contrário.
              Exemplo: {"marca": "VW", "modelo": "Virtus HL", "ano": 2018, "valor": 74442.0}
    """
    url = "https://placafipe.com.br/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://placafipe.com.br/",
        "Origin": "https://placafipe.com.br",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "placa": placa,
        "go": ""
    }

    try:
        print(f"Acessando {url} para buscar dados da placa {placa}...")
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response.raise_for_status() # Verifica se houve erro HTTP

        soup = BeautifulSoup(response.text, "html.parser")

        # Procurar a tabela com os dados
        tabela = soup.find("table", class_="fipeTablePriceDetail")
        
        if not tabela:
            # Tentar encontrar mensagem de erro
            erro_msg = soup.find("div", class_="alert-danger")
            if erro_msg:
                print(f"Erro encontrado no site placafipe: {erro_msg.get_text(strip=True)}")
            else:
                print("Não foi possível encontrar a tabela de detalhes ou mensagem de erro no site.")
            return None

        dados = {}
        linhas = tabela.find_all("tr")

        for linha in linhas:
            celulas = linha.find_all("td")
            if len(celulas) == 2:
                chave = celulas[0].get_text(strip=True).lower()
                valor = celulas[1].get_text(strip=True)
                
                if "marca" in chave:
                    dados["marca"] = valor
                elif "modelo" in chave:
                    dados["modelo"] = valor
                elif "ano modelo" in chave:
                    # Extrair apenas o ano (primeiros 4 dígitos)
                    match = re.search(r"\b(\d{4})\b", valor)
                    if match:
                        try:
                            dados["ano"] = int(match.group(1))
                        except ValueError:
                            print(f"Não foi possível converter o ano '{match.group(1)}' para inteiro.")
                elif "preço médio" in chave or "valor" in chave:
                    # Limpar o valor (remover R$, pontos e substituir vírgula por ponto)
                    valor_limpo = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
                    try:
                        dados["valor"] = float(valor_limpo)
                    except ValueError:
                        print(f"Não foi possível converter o valor '{valor_limpo}' para float.")
                # Adicionar outras chaves se necessário

        # Verificar se os dados essenciais foram encontrados
        if "marca" in dados and "modelo" in dados and "ano" in dados and "valor" in dados:
            print("Dados encontrados com sucesso:")
            print(json.dumps(dados, indent=2))
            return dados
        else:
            print("Não foi possível extrair todos os dados necessários da tabela.")
            print(f"Dados extraídos: {dados}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao acessar {url}: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar dados online: {e}")
        return None

# Exemplo de uso
if __name__ == "__main__":
    placa_teste_valida = "PGX9873" # Usar uma placa real para teste
    print(f"--- Testando com placa válida: {placa_teste_valida} ---")
    dados_veiculo = buscar_dados_placa_online(placa_teste_valida)
    if dados_veiculo:
        print("Busca online bem-sucedida.")
    else:
        print("Falha na busca online.")

    print("\n--- Testando com placa inválida: ABC1234 ---")
    dados_veiculo_invalido = buscar_dados_placa_online("ABC1234")
    if not dados_veiculo_invalido:
        print("Teste com placa inválida passou (nenhum dado encontrado).")
    else:
        print("Erro no teste: Dados encontrados para placa inválida.")
