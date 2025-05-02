# ----- INÍCIO DO CÓDIGO CORRIGIDO PARA converte_pdf.py -----
import sys
# sys.path.append("/opt/.manus/.sandbox-runtime") # Manter se necessário
import os
import subprocess
import logging # Usar logging é melhor que print
import traceback

# Configurar logging (pode ser configurado globalmente em app.py)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log_prefix = "[converte_pdf]"

def converter_pptx_para_pdf(pptx_path, output_dir): # Alterado para receber output_dir
    """Converte um arquivo PowerPoint para PDF usando LibreOffice.
    Salva o PDF no diretório especificado com o mesmo nome base do PPTX.

    Args:
        pptx_path (str): Caminho para o arquivo PowerPoint de entrada (.pptx).
        output_dir (str): Caminho para o diretório onde o PDF será salvo.

    Returns:
        str or None: O caminho completo para o arquivo PDF gerado em caso de sucesso, 
                     None caso contrário.
    """
    logging.info(f"{log_prefix} Iniciando conversão de '{pptx_path}' para PDF em '{output_dir}'")

    # Verificar se o arquivo de entrada existe
    if not os.path.exists(pptx_path):
        logging.error(f"{log_prefix} Arquivo de entrada PPTX não encontrado: {pptx_path}")
        return None

    # Verificar se o diretório de saída existe (deve ter sido criado por app.py)
    if not os.path.isdir(output_dir):
         logging.error(f"{log_prefix} Diretório de saída não existe: {output_dir}")
         # Poderia tentar criar, mas é melhor garantir que app.py criou
         # os.makedirs(output_dir, exist_ok=True) 
         return None


    # Construir o comando do LibreOffice
    # Assume que 'libreoffice' está no PATH dentro do container Docker
    cmd = [
        'libreoffice',
        '--headless',         # Não abrir interface gráfica
        '--convert-to', 'pdf', # Formato de saída
        '--outdir', output_dir, # Diretório onde salvar o PDF
        pptx_path             # Arquivo de entrada
    ]

    logging.info(f"{log_prefix} Executando comando: {' '.join(cmd)}")
    pdf_gerado_path = None # Inicializa como None

    try:
        # Executar o comando
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE, # Captura saída padrão
            stderr=subprocess.PIPE, # Captura saída de erro
            text=True,              # Decodifica saídas como texto
            check=False,            # Não lança exceção automaticamente se returncode != 0
            timeout=120             # Timeout de 2 minutos (ajuste se necessário)
        )

        # Logar saídas do LibreOffice (útil para debug)
        if result.stdout:
            logging.info(f"{log_prefix} Saída (stdout) do LibreOffice:\n{result.stdout}")
        if result.stderr:
            if result.returncode == 0:
                 logging.warning(f"{log_prefix} Saída de erro (stderr) do LibreOffice (mas retornou 0):\n{result.stderr}")
            else:
                 logging.error(f"{log_prefix} Saída de erro (stderr) do LibreOffice:\n{result.stderr}")

        # Verificar se o comando foi executado com sucesso (código de saída 0)
        if result.returncode == 0:
            # Construir o nome esperado do arquivo PDF
            base_name = os.path.basename(pptx_path)
            base_name_without_ext = os.path.splitext(base_name)[0]
            expected_pdf_path = os.path.join(output_dir, f"{base_name_without_ext}.pdf")

            # Verificar se o arquivo PDF realmente foi criado
            if os.path.exists(expected_pdf_path):
                logging.info(f"{log_prefix} PDF criado com sucesso: {expected_pdf_path}")
                pdf_gerado_path = expected_pdf_path # Guarda o caminho do PDF gerado
            else:
                # Às vezes LibreOffice retorna 0 mas não cria o arquivo se houve warning interno
                logging.error(f"{log_prefix} Comando LibreOffice retornou 0, mas arquivo PDF não foi encontrado em {expected_pdf_path}.")

        else:
            logging.error(f"{log_prefix} Comando LibreOffice falhou com código de saída: {result.returncode}")

    except subprocess.TimeoutExpired:
         logging.error(f"{log_prefix} Comando LibreOffice excedeu o timeout de 120 segundos.")
    except FileNotFoundError:
         # Isso aconteceria se o comando 'libreoffice' não fosse encontrado no sistema
         logging.error(f"{log_prefix} ERRO CRÍTICO: Comando 'libreoffice' não encontrado. Verifique a instalação no Dockerfile.")
    except Exception as e:
        logging.error(f"{log_prefix} Erro inesperado durante a execução do subprocess do LibreOffice: {e}")
        logging.error(traceback.format_exc())

    # Retorna o caminho do PDF se foi gerado, senão None
    logging.info(f"{log_prefix} Retornando caminho do PDF: {pdf_gerado_path}")
    return pdf_gerado_path


# --- Bloco de Teste Local (Comentado - ajuste caminhos se for usar) ---
# if __name__ == '__main__':
#     print("Executando teste local de converte_pdf.py")
#     # Ajuste estes caminhos para seu ambiente local
#     teste_pptx = "input_files/cotacao_auto.pptx" 
#     teste_output_dir = "output_teste_local"
#     os.makedirs(teste_output_dir, exist_ok=True)
    
#     if os.path.exists(teste_pptx):
#          pdf_result_path = converter_pptx_para_pdf(teste_pptx, teste_output_dir)
#          if pdf_result_path:
#               print(f"Teste local bem-sucedido. PDF em: {pdf_result_path}")
#          else:
#               print("Teste local falhou na conversão.")
#     else:
#          print(f"ERRO Teste Local: Arquivo de template não encontrado em '{teste_pptx}'")

# ----- FIM DO CÓDIGO -----
