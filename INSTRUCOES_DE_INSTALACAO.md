# Instruções de Instalação e Execução - Gerador de Cotações Bravax

Este documento contém instruções detalhadas sobre como instalar e executar a aplicação Gerador de Cotações Bravax em seu próprio computador ou servidor.

## Requisitos do Sistema

Para executar esta aplicação, você precisará:

1. **Python 3.8 ou superior**
2. **LibreOffice** (para conversão de PowerPoint para PDF)
3. **Bibliotecas Python** (listadas abaixo)
4. **Acesso à internet** (para baixar as dependências)

## Passo a Passo para Instalação

### 1. Extrair o Pacote ZIP

Extraia o arquivo `projeto_cotacao_bravax_final.zip` em uma pasta de sua escolha.

### 2. Instalar o Python

Se você ainda não tem o Python instalado:

- **Windows**: Baixe e instale do [site oficial do Python](https://www.python.org/downloads/windows/)
- **Mac**: Baixe e instale do [site oficial do Python](https://www.python.org/downloads/mac-osx/)
- **Linux**: Use o gerenciador de pacotes da sua distribuição:
  ```
  sudo apt-get update
  sudo apt-get install python3 python3-pip
  ```

### 3. Instalar o LibreOffice

O LibreOffice é necessário para converter os arquivos PowerPoint em PDF:

- **Windows**: Baixe e instale do [site oficial do LibreOffice](https://www.libreoffice.org/download/download/)
- **Mac**: Baixe e instale do [site oficial do LibreOffice](https://www.libreoffice.org/download/download/)
- **Linux**: Use o gerenciador de pacotes da sua distribuição:
  ```
  sudo apt-get install libreoffice
  ```

### 4. Instalar as Dependências Python

Abra um terminal ou prompt de comando, navegue até a pasta onde você extraiu o projeto e execute:

```
pip3 install pandas openpyxl python-pptx Flask
```

## Executando a Aplicação

### 1. Iniciar o Servidor

No terminal ou prompt de comando, navegue até a pasta do projeto e execute:

```
python3 app.py
```

Você verá uma mensagem indicando que o servidor está rodando, geralmente em `http://127.0.0.1:8080`.

### 2. Acessar a Aplicação

Abra seu navegador web e acesse:

```
http://127.0.0.1:8080
```

A interface do Gerador de Cotações Bravax será exibida e você poderá começar a usar.

## Estrutura de Arquivos

- `app.py`: Aplicação principal Flask
- `calculo_precos.py`: Script para cálculo de preços baseado no valor FIPE
- `preenche_cotacao.py`: Script para preenchimento do modelo PowerPoint
- `converte_pdf.py`: Script para conversão de PowerPoint para PDF
- `templates/index.html`: Interface web da aplicação
- `input_files/`: Pasta contendo os arquivos de entrada
  - `Tabela 2023.xlsx`: Tabela de preços
  - `Cotação auto.pptx`: Modelo PowerPoint para cotação

## Solução de Problemas

### A aplicação não inicia

- Verifique se todas as dependências foram instaladas corretamente
- Certifique-se de que está usando Python 3.8 ou superior
- Verifique se não há outro serviço usando a porta 8080

### Erro na conversão para PDF

- Verifique se o LibreOffice está instalado corretamente
- Certifique-se de que o caminho para o LibreOffice está no PATH do sistema
- Em alguns sistemas, pode ser necessário ajustar o caminho do LibreOffice no arquivo `converte_pdf.py`

### Erro ao calcular preços

- Verifique se o arquivo `input_files/Tabela 2023.xlsx` existe e está no formato correto
- Certifique-se de que o valor FIPE inserido está dentro das faixas da tabela

## Executando em um Servidor

Para executar a aplicação em um servidor e torná-la acessível pela internet:

1. Instale todas as dependências conforme descrito acima
2. Modifique o arquivo `app.py` para usar um servidor WSGI como Gunicorn (recomendado para produção)
3. Configure um proxy reverso como Nginx ou Apache
4. Configure um certificado SSL para HTTPS (recomendado)

Exemplo de configuração com Gunicorn e Nginx:

1. Instale o Gunicorn:
   ```
   pip3 install gunicorn
   ```

2. Execute a aplicação com Gunicorn:
   ```
   gunicorn -w 4 -b 127.0.0.1:8000 app:app
   ```

3. Configure o Nginx como proxy reverso (exemplo básico):
   ```
   server {
       listen 80;
       server_name seu-dominio.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Suporte

Se você encontrar problemas durante a instalação ou execução, entre em contato com o suporte técnico.

---

Estas instruções foram preparadas para ajudar você a instalar e executar o Gerador de Cotações Bravax em seu próprio ambiente. Esperamos que a aplicação seja útil para o seu negócio!
