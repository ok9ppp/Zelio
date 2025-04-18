"""
DeepSeek 提示模板和标准答案格式

该模块定义了与DeepSeek API交互时使用的标准提示和响应格式，
主要用于医疗治疗方案的风险评估和分析。
"""

import json
from typing import Dict, List, Any, Optional

# 风险评估的系统提示
RISK_ASSESSMENT_SYSTEM_PROMPT = """你是一个医疗咨询师，你的任务是根据提供的医疗治疗方案信息，
评估治疗过程中可能出现的风险，将风险按照严重程度分为三级，并给出每种风险的发生概率。
请确保你的回答专业、客观、详细且结构化。回答必须按照指定格式输出。"""

# 风险评估的用户提示模板
RISK_ASSESSMENT_USER_PROMPT_TEMPLATE = """请对以下医疗治疗方案进行风险评估：

- 疾病：{disease}
- 治疗方案：{treatment_plan}
- 方案简介：{plan_description}
- 治疗时间：{treatment_duration}
- 人群特征：{population_characteristics}

请分析这个治疗方案可能存在的风险，并按照以下格式回答：
1. 一级风险（轻微不适，可自行恢复）：列出具体风险表现和发生概率
2. 二级风险（需干预治疗，可能有后遗症）：列出具体风险表现和发生概率
3. 三级风险（可能危及生命或造成永久损伤）：列出具体风险表现和发生概率
4. 总体风险评估：基于风险权重计算（一级×2 + 二级×5 + 三级×10）

注意：
- 风险必须具体明确，避免模糊表述
- 每个风险都必须给出发生概率（百分比）
- 回答必须采用JSON格式"""

# 风险评估的标准输出格式（仅供参考）
RISK_ASSESSMENT_RESPONSE_FORMAT = {
    "一级风险": [
        {"风险表现": "轻度头痛", "发生概率": "15.5%"},
        {"风险表现": "恶心", "发生概率": "8.2%"}
    ],
    "二级风险": [
        {"风险表现": "过敏反应", "发生概率": "3.6%"},
        {"风险表现": "暂时性视力模糊", "发生概率": "1.8%"}
    ],
    "三级风险": [
        {"风险表现": "严重器官损伤", "发生概率": "0.5%"},
        {"风险表现": "过敏性休克", "发生概率": "0.2%"}
    ],
    "总体风险评级": "中风险",
    "风险评分": 4.8,
    "评估依据": "该治疗方案主要涉及药物治疗，一级风险主要是常见的药物副作用，二级风险主要是过敏反应，三级风险发生概率较低但存在可能性。综合风险评分为4.8分，属于中等风险。"
}

def format_risk_assessment_prompt(disease: str, treatment_plan: str, 
                                  plan_description: str, treatment_duration: str,
                                  population_characteristics: str = "一般人群") -> List[Dict[str, str]]:
    """
    格式化风险评估提示，生成与DeepSeek API交互的消息列表
    
    Args:
        disease: 疾病名称
        treatment_plan: 治疗方案名称
        plan_description: 方案简介
        treatment_duration: 治疗时间
        population_characteristics: 人群特征，默认为"一般人群"
        
    Returns:
        包含系统提示和用户提示的消息列表
    """
    user_prompt = RISK_ASSESSMENT_USER_PROMPT_TEMPLATE.format(
        disease=disease,
        treatment_plan=treatment_plan,
        plan_description=plan_description,
        treatment_duration=treatment_duration,
        population_characteristics=population_characteristics
    )
    
    return [
        {"role": "system", "content": RISK_ASSESSMENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

def parse_risk_assessment_response(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    解析DeepSeek API的风险评估响应
    
    Args:
        response: DeepSeek API的原始响应
        
    Returns:
        解析后的风险评估结果，如果解析失败则返回None
    """
    try:
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            
            # 尝试从内容中提取JSON部分
            try:
                # 如果整个内容就是一个JSON
                risk_data = json.loads(content)
            except json.JSONDecodeError:
                # 尝试从文本中提取JSON部分
                import re
                json_match = re.search(r'```json(.*?)```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    risk_data = json.loads(json_str)
                else:
                    # 尝试查找最接近JSON格式的部分
                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        json_str = content[start_idx:end_idx+1]
                        risk_data = json.loads(json_str)
                    else:
                        return None
            
            # 验证数据结构
            required_keys = ["一级风险", "二级风险", "三级风险", "总体风险评级"]
            if all(key in risk_data for key in required_keys):
                return risk_data
            
        return None
    except Exception as e:
        print(f"解析风险评估响应时出错: {str(e)}")
        return None

# 便利度评估的系统提示
CONVENIENCE_ASSESSMENT_SYSTEM_PROMPT = """你是一个专业的医疗便利度评估助手，你的任务是根据提供的医疗治疗方案信息，
评估治疗过程的便利程度，包括操作难度、时间成本和生活干扰，并给出总体便利度评级。
请确保你的回答专业、客观、详细且结构化。回答必须按照指定格式输出。"""

# 便利度评估的用户提示模板
CONVENIENCE_ASSESSMENT_USER_PROMPT_TEMPLATE = """请对以下医疗治疗方案进行便利度评估：

- 疾病：{disease}
- 治疗方案：{treatment_plan}
- 方案简介：{plan_description}
- 治疗时间：{treatment_duration}
- 治疗频次：{treatment_frequency}

请分析这个治疗方案的便利程度，并按照以下格式回答：
1. 操作难度评分（1-5分）：
   - 复杂的专业技能操作: 1分
   - 需要培训的简单操作: 3分
   - 不需要培训的操作: 5分

2. 时间成本评分（0-5分）：
   - 单月小于7小时: 5分
   - 单月7-14小时: 4分
   - 单月14-21小时: 3分
   - 单月21-28小时: 2分
   - 单月28-35小时: 1分
   - 单月35小时以上: 0分

3. 生活干扰评分（1-5分）：
   - 严重影响生活: 1分
   - 可调整: 3分
   - 影响较低: 5分

4. 总便利度评分和评级：
   - 总分>10: 高便利度
   - 6<总分≤10: 中便利度
   - 总分≤5: 低便利度

注意：
- 每项评分必须有明确的理由
- 回答必须采用JSON格式"""

# 其他提示模板和响应格式可以根据需要继续添加... 