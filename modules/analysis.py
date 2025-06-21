import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
from modules.stats import basic_stats, get_word_frequencies, extract_named_entities_natasha, normalize_with_morph
import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from collections import Counter


def analyze_book(text, title, author, config):
    """
    Функция для анализа книги с настройками конфигурации.
    """
    # Статистика
    stats = basic_stats(text)

    # Вывод статистики
    st.subheader(f"📊 Статистика для книги: {title} ({author})")
    st.metric("Количество слов", stats["word_count"])
    st.metric("Количество предложений", stats["sentence_count"])
    st.metric("Количество уникальных слов", stats["unique_words"])
    st.write(f"Средняя длина слова: {stats['avg_word_len']} символов")

    if stats["reading_level"] is not None:
        st.write(f"Уровень читаемости (Flesch): {stats['reading_level']:.2f}")

    # Генерация облака слов
    if config.get("wordcloud", {}).get("enabled", False):
        st.subheader("☁️ Облако слов")
        selected_pos = config["wordcloud"]["pos"]
        min_freq = config["wordcloud"]["min_freq"]
        background_color = config["wordcloud"]["background"]
        colormap = config["wordcloud"]["colormap"]

        freqs = get_word_frequencies(text, allowed_pos=selected_pos)
        filtered_freqs = {word: freq for word, freq in freqs.items() if freq >= min_freq}

        if filtered_freqs:
            wordcloud = WordCloud(
                width=600,
                height=300,
                background_color=background_color,
                colormap=colormap
            ).generate_from_frequencies(filtered_freqs)

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)

            # Сохранение PNG изображения
            img_buffer = BytesIO()
            wordcloud.to_image().save(img_buffer, format='PNG')
            st.download_button(
                label="📥 Скачать PNG",
                data=img_buffer.getvalue(),
                file_name="wordcloud.png",
                mime="image/png"
            )
        else:
            st.info("Недостаточно слов для генерации облака. Попробуйте снизить порог частоты.")

    # Анализ Named Entity Recognition (NER)
    if config.get("ner", False):
        st.subheader("🧍‍♂️ Именованные сущности (NER)")

        ner_data = extract_named_entities_natasha(text, config["ner"])

        if ner_data:
            ent_tables = []
            for ent_type, entities in ner_data.items():
                label = ent_type
                sorted_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)[:10]
                df = pd.DataFrame(sorted_entities, columns=["Сущность", "Частота"])
                ent_tables.append((label, df))

            # Показываем в 2–3 колонки
            for i in range(0, len(ent_tables), 3):
                cols = st.columns(min(3, len(ent_tables) - i))
                for j, (label, df) in enumerate(ent_tables[i:i + 3]):
                    with cols[j]:
                        st.markdown(f"**{label}**")
                        st.dataframe(df, use_container_width=True)
        else:
            st.info("Не удалось извлечь сущности из текста.")

    # Проверка, если NER не выбрано
    if not config.get("ner", False):
        st.error("Для построения графа необходимо использовать анализ NER.")
        return  # Прекращаем выполнение функции, если NER не выбрано

    # Построение графа персонажей
    if config.get("graph", False):
        st.subheader("🔗 Граф взаимодействий персонажей")
        context_size = config.get("context_size", 1)  # Получаем размер контекста

        G = create_character_interaction_graph(text, config["ner"], context_size)

        if len(G.nodes) > 0:
            # Визуализируем граф
            visualize_character_interaction_graph(G)
        else:
            st.info("Взаимодействия персонажей не найдены.")


def create_character_interaction_graph(text, selected_ner_labels, context_size=2):
    """
    Строит граф взаимодействий персонажей, локаций и организаций на основе их упоминаний в контексте.
    Взаимодействие считается, если персонажи, локации или организации упоминаются в одном и том же контексте.
    Для каждого типа сущности (PER, LOC, ORG) берём топ-10.
    """
    # Извлекаем сущности с NER

    ner_data = extract_named_entities_natasha(text, selected_ner_labels)
    print(text[:100])
    print(selected_ner_labels)
    # Граф взаимодействий
    interactions = Counter()

    # Разбиваем текст на предложения
    sentences = text.split(".")  # Простой способ разделить на предложения

    # Создаем множество сущностей для всех типов для быстрого поиска
    entities = {}
    for label, entities_list in ner_data.items():
        if label in selected_ner_labels:  # Проверяем, если тип сущности в выбранных
            for entity in entities_list:
                normalized_entity = normalize_with_morph(entity)  # Нормализуем имена с лемматизацией
                entities.setdefault(label, {})[normalized_entity] = entity  # Сохраняем сущности по типам

    # Логируем извлечённые сущности
    # print("Extracted entities:", entities)

    # Обрабатываем текст в контексте заданного размера
    for i in range(len(sentences) - context_size + 1):
        # Составляем контекст из нескольких предложений
        context = " ".join(sentences[i:i + context_size])

        # Логируем контекст
        # print(f"Context {i}: {context}")

        characters_in_context = set()

        # Проверяем, есть ли персонажи, локации или организации в контексте
        for label in entities:
            for entity in entities[label]:
                if entity in context.lower():  # Проверяем, упоминается ли сущность в контексте
                    characters_in_context.add(entities[label][entity])  # Добавляем оригинальное имя сущности

        # Логируем найденных сущностей в контексте
        # if characters_in_context:
        #     print(f"Found entities in context {i}: {characters_in_context}")

        # Если в контексте больше одного персонажа/сущности, добавляем их взаимодействие
        if len(characters_in_context) > 1:
            characters_in_context = list(characters_in_context)
            for idx, char1 in enumerate(characters_in_context):
                for char2 in characters_in_context[idx + 1:]:
                    # Добавляем рёбра для всех сущностей, которые встречаются в контексте
                    interaction = f"{char1} - {char2}"
                    interactions[interaction] += 1

    # Строим граф на основе взаимодействий
    G = nx.Graph()

    # Для каждого типа сущности (PER, LOC, ORG) берём топ-10
    for label in entities:
        # Отбираем топ-10 для каждого типа сущности
        top_entities = sorted(entities[label].keys(), key=lambda x: interactions[f"{x} - {x}"], reverse=True)[:10]
        filtered_interactions = {k: v for k, v in interactions.items() if any(entity in k for entity in top_entities)}

        # Добавляем ребра в граф для каждого типа сущности
        for interaction, count in filtered_interactions.items():
            char1, char2 = interaction.split(" - ")
            G.add_edge(char1, char2, weight=count)

    # Логируем граф
    # print(f"Generated graph: {G.edges(data=True)}")

    return G

def visualize_character_interaction_graph(G):
    """
    Визуализирует граф взаимодействий персонажей.
    Увеличивает расстояние между узлами для лучшей читаемости.
    """
    plt.figure(figsize=(12, 10))

    # Раскладка узлов с измененным параметром k для оптимального расстояния
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)  # Умеренное значение k

    # Рисуем граф
    nx.draw_networkx_nodes(G, pos, node_size=3000, node_color='skyblue', alpha=0.7)
    nx.draw_networkx_edges(G, pos, width=2, alpha=0.5, edge_color='gray')
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', font_color='black')

    # Настроим отображение
    plt.axis('off')
    plt.title("Граф взаимодействий персонажей")
    plt.show()

# import networkx as nx
# import plotly.graph_objects as go
#
# def visualize_character_interaction_graph(G):
#     """
#     Визуализирует граф взаимодействий персонажей с использованием Plotly для интерактивности.
#     """
#     # Получаем позиции узлов с помощью layout из NetworkX
#     pos = nx.spring_layout(G, seed=42)
#
#     # Извлекаем координаты узлов
#     x_nodes = [pos[node][0] for node in G.nodes()]
#     y_nodes = [pos[node][1] for node in G.nodes()]
#
#     # Извлекаем рёбра для отображения
#     edges = G.edges()
#     x_edges = []
#     y_edges = []
#     for edge in edges:
#         x_edges.append(pos[edge[0]][0])
#         x_edges.append(pos[edge[1]][0])
#         y_edges.append(pos[edge[0]][1])
#         y_edges.append(pos[edge[1]][1])
#
#     # Создаем фигуру Plotly для рёбер
#     edge_trace = go.Scatter(
#         x=x_edges,
#         y=y_edges,
#         line=dict(width=1, color='gray'),
#         hoverinfo='none',
#         mode='lines'
#     )
#
#     # Создаем фигуру Plotly для узлов
#     node_trace = go.Scatter(
#         x=x_nodes,
#         y=y_nodes,
#         mode='markers',
#         hoverinfo='text',
#         marker=dict(
#             showscale=True,
#             colorscale='Blues',
#             size=10,
#             color=list(range(len(G.nodes()))),  # Используем list(range()) для цветов
#             colorbar=dict(thickness=15, title='Node Connections')
#         )
#     )
#
#     # Добавляем информацию о каждом узле
#     node_text = []
#     for node in G.nodes():
#         node_text.append(f'Node: {node}')
#     node_trace.text = node_text
#
#     # Создаем фигуру для визуализации
#     fig = go.Figure(data=[edge_trace, node_trace],
#                     layout=go.Layout(
#                         title="Граф взаимодействий персонажей",
#                         title_font=dict(size=16),  # Исправляем на правильный параметр
#                         showlegend=False,
#                         hovermode='closest',
#                         xaxis=dict(showgrid=False, zeroline=False),
#                         yaxis=dict(showgrid=False, zeroline=False)
#                     ))
#
#     fig.show()