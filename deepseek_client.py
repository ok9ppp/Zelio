import requests
import os
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

class DeepSeekClient:
    """DeepSeek API客户端，用于调用DeepSeek的对话接口"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        # 预设问答集合
        self.predefined_qa = {
            "边界中医价值医疗的流程": """1.若已经诊断明确沟通明确需求即可，若未明确需求可根据大模型和人类医生及咨询师与患者沟通明确需求。
2.根据需求，AI和人类咨询师挑选和拟定治疗方案、医生、价格及相关协议签订。
3.由主负责医生审核通过后，确定执行计划和负责人员并监督完成。
4.若需调整计划应与咨询师沟通由其负责协调并重新签订协议。
5.完成诊疗计划后由医院，医生，患者三方签订疗效确认书，
6.用户进行评分，并给出意见和建议。"""
        }
        
        if not self.api_key:
            logger.warning("DeepSeek API密钥未设置，请在.env文件中设置DEEPSEEK_API_KEY")
    
    def chat(self, messages, temperature=0.7, max_tokens=2000):
        """
        调用DeepSeek的对话接口
        
        Args:
            messages (list): 对话历史，格式为[{"role": "user", "content": "你好"}, ...]
            temperature (float): 输出随机性，值越大输出越随机
            max_tokens (int): 最大生成token数
            
        Returns:
            dict: API响应结果
        """
        # 检查是否有预设答案
        if len(messages) > 0 and messages[-1]["role"] == "user":
            user_query = messages[-1]["content"].strip()
            
            # 检查是否匹配预设问题
            for question, answer in self.predefined_qa.items():
                if self._is_similar_question(user_query, question):
                    logger.info(f"找到匹配的预设问题: {question}")
                    return {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": answer
                                }
                            }
                        ]
                    }
        
        if not self.api_key:
            return {"error": "DeepSeek API密钥未设置"}
        
        try:
            url = f"{self.api_base}/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"DeepSeek API调用失败: {response.status_code}, {response.text}")
                return {"error": f"DeepSeek API调用失败: {response.status_code}", "details": response.text}
                
        except Exception as e:
            logger.error(f"调用DeepSeek API时发生异常: {str(e)}")
            return {"error": f"调用DeepSeek API时发生异常: {str(e)}"}
    
    def _is_similar_question(self, user_query, predefined_question):
        """
        检查用户问题是否与预设问题相似
        
        Args:
            user_query (str): 用户问题
            predefined_question (str): 预设问题
            
        Returns:
            bool: 是否相似
        """
        # 简单的关键词匹配，可以根据需要扩展为更复杂的相似度计算
        normalized_user_query = user_query.lower().strip()
        normalized_question = predefined_question.lower().strip()
        
        # 检查完全匹配
        if normalized_user_query == normalized_question:
            return True
            
        # 检查部分匹配
        key_terms = ["边界中医", "价值医疗", "流程"]
        question_terms = ["边界中医价值医疗"]
        
        # 如果用户查询包含关键词且包含"流程"一词
        for term in key_terms:
            if term in normalized_user_query:
                # 如果同时包含相关词和流程，认为是相似问题
                if "流程" in normalized_user_query:
                    return True
        
        # 如果用户查询完整包含了问题短语
        for term in question_terms:
            if term in normalized_user_query:
                return True
                
        return False
    
    def health_check(self):
        """检查DeepSeek API连接状态"""
        if not self.api_key:
            return {"status": "error", "message": "API密钥未设置"}
        
        try:
            # 简单测试请求
            messages = [{"role": "user", "content": "你好"}]
            response = self.chat(messages, max_tokens=10)
            
            if "error" in response:
                return {"status": "error", "message": response["error"]}
            
            return {"status": "ok", "message": "DeepSeek API连接正常"}
            
        except Exception as e:
            return {"status": "error", "message": f"连接测试失败: {str(e)}"}
    
    def add_predefined_qa(self, question, answer):
        """
        添加预设问答对
        
        Args:
            question (str): 问题
            answer (str): 答案
        """
        self.predefined_qa[question] = answer
        logger.info(f"已添加预设问答: {question}") 