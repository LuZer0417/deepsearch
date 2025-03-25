from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
from search_func import or_search, and_search, phrase_search
import uvicorn
import socket
from query_parser import parse_query, parse_to_list, handle_long_query
from retrieval_model import retrieval_sort
from ds_api import ds_api
import asyncio
from fastapi import applications
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import threading
import queue
from query_extension import extend_query_gpt35
import time  # 添加导入，如果尚未导入

# 定义请求和响应模型
class SearchRequest(BaseModel):
    query: str
    type: str = 'or'

class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    keywords: Optional[List[str]] = None

class SearchResponse(BaseModel):
    count: int
    results: List[SearchResult]
    error: Optional[str] = None
    keywords: Optional[List[str]] = None
    search_time: Optional[float] = None  # 仅搜索时间
    ai_time: Optional[float] = None  # 仅AI处理时间
    elapsed_time: Optional[float] = None  # 总时间

# 只创建一个FastAPI实例！
app = FastAPI(title="搜索引擎 API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 搜索接口
@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        # 记录开始时间
        start_time = time.time()
        
        query = request.query.strip()
        search_type = request.type

        # 添加调试打印
        print("\n=== 搜索请求信息 ===")
        print(f"收到查询: {query}")
        print(f"查询类型: {search_type}")
        
        if not query:
            print("错误: 空查询")
            raise HTTPException(status_code=400, detail="查询不能为空")

        # 获取关键词列表用于高亮
        keywords = parse_to_list(query)
        print(f"高亮关键词: {keywords}")

        try:
            processed_query = query
            print(f"正在查询: {processed_query}")
        except Exception as e:
            print(f"查询处理错误: {str(e)}")
            raise HTTPException(status_code=400, detail=f"查询处理错误: {str(e)}")

        # 执行搜索
        try:
            print(f"执行搜索...")
            results = parse_query(processed_query)
            print(f"初始搜索返回结果结构: {results.keys() if isinstance(results, dict) else '非字典结构'}")
            
            # 检查结果是否为空或少于30条
            result_count = 0
            if isinstance(results, dict) and "results" in results:
                result_count = len(results["results"])
            
            print(f"初始搜索找到 {result_count} 条结果")
            
            # 修改检查逻辑，处理结果可能为空的情况
            if result_count < 30:
                print(f"搜索结果较少 (仅{result_count}条)，尝试使用handle_long_query函数")
                # 调用handle_long_query获取更多结果
                alternative_results = handle_long_query(processed_query)
                
                # 检查替代结果
                alt_result_count = 0
                if isinstance(alternative_results, dict) and "results" in alternative_results:
                    alt_result_count = len(alternative_results["results"])
                
                print(f"替代搜索找到 {alt_result_count} 条结果")
                
                # 只有当替代结果有更多内容时才替换
                if alt_result_count > result_count:
                    print(f"使用handle_long_query获得更多结果: {alt_result_count}条")
                    results = alternative_results
                else:
                    print("handle_long_query未能提供更好的结果，保留原始结果")
            
            # 限制结果数量，防止排序过慢
            max_results = 5000
            if "results" in results and len(results["results"]) > max_results:
                print(f"结果数量过多 ({len(results['results'])}), 限制为前{max_results}条进行排序")
                results["results"] = results["results"][:max_results]
            
            print(f"搜索结束，开始进行推荐排序")
            print(f"开始计时")
            start_time = time.time()
            result_after_sort = retrieval_sort(results)
            print(f"排序完成，用时: {time.time() - start_time:.2f} 秒")
            
        except Exception as e:
            print(f"搜索执行错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"搜索执行错误: {str(e)}")
            
        # 处理结果
        simplified_results = []
        if "results" in result_after_sort:
            print(f"处理 {len(result_after_sort['results'])} 个结果...")
            for doc in result_after_sort["results"]:
                try:
                    # 修复 URL
                    url = doc["url"]
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url.lstrip('/')
                    
                    # 添加关键词列表用于前端高亮
                    simplified_result = SearchResult(
                        title=doc["title"],
                        url=url,
                        content=doc["content"],
                        keywords=keywords  # 添加关键词列表
                    )
                    simplified_results.append(simplified_result)
                except Exception as e:
                    print(f"处理文档时出错: {str(e)}, 文档: {doc}")

        print(f"找到结果数量: {len(simplified_results)}")
        # 停止计时，记录搜索时间
        search_elapsed_time = time.time() - start_time
        print(f"搜索完成，用时: {search_elapsed_time:.2f} 秒")
        
        # AI处理（如果有）...
        # 这部分不计入搜索时间

        response = SearchResponse(
            count=len(simplified_results),
            results=simplified_results,
            keywords=keywords,
            elapsed_time=search_elapsed_time  # 仅包含搜索部分的时间
        )

        # 检查序列化
        try:
            from fastapi.encoders import jsonable_encoder
            response_json = jsonable_encoder(response)
            print(f"响应JSON长度: {len(str(response_json))}")
            if len(simplified_results) > 0:
                print(f"第一个结果: {response_json['results'][0]}")
        except Exception as e:
            print(f"序列化响应时出错: {str(e)}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

# AI流式响应端点
@app.get("/api/ai-stream")
async def ai_stream_endpoint(query: Optional[str] = None):
    """AI流式响应端点"""
    if not query or not query.strip():
        return StreamingResponse(
            iter(["data: Error: Empty query\n\n"]),
            media_type="text/event-stream"
        )
        
    print(f"收到AI流式请求，查询: '{query}'")
    
    # 创建一个标准队列用于线程间通信
    message_queue = queue.Queue()
    
    # 定义回调函数将流式输出放入队列
    def stream_callback(chunk: str):
        message_queue.put(chunk)
    
    # 在后台线程中运行 ds_api
    def run_ds_api():
        try:
            ds_api(query, stream_callback)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            message_queue.put(error_msg)
        finally:
            # 标记流结束
            message_queue.put(None)
    
    # 启动后台线程
    thread = threading.Thread(target=run_ds_api)
    thread.daemon = True
    thread.start()
    
    # 从队列读取并输出数据的异步生成器
    async def generate_stream() -> AsyncGenerator[str, None]:
        while True:
            try:
                chunk = message_queue.get(timeout=0.1)
                
                if chunk is None:  # 流结束标记
                    break
                    
                yield f"data: {chunk}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
    
    # 返回 SSE 流
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# 静态文件和主页路由
@app.get("/")
async def read_root():
    return FileResponse("../front-end/index.html")

app.mount("/static", StaticFiles(directory="../front-end"), name="static")

# 调试和测试端点
@app.get("/routes", include_in_schema=False)
async def show_routes():
    """列出所有注册的路由"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "name": route.name,
                "methods": list(route.methods)
            })
    return {"routes": routes}

@app.get("/api/test", response_model=dict)
async def test_endpoint():
    """简单测试端点，确认API正常工作"""
    return {"status": "ok", "message": "Test endpoint is working"}

# 应用启动事件处理
@app.on_event("startup")
async def startup_event():
    print("\n=== 已注册的API路由 ===")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ", ".join(route.methods)
            print(f"{methods:8} {route.path}")
    print("=====================\n")

# 端口查找函数
def find_free_port(start_port=5000, max_port=5100):
    """找到一个可用的端口"""
    for port in range(start_port, max_port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('', port))
            s.close()
            return port
        except OSError:
            continue
    raise OSError("Could not find a free port")

# 添加此API端点，获取查询扩展建议
@app.get("/api/query-suggestions")
async def get_query_suggestions(query: str):
    """根据用户查询返回查询扩展建议"""
    if not query or len(query.strip()) < 2:
        return {"suggestions": []}
    
    try:
        # 使用extend_query_gpt35生成建议
        result = extend_query_gpt35(query)
        
        # 获取扩展查询列表
        suggestions = result.get("expanded_queries", [])
        
        # 返回原始查询和扩展建议
        return {
            "original_query": result.get("original_query", query),
            "suggestions": suggestions
        }
    except Exception as e:
        print(f"生成查询建议时出错: {str(e)}")
        return {"suggestions": [], "error": str(e)}

# 应用入口
if __name__ == "__main__":
    try:
        port = 8080
        print(f"\n服务器启动在端口 {port}")
        print(f"请访问: http://localhost:{port}")
        print(f"API文档: http://localhost:{port}/docs\n")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"启动服务器时出错: {e}")




