import json
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

# 创建一个示例JSON，包含风险数据，用于前端开发参考
example_response = {
    "detail_page": {
        "risk_level_1": "未知",
        "risk_level_2": "未知", 
        "risk_level_3": "未知",
        "risk_prob_1": "15%",
        "risk_prob_2": "5%",
        "risk_prob_3": "1%"
    },
    "risk_data": {
        "levels": {
            "level_1": "未知",
            "level_2": "未知",
            "level_3": "未知"
        },
        "probabilities": {
            "prob_1": "15%",
            "prob_2": "5%",
            "prob_3": "1%"
        }
    }
}

print(json.dumps(example_response, cls=JSONEncoder, ensure_ascii=False, indent=2)) 