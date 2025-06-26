from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# HTML 정적 파일 제공
app.mount("/static", StaticFiles(directory="static"), name="static")

meals = []

class MealData(BaseModel):
    food_name: str
    meal_type: str


@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/food_diary")
async def food_diary():
    return FileResponse("static/food_diary.html")

@app.post("/register-meal")
async def register_meal(data: MealData):
    # 중복 검사
    for meal in meals:
        if meal.food_name == data.food_name and meal.meal_type == data.meal_type:
            raise HTTPException(status_code=400, detail="이미 등록된 음식입니다.")
    
    meals.append(data)
    return {"message": "등록 성공!"}

@app.get("/load-meal")
async def load_meal():
    return [meal.dict() for meal in meals]
