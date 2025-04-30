# Gerador de Cotações Bravax

## Descrição

Esta aplicação web foi desenvolvida para automatizar a geração de cotações de seguro automotivo personalizadas para a Bravax. Ela permite que o usuário insira os dados do veículo e do cliente através de uma interface web simples e gera um arquivo PDF com a cotação, baseado em um modelo PowerPoint e uma tabela de preços.

## Funcionalidades

*   **Interface Web:** Uma página web amigável (com layout inspirado na página de adesão da Bravax, usando as cores vermelho e branco) para entrada de dados do cliente e do veículo (Nome, Placa, Marca, Modelo, Ano, Valor FIPE, Categoria). Os indicadores de etapas foram removidos conforme solicitado.
*   **Cálculo de Preços:** Calcula automaticamente os valores dos planos (Adesão, Ouro, Diamante, Platinum, Pesados) com base no Valor FIPE informado, utilizando a `Tabela 2023.xlsx`.
*   **Lógica Especial (> R$ 100.000):** Para veículos com Valor FIPE acima de R$ 100.000,00:
    *   Utiliza os preços da faixa mais alta da tabela (R$ 95.000,01 - R$ 100.000,00) como base.
    *   Acrescenta 1% ao valor das parcelas mensais (exceto Adesão) para cada R$ 1.000,00 que exceder os R$ 100.000,00.
    *   Inclui um aviso "Sujeito à aprovação da diretoria" na cotação gerada.
    *   Exibe um aviso na interface web informando sobre a necessidade de aprovação.
*   **Preenchimento Automático:** Preenche um modelo PowerPoint (`Cotação auto.pptx`) com os dados do cliente, do veículo e os preços calculados.
*   **Geração de PDF:** Converte o arquivo PowerPoint preenchido em um arquivo PDF.
*   **Download:** Disponibiliza o arquivo PDF gerado para download diretamente pela interface web.

## Arquivos do Projeto

*   `app.py`: Script principal da aplicação Flask. Controla a interface web, recebe os dados, chama os outros scripts e gerencia a geração/download dos arquivos.
*   `calculo_precos.py`: Script responsável por ler a `Tabela 2023.xlsx` e calcular os preços dos planos com base no Valor FIPE, incluindo a lógica especial para valores acima de R$ 100.000,00.
*   `preenche_cotacao.py`: Script que utiliza a biblioteca `python-pptx` para preencher o template `Cotação auto.pptx` com os dados da cotação, incluindo o aviso de aprovação quando necessário.
*   `converte_pdf.py`: Script que utiliza o LibreOffice (instalado no ambiente) para converter o arquivo `.pptx` preenchido em `.pdf`.
*   `templates/index.html`: Arquivo HTML que define a estrutura e o estilo (CSS) da interface web.
*   `input_files/`: Diretório contendo os arquivos de entrada originais.
    *   `Tabela 2023.xlsx`: Planilha com as faixas de valores e preços dos planos.
    *   `Cotação auto.pptx`: Modelo PowerPoint da cotação.
*   `output/`: Diretório criado automaticamente pela aplicação para armazenar os arquivos PDF gerados temporariamente antes do download. (Não incluído no zip, será criado ao rodar `app.py`).
*   `README.md`: Este arquivo de documentação.

## Como Usar

1.  **Acesse a Interface Web:** Utilize o link fornecido (link temporário).
    *   Link atual (pode expirar): http://8080-igeebabhvcsnevj5c8jsd-986a5781.manus.computer
2.  **Consulte a FIPE:** Se necessário, consulte o valor FIPE do veículo em [placafipe.com.br](https://placafipe.com.br/) (link disponível na interface).
3.  **Preencha os Dados:** Insira o nome do cliente, placa, marca, modelo, ano e o valor FIPE do veículo. A categoria é opcional.
4.  **Gere a Cotação:** Clique no botão "Gerar Cotação".
5.  **Aguarde:** O sistema processará os dados, calculará os preços, preencherá o modelo e converterá para PDF.
6.  **Download:** Se tudo ocorrer bem, uma mensagem de sucesso será exibida junto com um botão para baixar o arquivo PDF da cotação. Se o valor FIPE for acima de R$ 100.000,00, um aviso sobre a necessidade de aprovação da diretoria também será mostrado.

## Execução Local (Instruções Técnicas)

1.  **Pré-requisitos:**
    *   Python 3
    *   LibreOffice (para conversão PPTX -> PDF)
    *   Dependências Python: Instale com `pip3 install Flask pandas openpyxl python-pptx` (outras dependências como pdf2image e Pillow foram instaladas durante o desenvolvimento mas não são estritamente necessárias para a versão final que usa LibreOffice).
2.  **Estrutura:** Coloque os arquivos `Tabela 2023.xlsx` e `Cotação auto.pptx` no diretório `input_files/` dentro da pasta do projeto. Os scripts foram ajustados para buscar os arquivos de entrada neste local.
3.  **Execução:** Navegue até o diretório do projeto e execute `python3 app.py`.
4.  **Acesso:** Acesse a aplicação em `http://localhost:8080` (ou o endereço IP da máquina) no seu navegador.
