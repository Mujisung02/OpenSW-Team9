import os
import sys
from datetime import datetime

# ==========================================
# 1. 기준 재료 리스트
# ==========================================
INGREDIENTS = [
    "김치",
    "돼지고기",
    "양파",
    "계란",
    "대파",
    "마늘",
    "감자",
    "두부",
    "닭고기",
    "소고기",
    "스파게티면",
    "토마토소스",
    "치즈",
    "밥",
]

# ==========================================
# 2. 레시피 데이터베이스
# ==========================================
RAW_RECIPES = {
    "김치찌개": {"김치": 0.5, "돼지고기": 0.2, "대파": 0.05, "마늘": 0.05, "두부": 0.2},
    "제육볶음": {"돼지고기": 0.65, "양파": 0.2, "대파": 0.1, "마늘": 0.05},
    "계란말이": {"계란": 0.8, "양파": 0.1, "대파": 0.1},
    "김치볶음밥": {"김치": 0.35, "밥": 0.35, "돼지고기": 0.1, "양파": 0.1, "계란": 0.1},
    "닭볶음탕": {"닭고기": 0.5, "감자": 0.2, "양파": 0.15, "대파": 0.1, "마늘": 0.05},
    "된장찌개": {"양파": 0.2, "대파": 0.2, "마늘": 0.1, "감자": 0.1, "두부": 0.3, "소고기": 0.1},
    "토마토파스타": {"스파게티면": 0.45, "토마토소스": 0.35, "양파": 0.1, "마늘": 0.1},
    "김치전": {"김치": 0.7, "양파": 0.1, "대파": 0.1, "계란": 0.1},
    "오므라이스": {"밥": 0.45, "계란": 0.25, "돼지고기": 0.1, "양파": 0.1, "감자": 0.1},
    "소고기무국": {"소고기": 0.6, "대파": 0.2, "마늘": 0.2},
}

# 딕셔너리 -> DataFrame 고정 벡터 변환
recipe_vectors = {}
for recipe_name, ing_dict in RAW_RECIPES.items():
    vec = np.zeros(len(INGREDIENTS))
    for ing_name, weight in ing_dict.items():
        if ing_name in INGREDIENTS:
            idx = INGREDIENTS.index(ing_name)
            vec[idx] = weight
    recipe_vectors[recipe_name] = vec

df_recipes = pd.DataFrame(recipe_vectors, index=INGREDIENTS).T


# ==========================================
# 3. 사용자 직접 입력 처리 및 추천 함수
# ==========================================
def recommend_by_user_input(user_fridge_dict, top_n=3):
    """사용자가 직접 입력한 냉장고 재료 딕셔너리를 받아 비율을 계산하고 레시피를 추천합니다."""
    user_vector = np.zeros(len(INGREDIENTS))

    # 사용자 입력 매핑
    for ing_name, amount in user_fridge_dict.items():
        if ing_name in INGREDIENTS:
            idx = INGREDIENTS.index(ing_name)
            user_vector[idx] = amount
        else:
            print(
                f"안내: '{ing_name}'은(는) 추천 기준 재료가 아니므로 비율 계산에서 제외됩니다."
            )

    # 비율(가중치) 벡터로 변환
    total_amount = np.sum(user_vector)
    if total_amount == 0:
        print("냉장고에 입력된 유효한 핵심 재료가 없습니다.")
        return []

    user_ratio_vector = user_vector / total_amount
    user_ratio_vector = user_ratio_vector.reshape(1, -1)

    # 코사인 유사도 계산 및 정렬
    similarities = cosine_similarity(df_recipes.values, user_ratio_vector).flatten()
    result_df = pd.DataFrame({"추천 점수": similarities}, index=df_recipes.index)
    recommendations = result_df.sort_values(
        by="추천 점수", ascending=False
    ).head(top_n)

    # 결과 출력
    print("\n==== 입력 기반 재료 비율 분석 ====")
    for idx, ratio in enumerate(user_ratio_vector[0]):
        if ratio > 0:
            print(f"- {INGREDIENTS[idx]}: {ratio*100:.1f}%")

    print(f"\n==== 맞춤 레시피 추천 TOP {top_n} ====")
    return list(recommendations.itertuples(index=True, name=None))


# ==========================================
# 4. 테스트 실행
# ==========================================
my_fridge = {
    "스파게티면": 200,
    "토마토소스": 150
}

results = recommend_by_user_input(my_fridge, top_n=3)

print("-" * 40)
for rank, (recipe, score) in enumerate(results, start=1):
    print(f"{rank}위: {recipe} (매칭 점수: {score:.2f})")