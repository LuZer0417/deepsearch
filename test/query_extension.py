import os
import json
import openai

# 请确保在环境变量中设置了 OPENAI_API_KEY，
# 或者在下面直接指定你的 API 密钥，如：
openai.api_key = "sk-proj-XXX"

def extend_query_gpt35(original_query: str) -> list:
    """
    使用 OpenAI 的 GPT-3.5 API 生成 10 个相关查询拓展，
    并返回列表：
    {
        "original_query": "artificial intelligence",
        "expanded_queries": [
            "query expansion 1",
            "query expansion 2",
            ... (共10项)
        ]
    }
    """
    # 构造 prompt，指示模型输出严格的 10 个编号行，不包含额外文字
    prompt = (
        f'For the search query "{original_query}", generate exactly 10 distinct and relevant expanded queries. '
        "Output ONLY a numbered list in the following format (do not include any additional text):\n\n"
        "1. <expanded query 1>\n"
        "2. <expanded query 2>\n"
        "3. <expanded query 3>\n"
        "4. <expanded query 4>\n"
        "5. <expanded query 5>\n"
        "6. <expanded query 6>\n"
        "7. <expanded query 7>\n"
        "8. <expanded query 8>\n"
        "9. <expanded query 9>\n"
        "10. <expanded query 10>\n"
    )
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=200
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=4)
    
    # 提取模型返回的文本内容
    output_text = response.choices[0].message["content"].strip()
    
    # 使用简单的分行和正则提取编号项
    lines = output_text.splitlines()
    expanded_queries = []
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit():
            # 去掉编号和句点
            parts = line.split(".", 1)
            if len(parts) == 2:
                query_expansion = parts[1].strip()
                if query_expansion:
                    expanded_queries.append(query_expansion)
        if len(expanded_queries) >= 10:
            break
    
    result = {
        "original_query": original_query,
        "expanded_queries": expanded_queries[:10]
    }
    return result


def extend_query_gpt35_json(original_query: str) -> str:
    """返回 JSON 格式的查询扩展结果"""
    result = extend_query_gpt35(original_query)
    return json.dumps(result, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    query = input("Enter query: ").strip()
    result_json = extend_query_gpt35(query)
    print("Generated result:")
    print(result_json)
