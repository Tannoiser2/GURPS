# Backend GURPS — immagine con OCR (tesseract) per il fallback sui PDF con
# text-layer corrotto. Il runtime python nativo di Render non consente apt-get,
# quindi per abilitare l'OCR si usa questa immagine Docker.
FROM python:3.11-slim

# Tesseract OCR + pacchetto lingua italiana (e inglese, già incluso di base).
# Senza questi, l'app funziona comunque ma salta l'OCR e usa il testo embedded.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-ita \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installa prima le dipendenze (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice del backend (il contesto build è ./backend)
COPY . .

# Render/Railway iniettano $PORT; default 8000 in locale.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn App.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
