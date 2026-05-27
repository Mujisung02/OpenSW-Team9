from datetime import datetime
import json

def process_ingredients(raw_inputs):
    """
    4번(인터페이스) 팀원에게 받은 raw 데이터를 정제하고 유통기한 순으로 정렬합니다.
    """
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
    """
    정렬된 리스트를 메인 파일 구조에 맞게
    {재료명: {'quantity': 수량, 'days_left': D-Day}} 형태로 변환합니다.
    """
    fridge_dict = {}
    for item in sorted_list:
        # 💡 팀원의 RecipeScorer가 요구하는 키 이름(quantity, days_left)에 정확히 맞춤!
        fridge_dict[item['name']] = {
            "quantity": item['amount_num'],
            "days_left": item['d_day']
        }
    return fridge_dict


# ==========================================
# 테스트 실행 (단위 테스트)
# ==========================================
if __name__ == "__main__":
    print("=== 정렬 및 데이터 변환 테스트 시작 ===\n")

    # 4번 팀원이 넘겨줄 가짜 입력 데이터
    dummy_ui_input = [
        {"name": "돼지고기", "expire_date": "2026-05-30", "amount": "600g"},
        {"name": "양파", "expire_date": "2026-05-20", "amount": "200"},
        {"name": "대파", "expire_date": "2026-05-18", "amount": "100g"}
    ]

    # 함수 실행
    sorted_detailed_list = process_ingredients(dummy_ui_input)
    final_fridge_dict = get_fridge_dict_for_main(sorted_detailed_list)

    print("팀장/팀원 메인 함수에 들어갈 최종 딕셔너리 포맷:")
    print(json.dumps(final_fridge_dict, indent=4, ensure_ascii=False))