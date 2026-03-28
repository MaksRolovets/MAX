import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, MessageCallback, CallbackButton, CommandStart
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

bot = Bot(token="f9LHodD0cOLgf_0buCip0sDbatL0euGdP2f6NBNbTBx8tBc9_bXK8r5jVOKt06lDVrVCK6IIRBf_LWwnHbjh")
dp = Dispatcher()


async def send_menu(chat_id: int) -> None:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="Кнопка 1", payload="btn_1"),
        CallbackButton(text="Кнопка 2", payload="btn_2"),
    )
    builder.row(CallbackButton(text="Главное меню", payload="menu"))

    await bot.send_message(
        chat_id=chat_id,
        text="Привет! Тест кнопок MaxAPI.",
        attachments=[builder.as_markup()],
    )


@dp.message_created(CommandStart())
async def start_handler(event: MessageCreated):
    await send_menu(event.chat_id)


@dp.message_callback()
async def on_callback(event: MessageCallback):
    payload = event.callback.payload
    if payload == "menu":
        await event.message.answer("Ок, показываю меню заново.")
        await send_menu(event.chat_id)
        return

    if payload in ("btn_1", "btn_2"):
        await event.answer(new_text=f"Вы нажали: {payload}")
        await event.message.answer("Можно снова открыть меню командой /start")
        return

    await event.message.answer(f"Получен callback: {payload}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
