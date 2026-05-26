from fastapi import FastAPI

from backend.App.main import app as backend_app


app = FastAPI()
app.mount("/_/backend", backend_app)
