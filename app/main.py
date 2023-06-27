from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBasicCredentials
from app.admin import models, auth, crud, schemas
from app.core.base_bot import BaseBot
from app.bot_template.telegram_webhook import TelegramWebhookHandler
from app.bot_template.telegram_bot import TelegramBot
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
from app.database import SessionLocal, engine
import redis
import subprocess

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

r = redis.Redis(host='localhost', port=6379, db=0)


@app.on_event("startup")
async def startup_event():
    # Initialize your bots here
    telegram_bot = TelegramBot("your-telegram-bot-token")
    telegram_webhook_handler = TelegramWebhookHandler(
        "your-telegram-bot-token")
    await telegram_webhook_handler.set_webhook("your-webhook-url")


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate_user(
        crud.fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)


@app.get("/bot/{bot_id}")
def read_bot(bot_id: int, status: Optional[str] = None, credentials: HTTPBasicCredentials = Depends(auth.authenticate)):
    try:
        if status:
            # Update bot status in Redis
            r.set(bot_id, status)
        # Get bot status from Redis
        status = r.get(bot_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Bot not found")
        return {"bot_id": bot_id, "status": status}
    except redis.RedisError:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/start_bot/{bot_id}")
def start_bot(bot_id: int, credentials: HTTPBasicCredentials = Depends(auth.authenticate)):
    # Start the Telegram bot
    subprocess.Popen(["python", f"bot_{bot_id}.py"])
    return {"bot_id": bot_id, "status": "starting"}
