from fastapi import APIRouter, Depends, HTTPException, Response
from src.database.models import User, get_db
from sqlalchemy.orm import Session
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    name: str
    email: str

@router.post('/register')
async def register_user(user: UserCreate, response: Response, db: Session = Depends(get_db)):
    # check if user already exists
    name = user.name
    email = user.email
    print(name, email)
    user = db.query(User).filter(User.email == email).first()
    if (user != None):
        return user
    # save email to database
    new_user = User(name=name, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get('/{email}')
async def get_user(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if (user == None):
        return {"message": "User not found"}
    return user