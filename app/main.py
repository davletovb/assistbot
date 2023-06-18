from fastapi import FastAPI
from app.admin import models, auth

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/login")
def login(user: auth.UserLogin):
    return {"token": "your-token-here"}
