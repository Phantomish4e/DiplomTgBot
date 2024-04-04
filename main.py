import asyncio
import json
import logging
import math
import time
import datetime
import pytz
import requests

from aiogram import Bot, Dispatcher, types, F
from asyncio.exceptions import CancelledError

from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from DB.db_conn import create_db, add_users_in_db, see_all_users, add_street_to_incident, add_incidient, get_user_by_id, \
    delete_dispatcher, add_description_to_incidient, check_for_updates
from config import settings

dp = Dispatcher()
bot = Bot(token=settings.bot_token)
YANDEX_API_KEY = settings.yandex_api_key
utc_timezone = pytz.timezone("UTC")
chat_id = []
TypeInc = None
description = None
dispatchers_list = []


@dp.message(CommandStart())
async def handle_start(msg: types.Message):
    await msg.bot.send_chat_action(
        chat_id=msg.chat.id,
        action=ChatAction.TYPING,
    )
    add_users_in_db(msg.from_user.id, msg.from_user.username, msg.from_user.is_bot)
    await msg.answer(
        text=f'Здравстуйте, {msg.from_user.first_name}, что у вас произошло?',
    )


@dp.message(Command("help"))
async def handle_short_numbers(msg: types.Message):
    await msg.answer(
        text="101 - Пожарная\n"
             "102 - Милиция\n"
             "103 - Скорая\n"
             "104 - Газовая\n",
    )


@dp.message(Command("find"))
async def handle_command_find(msg: types.Message):
    call_fire_dep_btn = InlineKeyboardButton(
        text="Пожарная",
        callback_data="fire department",
    )
    call_police_btn = InlineKeyboardButton(
        text="Милиция",
        callback_data="police station",
    )
    call_emergency_btn = InlineKeyboardButton(
        text="Скорая помощь",
        callback_data="hospital",
    )
    call_gas_btn = InlineKeyboardButton(
        text="Газовая",
        callback_data="gas service",
    )
    rows = [
        [call_fire_dep_btn],
        [call_police_btn],
        [call_emergency_btn],
        [call_gas_btn],
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await msg.answer(
        text=f"Кого хотите вызвать?",
        reply_markup=markup,
    )


@dp.message(Command("location"))
async def handle_command_location(msg: types.Message):
    button = KeyboardButton(
        text="Отправить геолокацию",
        request_location=True,
    )
    buttons = [button]
    markup = ReplyKeyboardMarkup(
        keyboard=[buttons],
    )
    await msg.answer(
        text="Нажмите кнопку",
        reply_markup=markup,
    )


@dp.message(Command("call"))
async def handle_command_call(msg: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Пожар",
        callback_data="fire"
    )
    builder.button(
        text="Авария",
        callback_data="car crash"
    )
    builder.button(
        text="Пострадал человек",
        callback_data="emergency"
    )
    builder.button(
        text="Утечка газа",
        callback_data="gas"
    )
    builder.adjust(1)
    await msg.bot.send_message(
        chat_id=msg.chat.id,
        text="Что у вас произшло?",
        reply_markup=builder.as_markup()
    )


@dp.message(Command("chatId"), F.from_user.id.in_({42, 1012387760}))
async def save_chat_id(msg: types.Message):
    chat_id = msg.chat.id
    f = open('chat_id.txt', 'r+')
    f.write(str(chat_id))
    f.close()


@dp.message(Command("users"), F.from_user.id.in_({42, 1012387760}))
async def see_all_chat_users(msg: types.Message):
    button_add = InlineKeyboardButton(
        text='Установить как диспетчера',
        callback_data='setDispatcher',
    )
    button_delete = InlineKeyboardButton(
        text='Удалить диспетчера',
        callback_data='deleteDispatcher',
    )
    row_first = [button_add]
    row_second = [button_delete]
    rows = [row_first, row_second]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await msg.answer(
        text=f"Пользователи чата:",
    )
    for line in see_all_users():
        await msg.answer(
            text=f"{line}",
            reply_markup=markup,
        )


@dp.message(F.location)
async def handle_location(msg: types.Message):
    await msg.bot.send_chat_action(
        chat_id=msg.chat.id,
        action=ChatAction.FIND_LOCATION
    )
    global longitude, latitude
    longitude = msg.location.longitude
    latitude = msg.location.latitude
    await msg.answer(
        text=f"Ваша позиция: {latitude},{longitude}",
    )
    return longitude, latitude


@dp.callback_query(F.data == "edit_message")
async def edit_message(call: CallbackQuery):
    await call.bot.send_message(
        chat_id=call.message.chat.id,
        text="Хорошо, укажите где это произошло"
    )


@dp.callback_query(F.data == "add_street")
async def add_street(call: CallbackQuery):
    global TypeInc
    try:
        senders_location = f"Широта: {latitude}, Долгота: {longitude}"
    except (AttributeError, NameError):
        senders_location = "Местоположение не определено"

    place = call.message.text
    performed_date = time.time()
    if TypeInc is not None:
        if description is not None:
            add_street_to_incident(Type=TypeInc, sender_name=call.from_user.first_name,
                                   sender_id=call.from_user.id, sender_location=senders_location,
                                   Date=datetime.datetime.fromtimestamp(performed_date),
                                   place=place, description=description)
            await call.bot.send_message(
                chat_id=call.message.chat.id,
                text="Спасибо за сообщение, ожидайте...",
            )
            await call.message.delete_reply_markup()
        else:
            await call.bot.send_message(
                chat_id=call.message.chat.id,
                text="Пожалуйста опишите что у вас произошло"
            )
    else:
        await call.bot.send_message(
            chat_id=call.message.chat.id,
            text="Пожалуйста нажмите /call"
        )
        return


@dp.callback_query(F.data == "fire")
async def handle_cb_call_fire(call: CallbackQuery):
    global TypeInc
    global longitude, latitude
    TypeInc = "Пожар"
    sender_id = call.from_user.id
    sender_name = call.from_user.first_name
    performed_date = time.time()
    try:
        senders_location = f"Широта: {latitude}, Долгота: {longitude}"
    except (AttributeError, NameError):
        senders_location = "Местоположение не определено"
    await call.bot.send_message(
        chat_id=call.message.chat.id,
        text="Опишитие что произошло",
        reply_to_message_id=call.message.message_id
    )
    try:
        add_incidient(TypeInc, sender_id, sender_name, senders_location,
                      datetime.datetime.fromtimestamp(performed_date))
    except Exception:
        await call.answer(
            text="Что-то пошло не так, попробуйте заново"
        )


@dp.callback_query(F.data == "car crash")
async def handle_cb_call_car_crash(call: CallbackQuery):
    global TypeInc
    global latitude, longitude
    TypeInc = "Авария"
    sender_id = call.from_user.id
    sender_name = call.from_user.first_name
    performed_date = time.time()
    try:
        senders_location = f"Широта: {latitude}, Долгота: {longitude}"
    except (AttributeError, NameError):
        senders_location = "Местоположение не определено"
    await call.bot.send_message(
        chat_id=call.message.chat.id,
        text="Опишитие что произошло",
        reply_to_message_id=call.message.message_id
    )
    try:
        add_incidient(TypeInc, sender_id, sender_name, senders_location,
                      datetime.datetime.fromtimestamp(performed_date))
    except Exception:
        await call.answer(
            text="Что-то пошло не так, попробуйте заново"
        )


@dp.callback_query(F.data == "emergency")
async def handle_cb_call_emergency(call: CallbackQuery):
    global TypeInc
    global latitude, longitude
    TypeInc = "Пострадал человек"
    sender_id = call.from_user.id
    sender_name = call.from_user.first_name
    performed_date = time.time()
    try:
        senders_location = f"Широта: {latitude}, Долгота: {longitude}"
    except (AttributeError, NameError):
        senders_location = "Местоположение не определено"
    await call.bot.send_message(
        chat_id=call.message.chat.id,
        text="Опишитие что произошло",
        reply_to_message_id=call.message.message_id
    )
    try:
        add_incidient(TypeInc, sender_id, sender_name, senders_location,
                      datetime.datetime.fromtimestamp(performed_date))
    except Exception:
        await call.answer(
            text="Что-то пошло не так, попробуйте заново"
        )
    return TypeInc


@dp.callback_query(F.data == "gas")
async def handle_cb_call_gas(call: CallbackQuery):
    global TypeInc
    global latitude, longitude
    TypeInc = "Утечка газа"
    sender_id = call.from_user.id
    sender_name = call.from_user.first_name
    performed_date = time.time()
    try:
        senders_location = f"Широта: {latitude}, Долгота: {longitude}"
    except (AttributeError, NameError):
        senders_location = "Местоположение не определено"
    await call.bot.send_message(
        chat_id=call.message.chat.id,
        text="Опишитие что произошло",
        reply_to_message_id=call.message.message_id
    )
    try:
        add_incidient(TypeInc, sender_id, sender_name, senders_location,
                      datetime.datetime.fromtimestamp(performed_date))
    except Exception:
        await call.answer(
            text="Что-то пошло не так, попробуйте заново"
        )


@dp.callback_query(F.data == 'setDispatcher')
async def cb_set_dispatcher(call: CallbackQuery):
    global dispatchers_list
    str = call.message.text
    symbols_to_remove = "(') "
    for symbol in symbols_to_remove:
        str = str.replace(symbol, "")
    list = str.split(",")
    dispatchers_list.append(int(list[1]))
    get_user_by_id(list[0])
    await call.answer(
        text="Пользователь назначен диспетчером!",
    )


@dp.callback_query(F.data == 'deleteDispatcher')
async def cb_delete_dispatcher(call: CallbackQuery):
    global dispatchers_list
    str = call.message.text
    symbols_to_remove = "(') "
    for symbol in symbols_to_remove:
        str = str.replace(symbol, "")
    list = str.split(",")
    delete_dispatcher(list[0])
    await call.answer(
        text="Диспетчер удален!"
    )


@dp.callback_query(F.data == "fire department")
async def handle_cb_fire_btn(call: CallbackQuery):
    global longitude, latitude
    try:
        if latitude is not None and longitude is not None:
            await call.bot.send_chat_action(
                chat_id=call.message.chat.id,
                action=ChatAction.FIND_LOCATION,
            )
            url = (f"https://search-maps.yandex.ru/v1/?text=fire_department&ll={longitude},{latitude}&type=biz&results"
                   f"=3&lang=ru_RU&apikey={settings.yandex_api_key}")
            response = requests.get(url=url)
            if response.status_code == 200:
                data = json.loads(response.text)
                if "features" in data:
                    for feature in data["features"]:
                        geometry = feature["geometry"]
                        coord = geometry.get("coordinates", "Координаты не найдены")
                        r = 6371
                        lat1 = math.radians(latitude)
                        lon1 = math.radians(longitude)
                        lat2 = math.radians(coord[1])
                        lon2 = math.radians(coord[0])

                        dlat = lat2 - lat1
                        dlon = lon2 - lon1

                        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

                        dist = r * c

                        if "properties" in feature and "CompanyMetaData" in feature["properties"]:
                            company_metadata = feature["properties"]["CompanyMetaData"]
                            name = company_metadata.get("name", "Название не найдено")
                            address = company_metadata.get("address", "Адрес не найден")
                            phones = [phone["formatted"] for phone in company_metadata.get("Phones", [])]

                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Название: {name}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Адрес: {address}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Телефоны: {', '.join(phones)}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Расстояние до места: {round(dist, 2)} км"
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text="-----------------------------"
                            )
                            await asyncio.sleep(1)
                        else:
                            print("Не удалось найти информацию о компании")
                else:
                    print("Отсутствуют объекты (features) в JSON-ответе")
            else:
                print("Ошибка в запросе: ", response.status_code)
        else:
            await call.answer(
                text="Отправьте пожалуйста вашу позицию",
            )
    except NameError:
        await call.answer(
            text="Отправьте пожалуйста вашу позицию",
        )


@dp.callback_query(F.data == "police station")
async def handle_cb_police_btn(call: CallbackQuery):
    global longitude, latitude
    try:
        if latitude is not None and longitude is not None:
            await call.bot.send_chat_action(
                chat_id=call.message.chat.id,
                action=ChatAction.FIND_LOCATION,
            )
            url = f"https://search-maps.yandex.ru/v1/?text=police_station&ll={longitude},{latitude}&type=biz&results=3&lang=ru_RU&apikey={settings.yandex_api_key}"
            response = requests.get(url=url)
            if response.status_code == 200:
                data = json.loads(response.text)
                if "features" in data:
                    for feature in data["features"]:
                        geometry = feature["geometry"]
                        coord = geometry.get("coordinates", "Координаты не найдены")
                        r = 6371
                        lat1 = math.radians(latitude)
                        lon1 = math.radians(longitude)
                        lat2 = math.radians(coord[1])
                        lon2 = math.radians(coord[0])

                        dlat = lat2 - lat1
                        dlon = lon2 - lon1

                        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

                        dist = r * c

                        if "properties" in feature and "CompanyMetaData" in feature["properties"]:
                            company_metadata = feature["properties"]["CompanyMetaData"]
                            name = company_metadata.get("name", "Название не найдено")
                            address = company_metadata.get("address", "Адрес не найден")
                            phones = [phone["formatted"] for phone in company_metadata.get("Phones", [])]

                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Название: {name}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Адрес: {address}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Телефоны: {', '.join(phones)}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Расстояние до места: {round(dist, 2)} км"
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text="-----------------------------"
                            )
                            await asyncio.sleep(1)
                        else:
                            print("Не удалось найти информацию о компании")
                else:
                    print("Отсутствуют объекты (features) в JSON-ответе")
            else:
                print("Ошибка в запросе: ", response.status_code)
        else:
            await call.answer(
                text="Отправьте пожалуйста вашу позицию",
            )
    except NameError:
        await call.answer(
            text="Отправьте пожалуйста вашу позицию",
        )


@dp.callback_query(F.data == "hospital")
async def handle_cb_emergency_btn(call: CallbackQuery):
    global longitude, latitude
    try:
        if latitude is not None and longitude is not None:
            await call.bot.send_chat_action(
                chat_id=call.message.chat.id,
                action=ChatAction.FIND_LOCATION,
            )
            url = f"https://search-maps.yandex.ru/v1/?text=hospital&ll={longitude},{latitude}&type=biz&results=3&lang=ru_RU&apikey={settings.yandex_api_key}"
            response = requests.get(url=url)
            if response.status_code == 200:
                data = json.loads(response.text)
                if "features" in data:
                    for feature in data["features"]:
                        geometry = feature["geometry"]
                        coord = geometry.get("coordinates", "Координаты не найдены")
                        r = 6371
                        lat1 = math.radians(latitude)
                        lon1 = math.radians(longitude)
                        lat2 = math.radians(coord[1])
                        lon2 = math.radians(coord[0])

                        dlat = lat2 - lat1
                        dlon = lon2 - lon1

                        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

                        dist = r * c

                        if "properties" in feature and "CompanyMetaData" in feature["properties"]:
                            company_metadata = feature["properties"]["CompanyMetaData"]
                            name = company_metadata.get("name", "Название не найдено")
                            address = company_metadata.get("address", "Адрес не найден")
                            phones = [phone["formatted"] for phone in company_metadata.get("Phones", [])]

                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Название: {name}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Адрес: {address}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Телефоны: {', '.join(phones)}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Расстояние до места: {round(dist, 2)} км"
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text="-----------------------------"
                            )
                            await asyncio.sleep(1)
                        else:
                            print("Не удалось найти информацию о компании")
                else:
                    print("Отсутствуют объекты (features) в JSON-ответе")
            else:
                print("Ошибка в запросе: ", response.status_code)
        else:
            await call.answer(
                text="Отправьте пожалуйста вашу позицию",
            )
    except NameError:
        await call.answer(
            text="Отправьте пожалуйста вашу позицию",
        )


@dp.callback_query(F.data == "gas service")
async def handle_cb_gas_btn(call: CallbackQuery):
    global longitude, latitude
    try:
        if latitude is not None and longitude is not None:
            await call.bot.send_chat_action(
                chat_id=call.message.chat.id,
                action=ChatAction.FIND_LOCATION,
            )
            url = f"https://search-maps.yandex.ru/v1/?text=gas_service&ll={longitude},{latitude}&type=biz&results=3&lang=ru_RU&apikey={settings.yandex_api_key}"
            response = requests.get(url=url)
            if response.status_code == 200:
                data = json.loads(response.text)
                if "features" in data:
                    for feature in data["features"]:
                        geometry = feature["geometry"]
                        coord = geometry.get("coordinates", "Координаты не найдены")
                        r = 6371
                        lat1 = math.radians(latitude)
                        lon1 = math.radians(longitude)
                        lat2 = math.radians(coord[1])
                        lon2 = math.radians(coord[0])

                        dlat = lat2 - lat1
                        dlon = lon2 - lon1

                        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
                        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

                        dist = r * c

                        if "properties" in feature and "CompanyMetaData" in feature["properties"]:
                            company_metadata = feature["properties"]["CompanyMetaData"]
                            name = company_metadata.get("name", "Название не найдено")
                            address = company_metadata.get("address", "Адрес не найден")
                            phones = [phone["formatted"] for phone in company_metadata.get("Phones", [])]

                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Название: {name}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Адрес: {address}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Телефоны: {', '.join(phones)}",
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text=f"Расстояние до места: {round(dist, 2)} км"
                            )
                            await call.bot.send_message(
                                chat_id=call.message.chat.id,
                                text="-----------------------------"
                            )
                            await asyncio.sleep(1)
                        else:
                            print("Не удалось найти информацию о компании")
                else:
                    print("Отсутствуют объекты (features) в JSON-ответе")
            else:
                print("Ошибка в запросе: ", response.status_code)
        else:
            await call.answer(
                text="Отправьте пожалуйста вашу позицию",
            )
    except NameError:
        await call.answer(
            text="Отправьте пожалуйста вашу позицию",
        )


@dp.message(F.text.contains("Ул") | F.text.contains("ул"))
async def incidient_place(msg: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data="add_street")
    builder.button(text="Нет", callback_data="edit_message")
    builder.adjust(2)
    place = msg.text
    await msg.answer(
        text=f"Это произошло на {place}",
        reply_markup=builder.as_markup(),
    )


@dp.message()
async def incidient_discription(msg: types.Message):
    try:
        senders_location = f"Широта: {latitude}, Долгота: {longitude}"
    except (AttributeError, NameError):
        senders_location = "Местоположение не определено"
    global description, TypeInc
    description = msg.text
    performed_date = time.time()
    if TypeInc is None:
        print(TypeInc)
        await msg.answer(
            text="Пожалуйста нажмите /call"
        )
        return
    else:
        if description is not None:
            add_description_to_incidient(Type=TypeInc, sender_id=msg.from_user.id, sender_name=msg.from_user.first_name,
                                         description=description, sender_location=senders_location,
                                         Date=datetime.datetime.fromtimestamp(performed_date))
            print("Успешно добавлен")
        else:
            await msg.answer(
                text="Введите корректное сообщение"
            )
            return
        await msg.answer(
            text=f"Вы утверждаете что: {description}"
        )

    await msg.answer(
        text="Укажите улицу где это произошло"
    )


@dp.message(F.from_user.id.in_(dispatchers_list))
async def periodic_check_updates():
    try:
        new_value = check_for_updates()
        f = open('chat_id.txt', 'r')
        chat_id = f.readline()
        for line in new_value:
            await bot.send_message(
                chat_id=chat_id,
                text=f"Тип: {line[1]}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=f"id отправителя: {line[2]}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=f"Имя отправителя: {line[3]}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=f"Что произоло: {line[4]}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=f"Местоположение отправителя: {line[5]}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=f"Где произошло: {line[6]}"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=f"Дата отправки: {line[7]}"
            )
    except UnboundLocalError:
        print("Новых обновлений нет")


async def main():
    logging.basicConfig(
        level=logging.INFO
    )
    create_db()
    loop = asyncio.get_event_loop()
    loop.call_later(150, repeat, periodic_check_updates, loop)
    await dp.start_polling(bot, loop=loop)


def repeat(coro, loop):
    asyncio.ensure_future(coro(), loop=loop)
    loop.call_later(150, repeat, coro, loop)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, CancelledError):
        pass
