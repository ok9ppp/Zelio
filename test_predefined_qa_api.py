#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试预设问答API
"""

import requests
import json
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API基本URL，根据实际情况调整
BASE_URL = "http://localhost:5000"

# 存储访问令牌
TOKEN = None

def login():
    """登录并获取令牌"""
    global TOKEN
    url = f"{BASE_URL}/api/login"
    
    # 替换为实际的用户名和密码
    payload = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        TOKEN = data.get('access_token')
        
        if TOKEN:
            logger.info("登录成功，获取到访问令牌")
            return True
        else:
            logger.error("登录成功但未获取到访问令牌")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"登录失败: {e}")
        if response.text:
            logger.error(f"响应内容: {response.text}")
        return False

def get_predefined_qa():
    """获取所有预设问答"""
    if not TOKEN:
        logger.error("未登录，请先调用login()")
        return None
        
    url = f"{BASE_URL}/api/predefined-qa"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        logger.info("获取预设问答成功")
        return data.get('predefined_qa', {})
    except requests.exceptions.RequestException as e:
        logger.error(f"获取预设问答失败: {e}")
        if response.text:
            logger.error(f"响应内容: {response.text}")
        return None

def add_predefined_qa(question, answer):
    """添加预设问答"""
    if not TOKEN:
        logger.error("未登录，请先调用login()")
        return False
        
    url = f"{BASE_URL}/api/predefined-qa"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "question": question,
        "answer": answer
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        logger.info(f"添加预设问答成功: {question}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"添加预设问答失败: {e}")
        if response.text:
            logger.error(f"响应内容: {response.text}")
        return False

def test_chat_with_predefined_qa(question):
    """测试使用预设问答进行对话"""
    if not TOKEN:
        logger.error("未登录，请先调用login()")
        return None
        
    url = f"{BASE_URL}/api/chat"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "messages": [
            {"role": "user", "content": question}
        ],
        "use_predefined": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        logger.info("对话请求成功")
        
        # 提取回复内容
        try:
            answer = data["choices"][0]["message"]["content"]
            return answer
        except (KeyError, IndexError):
            logger.error(f"无法提取回复内容: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"对话请求失败: {e}")
        if response.text:
            logger.error(f"响应内容: {response.text}")
        return None

def main():
    """主函数"""
    # 登录
    if not login():
        logger.error("登录失败，测试中止")
        return
    
    # 获取当前预设问答
    logger.info("获取当前预设问答...")
    current_predefined_qa = get_predefined_qa()
    logger.info(f"当前预设问答: {json.dumps(current_predefined_qa, ensure_ascii=False, indent=2)}")
    
    # 测试已有的预设问答
    predefined_question = "边界中医价值医疗的流程"
    logger.info(f"测试已有的预设问答: {predefined_question}")
    answer = test_chat_with_predefined_qa(predefined_question)
    
    if answer:
        logger.info(f"预设回复:\n{answer}")
    else:
        logger.error("没有获取到预设回复")
    
    # 添加新的预设问答
    new_question = "边界中医的价值定位"
    new_answer = """边界中医的价值定位是：
1. 融合传统中医与现代医学，提供更全面的诊疗方案
2. 通过价值医疗模式，以患者健康结果为导向，重视疗效
3. 利用人工智能和大数据技术，提高诊疗精准度和效率
4. 建立明确的风险评估和疗效评价体系，提供透明的医疗服务"""
    
    logger.info(f"添加新的预设问答: {new_question}")
    if add_predefined_qa(new_question, new_answer):
        # 测试新添加的预设问答
        logger.info(f"测试新添加的预设问答: {new_question}")
        answer = test_chat_with_predefined_qa(new_question)
        
        if answer:
            logger.info(f"预设回复:\n{answer}")
        else:
            logger.error("没有获取到预设回复")
    
    # 再次获取所有预设问答，确认是否添加成功
    logger.info("再次获取所有预设问答...")
    updated_predefined_qa = get_predefined_qa()
    logger.info(f"更新后的预设问答: {json.dumps(updated_predefined_qa, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    main() 