from datetime import datetime
import json

def process_ingredients(raw_inputs):
    """
    팀원에게 받은 raw 데이터를 정제하고 정렬합니다.
    raw_inputs 예시: [{"name": "우유", "expire_date": "2026-05-18", "amount": "500ml"}, ...]
    """
    processed_list = []
    today = datetime.now() # 오늘 날짜 기준

    # item이라는 하나의 딕셔너리로 꺼내온 뒤, 키(Key)를 이용해 값을 찾습니다.
    for item in raw_inputs:
        name = item['name']
        date_str = item['expire_date']
        amount_str = item['amount']
        
        # 1. 유통기한 계산
        expire_date = datetime.strptime(date_str, "%Y-%m-%d")
        d_day = (expire_date - today).days
        
        # 2. 숫자와 단위 분리 (소수점 포함 처리로 수정)
        amount_num = ''.join(filter(lambda x: x.isdigit() or x == '.', amount_str))
        unit = ''.join(filter(str.isalpha, amount_str))
        
        # 3. 딕셔너리로 구조화
        ingredient_data = {
            'name': name,
            'expire_date': date_str,
            'd_day': d_day,
            'amount_num': float(amount_num) if amount_num else 0.0, # 테스트 코드와 맞추기 위해 float, amount_num으로 변경
            'unit': unit
        }
        processed_list.append(ingredient_data)
    
    # 4. 유통기한(d_day)이 임박한 순으로 정렬!
    processed_list.sort(key=lambda x: x['d_day'])
    
    return processed_list