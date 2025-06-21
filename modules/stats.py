import nltk
import spacy
from collections import Counter
import textstat
import pymorphy2
from natasha import (
    Segmenter,
    NewsNERTagger,
    Doc,
    NewsEmbedding,
    MorphVocab
)

# Загружаем spaCy для лемматизации
nlp = spacy.load("ru_core_news_sm")

# Инициализация объектов Natasha и pymorphy2
segmenter = Segmenter()
morph_vocab = MorphVocab()
ner_tagger = NewsNERTagger(NewsEmbedding())
morph = pymorphy2.MorphAnalyzer()

# Загружаем стоп-слова для nltk


# Лемматизация сущности с использованием pymorphy2
def normalize_with_morph(text):
    """
    Лемматизация сущности с использованием pymorphy2.
    """
    words = text.split()
    lemmas = [morph.parse(word)[0].normal_form for word in words]
    return " ".join(lemmas)


def extract_named_entities_natasha(text, selected_ner_labels, min_length=3):
    """
    Извлекает именованные сущности с учетом выбранных параметров.
    Нормализуем извлечённые сущности перед возвращением.
    """
    # Получаем текст и выполняем сегментацию и NER
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(ner_tagger)

    entity_counter = {}

    # Фильтруем и добавляем сущности
    for span in doc.spans:
        span.normalize(morph_vocab)  # Нормализуем сущность

        # Получаем тип сущности (например, PER, LOC, ORG)
        label = span.type

        # Пропускаем, если эта сущность не в списке выбранных
        if label not in selected_ner_labels:
            continue

        # Лемматизация сущности для нормализации (например, "Москва", "Москве", "Москву" -> "Москва")
        lemma = span.normal.strip().lower()
        lemma = normalize_with_morph(lemma)  # Нормализуем сущность

        # Пропуск коротких сущностей или тех, которые не являются персонажами
        if len(lemma) < min_length or lemma in ['луна', 'нет', 'гестас', 'пила']:  # Исключаем эти слова
            continue

        if label not in entity_counter:
            entity_counter[label] = {}

        # Добавляем нормализованную сущность и её частоту
        entity_counter[label][lemma] = entity_counter[label].get(lemma, 0) + 1

    return entity_counter  # Возвращаем сущности в формате { "PER": {"пьер": 5, ...} }

def get_word_frequencies(text, allowed_pos=None, min_word_len=3):
    """
    Получаем частотный анализ слов по фильтрам частей речи.
    """
    if allowed_pos is None:
        allowed_pos = {"NOUN", "VERB", "ADJ"}

    # Используем spacy для лемматизации слов и фильтрации
    doc = nlp(text)
    tokens = [
        token.lemma_.lower()
        for token in doc
        if token.pos_ in allowed_pos
           and not token.is_stop
           and token.is_alpha
           and len(token.text) >= min_word_len
    ]
    return Counter(tokens)


def basic_stats(text):
    """
    Основная статистика по тексту книги.
    """
    words = nltk.word_tokenize(text)
    sentences = nltk.sent_tokenize(text)
    word_count = len(words)
    sentence_count = len(sentences)
    vocab = set(words)
    avg_word_len = sum(len(w) for w in words) / word_count if word_count > 0 else 0
    reading_level = textstat.flesch_reading_ease(text)
    freq = Counter(words)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "unique_words": len(vocab),
        "avg_word_len": round(avg_word_len, 2),
        "reading_level": reading_level,
        "top_words": freq.most_common(10)
    }
