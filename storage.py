# import os

# def save_file(file):
#     save_dir = "uploads/"
#     os.makedirs(save_dir, exist_ok=True)
#     file_path = os.path.join(save_dir, file.filename)
#     with open(file_path, "wb") as buffer:
#         buffer.write(file.file.read())
#     return file_path

import os
from fastapi import UploadFile
from datetime import datetime
import shutil

# Create uploads directory inside "static"
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_file(file: UploadFile) -> str:
    """
    Save uploaded file into static/uploads and return its relative URL
    """
    # Generate safe unique filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Return URL path (FastAPI will serve this via /static route)
    return f"/static/uploads/{filename}"
