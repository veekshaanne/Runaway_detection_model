
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticDetector:
    def __init__(self, similarity_threshold=0.8):
        self.similarity_threshold = similarity_threshold
        self.history = []

    def _text(self, value):
        if isinstance(value, dict):
            return " ".join(self._text(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return " ".join(self._text(v) for v in value)
        return str(value)

    def check(self, action):
        action_type = action.get("action_type", "")
        target = action.get("target", "")
        arguments = self._text(action.get("arguments", {})).strip()

        best_similarity = 0.0

        for old_type, old_target, old_text in self.history:
            if old_type != action_type or old_target != target:
                continue

            if old_text == arguments:
                continue

            try:
                vectorizer = TfidfVectorizer(
                    stop_words="english",
                    ngram_range=(1, 2),
                )
                vectors = vectorizer.fit_transform(
                    [old_text, arguments]
                )
                similarity = cosine_similarity(
                    vectors[0:1], vectors[1:2]
                )[0][0]

                best_similarity = max(
                    best_similarity, float(similarity)
                )
            except ValueError:
                continue

        self.history.append((action_type, target, arguments))

        suspicious = best_similarity >= self.similarity_threshold

        return {
            "suspicious": suspicious,
            "similarity": round(best_similarity, 3),
            "risk_score": 0.65 if suspicious else 0.0,
        }
