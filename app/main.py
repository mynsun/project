from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai
import json
import re

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()


class FoodRequest(BaseModel):
    food_name: str

class NutritionGapResponse(BaseModel):
    food_name: str
    serving_nutrition: dict
    daily_gap: dict

PROMPT_TEMPLATE = """
{food_name}의 1인분(typical serving size) 기준 영양성분을 아래 형식으로 JSON 출력:
{{
    "calories": 칼로리(정수),
    "protein": 단백질(g),
    "carbs": 탄수화물(g),
    "fat": 지방(g)
}}
"""

DAILY_GOAL = {
    "calories": 2300,
    "protein": 56, 
    "carbs": 300,
    "fat": 70
}

def parse_gpt_response(response: str) -> dict:
    """GPT 응답에서 JSON 추출"""
    try:
        json_str = re.search(r'\{.*\}', response, re.DOTALL).group()
        json_str = json_str.replace("'", '"').replace("`", "")
        return json.loads(json_str)
    except Exception as e:
        raise HTTPException(500, f"GPT 응답 파싱 실패: {str(e)}")

@app.post("/analyze-daily-gap", response_model=NutritionGapResponse)
async def analyze_daily_gap(request: FoodRequest):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": PROMPT_TEMPLATE.format(food_name=request.food_name)
            }]
        )
        
        nutrition = parse_gpt_response(response.choices[0].message.content)
        
        gap_percent = {
            nutrient: round((nutrition.get(nutrient, 0) / DAILY_GOAL[nutrient]) * 100, 1)
            for nutrient in ["calories", "protein", "carbs", "fat"]
        }
        
        return {
            "food_name": request.food_name,
            "serving_nutrition": nutrition,
            "daily_gap": gap_percent
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(500, f"서버 오류: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)