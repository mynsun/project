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
    st.title("🍽️ 다중 음식 영양소 계산기")
    st.subheader("아침/점심/저녁 별로 여러 음식을 콤마(,)로 구분해 입력하세요")

    # 3개의 입력 필드
    col1, col2, col3 = st.columns(3)
    with col1:
        breakfast = st.text_input("아침 메뉴", placeholder="계란후라이 2개, 바나나 1개")
    with col2:
        lunch = st.text_input("점심 메뉴", placeholder="김치찌개 1인분, 현미밥 1공기")
    with col3:
        dinner = st.text_input("저녁 메뉴", placeholder="소고기 150g, 두부조림")

    if st.button("계산 시작"):
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        meal_details = []

        # 각 식사별 처리
        for meal_type, foods in [("아침", breakfast), ("점심", lunch), ("저녁", dinner)]:
            if foods.strip():
                food_list = [f.strip() for f in foods.split(",") if f.strip()]
                meal_total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
                for food in food_list:
                    nutrition = get_nutrition_info(food)
                    if nutrition:
                        for key in meal_total:
                            meal_total[key] += nutrition.get(key, 0)
                for key in total_nutrition:
                    total_nutrition[key] += meal_total[key]
                meal_details.append((meal_type, meal_total))

        # 남은 영양소 계산 (탄단지 소수점 1자리)
        remaining = {
            "calories": max(DAILY_GOAL["calories"] - total_nutrition["calories"], 0),
            "protein": round(max(DAILY_GOAL["protein"] - total_nutrition["protein"], 0), 1),
            "carbs": round(max(DAILY_GOAL["carbs"] - total_nutrition["carbs"], 0), 1),
            "fat": round(max(DAILY_GOAL["fat"] - total_nutrition["fat"], 0), 1)
        }

        st.divider()
        st.subheader("🔍 식사별 상세 분석")
        cols = st.columns(len(meal_details))
        for idx, (col, (meal_type, nutrition)) in enumerate(zip(cols, meal_details)):
            with col:
                st.markdown(f"### {meal_type}")
                st.write(f"**칼로리**: {nutrition['calories']}kcal")
                st.write(f"**단백질**: {nutrition['protein']}g")
                st.write(f"**탄수화물**: {nutrition['carbs']}g")
                st.write(f"**지방**: {nutrition['fat']}g")

        st.divider()
        st.subheader("📈 종합 리포트")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 총 섭취량")
            st.metric("칼로리", f"{total_nutrition['calories']}kcal")
            st.metric("단백질", f"{total_nutrition['protein']}g")
            st.metric("탄수화물", f"{total_nutrition['carbs']}g")
            st.metric("지방", f"{total_nutrition['fat']}g")
        with col2:
            st.markdown("### 남은 섭취량")
            st.metric("칼로리", f"{remaining['calories']}kcal")
            st.metric("단백질", f"{remaining['protein']}g")
            st.metric("탄수화물", f"{remaining['carbs']}g")
            st.metric("지방", f"{remaining['fat']}g")

        st.divider()
        st.subheader("📊 영양소 분포 (칼로리 제외)")
        chart_data = {
            "영양소": ["단백질", "탄수화물", "지방"],
            "섭취량": [
                total_nutrition["protein"],
                total_nutrition["carbs"],
                total_nutrition["fat"]
            ]
        }
        st.bar_chart(chart_data, x="영양소", y="섭취량")

if __name__ == "__main__":
    main()