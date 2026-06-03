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
# 3. 데이터 정렬 및 변환 모듈
# ==========================================
def process_ingredients(raw_inputs):
    """UI에서 받은 raw 데이터를 정제하고 유통기한 순으로 정렬합니다."""
    processed_list = []
    today = datetime.now() 

    for item in raw_inputs:
        name = item['name']
        date_str = item['expire_date']
        amount_str = str(item['amount']) 
        
        # 1. 유통기한 D-Day 계산
        expire_date = datetime.strptime(date_str, "%Y-%m-%d")
        d_day = (expire_date - today).days
        
        # 2. 숫자(수량)만 분리하여 실수(float)로 변환
        amount_num_str = ''.join(filter(lambda x: x.isdigit() or x == '.', amount_str))
        amount_num = float(amount_num_str) if amount_num_str else 0.0
        
        # 3. 딕셔너리로 구조화
        ingredient_data = {
            'name': name,
            'expire_date': date_str,
            'd_day': d_day,
            'amount_num': amount_num
        }
        processed_list.append(ingredient_data)
    
    # 4. 유통기한(d_day)이 임박한 순으로 정렬!
    processed_list.sort(key=lambda x: x['d_day'])
    
    return processed_list

def get_fridge_dict_for_main(sorted_list):
    """정렬된 리스트를 메인 추천 함수의 규격에 맞게 변환합니다."""
    fridge_dict = {}
    for item in sorted_list:
        fridge_dict[item['name']] = {
            "quantity": item['amount_num'],
            "days_left": item['d_day']
        }
    return fridge_dict

# ==========================================
# 4. RecipeScorer 클래스 (사용자 가중치 로직)
# ==========================================
class RecipeScorer:
    def __init__(self):
        # 항목별 평가 가중치 설정
        self.w_expiration = 0.5  # 유통기한 임박 우선
        self.w_quantity = 0.3    # 재료 소모량 우선
        self.w_match_rate = 0.2  # 레시피 매칭률 우선

    def calculate_score(self, recipe_name, recipe_ingredients, user_inventory):
        # 평가 점수 초기화
        expire_score = 0
        quantity_score = 0
        match_count = 0
        
        # 레시피에 필요한 재료 목록과 총 개수 확인
        required_ingredients = list(recipe_ingredients.keys())
        total_required = len(required_ingredients)

        for ing in required_ingredients:
            # 1. 보유 재료 확인: 사용자의 인벤토리에 필요한 재료가 있는지 체크
            if ing in user_inventory:
                match_count += 1
                ing_info = user_inventory[ing]
                
                # 데이터 타입에 따라 수량(qty)과 남은 유통기한(days_left) 추출
                if isinstance(ing_info, dict):
                    qty = ing_info.get('quantity', 0)
                    days_left = ing_info.get('days_left', 999)
                else:
                    qty = ing_info
                    days_left = 999
                
                # 2. 유통기한 점수 계산: 7일 이하로 남은 경우, 임박할수록 더 높은 점수 부여
                if days_left <= 7:
                    expire_score += (8 - days_left) / 7 
                
                # 3. 수량 점수 계산: 보유 수량이 많을수록 더 높은 점수 부여
                quantity_score += qty / 10

        # 4. 매칭률 계산: (보유한 필요 재료 수 / 전체 필요 재료 수)
        match_rate = match_count / total_required

        # 5. 최종 점수 산출: 각 항목의 점수에 가중치를 곱하여 합산
        total_score = (
            (expire_score * self.w_expiration) +
            (quantity_score * self.w_quantity) +
            (match_rate * self.w_match_rate)
        )
        
        # 결과를 소수점 둘째 자리까지 반올림하여 반환
        return round(total_score, 2)
# ==========================================
# 5. 사용자 직접 입력 처리 및 추천 함수
# ==========================================
def recommend_by_user_input(user_fridge_dict, top_n=3):
    user_vector = np.zeros(len(INGREDIENTS))

    for ing_name, amount in user_fridge_dict.items():
        if ing_name in INGREDIENTS:
            idx = INGREDIENTS.index(ing_name)
            qty = amount['quantity'] if isinstance(amount, dict) else amount
            user_vector[idx] = qty
        else:
            print(f"안내: '{ing_name}'은(는) 추천 기준 재료가 아니므로 비율 계산에서 제외됩니다.")

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

    scorer = RecipeScorer()
    results = []
    
    for recipe_name, ing_dict in RAW_RECIPES.items():
        score = scorer.calculate_score(recipe_name, ing_dict, user_fridge_dict)
        results.append((recipe_name, score))

    results.sort(key=lambda x: x[1], reverse=True)
    top_recommendations = results[:top_n]

    print(f"\n==== 맞춤 레시피 추천 TOP {top_n} ====")
    return top_recommendations

# ==========================================
# 6. 인터페이스 (UI) 클래스 구현
# ==========================================
class RecipeRecommenderCLI:
    """
    사용자와 상호작용하는 커맨드 라인 인터페이스(CLI)를 관리하는 클래스입니다.
    냉장고 재료 추가, 조회, 초기화 및 레시피 추천 메뉴를 제공합니다.
    """
    
    def __init__(self):
        self.user_ingredients = {}

    def clear_screen(self):
        """운영체제(OS)에 맞게 콘솔 창의 화면을 지워주는 헬퍼 메서드"""
        # Windows('nt')인 경우 'cls' 명령어, Mac/Linux 등 다른 OS인 경우 'clear' 명령어 실행
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_header(self):
        """메인 화면의 상단 타이틀과 현재 등록된 냉장고 재료 목록을 출력하는 메서드"""
        print("========================================")
        print("     🍳 냉장고 파먹기 레시피 추천 🍳      ")
        print("========================================")
        print("[현재 냉장고 속 재료]")
        
        # 등록된 재료가 없을 경우 안내 메시지 출력
        if not self.user_ingredients:
            print("텅 비어있습니다. 재료를 추가해주세요.")
        else:
            # 등록된 재료가 있을 경우 보기 좋게 표 형태로 출력
            print(f"{'재료명':<10} | {'수량/무게':<10} | {'유통기한'}")
            print("-" * 40)
            for name, info in self.user_ingredients.items():
                # .items()를 통해 재료명(name)과 상세 정보 딕셔너리(info)를 가져와 형식에 맞춰 출력
                print(f"{name:<10} | {info['amount']:<10} | {info['exp_date']}")
        print("========================================")

    def add_ingredient(self):
        """사용자로부터 새로운 재료의 이름, 양, 유통기한을 입력받아 저장하는 메서드"""
        print("\n[새 재료 추가]")
        print("취소하고 메인으로 돌아가려면 엔터를 누르세요.")
        
        # 여러 개의 재료를 연속으로 입력받기 위해 무한 루프 사용
        while True:
            # 1. 재료 이름 입력
            name = input("\n1. 재료 이름 (예: 김치, 계란): ").strip()
            # 아무것도 입력하지 않고 엔터를 치면 루프를 종료하고 메인 메뉴로 복귀
            if not name:
                break
                
            # 2. 재료 양 입력
            amount = input("2. 양 (예: 500g 등 gram 단위 기준으로 정확히 입력해 주세요): ").strip()
            if not amount:
                amount = "모름" # 입력 생략 시 기본값 할당
                
            # 3. 유통기한 입력 및 형식 검증
            while True:
                exp_date = input("3. 유통기한 (YYYY-MM-DD 형식, 예: 2026-05-30): ").strip()
                if not exp_date:
                    exp_date = "기한 없음" # 입력 생략 시 기본값 할당
                    break
                
                try:
                    # 사용자가 입력한 문자열이 실제 날짜 형식에 맞는지 검증
                    valid_date = datetime.strptime(exp_date, "%Y-%m-%d")
                    # 검증된 날짜를 다시 지정된 포맷의 문자열로 변환하여 저장
                    exp_date = valid_date.strftime("%Y-%m-%d")
                    break # 정상적인 날짜가 입력되면 검증 루프 탈출
                except ValueError:
                    # 날짜 형식이 틀렸을 경우 예외 처리하여 재입력 요구
                    print("[오류] 올바른 날짜 형식이 아닙니다. 다시 입력해주세요.")

            # 입력받은 정보를 user_ingredients 딕셔너리에 저장 (기존에 같은 이름이 있다면 덮어씌워짐)
            self.user_ingredients[name] = {
                "amount": amount,
                "exp_date": exp_date
            }
            print(f"\n✅ [{name}] 등록 완료! (계속 추가하려면 다음 재료를 입력하세요)")
            
    def reset_ingredients(self):
        """저장된 모든 냉장고 재료 데이터를 삭제(초기화)하는 메서드"""
        self.user_ingredients.clear() # 딕셔너리의 모든 항목 삭제
        print("\n🗑️ 냉장고를 깨끗하게 비웠습니다!")
        input("\n계속하려면 엔터를 누르세요...") # 사용자가 메시지를 확인할 수 있도록 대기

    def show_recommendations(self):
        """입력된 재료 데이터를 가공하여 추천 알고리즘을 돌리고 결과를 출력하는 메서드"""
        print("\n[레시피 추천 결과]")
        
        # 재료가 하나도 등록되지 않은 경우 추천을 진행하지 않음
        if not self.user_ingredients:
            print("먼저 냉장고에 재료를 입력해주세요!")
            input("\n계속하려면 엔터를 누르세요...")
            return # 메서드 실행 종료 후 메인으로 복귀

        # 1. 정렬 알고리즘이 요구하는 형식(리스트 내 딕셔너리)으로 데이터 변환
        raw_list_for_sorter = []
        for name, info in self.user_ingredients.items():
            exp_date = info['exp_date']
            
            # '기한 없음'인 재료는 유통기한 임박도 계산 시 가장 낮은 우선순위를 갖도록 
            # 임의의 아주 먼 미래 날짜(2099-12-31)로 세팅
            if exp_date == "기한 없음":
                exp_date = "2099-12-31" 
                
            raw_list_for_sorter.append({
                "name": name,
                "amount": info['amount'],
                "expire_date": exp_date
            })

        # 2. 내 정렬 모듈 직접 실행 (단일 파일 내부 함수 호출)
        # process_ingredients: 유통기한이 임박한 순 등 특정 기준에 따라 재료를 정렬
        sorted_list = process_ingredients(raw_list_for_sorter)
        
        # get_fridge_dict_for_main: 추천 알고리즘에 넣기 좋은 최종 딕셔너리 형태로 파싱
        parsed_fridge = get_fridge_dict_for_main(sorted_list)
        # ---------------------------------------------------------

        # 3. 추천 로직 호출
        # recommend_by_user_input: 파싱된 재료를 기반으로 레시피 가중치 점수를 계산하여 상위 N개 반환
        results = recommend_by_user_input(parsed_fridge, top_n=3)

        # 4. 결과 출력
        if results:
            print("-" * 40)
            # enumerate를 사용해 1위부터 순위(rank)와 함께 레시피명, 점수 출력
            for rank, (recipe, score) in enumerate(results, start=1):
                print(f"{rank}위: {recipe} (가중치 점수: {score:.2f})")
                
        input("\n메인 메뉴로 돌아가려면 엔터를 누르세요...")

    def run(self):
        """프로그램의 메인 루프를 실행하여 메뉴 선택 및 동작을 제어하는 메서드"""
        while True:
            self.clear_screen()  # 화면을 매번 초기화하여 깔끔한 UI 유지
            self.display_header() # 상단 타이틀 및 재료 목록 출력
            
            # 사용자 메뉴 출력
            print("1. 냉장고 재료 추가하기")
            print("2. 내 냉장고 비우기")
            print("3. 맞춤 레시피 추천받기")
            print("4. 프로그램 실행 종료")
            print("----------------------------------------")
            
            # 메뉴 번호 입력 받기
            choice = input(">> 원하는 메뉴 번호를 선택하세요: ").strip()

            # 입력된 번호에 따라 해당 메서드 분기 실행
            if choice == '1':
                self.add_ingredient()
            elif choice == '2':
                self.reset_ingredients()
            elif choice == '3':
                self.show_recommendations()
            elif choice == '4':
                # 프로그램 정상 종료 처리
                print("\n프로그램을 종료합니다. 맛있는 식사 되세요! 🍽️")
                sys.exit() # 파이썬 스크립트 실행 종료
            else:
                # 1~4 이외의 값 입력 시 예외 처리
                print("\n잘못된 입력입니다. 1~4 사이의 숫자를 입력해주세요.")
                input("\n계속하려면 엔터를 누르세요...")

# ==========================================
# 7. 실행부
# ==========================================
if __name__ == "__main__":
    app = RecipeRecommenderCLI()
    app.run()