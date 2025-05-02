import sys
sys.path.append("/opt/.manus/.sandbox-runtime")
import os
import subprocess
from pptx import Presentation
import tempfile

def converter_pptx_para_pdf(pptx_path, pdf_path):
    """Converte um arquivo PowerPoint para PDF usando LibreOffice.
    
    Args:
        pptx_path (str): Caminho para o arquivo PowerPoint (.pptx)
        pdf_path (str): Caminho para salvar o arquivo PDF
        
    Returns:
        bool: True se a conversão foi bem-sucedida, False caso contrário
    """
    try:
        # Verificar se o LibreOffice está instalado
        try:
            subprocess.run(['libreoffice', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            print("LibreOffice está instalado.")
        except (subprocess.SubprocessError, FileNotFoundError):
            print("LibreOffice não está instalado. Instalando...")
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libreoffice'], check=True)
            print("LibreOffice instalado com sucesso.")
        
        # Converter PPTX para PDF usando LibreOffice
        cmd = [
            'libreoffice', 
            '--headless', 
            '--convert-to', 'pdf', 
            '--outdir', os.path.dirname(pdf_path),
            pptx_path
        ]
        
        print(f"Executando comando: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"Erro ao converter para PDF: {result.stderr}")
            return False
            
        # LibreOffice salva o arquivo com o mesmo nome, mas extensão .pdf
        # Verificar se o arquivo foi criado
        base_name = os.path.basename(pptx_path)
        base_name_without_ext = os.path.splitext(base_name)[0]
        expected_pdf = os.path.join(os.path.dirname(pdf_path), f"{base_name_without_ext}.pdf")
        
        if os.path.exists(expected_pdf) and expected_pdf != pdf_path:
            # Renomear para o caminho desejado se necessário
            os.rename(expected_pdf, pdf_path)
            
        if os.path.exists(pdf_path):
            print(f"PDF criado com sucesso: {pdf_path}")
            return True
        else:
            print(f"Falha ao criar o PDF. Arquivo não encontrado: {pdf_path}")
            return False
            
    except Exception as e:
        print(f"Erro durante a conversão para PDF: {e}")
        return False

# Exemplo de uso (será chamado de outro script posteriormente)
if __name__ == '__main__':
    from busca_dados import buscar_dados_veiculo
    from preenche_cotacao import preencher_cotacao_pptx
    
    placa_teste = 'PGX9873'
    arquivo_db = '/home/ubuntu/upload/Consulta fipe aut.xlsx'
    template_pptx = '/home/ubuntu/upload/Cotação auto.pptx'
    output_pptx = f'/home/ubuntu/projeto_cotacao/cotacao_{placa_teste}.pptx'
    output_pdf = f'/home/ubuntu/projeto_cotacao/cotacao_{placa_teste}.pdf'
    
    # Buscar dados e preencher PowerPoint
    dados = buscar_dados_veiculo(placa_teste, arquivo_db)
    
    if dados:
        print("\nIniciando preenchimento do PowerPoint...")
        sucesso_pptx = preencher_cotacao_pptx(template_pptx, output_pptx, dados)
        
        if sucesso_pptx:
            print("\nIniciando conversão para PDF...")
            sucesso_pdf = converter_pptx_para_pdf(output_pptx, output_pdf)
            
            if sucesso_pdf:
                print("Processo completo! PowerPoint preenchido e convertido para PDF com sucesso.")
            else:
                print("Falha na conversão para PDF.")
        else:
            print("Falha ao preencher o PowerPoint.")
    else:
        print(f"Não foi possível processar a cotação pois a placa {placa_teste} não foi encontrada.")
