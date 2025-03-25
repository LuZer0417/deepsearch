import requests
import json
import sys
import time
from Boolean_test import build_query


'''
模型提供方
DeepSeek
API密钥
sk-XXX

模型
deepseek-reasoner
deepseek-chat
'''
# 你的 DeepSeek API 密钥
api_key = "sk-XXX"

# API 端点（假设是 chat/completions）
url = "https://api.deepseek.com/v1/chat/completions"

# 请求头
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
def ds_api(question, stream_handler=None):
    """
    调用 DeepSeek API 并处理响应
    
    参数:
    question - 要发送的问题
    stream_handler - 可选的回调函数，用于处理流式数据
    
    返回值:
    生成的完整文本
    """

    question_processed = build_query(question)
    data = {
    "model": "deepseek-chat",
    "messages": [
        {
            "role": "system",
            "content": """You are an assistant in a search engine. Please answer user queries following these guidelines:

1. Use full **Markdown** formatting.
2. Utilize appropriate headings (**###, ####**).
3. Present key points in **list format**.
4. Highlight important concepts using **bold text**.
5. Ensure proper spacing between paragraphs.
6. Keep responses **concise and well-structured**.

Provide direct answers without introductory phrases like 'Here is information about...'. """
        },
        {
            "role": "user",
            "content": "Please introduce: " + question_processed
        }
    ],
    "max_tokens": 300,
    "temperature": 0.7,
    "top_p": 1.0,
    "stream": True
}

    full_text = ""
    
    try:
        with requests.post(url, headers=headers, json=data, stream=True) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            line_text = line.decode('utf-8')
                            if line_text.startswith('data: '):
                                content = line_text[6:]
                                
                                if content == '[DONE]':
                                    break
                                    
                                payload = json.loads(content)
                                delta = payload.get('choices', [{}])[0].get('delta', {})
                                
                                if 'content' in delta:
                                    text_chunk = delta['content']
                                    full_text += text_chunk
                                    
                                    # 控制台输出
                                    sys.stdout.write(text_chunk)
                                    sys.stdout.flush()
                                    time.sleep(0.01)
                                    
                                    # 如果提供了流处理函数，调用它
                                    if stream_handler:
                                        stream_handler(text_chunk)
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            print(f"\n处理响应时出错: {str(e)}")
                print()
            else:
                print(f"请求失败，状态码：{response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"发送请求时出错: {str(e)}")
        
    return full_text

if __name__ == "__main__":
    question = "what is machine learning?"
    question = build_query(question)
    ds_api(question)