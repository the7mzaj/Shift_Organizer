from fastapi import FastAPI, Depends, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# -----------------------------
# Database setup (SQLite)
# -----------------------------
DATABASE_URL = "sqlite:///./availability.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Availability(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    day = Column(String)
    time_slot = Column(String)


Base.metadata.create_all(bind=engine)

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI()

# Serve the frontend from /static
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Convenience: redirect "/" -> "/static/index.html"
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/static/index.html", status_code=302)

# CORS (safe to keep on for local dev; same-origin won't need it)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can lock this down later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Dependency to get DB session
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# API (prefix all endpoints with /api/*)
# -----------------------------

# Create availability entry
@app.post("/api/availability")
def create_availability(
    user_id: str = Form(...),
    day: str = Form(...),
    time_slot: str = Form(...),
    db: Session = Depends(get_db),
):
    entry = Availability(user_id=user_id, day=day, time_slot=time_slot)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "user_id": entry.user_id, "day": entry.day, "time_slot": entry.time_slot}

# Get all availability for a user
@app.get("/api/availability/{user_id}")
def get_user_availability(user_id: str, db: Session = Depends(get_db)):
    entries = (
        db.query(Availability)
        .filter(Availability.user_id == user_id)
        .order_by(Availability.day, Availability.time_slot)
        .all()
    )
    return [{"id": e.id, "user_id": e.user_id, "day": e.day, "time_slot": e.time_slot} for e in entries]

# Delete a specific availability entry by its ID
@app.delete("/api/availability/{entry_id}")
def delete_availability(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Availability).filter(Availability.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Shift not found")
    db.delete(entry)
    db.commit()
    return {"ok": True, "deleted_id": entry_id}
