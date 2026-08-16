from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import Base,engine
from app.api.v1 import router
Base.metadata.create_all(bind=engine)
app=FastAPI(title="WHO AM I? API",version="0.2.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
@app.get("/health")
def health():return {"status":"ok","service":"who-am-i","version":"0.2.0"}
FRONTEND=Path(__file__).resolve().parents[2]/"frontend"
if FRONTEND.exists():
    app.mount("/static",StaticFiles(directory=FRONTEND),name="static")
    @app.get("/")
    def home():return FileResponse(FRONTEND/"index.html")
    @app.get("/demo",include_in_schema=False)
    def judge_demo():return FileResponse(FRONTEND/"index.html")
