import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiopg.sa import Engine

from oc_ref_bot.database import get_user_settings, set_user_settings

router = Router()

log = logging.getLogger(__name__)


class SettingsState(StatesGroup):
    settings_verification_mark = State()
    settings_inline_format = State()
    settings_input_mode = State()


main_settings_buttons_markup = ReplyKeyboardBuilder()
main_settings_buttons_markup.button(text='Изменить настройки для галочки верификации')
main_settings_buttons_markup.button(text='Изменить формат отправки через инлайн меню')
main_settings_buttons_markup.button(text='Переключение обработки поля ввода инлайн меню')
main_settings_buttons_markup.adjust(1)
main_settings_buttons_markup = main_settings_buttons_markup.as_markup(one_time_keyboard=True)


@router.message(Command('settings'))
async def cmd_settings(message: Message) -> None:
    await message.answer(
        'Вы открыли меню настроек. Выберите, что вы хотите сделать',
        reply_markup=main_settings_buttons_markup,
    )
    log.info('User %s opens settings', message.from_user.full_name)


@router.message(F.text == 'Изменить настройки для галочки верификации')
async def edit_verification_settings(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        settings = await get_user_settings(conn, message.from_user.id)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='✅ Включить отображение верификации')
    rkb.button(text='❌ Выключить отображение верификации')
    await state.set_state(SettingsState.settings_verification_mark)
    await message.reply(
        'Настройки: галочка верификации\n\n'
        'Галочка верификации ставится под рефками людей, '
        'владелец бота которых хорошо знает и уверен в том, '
        'что персонаж принадлежит именно этому человеку, '
        'персонаж существует достаточно долгое время и с ним есть много артов.\n\n'
        'В связи с этим при отправке референса через бота,'
        'под рефкой добавляется подпись о том что реф верифицирован.\n\n'
        'Если один или несколько ваших референсов имеют эту галочку, '
        'но вы не хотите чтоб она отправлялась под рефом - вы можете отключить это здесь.\n\n'
        f'Текущий статус: <b>{"✅ ВКЛЮЧЕНО" if settings["show_verification"] else "❌ Выключено"}</b>',
        reply_markup=rkb.as_markup(one_time_keyboard=True),
    )


@router.message(SettingsState.settings_verification_mark, F.text == '✅ Включить отображение верификации')
async def edit_verification_settings_enable(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, show_verification=True)
    await state.clear()
    await message.answer('Отображение галочки верификации включено', reply_markup=main_settings_buttons_markup)


@router.message(SettingsState.settings_verification_mark, F.text == '❌ Выключить отображение верификации')
async def edit_verification_settings_disable(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, show_verification=False)
    await state.clear()
    await message.answer('Отображение галочки верификации отключено', reply_markup=main_settings_buttons_markup)


@router.message(F.text == 'Изменить формат отправки через инлайн меню')
async def edit_inline_format(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        settings = await get_user_settings(conn, message.from_user.id)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='🖼 Только фото')
    rkb.button(text='📂 Только файл')
    rkb.button(text='🖼+📂 Оба')
    names_dict = {'PHOTO+DOC': 'Фото + Файл', 'PHOTO': 'Фото', 'DOC': 'Файл'}
    await state.set_state(SettingsState.settings_inline_format)
    await message.reply(
        'Настройки: формат инлайн меню\n\n'
        'По умолчанию в инлайн меню бот предлагает '
        'отправлять рефки и в виде картинки, и в виде файла\n'
        'Если у вас нет необходимости отправлять рефки как файл,'
        ' или наоборот, как картинку, '
        'вы можете отключить отображение этих пунктов в инлайн меню\n\n'
        f'Текущий статус: <b>{names_dict.get(settings["inline_format"])}</b>',
        reply_markup=rkb.as_markup(one_time_keyboard=True),
    )


@router.message(SettingsState.settings_inline_format, F.text == '🖼 Только фото')
async def edit_inline_format_photo(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, inline_format='PHOTO')
    await state.clear()
    await message.answer('Формат инлайн меню изменён на "Только фото"', reply_markup=main_settings_buttons_markup)


@router.message(SettingsState.settings_inline_format, F.text == '📂 Только файл')
async def edit_inline_format_doc(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, inline_format='DOC')
    await state.clear()
    await message.answer('Формат инлайн меню изменён на "Только файл"', reply_markup=main_settings_buttons_markup)


@router.message(SettingsState.settings_inline_format, F.text == '🖼+📂 Оба')
async def edit_inline_format_photo_and_doc(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, inline_format='PHOTO+DOC')
    await state.clear()
    await message.answer('Формат инлайн меню изменён на "Фото + файл"', reply_markup=main_settings_buttons_markup)


@router.message(F.text == 'Переключение обработки поля ввода инлайн меню')
async def edit_input_mode(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        settings = await get_user_settings(conn, message.from_user.id)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='🔍 Использовать ввод как поиск')
    rkb.button(text='🔤 Использовать ввод как подпись под рефкой')
    names_dict = {'CAPTION': 'Подпись под фото/файлом', 'SEARCH': 'Поиск референсов'}
    await state.set_state(SettingsState.settings_input_mode)
    await message.reply(
        'Настройки: режим обработки поля ввода в инлайн меню\n\n'
        'По умолчанию, текст введённый в поле ввода при вызове инлайн меню '
        'используется в качестве поиска референса по названию.\n'
        'Если у вас мало референсов, при этом есть необходимость добавлять подпись '
        'Под отправленным файлом или изображением, вы можете использовать режим отправки подписи\n\n'
        'В таком случае перестанет работать поиск референсов, '
        'но можно будет добавить свой текст в сообщение перед отправкой\n\n'
        f'Текущий статус: <b>{names_dict.get(settings["inline_input_mode"])}</b>',
        reply_markup=rkb.as_markup(one_time_keyboard=True),
    )


@router.message(SettingsState.settings_input_mode, F.text == '🔍 Использовать ввод как поиск')
async def edit_input_mode_search(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, inline_input_mode='SEARCH')
    await state.clear()
    await message.answer('Режим ввода изменён на: Поиск', reply_markup=main_settings_buttons_markup)


@router.message(SettingsState.settings_input_mode, F.text == '🔤 Использовать ввод как подпись под рефкой')
async def edit_input_mode_caption(message: Message, pg: Engine, state: FSMContext) -> None:
    async with pg.acquire() as conn:
        await set_user_settings(conn, message.from_user.id, inline_input_mode='CAPTION')
    await state.clear()
    await message.answer('Режим ввода изменён на: Подпись', reply_markup=main_settings_buttons_markup)
