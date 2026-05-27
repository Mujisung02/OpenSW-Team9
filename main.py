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
# 4. 인터페이스 (UI) 클래스 구현
# ==========================================
class RecipeRecommenderCLI:
    def __init__(self):
        # 자료구조 변경: { "재료명": {"amount": "양", "exp_date": "유통기한"} }
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
            # 보기 좋게 표 형태로 출력
            print(f"{'재료명':<10} | {'수량/무게':<10} | {'유통기한'}")
            print("-" * 40)
            for name, info in self.user_ingredients.items():
                print(f"{name:<10} | {info['amount']:<10} | {info['exp_date']}")
        print("========================================")

    def add_ingredient(self):
        """재료, 양, 유통기한을 단계별로 입력받는 UI"""
        print("\n[새 재료 추가]")
        print("취소하고 메인으로 돌아가려면 엔터를 누르세요.")
        
        while True:
            name = input("\n1. 재료 이름 (예: 김치, 계란): ").strip()
            if not name:
                break
                
            amount = input("2. 양 (예: 500g, 2개): ").strip()
            if not amount:
                amount = "모름" # 기본값 처리
                
            # 유통기한 입력 및 형식 검증 (Robustness 강화)
            while True:
                exp_date = input("3. 유통기한 (YYYY-MM-DD 형식, 예: 2026-05-30): ").strip()
                if not exp_date:
                    exp_date = "기한 없음"
                    break
                
                try:
                    # 입력된 문자열이 실제 날짜 형식인지 검증
                    valid_date = datetime.strptime(exp_date, "%Y-%m-%d")
                    exp_date = valid_date.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    print("[오류] 올바른 날짜 형식이 아닙니다. 다시 입력해주세요.")

            # 데이터 딕셔너리에 저장
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

        # Interface의 문자열 데이터를 Master 로직에 맞게 변환 (전처리)
        parsed_fridge = {}
        for name, info in self.user_ingredients.items():
            amount_str = info['amount']
            
            # 정규식을 이용해 "500g", "2개" 등의 문자열에서 숫자만 추출
            numbers = re.findall(r'\d+\.?\d*', amount_str)
            if numbers:
                parsed_fridge[name] = float(numbers[0])
            else:
                parsed_fridge[name] = 1.0 # 수량 파악 불가 시 기본값

        # Master 브랜치의 실제 추천 로직 호출
        results = recommend_by_user_input(parsed_fridge, top_n=3)

        # 결과 출력 (Master 함수 내부에서 이미 출력문이 동작하므로 랭킹 출력만 보완)
        if results:
            print("-" * 40)
            for rank, (recipe, score) in enumerate(results, start=1):
                print(f"{rank}위: {recipe} (매칭 점수: {score:.2f})")
                
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
# 5. 실행부 (Master의 테스트 코드를 대체하여 인터페이스 실행)
# ==========================================
if __name__ == "__main__":
    # 기존 Master 브랜치의 테스트 코드는 주석 처리하여 남겨둠 (필요시 확인용)
    # my_fridge = {"스파게티면": 200, "토마토소스": 150}
    # results = recommend_by_user_input(my_fridge, top_n=3)
    # print("-" * 40)
    # for rank, (recipe, score) in enumerate(results, start=1):
    #     print(f"{rank}위: {recipe} (매칭 점수: {score:.2f})")
    
    # 실제 인터페이스 구동
    app = RecipeRecommenderCLI()
    app.run()