from pydantic import BaseModel

class FoodRequest(BaseModel):
    food_name: str

class NutritionResponse(BaseModel):
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float