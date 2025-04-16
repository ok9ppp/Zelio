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