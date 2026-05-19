# Imagem base Python
FROM python:3.10-slim

WORKDIR /app

# Dependências do sistema para WeasyPrint (Pango, Cairo, GDK-Pixbuf)
# e fontconfig para registrar a fonte Arial Black
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        fontconfig \
        fonts-liberation \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala Arial Black (necessária para o PDF gerado)
COPY fonts/ariblk.ttf /usr/share/fonts/truetype/ariblk.ttf
RUN fc-cache -fv

# Dependências Python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY . .

# Extrai imagens de fundo do template PPTX para static/slides/
# (executado uma vez no build, não a cada requisição)
RUN python -c "
import zipfile, os, hashlib
os.makedirs('static/slides', exist_ok=True)
pptx = 'input_files/cotacao_auto.pptx'
if os.path.exists(pptx):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = Presentation(pptx)
    for i, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                img = shape.image
                h = hashlib.md5(img.blob).hexdigest()[:8]
                name = f'slide{i+1}_{shape.name.replace(\" \",\"_\")}_{h}.{img.ext}'
                path = f'static/slides/{name}'
                if not os.path.exists(path):
                    with open(path, 'wb') as f:
                        f.write(img.blob)
                    print(f'Extracted: {name}')
                break  # apenas a primeira imagem (background) por slide
    print('Extração concluída.')
else:
    print('AVISO: template PPTX não encontrado.')
"

# Diretório de output
RUN mkdir -p /app/output

EXPOSE 8080

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
