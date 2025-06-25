import streamlit as st
import openai
import json
import re
from dotenv import load_dotenv
import os
import random
import streamlit.components.v1 as components
import requests

st.set_page_config(page_title="AI 영양 관리 시스템", layout="wide")

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
    try:
        json_match = re.search(r'({[\s\S]*})', response)
        if not json_match:
            st.warning("GPT 응답에서 JSON 형식을 찾지 못했습니다. 응답을 확인해주세요.")
            st.error(response)
            return None
        json_str = json_match.group(1)
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'(?m)//.*$', '', json_str)
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return json.loads(json_str)
    except Exception as e:
        st.error(f"JSON 파싱 실패: {str(e)}")
        st.error(f"원본 응답: {response}")
        return None

def get_nutrition_info(food_name: str) -> dict:
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
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return parse_gpt_response(response.choices[0].message.content)
    except Exception as e:
        st.error(f"OpenAI API 오류: {str(e)}")
        return None

def get_side_dish_recommission(main_dish: str):
    prompt = f"""
    Recommend 3 Korean side dishes for {main_dish} in this JSON format (Korean output only):
    {{
        "recommendations": ["반찬1", "반찬2", "반찬3"]
    }}
    Only output JSON. Do not add any explanation.
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

def get_recommendations_from_gpt(remaining, meal_type="general", cheat_mode=False):
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
        1. First two meals: Healthy & follow remaining nutrition
        2. Third meal: Cheat meal (ignore limits)
        3. All food names and meal names must be in Korean only. Do not use English.
        4. If you use English, the recommendation will be rejected.
        5. Only output JSON. Do not add any explanation.
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
        - Fat: {remaining['fat']}g... Conditions:
        1. Total nutrition must not exceed remaining values
        2. {"Consider dinner if recommending lunch" if meal_type == "lunch" else "Realistic combinations"}
        3. All food names and meal names must be in Korean only. Do not use English.
        4. If you use English, the recommendation will be rejected.
        5. Only output JSON. Do not add any explanation.
        """
    try:
        emojis = ["🍰", "🍩", "🍪", "🍣", "🍕", "🍔", "🥞", "🧁", "🍦", "🍎"]
        loading_emoji = random.choice(emojis)
        loading_placeholder = st.empty()
        loading_placeholder.info(f"식단 추천을 준비 중입니다 . . . {loading_emoji} {loading_emoji}")
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        loading_placeholder.empty()
        result = parse_gpt_response(response.choices[0].message.content)
        valid_recommendations = []
        if result and "recommendations" in result:
            for rec in result["recommendations"]:
                sum_cal = sum(float(item["calories"]) for item in rec["menu"])
                sum_pro = sum(float(item["protein"]) for item in rec["menu"])
                sum_carb = sum(float(item["carbs"]) for item in rec["menu"])
                sum_fat = sum(float(item["fat"]) for item in rec["menu"])
                rec["total_calories"] = round1(sum_cal)
                rec["total_protein"] = round1(sum_pro)
                rec["total_carbs"] = round1(sum_carb)
                rec["total_fat"] = round1(sum_fat)
                for item in rec["menu"]:
                    item["calories"] = round1(float(item["calories"]))
                    item["protein"] = round1(float(item["protein"]))
                    item["carbs"] = round1(float(item["carbs"]))
                    item["fat"] = round1(float(item["fat"]))
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
    # st.title("🍽️ 식단 관리 시스템")

    # 사진으로 음식 등록 버튼: 현재 페이지 내에서 이동
    if st.button("📸 사진으로 음식 등록", key="photo_upload"):
        st.markdown(
            """
            <meta http-equiv="refresh" content="0; url='http://15.164.56.89:30800/'" />
            """,
            unsafe_allow_html=True
    )

    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = {}
    if 'side_dish_active' not in st.session_state:
        st.session_state.side_dish_active = None

    meal_types = ["breakfast", "lunch", "dinner"]
    meal_labels = ["아침", "점심", "저녁"]
    meal_inputs = {}

    for i, (meal_type, label) in enumerate(zip(meal_types, meal_labels)):
        cols = st.columns([6, 1])
        with cols[0]:
            meal_input = st.text_input(
                f"{label} 메뉴",
                key=f"{meal_type}_input",
                placeholder="예: 계란후라이 2개"
            )
            meal_inputs[meal_type] = meal_input
        with cols[1]:
            st.write("")
            st.write("")
            if meal_input:
                main_dish = meal_input.split(",")[0].strip()
                if st.button("반찬 추천받기", key=f"{meal_type}_btn", use_container_width=True):
                    emojis = ["🍰", "🍩", "🍪", "🍣", "🍕", "🍔", "🥞", "🧁", "🍦", "🍎"]
                    loading_emoji = random.choice(emojis)
                    st.session_state.recommendations[meal_type] = None
                    st.session_state.side_dish_active = meal_type
                    recommendations = get_side_dish_recommission(main_dish)
                    st.session_state.recommendations[meal_type] = recommendations

    active = st.session_state.side_dish_active
    if active:
        label = meal_labels[meal_types.index(active)]
        st.markdown(f"**{label} 추천 반찬**")
        if st.session_state.recommendations.get(active) is None:
            emojis = ["🍰", "🍩", "🍪", "🍣", "🍕", "🍔", "🥞", "🧁", "🍦", "🍎"]
            loading_emoji = random.choice(emojis)
            st.info(f"반찬 추천을 준비 중입니다 . . . {loading_emoji} {loading_emoji}")
        elif st.session_state.recommendations.get(active):
            cols = st.columns(3)
            for idx, rec in enumerate(st.session_state.recommendations[active]):
                with cols[idx]:
                    st.write(f"- {rec}")
                    st.button(
                        f"추가하기 {idx+1}",
                        key=f"add_{active}_{idx}",
                        on_click=update_meal_input,
                        args=(active, rec),
                    )
        else:
            st.warning("추천 반찬을 찾지 못했습니다")

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
            if meal_inputs[meal_type].strip():
                registered_meals[meal_type] = True
                food_list = [f.strip() for f in meal_inputs[meal_type].split(",") if f.strip()]
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
        meal_type = "general"
        if registered_meals["lunch"] and not registered_meals["dinner"]:
            remaining["calories"] = DAILY_GOAL["calories"] - total_nutrition["calories"] - 600
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
        
        if all(registered_meals.values()) and not cheat_mode:
            st.info("오늘은 식사를 모두 마쳐서 추천이 없습니다. 내일도 맛있는 한 끼 되세요!")
        else:
            recommendations = get_recommendations_from_gpt(remaining, meal_type, cheat_mode)
            if recommendations:
                if cheat_mode:
                    st.markdown("##### 🔥 건강식 2개 + 치팅메뉴 1개 추천!")
                    cols = st.columns(len(recommendations))
                    for idx, (col, rec) in enumerate(zip(cols, recommendations)):
                        with col:
                            with st.expander(f"추천 {idx+1}: {rec.get('name', f'추천 {idx+1}')}", expanded=True):
                                st.write("메뉴:")
                                for item in rec['menu']:
                                    st.write(f"- {item['name']} ({round1(item['calories'])}kcal, 단백질 {round1(item['protein'])}g, 탄수화물 {round1(item['carbs'])}g, 지방 {round1(item['fat'])}g)")
                                st.markdown(f"""
**영양소 총합**  
- 칼로리: {round1(rec['total_calories'])}kcal  
- 단백질: {round1(rec['total_protein'])}g  
- 탄수화물: {round1(rec['total_carbs'])}g  
- 지방: {round1(rec['total_fat'])}g
""")

                                def add_recommended_meal(rec_name, rec_menu):
                                    target_meal = "lunch" if not registered_meals["lunch"] else "dinner"
                                    if not registered_meals[target_meal]:
                                        menu_str = ", ".join([item["name"] for item in rec_menu])
                                        current = st.session_state.get(f"{target_meal}_input", "")
                                        st.session_state[f"{target_meal}_input"] = f"{current}, {menu_str}".strip(", ")
                                    else:
                                        st.warning(f"이미 {meal_labels[meal_types.index(target_meal)]} 메뉴가 입력되어 있습니다.")

                                st.button(
                                    f"추천 {idx+1} 식단 추가",
                                    key=f"add_rec_{idx}",
                                    on_click=add_recommended_meal,
                                    args=(rec.get('name', f'추천 {idx+1}'), rec['menu']),
                                )
                else:
                    st.markdown("##### 🥗 건강한 식단 추천")
                    cols = st.columns(3)
                    for idx, (col, rec) in enumerate(zip(cols, recommendations)):
                        with col:
                            with st.expander(f"추천 {idx+1}: {rec.get('name', f'추천 {idx+1}')}", expanded=True):
                                st.write("구성 메뉴:")
                                for item in rec['menu']:
                                    st.write(f"- {item['name']} ({round1(item['calories'])}kcal, 단백질 {round1(item['protein'])}g, 탄수화물 {round1(item['carbs'])}g, 지방 {round1(item['fat'])}g)")
                                st.markdown(f"""
**영양소 총합**  
- 칼로리: {round1(rec['total_calories'])}kcal  
- 단백질: {round1(rec['total_protein'])}g  
- 탄수화물: {round1(rec['total_carbs'])}g  
- 지방: {round1(rec['total_fat'])}g
""")

                                def add_recommended_meal(rec_name, rec_menu):
                                    target_meal = "lunch" if not registered_meals["lunch"] else "dinner"
                                    if not registered_meals[target_meal]:
                                        menu_str = ", ".join([item["name"] for item in rec_menu])
                                        current = st.session_state.get(f"{target_meal}_input", "")
                                        st.session_state[f"{target_meal}_input"] = f"{current}, {menu_str}".strip(", ")
                                    else:
                                        st.warning(f"이미 {meal_labels[meal_types.index(target_meal)]} 메뉴가 입력되어 있습니다.")

                                st.button(
                                    f"추천 {idx+1} 식단 추가",
                                    key=f"add_rec_{idx}",
                                    on_click=add_recommended_meal,
                                    args=(rec.get('name', f'추천 {idx+1}'), rec['menu']),
                                )
            else:
                st.warning("조건에 맞는 추천을 찾지 못했습니다")

if __name__ == "__main__":
    main()
