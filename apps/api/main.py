import os

import psycopg
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="ArtBid API",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}
