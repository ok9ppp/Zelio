"""
DeepSeek API请求示例

该脚本展示了如何使用不同方式发送DeepSeek API请求，
包括直接消息、风险评估和便利度评估。
"""

import requests
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API配置
API_URL = "http://localhost:5000/api/chat"  # 本地API地址
TOKEN = os.getenv("JWT_TOKEN", "")  # JWT令牌，需要先登录获取

# 请求头
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def send_request(payload):
    """发送请求到DeepSeek API并打印结果"""
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"请求成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"发送请求时出错: {str(e)}")
        return None

# 示例1: 直接发送消息
def example_direct_message():
    """展示如何直接发送消息到DeepSeek"""
    print("\n==== 示例1: 直接发送消息 ====")
    
    payload = {
        "messages": [
            {"role": "system", "content": "你是一个医疗助手，请简明扼要地回答问题。"},
            {"role": "user", "content": "请简要介绍高血压的治疗方法。"}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    send_request(payload)

# 示例2: 风险评估请求
def example_risk_assessment():
    """展示如何发送风险评估请求"""
    print("\n==== 示例2: 风险评估请求 ====")
    
    payload = {
        "assessment_type": "risk",
        "disease": "2型糖尿病",
        "treatment_plan": "二甲双胍联合胰岛素治疗",
        "plan_description": "对于血糖控制不佳的2型糖尿病患者，采用二甲双胍口服药物联合胰岛素皮下注射的综合治疗方案，旨在有效控制血糖水平。",
        "treatment_duration": "长期治疗，需要持续监测",
        "population": "成年2型糖尿病患者，无严重肝肾功能不全"
    }
    
    send_request(payload)

# 示例3: 便利度评估请求
def example_convenience_assessment():
    """展示如何发送便利度评估请求"""
    print("\n==== 示例3: 便利度评估请求 ====")
    
    payload = {
        "assessment_type": "convenience",
        "disease": "轻度高血压",
        "treatment_plan": "氢氯噻嗪口服治疗",
        "plan_description": "使用氢氯噻嗪进行口服治疗，每日一次，需要定期监测血压和电解质水平。",
        "treatment_duration": "长期治疗",
        "treatment_frequency": "每日一次，每次服用一片，早餐后服用"
    }
    
    send_request(payload)

# 主函数
def main():
    """运行所有示例"""
    print("DeepSeek API请求示例")
    
    if not TOKEN:
        print("错误: 未设置JWT令牌，请先登录获取令牌")
        return
    
    example_direct_message()
    example_risk_assessment()
    example_convenience_assessment()

if __name__ == "__main__":
    main() 