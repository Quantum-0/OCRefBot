import logging
import os
import uuid
from pathlib import Path

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiopg.sa import Engine

from oc_ref_bot.config import settings
from oc_ref_bot.database import add_ref, RefAlreadyExistsError, del_ref

router = Router()

log = logging.getLogger(__name__)


class ChatState(StatesGroup):
    name_input = State()
    add_ref = State()
    confirm_adding = State()
    del_ref = State()
    del_ref_confirm = State()


@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.bot.send_message(
        message.chat.id,
        'Драсти\n\n'
        'Я бот, который помогает удобно хранить рефки на персонажей, с возможностью быстрого доступа к ним и отправки их\n\n'
        'Надеюсь я буду Вам полезен ^-^\n\n'
        'Чтоб получить подробную инструкцию по пользованию боту, используйте команду /help\n\n'
        'Меня сделал @quantum0, по всем вопросам насчёт меня можете обращаться к нему :>\n\n'
        'Он так же передаёт вам добра и желает хорошего дня ❤️\n\n'
    )
    await message.bot.send_sticker(
        message.chat.id,
       'CAACAgIAAxkBAT2NsWbDhsizAAFqJIcz1hZsDkrJm1UqfQACtUwAAiNsuErWfaHtCbzGbDUE'
    )
    log.info('User %s started the bot', message.from_user.full_name)


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.bot.send_message(
        message.chat.id,
        '<b>Справка по работе бота:</b>\n\n'
        'Для начала, тебе нужно загрузить рефку на своего персонажика.\n'
        'Для этого отправь команду /add, после чего я попрошу тебя прислать мне файлик и указать имя персонажа (название рефа, как удобно)\n'
        'Рефку нужно отправлять документом, не картинкой (кнопочка "отправить без сжатия")\n'
        'После того, как ты это сделаешь, я сохраню рефку в своей БД\n'
        'Теперь, для того чтобы отправить её кому-либо, перейди в диалог с этим человеком (так же поддерживаются групповые чаты и каналы) '
        'и напиши в начале своего сообщения моё имя, начиная с @\n'
        'Когда ты это сделаешь, прям в этом диалоге откроется inline-менюшечка, где ты увидишь свой реф\n'
        'Нажимаешь на него - рефка отправляется ^-^\n'
        'Если у тебя слишком много персонажей, то ты можешь начать вводить его имя, указанное при добавлении, я постараюсь найти его по имени с:\n\n'
        '"Зачем всё это нужно", спросишь ты. Я отвечу тебе так - вот ты где хранишь свои рефки? '
        'Когда тебе надо скинуть реф, куда ты лезешь? В избранное? В файлы на телефоне/компе? '
        'Воть моему создателю каждый раз неудобно открывать галерею на телефоне и искать там реф, '
        'Или лезть в свой канал, искать там закреплённое сообщение и его пересылать. Про "избранное" я вообще молчу.. '
        'Скажу тебе по секрету, у него там такааая помойка из всяких файлов/записок/заметок, ууххх.. '
        'Ну воть, а я сделан для того чтоб помочь легко найти и достать свой реф uwu\n\n'
        'Так же реф всегда можно удалить, для этого достаточно воспользоваться командой /del и выбрать, какой реф вы хотите удалить c:'
    )
    log.info('User %s asked for help', message.from_user.full_name)


@router.message(Command('add'))
async def cmd_add(message: Message, state: FSMContext):
    await message.bot.send_message(
        message.chat.id,
        'Укажи имя персонажа или название референса, который хочешь добавить'
    )
    await state.set_state(ChatState.name_input)
    log.info('User %s adding new ref', message.from_user.full_name)


@router.message(ChatState.name_input, F.text)
async def cmd_add_1(message: Message, state: FSMContext):
    if len(message.text) > 128:
        await message.bot.send_message(message.chat.id, 'Слишком длинное имя, давай что-нибудь покороче о:')
        return
    if len(message.text) < 2:
        await message.bot.send_message(message.chat.id, 'Слишком короткое имя, давай хотя бы пару букв о:')
        return
    await state.set_data({'name': message.text})
    await message.bot.send_message(message.chat.id, 'Отлично, теперь отправь рефку персонажа файлом')
    await state.set_state(ChatState.add_ref)
    log.info('User %s entered the name of the new ref: %s', message.from_user.full_name, message.text)


@router.message(ChatState.add_ref, F.photo)
async def cmd_add_2_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.bot.send_message(
        message.chat.id,
        'Нееет, рефку нужно отправить файлом, не фоткой :с\n'
        'Если конечно хочешь, я могу сохранить и в таком виде, но учитывай, '
        'что при сохранении как фото, изображение сжимается и немного теряет качество! О:\n',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Хочу сохранить в таком виде')]],
            one_time_keyboard=True,
        )
    )
    photo_file_id = message.photo[0].file_id
    data['photo_file_id'] = photo_file_id
    await state.set_data(data)
    log.info('User %s uploaded photo with ref', message.from_user.full_name)

    # for debug, remove later
    await message.forward(settings.admin_id)


@router.message(ChatState.add_ref, F.text == 'Хочу сохранить в таком виде')
async def cmd_add_2_confirm(message: Message, state: FSMContext, pg: Engine):
    async with pg.acquire() as conn:
        data = await state.get_data()
        try:
            await add_ref(conn, message.from_user.id, data['name'], data.get('doc_file_id'), data['photo_file_id'])
        except RefAlreadyExistsError:
            await message.answer('Рефка с таким названием уже добавлена! Укажи, пожалуйста, другое название')
            await state.set_state(ChatState.name_input)
            return
        except Exception:
            await message.answer('Что-то поломалось \>.\<')
            raise
    await message.bot.send_message(
        message.chat.id,
        'Хорошо, рефка добавлена, ближайшее время появится в inline-меню бота с:',
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()
    log.info('User %s has successfully added ref', message.from_user.full_name)


@router.message(ChatState.add_ref, F.document)
async def cmd_add_2_doc(message: Message, state: FSMContext):
    data = await state.get_data()
    path = Path(os.path.dirname(os.path.realpath(__file__))) / str(uuid.uuid4())
    try:
        await message.bot.download(message.document.file_id, destination=path)
        msg_with_photo = await message.answer_photo(FSInputFile(path),
                                                    caption='Конвертнул файл так же в фотку, для удобства с:')
        doc_file_id = message.document.file_id
        photo_file_id = msg_with_photo.photo[0].file_id
        data.update({'doc_file_id': doc_file_id, 'photo_file_id': photo_file_id})
    except TelegramBadRequest:
        await message.answer('Не удалось обработать запрос :\\<')
        return
    finally:
        os.remove(path)
    await state.set_data(data)
    await state.set_state(ChatState.confirm_adding)
    await message.bot.send_message(
        message.chat.id,
        'Отлично, всё готово. Сохраняем?',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text='Сохранить'), KeyboardButton(text='Отменить')]],
            one_time_keyboard=True,
        )
    )
    log.info('User %s uploaded doc with ref', message.from_user.full_name)

    # for debug, remove later
    await message.forward(settings.admin_id)


@router.message(ChatState.confirm_adding, F.text == 'Сохранить')
async def cmd_add_3_confirm(message: Message, state: FSMContext, pg: Engine):
    async with pg.acquire() as conn:
        data = await state.get_data()
        try:
            await add_ref(conn, message.from_user.id, data['name'], data['doc_file_id'], data['photo_file_id'])
        except RefAlreadyExistsError:
            await message.answer('Рефка с таким названием уже добавлена! Укажи, пожалуйста, другое название')
            await state.set_state(ChatState.name_input)
            return
        except Exception:
            await message.answer('Что-то поломалось >.<')
            raise
    await message.bot.send_message(
        message.chat.id,
        'Хорошо, рефка добавлена, ближайшее время появится в inline-меню бота с:',
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()
    log.info('User %s has successfully added ref', message.from_user.full_name)


@router.message(F.text == 'Отменить')
async def cmd_cancel(message: Message, state: FSMContext):
    log.info('User %s has canceled action', message.from_user.full_name)
    await message.bot.send_message(
        message.chat.id,
        'Отменено ^-^',
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()


@router.message(Command('del'))
async def cmd_del(message: Message, state: FSMContext):
    log.info('User %s deleting ref', message.from_user.full_name)
    await message.bot.send_message(
        message.chat.id,
        'Хорошо, тогда отправь мне пожалуйста реф, который желаешь удалить через инлайн-режим.\n\nДля этого в начале сообщения напиши @OCRefBot и затем выбери реф, который хочешь удалить из появившегося списка с:'
    )
    await state.set_state(ChatState.del_ref)


@router.message(ChatState.del_ref_confirm, F.text == 'Да, удалить')
async def cmd_del_confirm(message: Message, state: FSMContext, pg: Engine):
    async with pg.acquire() as conn:
        data = await state.get_data()
        try:
            result = await del_ref(conn, message.from_user.id, data['ref_id'])
            if result:
                await message.answer('Рефка успешно удалена! ^-^', reply_markup=ReplyKeyboardRemove())
            else:
                await message.answer('Не получилось удалить рефку, кажется она уже удалена о_О', reply_markup=ReplyKeyboardRemove())
        except Exception:
            await message.answer('Что-то поломалось >.<')
            raise
    log.info('User %s has deleted ref %s', message.from_user.full_name, data['ref_id'])
    await state.clear()