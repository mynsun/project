import streamlit as st
import openai
import json
import re
from dotenv import load_dotenv
import os
import random
import streamlit.components.v1 as components
import requests

st.set_page_config(page_title="AI 칼로리 분석", layout="wide")

components.html("""
<script>
window.addEventListener("message", function(event) {
    if(event.data && event.data.type === "photo_result" && event.data.value){
        const params = new URLSearchParams(window.location.search);
        params.set("photo_result", event.data.value);
        window.location.search = params.toString();
    }
});
</script>
""", height=0)

load_dotenv()

client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

DAILY_GOAL = {
    "calories": 2200,
    "protein": 50,
    "carbs": 260,
    "fat": 70
}

def parse_gpt_response(response: str) -> dict:
    """
    Parses the GPT response string to extract a JSON object.
    Handles common issues like single quotes and comments in JSON.
    """
    try:
        json_match = re.search(r'({[\s\S]*})', response)
        if not json_match:
            st.warning("GPT 응답에서 JSON 형식을 찾지 못했습니다. 응답을 확인해주세요.")
            st.error(response)
            return None
        json_str = json_match.group(1)
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'(?m)//.*$', '', json_str)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        return json.loads(json_str)
    except Exception as e:
        st.error(f"JSON 파싱 실패: {str(e)}")
        st.error(f"원본 응답: {response}")
        return None

def get_nutrition_info(food_name: str) -> dict:
    """
    Fetches nutritional information for a given food name using the OpenAI GPT-4 model.
    """
    prompt = f"""
    Provide nutritional info for {food_name} in this JSON format (Korean output only):
    {{
        "calories": integer,
        "protein": float,
        "carbs": float,
        "fat": float
    }}
    Only output JSON. Do not add any explanation.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return parse_gpt_response(response.choices[0].message.content)
    except Exception as e:
        st.error(f"OpenAI API 오류 (영양 정보): {str(e)}")
        return None

def get_side_dish_recommission(main_dish: str) -> list[str]:
    """
    Recommends 3 Korean side dishes for a given main dish using the OpenAI GPT-4 model.
    """
    prompt = f"""
    Recommend 3 Korean side dishes for {main_dish} in this JSON format (Korean output only):
    {{
        "recommendations": ["반찬1", "반찬2", "반찬3"]
    }}
    Only output JSON. Do not add any explanation.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_gpt_response(response.choices[0].message.content)
        return result.get("recommendations", []) if result else []
    except Exception as e:
        st.error(f"반찬 추천 오류: {str(e)}")
        return []

def update_meal_input(meal_type: str, selected_dish: str):
    """
    Updates the meal input text area in session state with a selected side dish.
    """
    if f"{meal_type}_input" not in st.session_state:
        st.session_state[f"{meal_type}_input"] = ""

    current_value = st.session_state.get(f"{meal_type}_input", "").strip()
    if selected_dish not in current_value:
        new_value = f"{current_value}, {selected_dish}".strip(", ")
        st.session_state[f"{meal_type}_input"] = new_value
    else:
        st.info(f"'{selected_dish}'은(는) 이미 {meal_type} 메뉴에 추가되어 있습니다.")


def get_recommendations_from_gpt(remaining: dict, meal_type: str = "general", cheat_mode: bool = False) -> list[dict]:
    """
    Generates meal recommendations (healthy or cheat) based on remaining nutrition goals.
    """
    remaining_str = {k: round1(v) for k, v in remaining.items()}

    if cheat_mode:
        prompt = f"""
        Recommend 3 meal sets in JSON format (2 healthy + 1 cheat):
        {{
            "recommendations": [
                {{
                    "name": "식단 이름(한글)",
                    "menu": [
                        {{
                            "name": "음식명(한글)",
                            "calories": 숫자,
                            "protein": 숫자,
                            "carbs": 숫자,
                            "fat": 숫자
                        }}
                    ],
                    "total_calories": 합계,
                    "total_protein": 합계,
                    "total_carbs": 합계,
                    "total_fat": 합계
                }},
                {{
                    "name": "식단 이름(한글)",
                    "menu": [
                        {{
                            "name": "음식명(한글)",
                            "calories": 숫자,
                            "protein": 숫자,
                            "carbs": 숫자,
                            "fat": 숫자
                        }}
                    ],
                    "total_calories": 합계,
                    "total_protein": 합계,
                    "total_carbs": 합계,
                    "total_fat": 합계
                }},
                {{
                    "name": "치팅메뉴(한글)",
                    "menu": [
                        {{
                            "name": "치킨/피자 등(한글)",
                            "calories": 숫자,
                            "protein": 숫자,
                            "carbs": 숫자,
                            "fat": 숫자
                        }}
                    ],
                    "total_calories": 합계,
                    "total_protein": 합계,
                    "total_carbs": 합계,
                    "total_fat": 합계
                }}
            ]
        }}
        Requirements:
        1. First two meals: Healthy & follow remaining nutrition limits.
        2. Third meal: Cheat meal (ignore limits but provide realistic high values).
        3. All food names and meal names must be in Korean only. Do not use English.
        4. Only output JSON. Do not add any explanation.
        """
    else:
        prompt = f"""
        Recommend 3 healthy meal sets in JSON format:
        {{
            "recommendations": [
                {{
                    "name": "식단 이름(한글)",
                    "menu": [
                        {{
                            "name": "음식명(한글)",
                            "calories": 숫자,
                            "protein": 숫자,
                            "carbs": 숫자,
                            "fat": 숫자
                        }}
                    ],
                    "total_calories": 합계,
                    "total_protein": 합계,
                    "total_carbs": 합계,
                    "total_fat": 합계
                }},
                {{
                    "name": "식단 이름(한글)",
                    "menu": [
                        {{
                            "name": "음식명(한글)",
                            "calories": 숫자,
                            "protein": 숫자,
                            "carbs": 숫자,
                            "fat": 숫자
                        }}
                    ],
                    "total_calories": 합계,
                    "total_protein": 합계,
                    "total_carbs": 합계,
                    "total_fat": 합계
                }},
                {{
                    "name": "식단 이름(한글)",
                    "menu": [
                        {{
                            "name": "음식명(한글)",
                            "calories": 숫자,
                            "protein": 숫자,
                            "carbs": 숫자,
                            "fat": 숫자
                        }}
                    ],
                    "total_calories": 합계,
                    "total_protein": 합계,
                    "total_carbs": 합계,
                    "total_fat": 합계
                }}
            ]
        }}
        [Remaining Nutrition]
        - Calories: {remaining_str['calories']}kcal
        - Protein: {remaining_str['protein']}g
        - Carbs: {remaining_str['carbs']}g
        - Fat: {remaining_str['fat']}g
        Conditions:
        1. Total nutrition of each recommended meal must not exceed the remaining daily values.
        2. {"Consider realistic dinner options if recommending for lunch (meaning, don't recommend a whole day's worth)." if meal_type == "lunch" else "Provide realistic and balanced combinations."}
        3. All food names and meal names must be in Korean only. Do not use English.
        4. Only output JSON. Do not add any explanation.
        """
    try:
        emojis = ["🍰", "🍩", "🍪", "🍣", "🍕", "🍔", "🥞", "🧁", "🍦", "🍎"]
        loading_emoji = random.choice(emojis)
        loading_placeholder = st.empty()
        loading_placeholder.info(f"식단 추천을 준비 중입니다 . . . {loading_emoji} {loading_emoji}")

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7 
        )
        loading_placeholder.empty()

        result = parse_gpt_response(response.choices[0].message.content)
        valid_recommendations = []
        if result and "recommendations" in result:
            for rec in result["recommendations"]:
                try:
                    sum_cal = sum(float(item.get("calories", 0)) for item in rec.get("menu", []))
                    sum_pro = sum(float(item.get("protein", 0)) for item in rec.get("menu", []))
                    sum_carb = sum(float(item.get("carbs", 0)) for item in rec.get("menu", []))
                    sum_fat = sum(float(item.get("fat", 0)) for item in rec.get("menu", []))

                    rec["total_calories"] = round1(sum_cal)
                    rec["total_protein"] = round1(sum_pro)
                    rec["total_carbs"] = round1(sum_carb)
                    rec["total_fat"] = round1(sum_fat)

                    for item in rec.get("menu", []):
                        item["calories"] = round1(item.get("calories", 0))
                        item["protein"] = round1(item.get("protein", 0))
                        item["carbs"] = round1(item.get("carbs", 0))
                        item["fat"] = round1(item.get("fat", 0))

                    valid_recommendations.append(rec)
                except (ValueError, TypeError) as ve:
                    st.warning(f"추천 식단 계산 중 오류 발생 (유효하지 않은 숫자 형식): {ve}. 이 식단은 건너뜁니다.")
                    continue
        return valid_recommendations
    except Exception as e:
        st.error(f"추천 생성 오류: {str(e)}")
        return []

def round1(x):
    """Rounds a number to one decimal place, handles non-numeric inputs gracefully."""
    try:
        return round(float(x), 1)
    except (ValueError, TypeError):
        return x 

def load_and_populate_meals():
    """
    Fetches meal data from the FastAPI endpoint and populates the
    Streamlit session state for meal input text fields.
    """
    try:
        response = requests.get("http://13.124.198.232:3000/load-meal")
        if response.status_code == 200:
            meals_from_api = response.json()

            meal_type_map = {
                "아침": "breakfast",
                "점심": "lunch",
                "저녁": "dinner"
            }

            temp_meal_inputs = {
                "breakfast": [],
                "lunch": [],
                "dinner": []
            }

            for meal in meals_from_api:
                korean_meal_type = meal.get("meal_type")
                food_name = meal.get("food_name")

                english_meal_type = meal_type_map.get(korean_meal_type)

                if english_meal_type in temp_meal_inputs and food_name:
                    temp_meal_inputs[english_meal_type].append(food_name)

            st.session_state.breakfast_input = ", ".join(temp_meal_inputs["breakfast"])
            st.session_state.lunch_input = ", ".join(temp_meal_inputs["lunch"])
            st.session_state.dinner_input = ", ".join(temp_meal_inputs["dinner"])

        # else:
        #     st.error(f"서버 오류 발생: {response.status_code}. 음식 목록을 불러오지 못했습니다.")
    except requests.exceptions.RequestException as e:
        st.error(f"서버 요청 실패: {e}. FastAPI 서버가 실행 중인지 확인하세요.")

def main():
    st.title("🍽️ AI 칼로리 분석")

    if 'breakfast_input' not in st.session_state:
        st.session_state.breakfast_input = ""
    if 'lunch_input' not in st.session_state:
        st.session_state.lunch_input = ""
    if 'dinner_input' not in st.session_state:
        st.session_state.dinner_input = ""

    if 'meals_loaded_initial' not in st.session_state:
        st.session_state.meals_loaded_initial = False

    if not st.session_state.meals_loaded_initial:
        load_and_populate_meals()
        st.session_state.meals_loaded_initial = True

    col_upload_photo, col_load_api = st.columns(2)

    with col_upload_photo:
        if st.button("📸 사진으로 음식 등록", key="photo_upload"):
            st.markdown(
                """
                <meta http-equiv="refresh" content="0; url='http://15.164.56.89:30800/'" />
                """,
                unsafe_allow_html=True
            )

    with col_load_api:
        # FastAPI에서 음식 데이터를 불러오는 임시 버튼 (테스트용)
        if st.button("FastAPI에서 음식 불러오기 (임시)", key="load_from_fastapi_temp"):
            load_and_populate_meals()

    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = {}
    if 'side_dish_active' not in st.session_state:
        st.session_state.side_dish_active = None

    meal_types = ["breakfast", "lunch", "dinner"]
    meal_labels = ["아침", "점심", "저녁"]

    for i, (meal_type, label) in enumerate(zip(meal_types, meal_labels)):
        cols = st.columns([6, 1])
        with cols[0]:
            st.session_state[f"{meal_type}_input"] = st.text_input(
                f"{label} 메뉴",
                value=st.session_state.get(f"{meal_type}_input", ""), 
                key=f"{meal_type}_input_widget", 
                placeholder="예: 계란후라이 2개"
            )

        with cols[1]:
            st.write("")
            st.write("")
            if st.session_state.get(f"{meal_type}_input", "").strip():
                main_dish = st.session_state[f"{meal_type}_input"].split(",")[0].strip()
                if st.button("반찬 추천받기", key=f"{meal_type}_btn", use_container_width=True):
                    st.session_state.recommendations[meal_type] = None
                    st.session_state.side_dish_active = meal_type
                    recommendations = get_side_dish_recommission(main_dish)
                    st.session_state.recommendations[meal_type] = recommendations

    active_meal_type = st.session_state.side_dish_active
    if active_meal_type:
        label = meal_labels[meal_types.index(active_meal_type)]
        st.markdown(f"**{label} 추천 반찬**")

        if st.session_state.recommendations.get(active_meal_type) is None:
            emojis = ["🍰", "🍩", "🍪", "🍣", "🍕", "🍔", "🥞", "🧁", "🍦", "🍎"]
            loading_emoji = random.choice(emojis)
            st.info(f"반찬 추천을 준비 중입니다 . . . {loading_emoji} {loading_emoji}")

        elif st.session_state.recommendations.get(active_meal_type):
            cols = st.columns(3)
            for idx, rec in enumerate(st.session_state.recommendations[active_meal_type]):
                with cols[idx]:
                    st.write(f"- {rec}")
                    st.button(
                        f"추가하기 {idx+1}",
                        key=f"add_side_dish_{active_meal_type}_{idx}",
                        on_click=update_meal_input,
                        args=(active_meal_type, rec),
                    )
        else:
            st.warning("추천 반찬을 찾지 못했습니다.")

    col_btn, col_check = st.columns([4, 1])
    with col_btn:
        analyze_clicked = st.button("영양 분석 & 식단 추천")
    with col_check:
        cheat_mode = st.checkbox("치팅 메뉴 확인하기")

    if analyze_clicked:
        total_nutrition = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        registered_meals = {"breakfast": False, "lunch": False, "dinner": False}
        meal_details = []

        emojis = ["🍰", "🍩", "🍪", "🍣", "🍕", "🍔", "🥞", "🧁", "🍦", "🍎"]
        loading_emoji = random.choice(emojis)
        loading_placeholder = st.empty()
        loading_placeholder.info(f"영양 분석 중입니다 . . . {loading_emoji} {loading_emoji}")

        for meal_type in meal_types:
            current_input_value = st.session_state.get(f"{meal_type}_input", "").strip()
            if current_input_value:
                registered_meals[meal_type] = True
                food_list = [f.strip() for f in current_input_value.split(",") if f.strip()]
                meal_total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

                for food in food_list:
                    nutrition = get_nutrition_info(food)
                    if nutrition:
                        for key in meal_total:
                            meal_total[key] += float(nutrition.get(key, 0))

                for key in total_nutrition:
                    total_nutrition[key] += meal_total[key]
                meal_details.append((meal_type, meal_total))

        loading_placeholder.empty()

        remaining = {
            nut: round1(DAILY_GOAL[nut] - total_nutrition[nut])
            for nut in DAILY_GOAL
        }

        rec_meal_type = "general"
        if registered_meals["breakfast"] and not registered_meals["lunch"]:
            rec_meal_type = "lunch"
        elif registered_meals["breakfast"] and registered_meals["lunch"] and not registered_meals["dinner"]:
            rec_meal_type = "dinner"
        elif all(registered_meals.values()):
            rec_meal_type = "completed"

        st.divider()
        st.subheader("📊 영양 분석 결과")
        if meal_details:
            cols = st.columns(len(meal_details))
            for idx, (col, (meal_type, nutrition)) in enumerate(zip(cols, meal_details)):
                with col:
                    st.markdown(f"### {meal_labels[meal_types.index(meal_type)]} (입력된 식사)")
                    st.write(f"**칼로리**: {round1(nutrition['calories'])}kcal")
                    st.write(f"**단백질**: {round1(nutrition['protein'])}g")
                    st.write(f"**탄수화물**: {round1(nutrition['carbs'])}g")
                    st.write(f"**지방**: {round1(nutrition['fat'])}g")
        else:
            st.info("아직 입력된 식사가 없습니다.")

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

        if rec_meal_type == "completed" and not cheat_mode:
            st.info("오늘은 식사를 모두 마쳐서 추천이 없습니다. 내일도 맛있는 한 끼 되세요!")
        else:
            recommendations = get_recommendations_from_gpt(remaining, rec_meal_type, cheat_mode)
            if recommendations:
                if cheat_mode:
                    st.markdown("##### 🔥 건강식 2개 + 치팅메뉴 1개 추천!")
                else:
                    st.markdown("##### 🥗 건강한 식단 추천")

                cols = st.columns(len(recommendations))
                for idx, (col, rec) in enumerate(zip(cols, recommendations)):
                    with col:
                        with st.expander(f"추천 {idx+1}: {rec.get('name', f'추천 {idx+1}')}", expanded=True):
                            st.write("메뉴:")
                            for item in rec.get('menu', []):
                                st.write(f"- {item.get('name', 'N/A')} ({round1(item.get('calories', 0))}kcal, 단백질 {round1(item.get('protein', 0))}g, 탄수화물 {round1(item.get('carbs', 0))}g, 지방 {round1(item.get('fat', 0))}g)")
                            st.markdown(f"""
**영양소 총합**  
- 칼로리: {round1(rec.get('total_calories', 0))}kcal  
- 단백질: {round1(rec.get('total_protein', 0))}g  
- 탄수화물: {round1(rec.get('total_carbs', 0))}g 
- 지방: {round1(rec.get('total_fat', 0))}g
""")

                            def add_recommended_meal_callback(rec_menu_list):
                                target_meal_type = None
                                if not registered_meals["lunch"]:
                                    target_meal_type = "lunch"
                                elif not registered_meals["dinner"]:
                                    target_meal_type = "dinner"

                                if target_meal_type:
                                    menu_str = ", ".join([item.get("name", "") for item in rec_menu_list if item.get("name")])
                                    current_input = st.session_state.get(f"{target_meal_type}_input", "").strip()

                                    if menu_str not in current_input:
                                        new_input = f"{current_input}, {menu_str}".strip(", ")
                                        st.session_state[f"{target_meal_type}_input"] = new_input
                                    else:
                                        st.info(f"이미 {meal_labels[meal_types.index(target_meal_type)]} 메뉴에 해당 추천 식단이 추가되어 있습니다.")
                                else:
                                    st.warning("더 이상 추가할 식사 시간이 없습니다. 모든 식사가 이미 입력되었습니다.")

                            st.button(
                                f"추천 {idx+1} 식단 추가",
                                key=f"add_rec_meal_{idx}",
                                on_click=add_recommended_meal_callback,
                                args=(rec['menu'],),
                            )
            else:
                st.warning("조건에 맞는 추천을 찾지 못했습니다.")

if __name__ == "__main__":
    main()