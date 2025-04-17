import requests
import json

# JWT token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc0MjUyNTQ2MiwianRpIjoiOGZiYTViMGMtYTBmNS00MTA2LWJiZjItYzcxOTc1NWVhY2JiIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY3ZDQ0NmY4OWYyOWM2OGFhNWZjMTQ2MCIsIm5iZiI6MTc0MjUyNTQ2MiwiY3NyZiI6ImU0NzllZWRlLTk2ZmItNDU4NC04YWIzLTkxNDQ3YjE2NTczYSIsImV4cCI6MTc0MjYxMTg2MiwidXNlcm5hbWUiOiJvazlwcHBvIiwicGhvbmUiOiIxNTM1NTAzMzgxMSJ9.FTk5sZqNy4HFiEcspauwf15OeSaBzfUz3fe684DETs0"

# 卡片IDs
card_ids = [
    "67dcc51031555b6b5d6e0b8b",
    "67dcca5d31555b6b5d6e0b8d",
    "67dcca5d31555b6b5d6e0b8e",
    "67dcca5d31555b6b5d6e0b8f"
]

# 测试每个卡片ID
for card_id in card_ids:
    url = f"http://localhost:5000/api/cards/detail/{card_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"Card ID: {card_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:100]}")
    print("-" * 50)
    
    if response.status_code == 200:
        try:
            data = response.json()
            if "data" in data:
                card_data = data["data"]
                
                # 检查评分字段
                print("评分字段检查:")
                
                # 前端期望字段
                frontend_fields = [
                    "complexity_score",         # 操作复杂度评分
                    "time_investment_score"     # 时间成本评分
                ]
                
                # 检查前端字段
                print("\n前端使用字段:")
                for field in frontend_fields:
                    if field in card_data:
                        print(f"✓ {field}: {card_data[field]}")
                    else:
                        print(f"✗ 缺少字段: {field}")
                
                # 兼容性字段
                compatibility_fields = [
                    "time_cost_score", "life_interference_score",
                    "操作难度评分", "时间成本评分", "生活干扰评分"
                ]
                
                # 检查兼容性字段
                print("\n兼容性字段:")
                for field in compatibility_fields:
                    if field in card_data:
                        print(f"✓ {field}: {card_data[field]}")
                    else:
                        print(f"✗ 缺少字段: {field}")
        except json.JSONDecodeError:
            print("无法解析JSON响应")
        
    print("\n") 