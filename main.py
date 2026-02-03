from fastapi import FastAPI, Depends, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# DB setup
DATABASE_URL = "sqlite:///./availability.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define how Availability table looks like in the database.
class Availability(Base):
    __tablename__ = "availability"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    day = Column(String)
    time_slot = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI()

# Serve frontend files
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Redirect root to frontend
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/static/index.html", status_code=302)

# Allow CORS (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get database connection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API: Save availability
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

# Returns the availability for the {user_id}... For example, /api/availability/Hamza
@app.get("/api/availability/{user_id}")
def get_user_availability(user_id: str, db: Session = Depends(get_db)):
    entries = (
        db.query(Availability)
        .filter(Availability.user_id == user_id)
        .order_by(Availability.day, Availability.time_slot)
        .all()
    )
    return [{"id": e.id, "user_id": e.user_id, "day": e.day, "time_slot": e.time_slot} for e in entries]

@app.get("/api/availability/{day}/{shift}")
def get_who_on_shift(day: str, shift: str, db: Session = Depends(get_db)):
    entries = (
         db.query(Availability)
         .filter(Availability.day == day)
         .filter(Availability.time_slot == shift)
         .all()
    )
    if not entries:
        raise HTTPException(status_code=404, detail="Shift is unoccupied")
    return [{"on-call":entry.user_id} for entry in entries]

# API: Delete a certain shift for a user... {entry_id} is the id of the shift to delete from the database.
@app.delete("/api/availability/{entry_id}")
def delete_availability(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Availability).filter(Availability.id == entry_id).first() # Returns a Availability object, or None if not found. (SQL row or nothing).
    if not entry:
        raise HTTPException(status_code=404, detail="Shift not found")
    db.delete(entry)
    db.commit()
    return {"ok": True, "deleted_id": entry_id}
