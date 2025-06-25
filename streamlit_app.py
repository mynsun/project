import streamlit as st
import openai
import json
import re

# OpenAI API 키 설정
openai.api_key = st.secrets["OPENAI_API_KEY"]

# JSON 파싱 함수
def parse_gpt_response(response_text):
    try:
        json_str = re.search(r'\{.*\}', response_text, re.DOTALL).group()
        return json.loads(json_str)
    except Exception as e:
        st.error(f"GPT 응답 파싱 오류: {e}")
        return None

# 영양 정보 추출 함수 (프롬프트 영어, 답변 한국어)
def get_nutrition_info(food_name):
    prompt = f"""
Please provide the calories, protein, carbohydrates, and fat for the following food in JSON format.
Use these keys only: calories, protein, carbs, fat. Values must be numbers only.
Food: {food_name}
Please answer in Korean.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a nutrition expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        return parse_gpt_response(response.choices[0].message['content'])
    except Exception as e:
        st.error(f"영양 정보 조회 오류: {e}")
        return None

# 반찬 추천 함수 (프롬프트 영어, 답변 한국어)
def get_side_dish_recommendation(main_dish):
    prompt = f"""
Please recommend 3 Korean side dishes that go well with '{main_dish}'.
List only the dish names, separated by commas.
Please answer in Korean.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a Korean food expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return response.choices[0].message['content'].split(',')
    except Exception as e:
        st.error(f"반찬 추천 오류: {e}")
        return []

# 식단 추천 함수 (프롬프트 영어, 답변 한국어)
def get_recommendations_from_gpt(remaining_nutrition, cheating=False):
    prompt = f"""
Based on the following nutrients, recommend a daily Korean meal plan (breakfast, lunch, dinner).
Calories: {remaining_nutrition['calories']}kcal,
Protein: {remaining_nutrition['protein']}g,
Carbohydrates: {remaining_nutrition['carbs']}g,
Fat: {remaining_nutrition['fat']}g

{"Include cheat day options." if cheating else ""}
Please output in the following format:
Breakfast: [food1, food2, ...]
Lunch: [food1, food2, ...]
Dinner: [food1, food2, ...]
Please answer in Korean.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a nutrition expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message['content']
    except Exception as e:
        st.error(f"식단 추천 오류: {e}")
        return ""

# 숫자 포맷팅 함수
def round1(num):
    return round(num, 1)

def main():
    st.title("AI 영양 관리 시스템")

    # 사진 등록 식사 시간 선택
    st.subheader("사진으로 음식 등록")
    meal_type = st.radio("등록할 식사 시간 선택:", ["아침", "점심", "저녁"], key="meal_type_selector")

    # 사진 등록 버튼
    if st.button("📸 사진으로 음식 등록", key="photo_upload"):
        js = f"""
        <script>
            window.open('http://15.164.56.89:30800/?meal_type={meal_type}','_blank');
        </script>
        """
        st.components.v1.html(js, height=0)

    # 사진 분석 결과 처리 (쿼리 파라미터로부터)
    query_params = st.experimental_get_query_params()
    photo_result = query_params.get("photo_result", [None])[0]
    photo_meal_type = query_params.get("meal_type", [None])[0]

    if photo_result and photo_meal_type:
        if photo_meal_type == "아침":
            st.session_state.breakfast_input = photo_result
        elif photo_meal_type == "점심":
            st.session_state.lunch_input = photo_result
        elif photo_meal_type == "저녁":
            st.session_state.dinner_input = photo_result
        st.experimental_set_query_params()

    # 식사 입력 섹션
    st.subheader("아침 먹은 음식")
    breakfast_input = st.text_input("아침에 먹은 음식을 입력하세요",
                                    key="breakfast_input",
                                    value=st.session_state.get("breakfast_input", ""))

    st.subheader("점심 먹은 음식")
    lunch_input = st.text_input("점심에 먹은 음식을 입력하세요",
                                key="lunch_input",
                                value=st.session_state.get("lunch_input", ""))

    st.subheader("저녁 먹은 음식")
    dinner_input = st.text_input("저녁에 먹은 음식을 입력하세요",
                                 key="dinner_input",
                                 value=st.session_state.get("dinner_input", ""))

    # 반찬 추천 섹션
    st.subheader("반찬 추천받기")
    selected_meal = st.radio("식사를 선택하세요", ["아침", "점심", "저녁"], key="side_meal_selector")
    if st.button("반찬 추천받기"):
        meal_input = breakfast_input if selected_meal == "아침" else lunch_input if selected_meal == "점심" else dinner_input
        if meal_input:
            side_dishes = get_side_dish_recommendation(meal_input)
            st.session_state.side_dishes = side_dishes
        else:
            st.warning("메인 메뉴를 먼저 입력해주세요.")

    if 'side_dishes' in st.session_state:
        st.write("추천 반찬:")
        for dish in st.session_state.side_dishes:
            st.write(f"- {dish.strip()}")

    # 영양 분석 및 추천 섹션
    st.subheader("영양 분석 및 식단 추천")
    cheating = st.checkbox("치팅 데이 적용 (더 다양한 식단 추천)")
    if st.button("영양 분석 & 식단 추천"):
        meals = [breakfast_input, lunch_input, dinner_input]
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        for meal in meals:
            if meal:
                nutrition = get_nutrition_info(meal)
                if nutrition:
                    for key in total_nutrition:
                        total_nutrition[key] += nutrition.get(key, 0)
        target_nutrition = {"calories": 2000, "protein": 150, "carbs": 250, "fat": 70}
        remaining_nutrition = {
            "calories": max(0, target_nutrition["calories"] - total_nutrition["calories"]),
            "protein": max(0, target_nutrition["protein"] - total_nutrition["protein"]),
            "carbs": max(0, target_nutrition["carbs"] - total_nutrition["carbs"]),
            "fat": max(0, target_nutrition["fat"] - total_nutrition["fat"])
        }
        st.session_state.total_nutrition = total_nutrition
        st.session_state.target_nutrition = target_nutrition
        st.session_state.remaining_nutrition = remaining_nutrition
        recommendations = get_recommendations_from_gpt(remaining_nutrition, cheating)
        st.session_state.recommendations = recommendations

    # 결과 표시
    if 'total_nutrition' in st.session_state:
        st.subheader("영양 분석 결과")
        st.markdown("""
        | 구분 | 칼로리(kcal) | 단백질(g) | 탄수화물(g) | 지방(g) |
        |------|--------------|-----------|-------------|---------|
        | 섭취 | {calories} | {protein} | {carbs} | {fat} |
        | 목표 | {target_calories} | {target_protein} | {target_carbs} | {target_fat} |
        | 남음 | {remaining_calories} | {remaining_protein} | {remaining_carbs} | {remaining_fat} |
        """.format(
            calories=round1(st.session_state.total_nutrition['calories']),
            protein=round1(st.session_state.total_nutrition['protein']),
            carbs=round1(st.session_state.total_nutrition['carbs']),
            fat=round1(st.session_state.total_nutrition['fat']),
            target_calories=round1(st.session_state.target_nutrition['calories']),
            target_protein=round1(st.session_state.target_nutrition['protein']),
            target_carbs=round1(st.session_state.target_nutrition['carbs']),
            target_fat=round1(st.session_state.target_nutrition['fat']),
            remaining_calories=round1(st.session_state.remaining_nutrition['calories']),
            remaining_protein=round1(st.session_state.remaining_nutrition['protein']),
            remaining_carbs=round1(st.session_state.remaining_nutrition['carbs']),
            remaining_fat=round1(st.session_state.remaining_nutrition['fat'])
        ))

    # 추천 식단 표시
    if 'recommendations' in st.session_state:
        st.subheader("추천 식단")
        st.write(st.session_state.recommendations)
        if st.button("추천 식단 적용하기"):
            lines = st.session_state.recommendations.split('\n')
            for line in lines:
                if "아침:" in line:
                    st.session_state.breakfast_input = line.replace("아침:", "").strip()
                elif "점심:" in line:
                    st.session_state.lunch_input = line.replace("점심:", "").strip()
                elif "저녁:" in line:
                    st.session_state.dinner_input = line.replace("저녁:", "").strip()

if __name__ == "__main__":
    main()
