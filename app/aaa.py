import streamlit as st
import openai
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DAILY_GOAL = {
    "calories": 2300,
    "protein": 56,
    "carbs": 300,
    "fat": 70
}

def parse_gpt_response(response: str) -> dict:
    """GPT 응답에서 JSON 추출 및 처리 (강화된 버전)"""
    try:
        json_match = re.search(r'({.*})', response, re.DOTALL)
        if not json_match:
            raise ValueError("JSON 형식을 찾을 수 없습니다")
        
        json_str = json_match.group(1)
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'//.*', '', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json.loads(json_str)
    except Exception as e:
        st.error(f"JSON 파싱 실패: {str(e)}")
        st.write("문제가 발생한 응답 내용:", response)
        return None

def get_nutrition_info(food_name: str) -> dict:
    """OpenAI API를 이용한 영양정보 추출"""
    prompt = f"""
    {food_name}의 1인분(typical serving size) 기준 영양성분을 아래 형식으로 JSON 출력:
    {{
        "calories": 칼로리(정수),
        "protein": 단백질(g),
        "carbs": 탄수화물(g),
        "fat": 지방(g)
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

def get_recommendations_from_gpt(remaining):
    prompt = f"""
    [영양소 정보]
    - 남은 칼로리: {remaining['calories']}kcal
    - 남은 단백질: {remaining['protein']}g
    - 남은 탄수화물: {remaining['carbs']}g
    - 남은 지방: {remaining['fat']}g

    다음 조건에 맞는 한국 한 끼 식단(메인, 밥, 반찬 등 2~4가지 조합)을 2세트 추천해주세요:
    1. 각 식단은 1인분 기준 전체 영양소가 남은 양을 초과하지 않을 것
    2. 대한민국에서 흔히 접할 수 있는 전통·현대 한식 조합
    3. 일반 가정에서 쉽게 준비할 수 있는 메뉴로 구성
    4. 각 식단별로 음식명/기준량/영양성분(칼로리, 단백질, 탄수화물, 지방) 총합을 표기
    5. 출력 형식:
    {{
        "recommendations": [
            {{
                "menu": ["음식1 (예: 김치찌개 1인분)", "음식2 (예: 밥 1공기)", ...],
                "total_calories": 숫자,
                "total_protein": 숫자,
                "total_carbs": 숫자,
                "total_fat": 숫자
            }},
            ...
        ]
    }}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_gpt_response(response.choices[0].message.content)
        if result and "recommendations" in result:
            return result["recommendations"]
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
    st.title("한 끼 식단 추천")
    st.subheader("아침/점심/저녁 입력 → 남은 영양소 분석 → AI 한 끼 식단 추천")

    # 식사 입력 필드
    col1, col2, col3 = st.columns(3)
    meals = {}
    with col1:
        meals["breakfast"] = st.text_input("아침 메뉴", placeholder="계란후라이 2개, 바나나 1개")
    with col2:
        meals["lunch"] = st.text_input("점심 메뉴", placeholder="김치찌개 1인분, 현미밥 1공기")
    with col3:
        meals["dinner"] = st.text_input("저녁 메뉴", placeholder="소고기 150g, 두부조림")

    if st.button("영양 분석 & 추천 받기"):
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        registered_meals = {"breakfast": False, "lunch": False, "dinner": False}
        meal_details = []

        # 영양소 계산
        for meal_type in ["breakfast", "lunch", "dinner"]:
            if meals[meal_type].strip():
                registered_meals[meal_type] = True
                food_list = [f.strip() for f in meals[meal_type].split(",") if f.strip()]
                meal_total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
                
                for food in food_list:
                    nutrition = get_nutrition_info(food)
                    if nutrition:
                        for key in meal_total:
                            meal_total[key] += nutrition.get(key, 0)
                
                for key in total_nutrition:
                    total_nutrition[key] += meal_total[key]
                meal_details.append((meal_type, meal_total))

        # 남은 영양소 계산
        remaining = {
            nut: round1(max(DAILY_GOAL[nut] - total_nutrition[nut], 0))
            for nut in DAILY_GOAL
        }

        # 결과 표시
        st.divider()
        st.subheader("📊 영양 분석 결과")
        
        # 식사별 분석
        if any(registered_meals.values()):
            cols = st.columns(len([m for m in registered_meals.values() if m]))
            for idx, (col, (meal_type, nutrition)) in enumerate(zip(cols, meal_details)):
                with col:
                    st.markdown(f"### {meal_type.capitalize()}")
                    st.write(f"**칼로리**: {round1(nutrition['calories'])}kcal")
                    st.write(f"**단백질**: {round1(nutrition['protein'])}g")
                    st.write(f"**탄수화물**: {round1(nutrition['carbs'])}g")
                    st.write(f"**지방**: {round1(nutrition['fat'])}g")

        # 종합 리포트
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
            st.metric("칼로리", f"{remaining['calories']}kcal")
            st.metric("단백질", f"{remaining['protein']}g")
            st.metric("탄수화물", f"{remaining['carbs']}g")
            st.metric("지방", f"{remaining['fat']}g")

        # AI 추천 시스템
        st.divider()
        st.subheader("한 끼 식단 추천")
        
        registered_count = sum(1 for meal in registered_meals.values() if meal)
        if registered_count == 0:
            st.warning("아직 음식이 등록되지 않았습니다! 아침/점심/저녁 메뉴를 입력해주세요.")
        elif registered_count < 3:
            if all(value <= 0 for value in remaining.values()):
                st.success("🎉 모든 영양소를 충족했습니다! 추가 섭취가 필요 없습니다.")
            else:
                recommendations = get_recommendations_from_gpt(remaining)
                if recommendations:
                    for idx, meal_set in enumerate(recommendations, 1):
                        st.markdown(f"""
**추천 식단 {idx}**
- {', '.join(meal_set['menu'])}
- **총합**: {meal_set['total_calories']}kcal / 
    단백질 {meal_set['total_protein']}g / 
    탄수화물 {meal_set['total_carbs']}g / 
    지방 {meal_set['total_fat']}g
""")
                        st.write("---")
                else:
                    st.warning("추천 메뉴를 생성하는 데 실패했습니다. 다시 시도해주세요.")
        else:
            st.success("🎉 오늘의 모든 식사를 마쳤습니다! 내일도 건강하게 식사하세요.")

if __name__ == "__main__":
    main()
