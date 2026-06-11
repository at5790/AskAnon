from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import engine, get_db
from .models import Base, ClassSession

import random
import string

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

def generate_join_code():
    letters_and_numbers = string.ascii_uppercase + string.digits
    code = ""

    for i in range(6):
        code += random.choice(letters_and_numbers)

    return code

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html"
    )

@app.get("/professor")
def professor_page(request: Request):
    return templates.TemplateResponse(
        request,
        "professor.html"
    )

@app.post("/create-session")
def create_session(
    title: str = Form(...),
    db: Session = Depends(get_db)
):
    join_code = generate_join_code()

    new_session = ClassSession(
        title=title,
        join_code=join_code
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return RedirectResponse(
        url=f"/dashboard/{new_session.join_code}",
        status_code=303
    )

@app.get("/dashboard/{join_code}")
def dashboard(
    join_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    session = db.query(ClassSession).filter(
        ClassSession.join_code == join_code
    ).first()

    if session is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": "Session not found."}
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"session": session}
    )

@app.get("/student")
def student_page(request: Request, error: str = None):
    return templates.TemplateResponse(
        request,
        "student.html",
        {"error": error}
    )

@app.post("/join-session")
def join_session(
    join_code: str = Form(...),
    db: Session = Depends(get_db)
):
    session = db.query(ClassSession).filter(
        ClassSession.join_code == join_code
    ).first()

    if session is None:
        return RedirectResponse(
            url="/student?error=Invalid join code. Please try again.",
            status_code=303
        )

    return RedirectResponse(
        url=f"/student/session/{session.join_code}",
        status_code=303
    )


@app.get("/student/session/{join_code}")
def student_session(
    join_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    session = db.query(ClassSession).filter(
        ClassSession.join_code == join_code
    ).first()

    if session is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": "Session not found."}
        )

    return templates.TemplateResponse(
        request,
        "student_session.html",
        {"session": session}
    )