import os
import uuid
import boto3

from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# =============================
# ENV
# =============================

DATABASE_URL = os.getenv("DATABASE_URL")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET = os.getenv("MINIO_BUCKET")

# =============================
# DATABASE SETUP
# =============================

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    photo = Column(String)

# =============================
# FASTAPI SETUP
# =============================

app = FastAPI()

# CORS (WAJIB supaya frontend bisa akses)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# MINIO SETUP
# =============================

s3 = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

# Buat bucket otomatis
try:
    s3.create_bucket(Bucket=BUCKET)
except:
    pass

# =============================
# STARTUP
# =============================

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

# =============================
# DATABASE DEPENDENCY
# =============================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================
# ENDPOINTS
# =============================

@app.get("/")
def root():
    return {"message": "API Running 🚀"}

# GET ALL USERS
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# CREATE USER + UPLOAD FOTO
@app.post("/users")
async def create_user(
    name: str = Form(...),
    email: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_name = f"{uuid.uuid4()}_{photo.filename}"

    # Upload ke MinIO
    s3.upload_fileobj(photo.file, BUCKET, file_name)

    # Simpan ke database
    user = User(name=name, email=email, photo=file_name)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

# UPDATE USER
@app.put("/users/{user_id}")
def update_user(
    user_id: int,
    name: str,
    email: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return {"message": "User tidak ditemukan"}

    user.name = name
    user.email = email

    db.commit()
    db.refresh(user)

    return user
# DELETE USER
@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return {"message": "User tidak ditemukan"}

    # Hapus foto dari MinIO
    try:
        s3.delete_object(Bucket=BUCKET, Key=user.photo)
    except:
        pass

    # Hapus user dari database
    db.delete(user)
    db.commit()

    return {"message": "User berhasil dihapus"}
