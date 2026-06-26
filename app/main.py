from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import engine, get_db
from .models import Base, ClassSession, Question

import random
import string

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

def get_voted_question_ids(request: Request):
    voted_cookie = request.cookies.get("voted_questions", "")

    voted_ids = set()

    for item in voted_cookie.split(","):
        if item.isdigit():
            voted_ids.add(int(item))

    return voted_ids


def save_voted_question_ids(response: RedirectResponse, voted_ids):
    cookie_value = ",".join(str(question_id) for question_id in sorted(voted_ids))

    response.set_cookie(
        key="voted_questions",
        value=cookie_value,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax"
    )

def generate_join_code():
    letters_and_numbers = string.ascii_uppercase + string.digits
    code = ""

    for i in range(6):
        code += random.choice(letters_and_numbers)

    return code

def get_my_question_ids(request: Request):
    my_questions_cookie = request.cookies.get("my_questions", "")

    my_question_ids = set()

    for item in my_questions_cookie.split(","):
        if item.isdigit():
            my_question_ids.add(int(item))

    return my_question_ids


def save_my_question_ids(response: RedirectResponse, my_question_ids):
    cookie_value = ",".join(str(question_id) for question_id in sorted(my_question_ids))

    response.set_cookie(
        key="my_questions",
        value=cookie_value,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax"
    )

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

    questions = db.query(Question).filter(
        Question.session_id == session.id
    ).order_by(Question.upvotes.desc()).all()

    total_questions = len(questions)

    total_upvotes = 0
    for question in questions:
        total_upvotes += question.upvotes

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "session": session,
            "questions": questions,
            "total_questions": total_questions,
            "total_upvotes": total_upvotes
        }
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

    questions = db.query(Question).filter(
        Question.session_id == session.id
    ).order_by(Question.upvotes.desc()).all()

    voted_ids = get_voted_question_ids(request)
    my_question_ids = get_my_question_ids(request)

    return templates.TemplateResponse(
        request,
        "student_session.html",
        {
            "session": session,
            "questions": questions,
            "voted_ids": voted_ids,
            "my_question_ids": my_question_ids

        }
    )

@app.post("/ask-question")
def ask_question(
    request: Request,
    join_code: str = Form(...),
    text: str = Form(...),
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

    new_question = Question(
        text=text,
        session_id=session.id
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    my_question_ids = get_my_question_ids(request)
    my_question_ids.add(new_question.id)

    response = RedirectResponse(
        url=f"/student/session/{session.join_code}",
        status_code=303
    )

    save_my_question_ids(response, my_question_ids)

    return response

@app.post("/upvote/{question_id}")
def upvote_question(
    question_id: int,
    request: Request, 
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(
        Question.id == question_id
    ).first()

    if question is None:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    session = db.query(ClassSession).filter(
        ClassSession.id == question.session_id
    ).first()

    voted_ids = get_voted_question_ids(request)
    my_question_ids = get_my_question_ids(request)

    if question.id not in voted_ids and question.id not in my_question_ids:
        question.upvotes += 1
        db.commit()
        voted_ids.add(question.id)

    response = RedirectResponse(
        url=f"/student/session/{session.join_code}",
        status_code=303
    )

    save_voted_question_ids(response, voted_ids)

    return response