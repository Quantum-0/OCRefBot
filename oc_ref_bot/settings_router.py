import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiopg.sa import Engine

router = Router()

log = logging.getLogger(__name__)


@router.message(Command('settings'))
async def cmd_settings(message: Message):
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Изменить настройки для галочки верификации')
    rkb.button(text='Изменить формат отправки через инлайн меню')
    await message.answer('Вы открыли меню настроек. Выберите, что вы хотите сделать', reply_markup=rkb.as_markup(one_time_keyboard=True),)
    log.info('User %s opens settings', message.from_user.full_name)


@router.message(F.text == 'Изменить настройки для галочки верификации')
async def edit_verification_settings(message: Message, pg: Engine):
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='✅ Включить отображение верификации')
    rkb.button(text='❌ Выключить отображение верификации')
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
        'Текущий статус: <b>✅ ВКЛЮЧЕНО</b>',
        reply_markup=rkb.as_markup(one_time_keyboard=True),
    )


@router.message(F.text == 'Изменить формат отправки через инлайн меню')
async def edit_inline_format(message: Message, pg: Engine):
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='🖼 Только фото')
    rkb.button(text='📂 Только файл')
    rkb.button(text='🖼+📂 Оба')
    await message.reply(
        'Настройки: формат инлайн меню\n\n'
        'По умолчанию в инлайн меню бот предлагает '
        'отправлять рефки и в виде картинки, и в виде файла\n'
        'Если у вас нет необходимости отправлять рефки как файл,'
        ' или наоборот, как картинку, '
        'вы можете отключить отображение этих пунктов в инлайн меню\n\n'
        'Текущий статус: <b>Фото + Файл</b>',
        reply_markup=rkb.as_markup(one_time_keyboard=True),
    )