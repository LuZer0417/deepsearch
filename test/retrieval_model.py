import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from rank_bm25 import BM25Okapi
from sklearn.preprocessing import MinMaxScaler

def load_search_results(filename):
    """加载指定的JSON文件，返回搜索结果。"""
    with open(filename, 'r') as f:
        return json.load(f)

def compute_tfidf(documents, queries):
    """计算TF-IDF分数。"""
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents)
    query_vector = vectorizer.transform(queries)
    doc_scores = np.asarray(query_vector.dot(tfidf_matrix.T).todense())
    return np.squeeze(np.asarray(np.sum(doc_scores, axis=0)))

def compute_bm25(documents, queries):
    """计算BM25分数。"""
    tokenized_docs = [doc.split() for doc in documents]
    bm25 = BM25Okapi(tokenized_docs)
    doc_scores = np.vstack([bm25.get_scores(query.split()) for query in queries])
    return np.sum(doc_scores, axis=0).ravel()

def compute_lm(documents, queries):
    """计算LM（语言模型）分数。"""
    term_frequencies = np.array([doc.lower().count(query) for doc in documents for query in queries]).reshape(len(documents), len(queries))
    return np.sum(term_frequencies, axis=1)

def normalize_sum(scores):
    """归一化分数，使其总和为1。"""
    total = scores.sum()
    return scores / total if total != 0 else scores

def compute_scores(documents, queries):
    """计算并归一化各模型的分数。"""
    tfidf_scores = compute_tfidf(documents, queries)
    bm25_scores = compute_bm25(documents, queries)
    lm_scores = compute_lm(documents, queries)

    tfidf_scores_normalized = normalize_sum(tfidf_scores)
    bm25_scores_normalized = normalize_sum(bm25_scores)
    lm_scores_normalized = normalize_sum(lm_scores)

    return tfidf_scores_normalized, bm25_scores_normalized, lm_scores_normalized

def rank_documents(doc_list, tfidf_scores, bm25_scores, lm_scores):
    """根据最终分数排序文档。"""
    final_scores = (
        0.1 * tfidf_scores +
        0.1 * bm25_scores +
        0.8 * lm_scores
    )
    
    # 合并文档和分数，并按分数排序
    sorted_docs = sorted(zip(doc_list, final_scores), key=lambda x: x[1], reverse=True)
    
    return sorted_docs

def get_top_documents(sorted_docs, top_n=300):
    """返回排序后的前N条文档。"""
    return sorted_docs[:top_n]

# def main(queries, filename='search_results_test.json'):
def main(results):
    """主函数：加载数据，计算分数，返回前N条文档。"""
    # 加载搜索结果
    search_results = results
    documents = [doc["content"] for doc in search_results["results"]]
    doc_list = search_results["results"]
    queries = search_results["found_terms"]
    print('给我看看queries: ', queries)
    # 计算分数
    tfidf_scores, bm25_scores, lm_scores = compute_scores(documents, queries)
    
    # 排序文档
    sorted_docs = rank_documents(doc_list, tfidf_scores, bm25_scores, lm_scores)
    
    # 获取前300条文档
    top_docs = get_top_documents(sorted_docs)
    
    # 准备输出，格式与原始的search_results_test.json一致
    output = {"results": top_docs,
              "found_terms": queries 
    }
    
    return output

def retrieval_sort(search_results, top_n=300):
    """
    对搜索结果进行高效重排序，优化为毫秒级
    :param search_results: 包含 'results' 键的字典
    :param top_n: 返回的最大文档数量，默认300
    :return: 重新排序后的结果
    """
    if not search_results or "results" not in search_results or not search_results["results"]:
        return search_results
        
    # 设置排序最大处理文档数，超过则先截断
    max_docs_to_process = 5000  # 限制计算量
    results = search_results["results"]
    if len(results) > max_docs_to_process:
        results = results[:max_docs_to_process]

    # 1. 使用更轻量级的特征：预先计算的TF与文档长度
    final_scores = np.zeros(len(results))
    
    # 快速提取查询词（不使用term_frequencies以提高速度）
    query_terms = search_results.get("found_terms", [])
    if not query_terms and len(results) > 0:
        # 从搜索结果标题提取作为备选
        query_terms = " ".join([doc.get("title", "") for doc in results[:5]]).split()[:10]
    
    # 如果仍然没有查询词，使用第一个结果的内容中的前10个单词
    if not query_terms and len(results) > 0 and "content" in results[0]:
        query_terms = results[0]["content"].split()[:10]
    
    # 2. 极速版BM25评分：只检查词是否存在而不计算完整TF-IDF
    term_weights = {term: 1.0 for term in query_terms}  # 简单词权重
    
    # 3. 并行计算得分 (使用numpy向量化操作代替循环)
    doc_lengths = np.array([len(doc.get("content", "").split()) for doc in results])
    avg_length = np.mean(doc_lengths) if doc_lengths.size > 0 else 1
    
    # 归一化文档长度
    length_factors = 1.0 / (0.5 + 0.5 * (doc_lengths / avg_length) + 1e-9)
    
    # 对每个文档预先计算一个基础分数
    for i, doc in enumerate(results):
        # 利用内置命中计数或position数据(如存在)
        content = doc.get("content", "").lower()
        term_count = sum(1 for term in query_terms if term.lower() in content)
        
        # 使用简化的BM25启发式公式
        final_scores[i] = term_count * length_factors[i]
        
        # 如果有total_tf，将其考虑在内
        if "total_tf" in doc:
            final_scores[i] += doc["total_tf"] * 0.3
    
    # 4. 使用argpartition代替完整排序（更快）
    if len(final_scores) > top_n:
        top_indices = np.argpartition(-final_scores, top_n)[:top_n]
        top_indices = top_indices[np.argsort(-final_scores[top_indices])]
    else:
        top_indices = np.argsort(-final_scores)
    
    # 5. 获取排序后的文档
    sorted_results = [results[i] for i in top_indices]
    
    # 返回结果
    return {
        "results": sorted_results,
        "found_terms": search_results.get("found_terms", [])
    }

