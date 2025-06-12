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
    """GPT 응답에서 JSON 추출 및 처리"""
    try:
        json_str = re.search(r'\{.*\}', response, re.DOTALL).group()
        json_str = json_str.replace("'", '"').replace("`", "")
        return json.loads(json_str)
    except Exception as e:
        st.error(f"GPT 응답 파싱 오류: {str(e)}")
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

def main():
    st.title("🥗 일일 영양소 관리 시스템")
    st.subheader("아침, 점심, 저녁 음식을 입력하면 누적 섭취량과 남은 영양소를 계산합니다")

    # 3개의 입력 필드 추가
    col1, col2, col3 = st.columns(3)
    with col1:
        breakfast = st.text_input("아침 메뉴", placeholder="예) 계란후라이 2개")
    with col2:
        lunch = st.text_input("점심 메뉴", placeholder="예) 참치김치찌개 1인분")
    with col3:
        dinner = st.text_input("저녁 메뉴", placeholder="예) 소고기구이 150g")

    if st.button("영양 분석 시작"):
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        meals = []

        # 각 식사별 영양 정보 수집
        for meal_type, food in [("아침", breakfast), ("점심", lunch), ("저녁", dinner)]:
            if food.strip():
                nutrition = get_nutrition_info(food)
                if not nutrition:
                    st.error(f"{meal_type} 메뉴 분석 실패: {food}")
                    return
                meals.append((meal_type, nutrition))
                for key in total_nutrition:
                    total_nutrition[key] += nutrition.get(key, 0)

        # 남은 영양소 계산
        remaining = {
            nutrient: max(DAILY_GOAL[nutrient] - total_nutrition.get(nutrient, 0), 0)
            for nutrient in DAILY_GOAL
        }

        # 결과 표시
        st.divider()
        st.subheader("📊 식사별 영양소 분석 결과")

        # 식사별 컬럼 표시
        cols = st.columns(len(meals))
        for idx, (col, (meal_type, nutrition)) in enumerate(zip(cols, meals)):
            with col:
                st.markdown(f"### {meal_type}")
                st.metric("칼로리", f"{nutrition['calories']}kcal")
                st.metric("단백질", f"{nutrition['protein']}g")
                st.metric("탄수화물", f"{nutrition['carbs']}g")
                st.metric("지방", f"{nutrition['fat']}g")

        # 누적 결과 표시
        st.divider()
        col_total, col_remaining = st.columns(2)
        
        with col_total:
            st.subheader("💰 총 누적 섭취량")
            st.metric("총 칼로리", f"{total_nutrition['calories']}kcal", 
                    delta=f"목표 대비 {total_nutrition['calories']/DAILY_GOAL['calories']*100:.1f}%")
            st.metric("총 단백질", f"{total_nutrition['protein']}g")
            st.metric("총 탄수화물", f"{total_nutrition['carbs']}g")
            st.metric("총 지방", f"{total_nutrition['fat']}g")

        with col_remaining:
            st.subheader("🎯 남은 목표량")
            st.metric("남은 칼로리", f"{remaining['calories']}kcal", 
                    delta=f"-{total_nutrition['calories']}kcal")
            st.metric("남은 단백질", f"{remaining['protein']}g")
            st.metric("남은 탄수화물", f"{remaining['carbs']}g")
            st.metric("남은 지방", f"{remaining['fat']}g")

        # 진행률 표시바
        st.divider()
        st.subheader("📈 목표 달성 현황")
        for nutrient in DAILY_GOAL:
            progress = total_nutrition[nutrient] / DAILY_GOAL[nutrient]
            st.progress(
                min(progress, 1.0), 
                text=f"{nutrient.capitalize()}: {total_nutrition[nutrient]}/{DAILY_GOAL[nutrient]} ({progress*100:.1f}%)"
            )

        st.info("""
        **해석 가이드**
        - 진행률 100% 이상: 빨간색으로 표시되며 목표를 초과한 상태
        - 남은 영양소가 0인 경우: 추가 섭취가 필요 없음을 의미
        - 단백질은 체중 1kg당 0.8g~1.2g을 권장
        """)

if __name__ == "__main__":
    main()