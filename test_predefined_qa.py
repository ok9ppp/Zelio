#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试DeepSeek客户端的预设问答功能
"""

import logging
from deepseek_client import DeepSeekClient

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_predefined_qa():
    """测试预设问答功能"""
    client = DeepSeekClient()
    
    # 测试预设问题
    predefined_question = "边界中医价值医疗的流程"
    messages = [
        {"role": "user", "content": predefined_question}
    ]
    
    # 使用预设问答
    logger.info(f"测试预设问题: {predefined_question}")
    response = client.chat(messages, use_predefined=True)
    
    if "error" in response:
        logger.error(f"API调用错误: {response['error']}")
        return
    
    # 输出预设答案
    try:
        answer = response["choices"][0]["message"]["content"]
        logger.info("预设答案:")
        logger.info(answer)
        
        # 验证答案是否与预期匹配
        expected_answer = client.get_predefined_answer(predefined_question)
        assert answer == expected_answer, "预设答案与预期不匹配"
        logger.info("✅ 预设答案验证成功")
    except (KeyError, IndexError) as e:
        logger.error(f"解析响应失败: {e}")
        logger.error(f"响应内容: {response}")
    
    # 测试添加新的预设问答
    new_question = "边界中医的三大优势"
    new_answer = """边界中医的三大优势包括：
1. 融合中西医精华，提供更全面的治疗方案
2. 采用价值医疗模式，以患者健康结果为导向
3. 结合AI技术辅助诊断，提高治疗精准度和效率"""
    
    logger.info(f"添加新的预设问答: {new_question}")
    client.add_predefined_qa(new_question, new_answer)
    
    # 测试新添加的预设问答
    messages = [
        {"role": "user", "content": new_question}
    ]
    response = client.chat(messages, use_predefined=True)
    
    try:
        answer = response["choices"][0]["message"]["content"]
        logger.info("新添加的预设答案:")
        logger.info(answer)
        
        # 验证新添加的答案是否与预期匹配
        assert answer == new_answer, "新添加的预设答案与预期不匹配"
        logger.info("✅ 新添加的预设答案验证成功")
    except (KeyError, IndexError) as e:
        logger.error(f"解析响应失败: {e}")
        logger.error(f"响应内容: {response}")
    
    # 测试绕过预设问答
    logger.info("测试绕过预设问答，直接调用API")
    response = client.chat(messages, use_predefined=False)
    
    if "error" in response:
        logger.error(f"API调用错误: {response['error']}")
        logger.info("⚠️ 注意: 这可能是因为未设置有效的API密钥")
    else:
        try:
            answer = response["choices"][0]["message"]["content"]
            logger.info("API返回的答案:")
            logger.info(answer)
        except (KeyError, IndexError) as e:
            logger.error(f"解析响应失败: {e}")
            logger.error(f"响应内容: {response}")

if __name__ == "__main__":
    test_predefined_qa() 