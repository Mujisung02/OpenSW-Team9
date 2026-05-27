import os
import sys
import re  # 인터페이스에서 수량(숫자) 추출을 위해 추가
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
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

# ==========================================
# 3. RecipeScorer 클래스 (사용자 가중치 로직)
# ==========================================
class RecipeScorer:
    def __init__(self):
        self.w_expiration = 0.5  # 유통기한 임박 우선
        self.w_quantity = 0.3    # 재료 소모량 우선
        self.w_match_rate = 0.2  # 레시피 매칭률 우선

    def calculate_score(self, recipe_name, recipe_ingredients, user_inventory):
        expire_score = 0
        quantity_score = 0
        match_count = 0
        
        required_ingredients = list(recipe_ingredients.keys())
        total_required = len(required_ingredients)

        for ing in required_ingredients:
            if ing in user_inventory:
                match_count += 1
                
                # 기존 데이터(숫자)와 새 데이터(딕셔너리) 모두 호환되도록 처리
                ing_info = user_inventory[ing]
                if isinstance(ing_info, dict):
                    qty = ing_info.get('quantity', 0)
                    days_left = ing_info.get('days_left', 999)
                else:
                    qty = ing_info
                    days_left = 999
                
                # 유통기한 점수: 7일 이내면 점수 부여
                if days_left <= 7:
                    expire_score += (8 - days_left) / 7 
                
                # 재료 소모 점수 (10개를 만점으로 가정)
                quantity_score += qty / 10

        match_rate = match_count / total_required

        total_score = (
            (expire_score * self.w_expiration) +
            (quantity_score * self.w_quantity) +
            (match_rate * self.w_match_rate)
        )
        return round(total_score, 2)


# ==========================================
# 4. 사용자 직접 입력 처리 및 추천 함수
# ==========================================
def recommend_by_user_input(user_fridge_dict, top_n=3):
    """사용자가 직접 입력한 냉장고 재료 딕셔너리를 받아 비율을 계산하고 레시피를 추천합니다."""
    
    # ----------------------------------------------------
    # [원본 코드 복구 구역] 사용자 입력 매핑 및 비율 분석 출력
    # ----------------------------------------------------
    user_vector = np.zeros(len(INGREDIENTS))

    # 사용자 입력 매핑
    for ing_name, amount in user_fridge_dict.items():
        if ing_name in INGREDIENTS:
            idx = INGREDIENTS.index(ing_name)
            # 입력값이 딕셔너리(유통기한 포함)일 경우 수량만 추출, 아니면 원래 숫자 사용
            qty = amount['quantity'] if isinstance(amount, dict) else amount
            user_vector[idx] = qty
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

    # 결과 출력
    print("\n==== 입력 기반 재료 비율 분석 ====")
    for idx, ratio in enumerate(user_ratio_vector[0]):
        if ratio > 0:
            print(f"- {INGREDIENTS[idx]}: {ratio*100:.1f}%")

    # ----------------------------------------------------
    # [변경 구역] 코사인 유사도 -> 가중치 점수(RecipeScorer) 교체
    # ----------------------------------------------------
    scorer = RecipeScorer()
    results = []
    
    for recipe_name, ing_dict in RAW_RECIPES.items():
        score = scorer.calculate_score(recipe_name, ing_dict, user_fridge_dict)
        results.append((recipe_name, score))

    # 결과 정렬
    results.sort(key=lambda x: x[1], reverse=True)
    top_recommendations = results[:top_n]

    print(f"\n==== 맞춤 레시피 추천 TOP {top_n} ====")
    return top_recommendations


# ==========================================
# 5. 테스트 실행
# ==========================================
if __name__ == "__main__":
    # 테스트용: 기존의 단순 수량 방식과 새로운 유통기한 방식 모두 호환 가능
    my_fridge = {
        "스파게티면": {"quantity": 200, "days_left": 10},
        "토마토소스": {"quantity": 150, "days_left": 3},
        "초콜릿": {"quantity": 10, "days_left": 30} # 제외되는 재료 테스트
    }

    results = recommend_by_user_input(my_fridge, top_n=3)

    print("-" * 40)
    for rank, (recipe, score) in enumerate(results, start=1):
        print(f"{rank}위: {recipe} (매칭 점수: {score:.2f})")
