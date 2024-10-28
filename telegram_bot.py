import numpy as np
import json
import random
import re
import os
import pymorphy2
from preprocessing.parse_jsons import replace_incorrect_spellings
from config import config

from functools import partial
from sentence_transformers import SentenceTransformer, util
from telegram import Update
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler




def extract_corpus_texts(json_path):

    with open(fr"{json_path}", "r") as read_file:
        texts = json.load(read_file)
        
    qa_sentences = set()
    paragraphs = texts["data"][0]["paragraphs"]
    
    for context in paragraphs:
        qas = context["qas"]
        for qa in qas:
            qa_sentences.add(qa["question"] + " " + qa["answers"][0]["text"])
    
    return list(qa_sentences)


def capitalize_first_letter(text):
    if type(text) != list:
        return re.sub(r'^\s*([a-zA-Z])', lambda match: match.group(1).upper(), text)
    else:
        print(*text)
        return [re.sub(r'^\s*([a-zA-Z])', lambda match: match.group(1).upper(), x) for x in text]


def write_feedback_to_json(user_question, bot_answer, user_reaction):
    
    context = user_question + " " + bot_answer
    context_block = {
        "context": context,
        "label": user_reaction,
        "id": random.randint(1, 20000),
        "qas": [
            {
                "id": random.randint(1, 20000),
                "question": user_question,
                "answers": [
                    {
                        "answer_start": random.randint(1, 20000),
                        "text": bot_answer
                    }
                ]
            }
        ]
    }
    
    with open("feedback.json", "a", encoding="utf-8") as file:
        json.dump(context_block, file, ensure_ascii=False, indent=4)
        file.write('\n')


    
def start(update: Update, context: CallbackContext) -> None:
    welcome_text = (
        "Привет! Я чат-бот, созданный для ответа на технические вопросы сервисов МИЭМ."
        "Вы можете задать мне вопросы по следующим темам:\n"
        "Wekan\n"
        "Gitlab\n"
        "Cabinet\n"
        "Jitsi\n"
        "Wiki\n"
        "Taiga\n"
        "Проектная деятельность\n\n"
        "Пожалуйста, выберите тему, чтобы продолжить."
    )
    keyboard = [
        [InlineKeyboardButton("Wekan", callback_data='Wekan')],
        [InlineKeyboardButton("Gitlab", callback_data='Gitlab')],
        [InlineKeyboardButton("Cabinet", callback_data='Cabinet')],
        [InlineKeyboardButton("Jitsi", callback_data='Jitsi')],
        [InlineKeyboardButton("Wiki", callback_data='Wiki')],
        [InlineKeyboardButton("Taiga", callback_data='Taiga')],
        [InlineKeyboardButton("Проектная деятельность", callback_data='Проектная деятельность')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_text, reply_markup=reply_markup)

  
  
def get_topic(update: Update, context: CallbackContext):
    chosen_topic = update.message.text.split("/")[1]
    
    context.user_data['last_topic'] = chosen_topic.lower()  
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Пожалуйста, задайте свой вопрос по теме {chosen_topic}."
    )
    context.user_data['command_flag'] =  True


def find_relevant_context_cosine(update: Update, context: CallbackContext, sentence_transformer, question, sentences, top=1):
    
    threshold = 0.6
    embeddings = []
    embebbidng_question = []
    
    embeddings = sentence_transformer.encode(sentences)
    embebbidng_question = sentence_transformer.encode(question)

    cos_sim = util.cos_sim(embebbidng_question, embeddings)
    
    polite_ans = "Пока что я только учусь, поэтому не могу ответить на Ваш вопрос. Пожалуйста, обратитесь в каналы технической поддержки в zulip."
    if top == 1:
        ind_max = cos_sim.argmax()
        el_max = cos_sim.max()
        if el_max < threshold:
            return polite_ans
        else:
            return sentences[ind_max].split("? ")[1]
    else:
        # find top-n embedding
        index_top_n = np.argsort(cos_sim.numpy())[0][::-1][:top]
        return [sentences[index] for index in index_top_n]        
    
# Обработчик выбора темы
def topic_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    selected_topic = query.data
    context.user_data['selected_topic'] = selected_topic
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Вы выбрали тему: {selected_topic.lower()}. Пожалуйста, задайте Ваш вопрос."
    )
    

def like(update: Update, context: CallbackContext, corrections, morph) -> None:
    query = update.callback_query
    query.answer()
    last_message = context.user_data.get('last_message')
    if last_message:
        bot_answer = last_message.get('bot_answer')
        user_question = last_message.get('user_question')
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Спасибо за положительную оценку!"
        )
        replaced_question = replace_incorrect_spellings(user_question, corrections, morph)
        write_feedback_to_json(replaced_question, bot_answer, "like")
    else:
        query.edit_message_text('Невозможно получить текст сообщений, на которые вы отреагировали.', reply_markup=query.message.reply_markup)


def dislike(update: Update, context: CallbackContext, corrections, morph) -> None:
    query = update.callback_query
    query.answer()
    
    last_message = context.user_data.get('last_message')
    if last_message:
        bot_answer = last_message.get('bot_answer')
        user_question = last_message.get('user_question')
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Спасибо за оценку, теперь я стану ещё умнее!"
        )
        replaced_question = replace_incorrect_spellings(user_question, corrections, morph)
        write_feedback_to_json(replaced_question, bot_answer, "dislike")
    else:
        query.edit_message_text('Невозможно получить текст сообщений, на которые вы отреагировали.', reply_markup=query.message.reply_markup)


# Обработчик кнопок
def button_handler(update: Update, context: CallbackContext, corrections, morph) -> None:
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'like':
        like(update, context, corrections, morph)
    elif data == 'dislike':
        dislike(update, context, corrections, morph)
    else:
        topic_handler(update, context)


def echo(update: Update, context: CallbackContext, model, corrections, morph) -> None:

    user_question = update.message.text
    replaced_question = replace_incorrect_spellings(user_question, corrections, morph)

    if 'command_flag' not in list(context.user_data.keys()):
        chosen_topic = context.user_data.get('selected_topic').lower()  
    elif 'command_flag' in list(context.user_data.keys()) and 'last_topic' in list(context.user_data.keys()):
        chosen_topic = context.user_data.get('last_topic').lower()
        

    path = os.getcwd()
    sentences = extract_corpus_texts(f"{path}/data/handmade_dataset/format of deeppavlov/full/{chosen_topic}.json")

    if chosen_topic:
        bot_answer = find_relevant_context_cosine(update, context, model, replaced_question, sentences)
        bot_answer = capitalize_first_letter(bot_answer)
        update.message.reply_text(bot_answer, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👍", callback_data='like')],
            [InlineKeyboardButton("👎", callback_data='dislike')]
        ]))

        # Сохранение последнего сообщения и ответа в контексте пользователя
        context.user_data['last_message'] = {'user_question': replaced_question, 'bot_answer': bot_answer}
    else:
        update.message.reply_text("Пожалуйста, сначала выберите тему.")
    

    
    
def main() -> None:
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    morph = pymorphy2.MorphAnalyzer()
    
    path = os.getcwd()
    with open(f"{path}/preprocessing/dictionary.json", 'r') as file:
        corrections = json.load(file)
        
    
    updater = Updater(config.TELEGRAM_KEY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("wekan", get_topic)) 
    dispatcher.add_handler(CommandHandler("gitlab", get_topic))
    dispatcher.add_handler(CommandHandler("cabinet", get_topic))
    dispatcher.add_handler(CommandHandler("jitsi", get_topic))
    dispatcher.add_handler(CommandHandler("wiki", get_topic))
    dispatcher.add_handler(CommandHandler("taiga", get_topic))
    dispatcher.add_handler(CommandHandler("project", get_topic))
    
    dispatcher.add_handler(CommandHandler("like", partial(like,  corrections=corrections, morph=morph)))
    dispatcher.add_handler(CommandHandler("dislike", partial(dislike, corrections=corrections, morph=morph)))
    dispatcher.add_handler(CallbackQueryHandler(partial(button_handler, corrections=corrections, morph=morph)))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, partial(echo, model=model, corrections=corrections, morph=morph)))


    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
