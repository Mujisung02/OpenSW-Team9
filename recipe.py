import os
import sys
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# ==========================================
# 1. 글로벌 기준 재료 및 레시피 정의
# ==========================================
INGREDIENTS = [
    "김치", "돼지고기", "양파", "계란", "대파", 
    "마늘", "감자", "두부", "닭고기", "소고기", 
    "스파게티면", "토마토소스", "치즈", "밥", "스팸"
]

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
    "양파계란볶음": {"양파": 0.5, "계란": 0.5},
    "스팸구이": {"스팸": 1.0},
    "스팸양파덮밥": {"스팸": 0.4, "양파": 0.4, "간장": 0.2}
}


# ==========================================
# 2. [데이터 전처리] 팀원 데이터 정제 함수
# ==========================================
def process_ingredients(raw_inputs):
    
    processed_dict = {}
    today = datetime.now()

    for item in raw_inputs:
        name = item['name']
        date_str = item['expire_date']
        amount_str = item['amount']
        
        # 1. 유통기한 및 남은 일수(d_day) 계산
        expire_date = datetime.strptime(date_str, "%Y-%m-%d")
        d_day = (expire_date - today).days
        
        # 2. 숫자와 단위 분리
        amount_num = ''.join(filter(lambda x: x.isdigit() or x == '.', amount_str))
        unit = ''.join(filter(str.isalpha, amount_str))
        
        # 3. 딕셔너리 구조화 (재료 이름을 Key로 활용하여 접근성 상향)
        processed_dict[name] = {
            'expire_date': date_str,
            'days_left': d_day,
            'quantity': float(amount_num) if amount_num else 0.0,
            'unit': unit
        }
        
    return processed_dict


# ==========================================
# 3. [추천 엔진] 통합 레시피 추천 클래스
# ==========================================
class RecipeRecommender:
    def __init__(self, ingredients_list, recipes_db):
        self.ingredients_list = ingredients_list
        self.recipes_db = recipes_db
        
        # 하이브리드 추천 가중치 설정 (합이 1이 되도록 권장)
        self.w_similarity = 0.5   # 코사인 유사도 (재료 비율 매칭)
        self.w_expiration = 0.3   # 유통기한 임박도 보너스
        self.w_quantity = 0.2     # 다다익선(재료 소모량) 보너스
        
        # 레시피 벡터 고정 데이터프레임 빌드
        self.df_recipes = self._build_recipe_matrix()

    def _build_recipe_matrix(self):
        recipe_vectors = {}
        for recipe_name, ing_dict in self.recipes_db.items():
            vec = np.zeros(len(self.ingredients_list))
            for ing_name, weight in ing_dict.items():
                if ing_name in self.ingredients_list:
                    idx = self.ingredients_list.index(ing_name)
                    vec[idx] = weight
            recipe_vectors[recipe_name] = vec
        return pd.DataFrame(recipe_vectors, index=self.ingredients_list).T

    def recommend(self, user_inventory, top_n=3):
        # 1. 사용자 벡터 및 비율 벡터 생성
        user_vector = np.zeros(len(self.ingredients_list))
        for ing_name, info in user_inventory.items():
            if ing_name in self.ingredients_list:
                idx = self.ingredients_list.index(ing_name)
                user_vector[idx] = info['quantity']

        total_amount = np.sum(user_vector)
        if total_amount == 0:
            print("안내: 냉장고에 추천 가능한 핵심 기준 재료가 없습니다.")
            return []

        user_ratio_vector = (user_vector / total_amount).reshape(1, -1)

        # 2. 기본 점수: 코사인 유사도 계산
        similarities = cosine_similarity(self.df_recipes.values, user_ratio_vector).flatten()
        
        # 결과 결합용 리스트
        final_scores = []
        
        # 3. 레시피별 추가 도메인 가중치(유통기한, 소모량) 계산
        for idx, recipe_name in enumerate(self.df_recipes.index):
            recipe_ingredients = self.recipes_db[recipe_name]
            
            sim_score = similarities[idx] # 코사인 유사도 점수 (0 ~ 1)
            expire_score = 0
            quantity_score = 0
            match_count = 0
            
            # 레시피에 필요한 재료들을 순회하며 유통기한/수량 평가
            for ing in recipe_ingredients.keys():
                if ing in user_inventory:
                    match_count += 1
                    
                    # 유통기한 점수 (7일 이내면 점수 부여, 짧을수록 고점)
                    days_left = user_inventory[ing]['days_left']
                    if days_left <= 7:
                        # 음수 d_day(유통기한 지남) 방지 및 최소값 0 처리
                        expire_score += max(0, (8 - days_left) / 7)
                    
                    # 재료 소모 점수 (최대 10개 기준으로 스케일링)
                    quantity_score += min(1.0, user_inventory[ing]['quantity'] / 10)

            # 매칭률 반영 (레시피 필요 재료 중 보유 재료 비율)
            match_rate = match_count / len(recipe_ingredients)
            
            # 최종 하이브리드 점수 산출
            total_score = (
                (sim_score * self.w_similarity) +
                (expire_score * self.w_expiration) +
                (quantity_score * self.w_quantity)
            ) * match_rate # 아무리 유사도가 좋아도 필수 재료가 너무 없으면 패널티
            
            final_scores.append({
                "recipe": recipe_name,
                "score": round(total_score, 2),
                "sim_score": round(sim_score, 2),
                "match_rate": round(match_rate * 100, 1)
            })

        # DataFrame으로 변환 후 정렬
        result_df = pd.DataFrame(final_scores).sort_values(by="score", ascending=False)
        
        # 4. 결과 출력용 프린트
        print("\n==== 현재 냉장고 핵심 재료 비율 ====")
        for idx, ratio in enumerate(user_ratio_vector[0]):
            if ratio > 0:
                print(f"- {self.ingredients_list[idx]}: {ratio*100:.1f}%")

        print(f"\n==== 맞춤 레시피 추천 TOP {top_n} ====")
        return result_df.head(top_n)


# ==========================================
# 4. 검증 및 테스트 실행
# ==========================================
if __name__ == "__main__":
    mock_raw_inputs = [
        {"name": "양파", "expire_date": "2026-05-28", "amount": "5.0개"}, # 유통기한 약 3일 남음 (임박), 양 많음
        {"name": "계란", "expire_date": "2026-06-15", "amount": "10.0개"}, # 유통기한 넉넉함, 양 많음
        {"name": "스팸", "expire_date": "2026-09-30", "amount": "1.0개"},  # 유통기한 매우 넉넉, 양 적음
        {"name": "간장", "expire_date": "2027-01-01", "amount": "500ml"}   # 기준 외 재료 테스트용
    ]

    # Step 1: 데이터 전처리 실행
    refined_inventory = process_ingredients(mock_raw_inputs)
    
    # Step 2: 추천 엔진 초기화
    recommender = RecipeRecommender(INGREDIENTS, RAW_RECIPES)
    
    # Step 3: 추천 결과 뽑기
    recommendations = recommender.recommend(refined_inventory, top_n=3)
    
    # Step 4: 최종 출력
    print(recommendations.to_string(index=False))