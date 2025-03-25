import re
from search_func import or_search, and_search, phrase_search
from Boolean_test import build_query

def parse_to_list(query_expr):
    """
    将查询表达式解析为单词列表
    
    参数:
        query_expr (str): 原始查询表达式
        
    返回:
        list: 查询中的单个单词列表，不包含运算符和括号
    """
    # 调用Boolean_test.py的方法，获得处理后的query 
    query_expr = build_query(query_expr)
    # print(f"被Boolean处理后的query: {query_expr}")
    
    # 移除多余的空格
    query_expr = query_expr.strip()
    
    # 处理括号和AND操作符
    query_expr = query_expr.replace('(', ' ').replace(')', ' ')
    terms = []
    
    # 分割AND部分
    if ' AND ' in query_expr:
        parts = query_expr.split(' AND ')
        for part in parts:
            # 提取每部分的单词
            words = [w.strip() for w in part.split() if w.strip()]
            terms.extend(words)
    else:
        # 如果没有AND，直接分割为单词
        terms = [w.strip() for w in query_expr.split() if w.strip()]
    
    # 移除重复项并保持原始顺序
    unique_terms = []
    for term in terms:
        if term not in unique_terms and term != 'AND':
            unique_terms.append(term)
    
    print(f"解析后的单词列表: {unique_terms}")
    return unique_terms

# 处理查询词太长的情况情况
def handle_long_query(query_expr):
    """
    处理查询词太长或结果很少的情况
    
    参数:
        query_expr (str): 原始查询表达式
        
    返回:
        dict: 包含搜索结果的字典
    """
    print(f"handle_long_query: 处理查询 '{query_expr}'")
    
    # 获取查询词列表
    word_list = parse_to_list(query_expr)
    print(f"解析到的关键词: {word_list}")
    
    # 简单地使用OR搜索查找更多可能的结果
    print("执行OR搜索以获取更广泛的结果")
    results = or_search(" ".join(word_list))
    
    # 检查结果
    result_count = len(results["results"]) if "results" in results else 0
    print(f"OR搜索返回 {result_count} 条结果")
    
    return results




def parse_query(query_expr):
    """
    解析查询表达式并调用对应的搜索函数
    
    支持的格式:
    - (term1) AND (term2)        -> and_search
    - (term1 term2)              -> phrase_search
    - (term1) AND (term2 term3)  -> 词查询和短语查询的交集
    """

    # 调用Boolean_test.py的方法，获得处理后的query 
    query_expr = build_query(query_expr)
    print(f"被Boolean处理后的query: {query_expr}")
    # 移除多余的空格
    query_expr = query_expr.strip()
    
    # 检查是否包含 AND
    if ' AND ' in query_expr:
        # 分割 AND 子句
        parts = query_expr.split(' AND ')
        
        # 检查是否有包含空格的子句（短语查询）
        has_phrase = any(' ' in part.strip('()') for part in parts)
        
        if not has_phrase:
            # 如果都是单个词，直接使用 AND 查询
            terms = []
            for part in parts:
                term = part.strip('()')
                terms.append(term)
            return and_search(' '.join(terms))
        
        # 如果有短语，需要进行交集操作
        results_list = []
        for part in parts:
            # 去掉括号并处理每个子句
            part = part.strip('()')
            if ' ' in part:  # 如果包含空格，作为短语处理
                results = phrase_search(part)
            else:  # 单个词直接 OR 搜索
                results = or_search(part)
            
            if "results" in results:
                results_list.append(set(doc["doc_id"] for doc in results["results"]))
            else:
                return results  # 返回错误信息
        
        # 求所有结果的交集
        if results_list:
            common_doc_ids = set.intersection(*results_list)
            # 从最后一次查询的结果中提取完整的文档信息
            final_results = []
            for doc in results["results"]:  # 使用最后一次查询的结果
                if doc["doc_id"] in common_doc_ids:
                    final_results.append(doc)
            
            return {
                "results": final_results,
                "found_terms": []  # 这里可以合并所有查询的found_terms
            }
    
    # 如果只有一个括号对，作为短语查询处理
    if query_expr.startswith('(') and query_expr.endswith(')'):
        query = query_expr[1:-1].strip()
        if ' ' in query:  # 如果包含空格，作为短语处理
            return phrase_search(query)
        else:  # 单个词用 OR 搜索
            return or_search(query)
    
    # 默认作为 OR 查询处理
    return or_search(query_expr)

def test_parser():
    """测试解析器"""
    test_queries = [
        # '(machine learning)',                    # 短语查询
        'python AND java AND code what is it',        # 普通 AND 查询
        # '(python) AND (machine learning)',       # 词查询和短语查询的交集
        # '(deep learning) AND (AI)'              # 短语查询和词查询的交集
    ]
    
    for query in test_queries:
        print("\n" + "="*60)
        print(f"处理查询: {query}")
        results = parse_query(query)
        if "results" in results:
            print(f"找到 {len(results['results'])} 条结果")
            for doc in results['results'][:3]:  # 只显示前3条结果
                print("-"*40)
                print(f"标题: {doc['title']}")
                print(f"URL: {doc['url']}")
                print(f"内容预览: {doc['content'][:100]}...")
        else:
            print(f"错误: {results['message']}")

if __name__ == "__main__":
    parse_to_list("python AND(java learning) AND( code what is it)")
    
    # test_parser() 