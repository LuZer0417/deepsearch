'''
input: content.json
output: inverted_index.json
'''

import nltk
nltk.download('wordnet')
nltk.download('stopwords')
import json
import re
from collections import defaultdict
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

# Initialize lemmatizer and stopwords
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

def preprocess_text(text):
    """
    Preprocess text, including lowercase, removing stopwords, non-alphabetic characters, and lemmatization
    """
    text = text.lower()
    words = re.findall(r'\b\w+\b', text)
    words = [lemmatizer.lemmatize(word) for word in words if word not in stop_words]
    return words

def build_inverted_index(json_file_path, limit=None):
    """
    Build inverted index from given JSON file, including term frequency, term positions and total document terms
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    if limit:
        data = data[:limit]  # Limit the number of documents to process

    inverted_index = defaultdict(lambda: defaultdict(lambda: {"tf": 0, "positions": [], "total_terms": 0}))

    for record in data:
        doc_id = record['doc_id']  # Extract document ID
        content = record['content']  # Extract document content

        # Preprocess content
        words = preprocess_text(content)
        total_terms = len(words)

        # Build inverted index
        for position, word in enumerate(words, start=1):
            inverted_index[word][doc_id]["tf"] += 1
            inverted_index[word][doc_id]["positions"].append(position)
            inverted_index[word][doc_id]["total_terms"] = total_terms

    return inverted_index

# Build inverted index
json_file_path = 'output.json'  # Replace with your JSON file path
# inverted_index = build_inverted_index(json_file_path, limit=5000)  # Process first 5000 data entries
inverted_index = build_inverted_index(json_file_path)  # Process all data

# Save inverted index to file
with open('inverted_index.json', 'w', encoding='utf-8') as f:
    json.dump(inverted_index, f, ensure_ascii=False, indent=4)

print("Inverted index construction completed")