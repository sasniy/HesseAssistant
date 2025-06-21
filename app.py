import os
import streamlit as st
from modules.analysis import analyze_book
from modules.parser import extract_text

os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

st.set_page_config(page_title="📘 Book Insight", layout="wide")

st.title("📘 BookInsight: Анализ текста книги")

uploaded_file = st.file_uploader("Загрузите файл (.txt / .pdf / .epub)", type=["txt", "pdf", "epub"])

if uploaded_file:
    # Показываем спиннер при загрузке
    with st.spinner("Загружаем книгу..."):
        text, title, author = extract_text(uploaded_file, uploaded_file.name)
        st.session_state.text = text
        st.session_state.title = title
        st.session_state.author = author

    st.success("Файл успешно загружен ✅")

    # Показываем название и автора
    st.header(f"📖 Название: {title}")
    st.subheader(f"Автор: {author}")

    # Этап настроек анализа
    st.header("⚙️ Настройки анализа")

    use_wordcloud = st.checkbox("Включить облако слов", value=False)
    use_ner = st.checkbox("Использовать Named Entity Recognition (NER)", value=True)
    use_graph = st.checkbox("Построить граф взаимодействий персонажей", value=False)

    # Параметр для настройки размера контекста
    context_size = st.slider("Размер контекста (количество предложений)", 1, 5, 1)

    config = {}

    # Настройки для облака слов
    if use_wordcloud:
        with st.expander("🔠 Настройки облака слов", expanded=True):
            pos_options = {
                "Существительные": "NOUN",
                "Глаголы": "VERB",
                "Прилагательные": "ADJ",
                "Наречия": "ADV",
            }
            selected_labels = st.multiselect(
                "Выберите части речи для облака:",
                options=list(pos_options.keys()),
                default=["Существительные", "Прилагательные"]
            )
            selected_pos = {pos_options[label] for label in selected_labels}
            min_freq = st.slider("Минимальная частота появления слова", 1, 20, 3)
            background_color = st.color_picker("Цвет фона", "#ffffff")
            colormap = st.selectbox("Цветовая палитра", ["viridis", "plasma", "inferno", "cividis", "Dark2", "Set3", "tab10"], index=0)

            config["wordcloud"] = {
                "enabled": True,
                "pos": selected_pos,
                "min_freq": min_freq,
                "background": background_color,
                "colormap": colormap
            }
    else:
        config["wordcloud"] = {"enabled": False}

    # Настройки для NER
    if use_ner:
        with st.expander("🧍‍♂️ Настройки NER", expanded=True):
            ner_labels = {
                "Персонажи (PER)": "PER",
                "Локации (LOC)": "LOC",
                "Организации (ORG)": "ORG"
            }

            selected_ner_labels = st.multiselect(
                "Выберите сущности для извлечения:",
                options=list(ner_labels.keys()),
                default=["Персонажи (PER)", "Локации (LOC)", "Организации (ORG)"]
            )

            selected_ner = {ner_labels[label] for label in selected_ner_labels}
            config["ner"] = selected_ner

    config["graph"] = use_graph
    config["context_size"] = context_size  # Добавляем параметр для контекста

    # Кнопка запуска анализа
    if st.button("🔍 Анализировать книгу"):
        analyze_book(
            text=st.session_state.text,
            title=st.session_state.title,
            author=st.session_state.author,
            config=config
        )
