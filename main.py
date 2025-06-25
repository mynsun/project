from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

meals = []

class MealData(BaseModel):
    food_name: str
    meal_type: str

@app.post("/register-meal")
async def register_meal(data: MealData):
    meals.append(data)
    return {"message": "등록 성공!"}

@app.get("/load-meal")
async def load_meal():
    return [meal.dict() for meal in meals]
