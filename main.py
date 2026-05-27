import os
import sys
import re
import numpy as np
from datetime import datetime

# ==========================================
# 1. 기준 재료 리스트
# ==========================================
INGREDIENTS = [
    "김치", "돼지고기", "양파", "계란", "대파", "마늘", "감자", "두부", 
    "닭고기", "소고기", "스파게티면", "토마토소스", "치즈", "밥"
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
    user_vector = np.zeros(len(INGREDIENTS))

    # 사용자 입력 매핑
    for ing_name, amount in user_fridge_dict.items():
        if ing_name in INGREDIENTS:
            idx = INGREDIENTS.index(ing_name)
            qty = amount['quantity'] if isinstance(amount, dict) else amount
            user_vector[idx] = qty
        else:
            print(f"안내: '{ing_name}'은(는) 추천 기준 재료가 아니므로 비율 계산에서 제외됩니다.")

    # 비율(가중치) 벡터로 변환
    total_amount = np.sum(user_vector)
    if total_amount == 0:
        print("냉장고에 입력된 유효한 핵심 재료가 없습니다.")
        return []

    user_ratio_vector = user_vector / total_amount
    user_ratio_vector = user_ratio_vector.reshape(1, -1)

    print("\n==== 입력 기반 재료 비율 분석 ====")
    for idx, ratio in enumerate(user_ratio_vector[0]):
        if ratio > 0:
            print(f"- {INGREDIENTS[idx]}: {ratio*100:.1f}%")

    # 가중치 점수 계산 (RecipeScorer)
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
# 5. 인터페이스 (UI) 클래스 구현
# ==========================================
class RecipeRecommenderCLI:
    def __init__(self):
        self.user_ingredients = {}

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_header(self):
        print("========================================")
        print("      🍳 냉장고 파먹기 레시피 추천 🍳      ")
        print("========================================")
        print("[현재 냉장고 속 재료]")
        
        if not self.user_ingredients:
            print("텅 비어있습니다. 재료를 추가해주세요.")
        else:
            print(f"{'재료명':<10} | {'수량/무게':<10} | {'유통기한'}")
            print("-" * 40)
            for name, info in self.user_ingredients.items():
                print(f"{name:<10} | {info['amount']:<10} | {info['exp_date']}")
        print("========================================")

    def add_ingredient(self):
        print("\n[새 재료 추가]")
        print("취소하고 메인으로 돌아가려면 엔터를 누르세요.")
        
        while True:
            name = input("\n1. 재료 이름 (예: 김치, 계란): ").strip()
            if not name:
                break
                
            amount = input("2. 양 (예: 500g, 2개): ").strip()
            if not amount:
                amount = "모름"
                
            while True:
                exp_date = input("3. 유통기한 (YYYY-MM-DD 형식, 예: 2026-05-30): ").strip()
                if not exp_date:
                    exp_date = "기한 없음"
                    break
                
                try:
                    valid_date = datetime.strptime(exp_date, "%Y-%m-%d")
                    exp_date = valid_date.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    print("[오류] 올바른 날짜 형식이 아닙니다. 다시 입력해주세요.")

            self.user_ingredients[name] = {
                "amount": amount,
                "exp_date": exp_date
            }
            print(f"\n✅ [{name}] 등록 완료! (계속 추가하려면 다음 재료를 입력하세요)")
            
    def reset_ingredients(self):
        self.user_ingredients.clear()
        print("\n🗑️ 냉장고를 깨끗하게 비웠습니다!")
        input("\n계속하려면 엔터를 누르세요...")

    def show_recommendations(self):
        print("\n[레시피 추천 결과]")
        
        if not self.user_ingredients:
            print("먼저 냉장고에 재료를 입력해주세요!")
            input("\n계속하려면 엔터를 누르세요...")
            return

        parsed_fridge = {}
        today = datetime.now()

        for name, info in self.user_ingredients.items():
            # 1. 수량 파싱 (정규식으로 숫자 추출)
            amount_str = info['amount']
            numbers = re.findall(r'\d+\.?\d*', amount_str)
            qty = float(numbers[0]) if numbers else 1.0
            
            # 2. 유통기한 파싱 및 남은 일수(days_left) 계산
            exp_date_str = info['exp_date']
            if exp_date_str == "기한 없음":
                days_left = 999
            else:
                try:
                    exp_date_obj = datetime.strptime(exp_date_str, "%Y-%m-%d")
                    delta = exp_date_obj - today
                    days_left = delta.days
                except ValueError:
                    days_left = 999
                    
            # 3. 새로운 로직에 맞는 딕셔너리 형태로 저장
            parsed_fridge[name] = {
                "quantity": qty,
                "days_left": days_left
            }

        # 추천 로직 호출
        results = recommend_by_user_input(parsed_fridge, top_n=3)

        if results:
            print("-" * 40)
            for rank, (recipe, score) in enumerate(results, start=1):
                print(f"{rank}위: {recipe} (가중치 점수: {score:.2f})")
                
        input("\n메인 메뉴로 돌아가려면 엔터를 누르세요...")

    def run(self):
        while True:
            self.clear_screen()
            self.display_header()
            
            print("1. 냉장고 재료 추가하기")
            print("2. 내 냉장고 비우기")
            print("3. 맞춤 레시피 추천받기")
            print("4. 프로그램 실행 종료")
            print("----------------------------------------")
            
            choice = input(">> 원하는 메뉴 번호를 선택하세요: ").strip()

            if choice == '1':
                self.add_ingredient()
            elif choice == '2':
                self.reset_ingredients()
            elif choice == '3':
                self.show_recommendations()
            elif choice == '4':
                print("\n프로그램을 종료합니다. 맛있는 식사 되세요! 🍽️")
                sys.exit()
            else:
                print("\n잘못된 입력입니다. 1~4 사이의 숫자를 입력해주세요.")
                input("\n계속하려면 엔터를 누르세요...")

# ==========================================
# 6. 실행부
# ==========================================
if __name__ == "__main__":
    app = RecipeRecommenderCLI()
    app.run()