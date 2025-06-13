import streamlit as st
import openai
import json
import re
from dotenv import load_dotenv
import os

st.set_page_config(page_title="AI 영양 관리 시스템", layout="wide")

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DAILY_GOAL = {
    "calories": 2300,
    "protein": 56,
    "carbs": 300,
    "fat": 70
}

def parse_gpt_response(response: str) -> dict:
    try:
        json_match = re.search(r'({[\s\S]*})', response)
        if not json_match:
            raise ValueError("JSON 형식을 찾을 수 없습니다")
        json_str = json_match.group(1)
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'(?m)//.*$', '', json_str)
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return json.loads(json_str)
    except Exception as e:
        st.error(f"JSON 파싱 실패: {str(e)}")
        return None

def get_nutrition_info(food_name: str) -> dict:
    prompt = f"""
    Please provide the nutritional information for one typical serving size of {food_name} in the following JSON format.
    The answer must be in Korean, and only output the JSON (no explanation, no comments).
    {{
        "calories": 정수,
        "protein": 실수,
        "carbs": 실수,
        "fat": 실수
    }}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return parse_gpt_response(response.choices[0].message.content)
    except Exception as e:
        st.error(f"OpenAI API 오류: {str(e)}")
        return None

def get_side_dish_recommendations(main_dish: str):
    prompt = f"""
    Please recommend 3 Korean side dishes that go well with {main_dish}. 
    The answer must be in Korean, and only output the following JSON format (no explanation, no comments):
    {{
        "recommendations": [
            "반찬1",
            "반찬2",
            "반찬3"
        ]
    }}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_gpt_response(response.choices[0].message.content)
        return result.get("recommendations", []) if result else []
    except Exception as e:
        st.error(f"반찬 추천 오류: {str(e)}")
        return []

def update_meal_input(meal_type: str, selected_dish: str):
    current_value = st.session_state.get(f"{meal_type}_input", "")
    new_value = f"{current_value}, {selected_dish}".strip(", ")
    st.session_state[f"{meal_type}_input"] = new_value

def get_recommendations_from_gpt(remaining, meal_type="general"):
    prompt = f"""
Please recommend 3 different meal sets (each containing 2-4 dishes) in the following JSON format.
Use actual nutritional values for each dish. All responses must be in Korean.
Only output the JSON, no explanation or comments.

{{
    "recommendations": [
        {{
            "name": "식단 이름",
            "menu": [
                {{
                    "name": "음식명",
                    "calories": 숫자,
                    "protein": 숫자,
                    "carbs": 숫자,
                    "fat": 숫자
                }},
                ...
            ],
            "total_calories": 합계,
            "total_protein": 합계,
            "total_carbs": 합계,
            "total_fat": 합계
        }},
        ...
    ]
}}

[Remaining Nutrition]
- Calories: {remaining['calories']}kcal
- Protein: {remaining['protein']}g
- Carbs: {remaining['carbs']}g
- Fat: {remaining['fat']}g

Conditions:
1. Each meal set must not exceed remaining values.
2. {"Consider dinner (600kcal) if recommending lunch." if meal_type == "lunch" else "Recommend realistic combinations for one meal."}
3. All dish names in Korean.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_gpt_response(response.choices[0].message.content)
        valid_recommendations = []
        if result and "recommendations" in result:
            for rec in result["recommendations"]:
                sum_cal = sum(item["calories"] for item in rec["menu"])
                sum_pro = sum(item["protein"] for item in rec["menu"])
                sum_carb = sum(item["carbs"] for item in rec["menu"])
                sum_fat = sum(item["fat"] for item in rec["menu"])
                if (sum_cal <= remaining["calories"] and
                    sum_pro <= remaining["protein"] and
                    sum_carb <= remaining["carbs"] and
                    sum_fat <= remaining["fat"]):
                    rec["total_calories"] = sum_cal
                    rec["total_protein"] = round(sum_pro, 1)
                    rec["total_carbs"] = round(sum_carb, 1)
                    rec["total_fat"] = round(sum_fat, 1)
                    # 소수점 첫째자리로 각 음식도 반영
                    for item in rec["menu"]:
                        item["calories"] = round1(item["calories"])
                        item["protein"] = round1(item["protein"])
                        item["carbs"] = round1(item["carbs"])
                        item["fat"] = round1(item["fat"])
                    rec["total_calories"] = round1(rec["total_calories"])
                    rec["total_protein"] = round1(rec["total_protein"])
                    rec["total_carbs"] = round1(rec["total_carbs"])
                    rec["total_fat"] = round1(rec["total_fat"])
                    valid_recommendations.append(rec)
            return valid_recommendations
        return []
    except Exception as e:
        st.error(f"추천 생성 오류: {str(e)}")
        return []

def round1(x):
    try:
        return round(float(x), 1)
    except:
        return x

def main():
    st.title("🍽️ 스마트 식단 관리 시스템")
    
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = {}
    
    meal_types = ["breakfast", "lunch", "dinner"]
    meal_labels = ["아침", "점심", "저녁"]
    meal_inputs = {}

    for i, (meal_type, label) in enumerate(zip(meal_types, meal_labels)):
        col1, col2 = st.columns([3, 1])
        with col1:
            meal_input = st.text_input(
                f"{label} 메뉴",
                key=f"{meal_type}_input",
                placeholder="예: 계란후라이 2개"
            )
            meal_inputs[meal_type] = meal_input
        
        with col2:
            if meal_input:
                main_dish = meal_input.split(",")[0].strip()
                if st.button(f"반찬 추천받기 ({label})", key=f"{meal_type}_btn"):
                    recommendations = get_side_dish_recommendations(main_dish)
                    st.session_state.recommendations[meal_type] = recommendations

    for meal_type in meal_types:
        if st.session_state.recommendations.get(meal_type):
            st.write(f"### {meal_labels[meal_types.index(meal_type)]} 추천 반찬")
            cols = st.columns(3)
            for idx, rec in enumerate(st.session_state.recommendations[meal_type]):
                with cols[idx]:
                    st.write(f"- {rec}")
                    st.button(
                        f"추가하기 {idx+1}",
                        key=f"add_{meal_type}_{idx}",
                        on_click=update_meal_input,
                        args=(meal_type, rec),
                    )

    if st.button("영양 분석 & 식단 추천"):
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        registered_meals = {"breakfast": False, "lunch": False, "dinner": False}
        meal_details = []

        for meal_type in meal_types:
            if meal_inputs[meal_type].strip():
                registered_meals[meal_type] = True
                food_list = [f.strip() for f in meal_inputs[meal_type].split(",") if f.strip()]
                meal_total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
                for food in food_list:
                    nutrition = get_nutrition_info(food)
                    if nutrition:
                        for key in meal_total:
                            meal_total[key] += nutrition.get(key, 0)
                for key in total_nutrition:
                    total_nutrition[key] += meal_total[key]
                meal_details.append((meal_type, meal_total))

        remaining = {
            nut: round1(max(DAILY_GOAL[nut] - total_nutrition[nut], 0))
            for nut in DAILY_GOAL
        }
        meal_type = "general"
        if registered_meals["lunch"] and not registered_meals["dinner"]:
            remaining["calories"] = max(remaining["calories"] - 600, 0)
            meal_type = "lunch"

        st.divider()
        st.subheader("📊 영양 분석 결과")
        if meal_details:
            cols = st.columns(len(meal_details))
            for idx, (col, (meal_type, nutrition)) in enumerate(zip(cols, meal_details)):
                with col:
                    st.markdown(f"### {meal_type.capitalize()}")
                    st.write(f"**칼로리**: {round1(nutrition['calories'])}kcal")
                    st.write(f"**단백질**: {round1(nutrition['protein'])}g")
                    st.write(f"**탄수화물**: {round1(nutrition['carbs'])}g")
                    st.write(f"**지방**: {round1(nutrition['fat'])}g")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 총 섭취량")
            st.metric("칼로리", f"{round1(total_nutrition['calories'])}kcal")
            st.metric("단백질", f"{round1(total_nutrition['protein'])}g")
            st.metric("탄수화물", f"{round1(total_nutrition['carbs'])}g")
            st.metric("지방", f"{round1(total_nutrition['fat'])}g")
        with col2:
            st.markdown("### 남은 섭취량")
            st.metric("칼로리", f"{round1(remaining['calories'])}kcal")
            st.metric("단백질", f"{round1(remaining['protein'])}g")
            st.metric("탄수화물", f"{round1(remaining['carbs'])}g")
            st.metric("지방", f"{round1(remaining['fat'])}g")

        st.divider()
        st.subheader("🍱 한 끼 식단 추천")
        recommendations = get_recommendations_from_gpt(remaining, meal_type)
        if recommendations:
            cols = st.columns(3)
            for idx, (col, rec) in enumerate(zip(cols, recommendations)):
                with col:
                    with st.expander(f"추천 식단 {idx+1}: {rec['name']}", expanded=True):
                        st.write("구성 메뉴:")
                        for item in rec['menu']:
                            st.write(f"- {item['name']} ({round1(item['calories'])}kcal, 단백질 {round1(item['protein'])}g, 탄수화물 {round1(item['carbs'])}g, 지방 {round1(item['fat'])}g)")
                        st.markdown(f"""
**영양소 총합**  
- 칼로리: {round1(rec['total_calories'])}kcal, 단백질: {round1(rec['total_protein'])}g, 탄수화물: {round1(rec['total_carbs'])}g, 지방: {round1(rec['total_fat'])}g
""")
        else:
            st.warning("조건에 맞는 추천을 찾지 못했습니다")

if __name__ == "__main__":
    main()
