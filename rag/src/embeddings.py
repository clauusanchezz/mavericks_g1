from sentence_transformers import SentenceTransformer

CONFIG_MODEL_NAME = "intfloat/multilingual-e5-small"
CONFIG_QUERY_PREFIX = "query: "
CONFIG_PASSAGE_PREFIX = "passage: "

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(CONFIG_MODEL_NAME)
    return _model


def embed_passages(texts):
    prefixed = []
    for text in texts:
        prefixed.append(CONFIG_PASSAGE_PREFIX + text)
    return _get_model().encode(prefixed, normalize_embeddings=True)


def embed_query(text):
    return _get_model().encode([CONFIG_QUERY_PREFIX + text], normalize_embeddings=True)[0]
