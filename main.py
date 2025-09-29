from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from models import User, Capsule, get_db, create_tables
from storage import save_file
import schemas
import os
import openai
from dotenv import load_dotenv
from typing import List
import json
from fastapi import Path


load_dotenv ()
app = FastAPI()
create_tables()


from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

SECRET_KEY = os.getenv("SECRET_KEY")
assert SECRET_KEY is not None, "SECRET_KEY must be set in .env"
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid authentication"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except JWTError:
        raise credentials_exception

@app.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User created"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/capsules")
def upload_capsule(
    title: str = Form(...),
    text: str = Form(...),
    date: str = Form(...),
    tags: str = Form(""),
    files: List[UploadFile] = File(None),
    time_capsule: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        date_obj = datetime.fromisoformat(date)

    except ValueError:
        raise HTTPException(status_code=400,detail="invalid date format")
    

    metadata = {"title": title, "date": date, "tags": tags.split(",")}
    file_urls = []
    for f in files:
        url = save_file(f)
        file_urls.append(url)
    capsule = Capsule(
        user_id=user.id,
        title=title,
        text=text,
        date=date,
        tags=tags,
        media=json.dumps(file_urls),
        time_capsule=time_capsule
    )
    db.add(capsule)
    db.commit()
    db.refresh(capsule)
    return {"msg": "Capsule uploaded", "id": capsule.id}

# Speech Recognition API (OpenAI Whisper)
@app.post("/audio-to-text")
def audio_to_text(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    audio_bytes = file.file.read()
    transcript = openai.Audio.transcribe("whisper-1", audio_bytes, api_key=os.getenv("OPENAI_API_KEY"))
    return {"text": transcript["text"]}

# Text to Audio (TTS)
@app.post("/text-to-audio")
def text_to_audio(textObj: schemas.TextToAudio, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Implement TTS (use gtts or similar for local, or API service for commercial use)
    from gtts import gTTS
    tts = gTTS(textObj.text)
    file_path = f"audio/{user.id}_{int(datetime.now().timestamp())}.mp3"
    tts.save(file_path)
    return {"audio_url": file_path}

@app.get("/capsules")
def get_capsules(
    tag: str = "",
    capsule_type: str = "",
    after: str = "",
    before: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(Capsule).filter(Capsule.user_id == user.id)
    if tag:
        query = query.filter(Capsule.tags.contains(tag))
    if capsule_type:
        query = query.filter(Capsule.media.any(capsule_type))
    if after:
        query = query.filter(Capsule.date >= after)
    if before:
        query = query.filter(Capsule.date <= before)
    return query.order_by(Capsule.date.desc()).all()


@app.delete("/capsules/{capsule_id}")
def delete_capsule(
    capsule_id: int = Path(..., description="ID of the capsule to delete"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    capsule = db.query(Capsule).filter(
        Capsule.id == capsule_id,
        Capsule.user_id == user.id
    ).first()

    if not capsule:
        raise HTTPException(status_code=404, detail="Capsule not found")

    # Delete associated files from disk
    try:
        media_list = json.loads(capsule.media) if capsule.media else []
        for m in media_list:
            if m.startswith("/static/"):  
                filepath = m.lstrip("/")  # remove leading slash
                if os.path.exists(filepath):
                    os.remove(filepath)
    except Exception as e:
        print("File cleanup error:", e)

    # Delete capsule from DB
    db.delete(capsule)
    db.commit()

    return {"msg": "Capsule deleted successfully"}
