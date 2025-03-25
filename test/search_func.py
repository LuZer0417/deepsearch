'''
input: mongoDB数据库 query
output: 查询到的结果，当前以list[doc]的格式

'''

import pymongo
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import nltk
import pickle
import os
import string
import json
from retrieval_model import retrieval_sort
# 缓存文件路径
CACHE_DIR = "cache"
# II_CACHE_FILE_A = os.path.join(CACHE_DIR, "inverted_index_a_cache.pkl")
II_CACHE_FILES = {
    char: os.path.join(CACHE_DIR, f"inverted_index_{char}_cache.pkl")
    for char in string.ascii_lowercase + string.digits
}
# 实例去访问
# print(II_CACHE_FILES["a"])  # /path/to/cache/inverted_index_a_cache.pkl


CONTENT_CACHE_FILE = os.path.join(CACHE_DIR, "content_cache.pkl")

# 确保缓存目录存在
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# 确保下载必要的NLTK数据
try:
    nltk.data.find('corpora/wordnet')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('wordnet')
    nltk.download('stopwords')

# 全局初始化词形还原器
lemmatizer = WordNetLemmatizer()

# 获取英文停用词列表
STOP_WORDS = set(stopwords.words('english'))

# 连接到 MongoDB
client = pymongo.MongoClient("mongodb://35.214.122.215:27017")
db = client['search_db']
content_collection = db['content']
# inverted_index_collection_a = db['inverted_index_a']
# inverted_index_collections["a"]
inverted_index_collections = {
    char: db[f"inverted_index_{char}"] for char in string.ascii_lowercase + string.digits
}

# 缓存数据
# _inverted_index_cache_a = None
# _inverted_index_caches["a"]
_inverted_index_caches = {char: None for char in string.ascii_lowercase + string.digits}

_content_cache = None

def load_inverted_index_caches(first_char):
    """加载倒排索引缓存"""
    for char, value in _inverted_index_caches.items():
        if char == first_char:
            if _inverted_index_caches[char] is None:
                globals()[f"_inverted_index_caches_{char}"] = _inverted_index_caches[char]
                print(f"加载倒排索引缓存{char}...")
                try:
                    with open(II_CACHE_FILES[char], 'rb') as f:
                        _inverted_index_caches[char] = pickle.load(f)
                    print(f"从文件加载倒排索引缓存{char}完成")
                except (FileNotFoundError, EOFError):
                    print(f"从数据库加载倒排索引缓存{char}...")
                    _inverted_index_caches[char] = {}
                    for term_doc in inverted_index_collections[char].find():
                        _inverted_index_caches[char][term_doc['term']] = term_doc['data']
                    # 保存到文件
                    with open(II_CACHE_FILES[char], 'wb') as f:
                        pickle.dump(_inverted_index_caches[char], f)
                    print(f"倒排索引缓存{char}已保存到文件")




def load_content_caches():
    """加载数据到缓存，优先从文件加载，如果文件不存在则从数据库加载并保存到文件"""
    global _content_cache
    
    if all(value is not None for value in _inverted_index_caches.values()) and _content_cache is not None:
        return  # 如果内存中已有缓存，直接返回
    
    # 尝试从文件加载文档内容缓存
    if _content_cache is None:
        print("加载文档内容...")
        try:
            with open(CONTENT_CACHE_FILE, 'rb') as f:
                _content_cache = pickle.load(f)
            print("从文件加载文档内容完成")
        except (FileNotFoundError, EOFError):
            print("从数据库加载文档内容...")
            _content_cache = {
                str(doc['doc_id']): doc 
                for doc in content_collection.find({}, {"_id": 0})
            }
            # 保存到文件
            with open(CONTENT_CACHE_FILE, 'wb') as f:
                pickle.dump(_content_cache, f)
            print("文档内容已保存到文件")
    

    # 在服务器中 可以一次性加载所有缓存文件
    # for char, value in _inverted_index_caches.items():
    #     if _inverted_index_caches[char] is None:
    #         globals()[f"_inverted_index_caches_{char}"] = _inverted_index_caches[char]
    #         print(f"加载倒排索引缓存{char}...")
    #         try:
    #             with open(II_CACHE_FILES[char], 'rb') as f:
    #                 _inverted_index_caches[char] = pickle.load(f)
    #             print(f"从文件加载倒排索引缓存{char}完成")
    #         except (FileNotFoundError, EOFError):
    #             print(f"从数据库加载倒排索引缓存{char}...")
    #             _inverted_index_caches[char] = {}
    #             for term_doc in inverted_index_collections[char].find():
    #                 _inverted_index_caches[char][term_doc['term']] = term_doc['data']
    #             # 保存到文件
    #             with open(II_CACHE_FILES[char], 'wb') as f:
    #                 pickle.dump(_inverted_index_caches[char], f)
    #             print(f"倒排索引缓存{char}已保存到文件")



def process_query(query):
    """
    处理查询字符串：小写化、去停用词、词形还原
    :param query: 原始查询字符串
    :return: 处理后的词列表
    """
    # 分词并小写化
    words = query.lower().split()
    # 去除停用词并进行词形还原
    return [lemmatizer.lemmatize(word) for word in words if word not in STOP_WORDS]

def or_search(query):
    """
    或查询（OR）：查找包含任意查询词的文档
    :param query: 查询的关键词字符串，多个关键词用空格分隔
    :return: 查询结果列表或错误信息
    """
    load_content_caches()
    query_terms = process_query(query)
    
    if not query_terms:
        return {"message": "No valid search terms after removing stop words."}
    
    doc_scores = {}
    found_terms = []
    
    for term in query_terms:
        first_char = term[0]
        load_inverted_index_caches(first_char)
        if term in _inverted_index_caches[first_char]:
            found_terms.append(term)
            results = _inverted_index_caches[first_char][term]
            for doc_id, data in results.items():
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'total_tf': 0,
                        'terms': {},
                        'positions': {}
                    }
                doc_scores[doc_id]['total_tf'] += data['tf']
                doc_scores[doc_id]['terms'][term] = data['tf']
                doc_scores[doc_id]['positions'][term] = data['positions']

    if not found_terms:
        return {"message": f"None of the search terms were found in the index."}

    output = []
    for doc_id, score_data in sorted(
        doc_scores.items(), 
        key=lambda x: x[1]['total_tf'], 
        reverse=True
    ):
        document = _content_cache.get(doc_id)
        if document:
            output.append({
                "doc_id": doc_id,
                "title": document['title'],
                "url": document['url'],
                "content": document['content'],
                "total_tf": score_data['total_tf'],
                "term_frequencies": score_data['terms'],
                "term_positions": score_data['positions']
            })
    
    return {
        "results": output, 
        "found_terms": found_terms
    }

def phrase_search(query):
    """
    短语查询：查找包含完整短语的文档（词必须相邻）
    :param query: 查询的短语（不需要引号）
    :return: 查询结果列表或错误信息
    """
    load_content_caches()
    query_terms = process_query(query)
    
    if len(query_terms) < 2:
        return {"message": "Phrase search requires at least two non-stop words."}
    
    doc_scores = {}
    found_terms = []
    
    # 首先找到包含所有查询词的文档
    for term in query_terms:
        first_char = term[0]
        load_inverted_index_caches(first_char)
        if term in _inverted_index_caches[first_char]:
            found_terms.append(term)
            results = _inverted_index_caches[first_char][term]
            for doc_id, data in results.items():
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'total_tf': 0,
                        'terms': {},
                        'positions': {},
                        'phrase_matches': 0
                    }
                doc_scores[doc_id]['total_tf'] += data['tf']
                doc_scores[doc_id]['terms'][term] = data['tf']
                doc_scores[doc_id]['positions'][term] = data['positions']
    
    if not found_terms:
        return {"message": f"None of the phrase terms were found in the index."}
    
    # 检查词的位置是否相邻
    filtered_docs = {}
    for doc_id, score_data in doc_scores.items():
        # 检查文档是否包含所有查询词
        if len(score_data['positions']) == len(query_terms):
            phrase_matches = find_phrase_matches(
                query_terms, 
                score_data['positions']
            )
            if phrase_matches > 0:
                score_data['phrase_matches'] = phrase_matches
                filtered_docs[doc_id] = score_data

    if not filtered_docs:
        return {"message": f"The phrase '{query}' was not found in any document."}

    output = []
    for doc_id, score_data in sorted(
        filtered_docs.items(), 
        key=lambda x: x[1]['phrase_matches'], 
        reverse=True
    ):
        document = _content_cache.get(doc_id)
        if document:
            output.append({
                "doc_id": doc_id,
                "title": document['title'],
                "url": document['url'],
                "content": document['content'],
                "total_tf": score_data['total_tf'],
                "term_frequencies": score_data['terms'],
                "term_positions": score_data['positions'],
                "phrase_matches": score_data['phrase_matches']
            })
    
    return {
        "results": output, 
        "found_terms": found_terms
    }

def and_search(query):
    """
    与查询：查找同时包含所有查询词的文档
    :param query: 查询的关键词字符串，多个关键词用空格分隔
    :return: 查询结果列表或错误信息
    """
    load_content_caches()
    query_terms = process_query(query)
    
    if len(query_terms) < 1:
        return {"message": "No valid search terms after removing stop words."}
    
    if len(query_terms) == 1:
        return or_search(" ".join(query_terms))
    
    doc_scores = {}
    found_terms = []
    term_docs = {}  # 存储每个词出现的文档集合
    
    # 首先收集每个词出现的文档
    for term in query_terms:
        first_char = term[0]
        load_inverted_index_caches(first_char)
        if term in _inverted_index_caches[first_char]:
            found_terms.append(term)
            results = _inverted_index_caches[first_char][term]
            term_docs[term] = set(results.keys())  # 该词出现的所有文档ID
            
            # 记录文档信息
            for doc_id, data in results.items():
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'total_tf': 0,
                        'terms': {},
                        'positions': {}
                    }
                doc_scores[doc_id]['total_tf'] += data['tf']
                doc_scores[doc_id]['terms'][term] = data['tf']
                doc_scores[doc_id]['positions'][term] = data['positions']
    
    if not found_terms:
        return {"message": f"None of the search terms were found in the index."}
    
    if len(found_terms) < len(query_terms):
        missing_terms = set(query_terms) - set(found_terms)
        return {"message": f"Some terms were not found: {', '.join(missing_terms)}"}
    
    # 计算所有词共同出现的文档（求交集）
    common_docs = set.intersection(*term_docs.values())
    
    if not common_docs:
        return {"message": f"No documents contain all the terms: {', '.join(query_terms)}"}
    
    # 只保留包含所有词的文档
    filtered_scores = {
        doc_id: score_data 
        for doc_id, score_data in doc_scores.items() 
        if doc_id in common_docs
    }

    output = []
    for doc_id, score_data in sorted(
        filtered_scores.items(), 
        key=lambda x: x[1]['total_tf'], 
        reverse=True
    ):
        document = _content_cache.get(doc_id)
        if document:
            output.append({
                "doc_id": doc_id,
                "title": document['title'],
                "url": document['url'],
                "content": document['content'],
                "total_tf": score_data['total_tf'],
                "term_frequencies": score_data['terms'],
                "term_positions": score_data['positions']
            })
    
    return {
        "results": output, 
        "found_terms": found_terms
    }

def find_phrase_matches(query_terms, positions):
    """
    查找短语匹配的次数
    :param query_terms: 查询词列表
    :param positions: 每个词的位置字典
    :return: 匹配的次数
    """
    if not query_terms or not positions:
        return 0
    
    # 获取第一个词的所有位置
    matches = 0
    first_positions = positions[query_terms[0]]
    
    # 对于第一个词的每个位置，检查是否存在连续的短语
    for pos in first_positions:
        is_match = True
        for i, term in enumerate(query_terms[1:], 1):
            # 检查下一个词是否在预期位置
            expected_pos = pos + i
            if term not in positions or expected_pos not in positions[term]:
                is_match = False
                break
        if is_match:
            matches += 1
    
    return matches

def test_search():
    """
    测试搜索功能并打印结果
    """
    # 测试关键词查询
    print("="*60)
    print("测试关键词查询")
    print("="*60)
    keyword_query = "type"
    print(f"搜索词: {keyword_query}")
    print(f"处理后的搜索词: {' '.join(process_query(keyword_query))}")
    print("-" * 50)
    results = or_search(keyword_query)
    print_results(results, query_type="关键词查询")
    print("^"*60)
    print("测试与查询 点到为止！")
    
    print("我看看排序后的结果: ", retrieval_sort(results))
    with open('search_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return 0
    # 测试与查询
    print("\n" + "="*60)
    print("测试与查询")
    print("="*60)
    and_query = "dogs and cats"
    print(f"搜索词: {and_query}")
    print("-" * 50)
    results = and_search(and_query)
    print_results(results, query_type="与查询")
    
    # 保存结果到 JSON 文件
    with open('search_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    

    # 测试短语查询
    print("\n" + "="*60)
    print("测试短语查询")
    print("="*60)
    phrase_query = "machine learning"
    print(f"搜索词: \"{phrase_query}\"")
    print("-" * 50)
    results = phrase_search(phrase_query)
    print_results(results, query_type="短语查询")
    return 0

def print_results(results, query_type):
    """
    打印搜索结果
    """
    if "results" in results:
        print("\n搜索结果:")
        print(f"查询类型: {query_type}")
        print(f"找到的关键词: {', '.join(results['found_terms'])}")
        print(f"找到 {len(results['results'])} 条结果：\n")
        
        for idx, doc in enumerate(results['results'], 1):
            print(f"结果 {idx}:")
            print(f"文档ID: {doc['doc_id']}")
            print(f"标题: {doc['title']}")
            print(f"URL: {doc['url']}")
            if "phrase_matches" in doc:
                print(f"短语出现次数: {doc['phrase_matches']}")
            print(f"关键词总出现次数: {doc['total_tf']}")
            print("每个关键词出现次数:")
            for term, freq in doc['term_frequencies'].items():
                print(f"  - {term}: {freq}次")
            print("关键词出现位置:")
            for term, pos in doc['term_positions'].items():
                print(f"  - {term}: {pos}")
            print(f"内容预览: {doc['content'][:200]}...")
            print("-" * 50)
    else:
        print(results["message"])

if __name__ == "__main__":
    test_search()