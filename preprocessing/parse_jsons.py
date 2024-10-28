import pandas as pd
import os
import json
import random
import re
import pymorphy2



def replace_incorrect_spellings(text, corrections, morph):
    
    # Создание словаря для обратного поиска
    reverse_corrections = {}
    for correct_spelling, wrong_spellings in corrections.items():
        for wrong_spelling in wrong_spellings:
            reverse_corrections[wrong_spelling.lower()] = correct_spelling
            
    
    # Функция для замены неправильных написаний
    def replace_words(match):
        word = match.group(0).lower()
        # Получаем грамматическую информацию о слове
        parsed_word = morph.parse(word)[0]
        # Определяем его корень
        root_word = parsed_word.normal_form
        # Ищем корень в словаре исправлений
        return reverse_corrections.get(root_word, word)

    # Регулярное выражение для поиска слов в тексте
    word_pattern = re.compile(r'\b\w+\b')

    # Замена слов в тексте
    corrected_text = word_pattern.sub(replace_words, text)
    
    return corrected_text

def load_csv(csv_file_path):
    """ Загружает CSV файл и возвращает DataFrame. """
    return pd.read_csv(csv_file_path)

def convert_to_deep_pavlov_json_format(df, json_file_path):
    """
    Конвертирует DataFrame в JSON файл в формате, подходящем для DeepPavlov.

    Параметры:
    - df: DataFrame с колонками 'question' и 'answer'.
    - json_file_path: Путь для сохранения JSON файла.
    """
    # Создаем структуру данных для JSON
    data = {
        "data": [
            {
                "title": "Custom QA Dataset",
                "paragraphs": []
            }
        ],
        "version": "1.0"
    }

    # Итерация по строкам DataFrame для добавления вопросов и ответов
    for index, row in df.iterrows():
        question = row['question']
        answer = row['answer']
        paragraph = {
            "context": answer,  # Пример, где ответ дублируется в контексте
            "qas": [
                {
                    "id": str(index),
                    "question": question,
                    "answers": [
                        {
                            "text": answer,
                            "answer_start": 0  # Начало ответа в контексте
                        }
                    ]
                }
            ]
        }
        data['data'][0]['paragraphs'].append(paragraph)

    # Сохраняем данные в JSON файл
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def csv_to_json(csv_file_path, json_file_path):
    """ Конвертирует CSV файл в JSON файл в нужном формате. """
    df = load_csv(csv_file_path)
    convert_to_deep_pavlov_json_format(df, json_file_path)


def merge_json_files(input_folder, output_file):
    # Собираем все файлы в папке
    json_files = [f for f in os.listdir(input_folder) if f.endswith('.json')]

    # Создаем пустой список для объединенных данных
    combined_data = []

    # Обходим каждый файл, читаем его и добавляем его данные в объединенный список
    for file_name in json_files:
        with open(os.path.join(input_folder, file_name), 'r') as file:
            data = json.load(file)
            combined_data.extend(data)

    # Записываем объединенные данные в один файл
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(combined_data, outfile, ensure_ascii=False, indent=4)


def split_train_test(input_file, train_ratio=0.8):
    with open(input_file, 'r') as file:
        data = json.load(file)
    
    # Перемешиваем данные
    random.shuffle(data)
    
    # Определяем количество данных для обучения и тестирования
    train_size = int(len(data) * train_ratio)
    
    # Разделяем данные на обучающую и тестовую выборки
    train_data = data[:train_size]
    test_data = data[train_size:]
    
    return train_data, test_data


def change_id_to_random(json_data):
    for context in json_data:
        for qa in context["qas"]:
            qa["id"] = str(random.randint(1, 1000))  # Генерируем случайное значение для поля 'id'



def convert_json_format(old_json_path, json_file_path):
    
    with open(old_json_path, 'r') as file:
        old_json = json.load(file)
        
    new_json = {
        "data": [
            {
                "title": "Custom QA Dataset",
                "paragraphs": []
                }
        ]
    }
    
    for item in old_json:
        qa_list = []
        for qa in item["qas"]:
            new_qa = {
                "id": random.randint(1, 10000),
                "question": qa["question"],
                "answers": qa["answers"]
            }
            
            qa_list.append(new_qa)
        
        new_json["data"][0]["paragraphs"].append({
            "context": item["context"],
            "id": random.randint(1, 10000),
            "qas": qa_list
        })
    
    with open(json_file_path, 'w', encoding='utf-8') as outfile:
        json.dump(new_json, outfile, ensure_ascii=False, indent=4)   
    
    