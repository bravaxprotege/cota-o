# Guia Simplificado: Colocando sua Aplicação Online com Docker

Este guia explica, de forma simples, como usar o arquivo `Dockerfile` que criei para colocar sua aplicação Gerador de Cotações Bravax online, com um link fixo, usando uma plataforma de hospedagem.

**O que é Docker e o Dockerfile?**

*   **Dockerfile:** É como uma receita de bolo. Ele monta a imagem com o Python, WeasyPrint e as bibliotecas nativas usadas para gerar PDF, além do código da aplicação.
*   **Docker:** É a ferramenta que lê essa receita (`Dockerfile`) e monta o pacote ("imagem"). As plataformas de hospedagem usam o Docker para rodar sua aplicação de forma isolada e consistente.

**Vantagem:** Usando o `Dockerfile`, você não precisa instalar Python nem as dependências nativas de PDF no servidor de hospedagem. A "receita" já cuida disso!

**Pré-requisito:**

*   **Conta em Plataforma de Hospedagem:** Você precisa ter uma conta em uma plataforma que permita hospedar aplicações usando um `Dockerfile`. Algumas opções populares (muitas com planos gratuitos ou de baixo custo para começar) são:
    *   **Render** (Procure pela opção de deploy com Docker)
    *   **Railway** (Suporta deploy via Dockerfile)
    *   **Google Cloud Run** (Requer um pouco mais de configuração inicial no Google Cloud)
    *   Outras como Fly.io, AWS App Runner, etc.
*   **Conta no GitHub (ou similar):** A forma mais fácil de enviar seu código para a plataforma de hospedagem é através de um repositório Git (como GitHub, GitLab, Bitbucket). É gratuito.

**Passo a Passo Geral (Pode variar um pouco entre plataformas):**

1.  **Prepare seu Código:**
    *   Baixe e extraia o arquivo `.zip` final que vou te enviar. Ele conterá todos os arquivos da aplicação, incluindo o `Dockerfile` e este guia.

2.  **Envie para o GitHub (ou similar):**
    *   Crie um novo repositório no GitHub (pode ser público ou privado).
    *   Faça o upload de **todos** os arquivos e pastas do projeto (extraídos do zip) para este repositório. Certifique-se de que o `Dockerfile` esteja na pasta principal do repositório.

3.  **Escolha e Configure a Plataforma de Hospedagem:**
    *   Acesse a plataforma de hospedagem escolhida (Render, Railway, etc.).
    *   Procure a opção para criar um novo serviço/aplicação.
    *   Escolha a opção de implantar (deploy) a partir de um **Repositório Git** ou especificamente usando um **Dockerfile**.
    *   Conecte sua conta da plataforma de hospedagem à sua conta do GitHub (ou similar) para que ela possa acessar seu repositório.
    *   Selecione o repositório que você criou na etapa 2.
    *   A plataforma geralmente detectará automaticamente o `Dockerfile` na raiz do seu repositório.
    *   Configure um nome para sua aplicação (ex: `bravax-cotador`).
    *   Verifique se a porta está correta. O `Dockerfile` está configurado para usar a porta `8080`. A plataforma pode detectar isso ou você pode precisar confirmar.
    *   **Importante:** Confira o plano e os recursos da hospedagem. A geração de PDF usa WeasyPrint e pode precisar de memória adicional em cotações grandes.
    *   **Segredos opcionais:** Configure `FIPE_API_TOKEN` no ambiente do serviço para o limite ampliado da API FIPE. Configure `COTACAO_AJUSTE_PIN` somente se a equipe deve usar ajustes de preço. Não grave esses valores no código ou no Git. Sem `COTACAO_AJUSTE_PIN`, os ajustes permanecem desativados.

4.  **Inicie o Deploy:**
    *   Clique no botão para criar ou implantar o serviço.
    *   A plataforma agora vai seguir a "receita" do `Dockerfile`:
        *   Baixar a imagem base do Python.
        *   Instalar as bibliotecas Python e as dependências nativas do WeasyPrint.
        *   Copiar seu código.
        *   Construir a imagem final da sua aplicação.
    *   Após construir a imagem, a plataforma vai iniciar sua aplicação usando o comando definido no `Dockerfile` (com Gunicorn).
    *   Você poderá acompanhar o progresso pelos logs na plataforma.

5.  **Acesse sua Aplicação Online!**
    *   Quando o deploy terminar com sucesso, a plataforma fornecerá um **link público e fixo** (ex: `bravax-cotador.onrender.com` ou similar).
    *   Acesse esse link no seu navegador. Sua aplicação Gerador de Cotações Bravax estará funcionando online, com todas as funcionalidades, incluindo a geração de PDF!

**Observações:**

*   **Primeiro Deploy:** O primeiro deploy pode demorar alguns minutos para instalar as dependências e construir a imagem.
*   **Atualizações:** Se você precisar atualizar a aplicação (ex: mudar a tabela de preços), basta atualizar os arquivos no seu repositório GitHub e a plataforma (geralmente) fará o deploy da nova versão automaticamente.
*   **Suporte da Plataforma:** Se encontrar problemas específicos durante o deploy, consulte a documentação da plataforma de hospedagem escolhida (Render, Railway, etc.).

Com este `Dockerfile`, o processo de colocar sua aplicação online se torna mais gerenciável, pois as dependências usadas pela aplicação estão automatizadas na "receita". Boa sorte!
