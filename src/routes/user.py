from fastapi import APIRouter, Depends, HTTPException
from src.database.models import User, get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.post('/register')
async def register_user(name: str, email: str, db: Session = Depends(get_db)):
    # check if user already exists
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