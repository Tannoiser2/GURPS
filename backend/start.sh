#!/bin/bash
# Carica variabili d'ambiente se esiste il file .env
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi
uvicorn App.main:app --host 127.0.0.1 --port 8002 --reload
