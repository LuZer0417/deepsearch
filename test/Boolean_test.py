import fasttext
import spacy
from symspellpy.symspellpy import SymSpell, Verbosity

model = fasttext.load_model("query_classifier.bin")
nlp = spacy.load("en_core_web_sm")

sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
sym_spell.load_dictionary("frequency_dictionary_en_82_765.txt", term_index=0, count_index=1)

STOPWORDS = {
    "the", "is", "a", "an", "of", "to", "and", "between", "which", "what",
    "when", "why", "who", "how", "are", "we", "for", "does", "do", "in",
    "on", "at", "that", "this", "be", "it", "should", "best", "ways",
    "will", "some", "recommend", "few", "much", "definition", "please", "i",
    "he", "she", "us", "you", "they", "me", "if", "any", "there", "about"
}


def spacy_preprocess(text: str):
    """
    Use spaCy for tokenization and dependency analysis, merging (compound + NOUN/PROPN) into a single phrase.
    Returns list: [(token_text, token_pos), ...]
    Preserves original case for proper PROPN recognition.
    """
    doc = nlp(text)
    tokens_out = []
    skip_next = False

    for i, token in enumerate(doc):
        if skip_next:
            skip_next = False
            continue

        if token.is_punct or token.is_space:
            continue

        if i < len(doc) - 1:
            next_token = doc[i + 1]
            # Check if current token is compound and next token is its head and a noun/proper noun
            if (token.dep_ == "compound"
                    and token.head == next_token
                    and next_token.pos_ in ["NOUN", "PROPN"]):
                merged_text = f"{token.orth_} {next_token.orth_}"  # Join with space
                # Merged pos_ temporarily inherits next_token's pos
                tokens_out.append((merged_text, next_token.pos_))
                skip_next = True
            else:
                tokens_out.append((token.orth_, token.pos_))
        else:
            tokens_out.append((token.orth_, token.pos_))

    return tokens_out


def classify_query_with_model(q: str) -> str:
    labels, probs = model.predict(q, k=1)
    label = labels[0]
    if label == "__label__boolean":
        return "boolean"
    elif label == "__label__phrase":
        return "phrase"
    else:
        return "boolean"


def parse_boolean_query(q: str) -> str:
    """
    Process with spacy_preprocess -> remove stopwords -> (optional) spell correction -> join boolean expression
    """
    tokens_pos = spacy_preprocess(q)
    # Each element is now (original text, pos), e.g. ("Google", "PROPN")
    corrected_tokens = []

    for token_text, token_pos in tokens_pos:
        # Remove leading/trailing spaces
        token_text_stripped = token_text.strip()
        if not token_text_stripped:
            # Empty string or spaces only, skip
            continue

        # Convert to lowercase for stopword comparison
        if token_text_stripped.lower() in STOPWORDS:
            continue

        # Check for proper nouns
        if token_pos == "PROPN":
            corrected_tokens.append(token_text_stripped)
            continue

        # For regular words, apply spell correction
        suggestions = sym_spell.lookup(token_text_stripped.lower(), Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            corrected_tokens.append(suggestions[0].term)
        else:
            corrected_tokens.append(token_text_stripped)

    # Parse OR / NOT / regular words
    subexps = []
    i = 0
    while i < len(corrected_tokens):
        token = corrected_tokens[i]

        # Use lowercase to check if it's OR/NOT
        token_lower = token.lower()

        if token_lower == "or":
            if subexps and i + 1 < len(corrected_tokens):
                left_expr = subexps.pop()
                right_expr = f"({corrected_tokens[i + 1]})"
                merged = f"({left_expr} OR {right_expr})"
                subexps.append(merged)
                i += 2
                continue
        elif token_lower == "not":
            if subexps and i + 1 < len(corrected_tokens):
                left_expr = subexps.pop()
                right_expr = f"({corrected_tokens[i + 1]})"
                merged = f"{left_expr} AND NOT {right_expr}"
                subexps.append(merged)
                i += 2
                continue

        # Regular token
        subexps.append(f"({token})")
        i += 1

    return " AND ".join(subexps)


def build_query(q: str) -> str:

    return parse_boolean_query(q)
    '''
    cat = classify_query_with_model(q)
    if cat == "boolean":
        return parse_boolean_query(q)
    else:
        return parse_phrase_query(q)
    '''


def parse_phrase_query(q: str) -> str:
    """
    Finally join into a phrase expression.
    """
    tokens_pos = spacy_preprocess(q)

    corrected_tokens = []
    for token_text, token_pos in tokens_pos:
        token_text_stripped = token_text.strip()
        if not token_text_stripped:
            continue
        if token_text_stripped.lower() in STOPWORDS:
            continue
        if token_pos == "PROPN":
            corrected_tokens.append(token_text_stripped)
            continue

        suggestions = sym_spell.lookup(token_text_stripped.lower(), Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            corrected_tokens.append(suggestions[0].term)
        else:
            corrected_tokens.append(token_text_stripped)

    phrase_str = " ".join(corrected_tokens)
    return f"\"{phrase_str}\""

# for test
if __name__ == "__main__":
    while True:
        user_query = input("Query: ")
        if user_query.lower() == 'exit':
            break

        final_expr = build_query(user_query)
        print(final_expr)
