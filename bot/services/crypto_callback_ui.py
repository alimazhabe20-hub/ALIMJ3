from __future__ import annotations
import html, re
from io import BytesIO
from telegram import InputMediaPhoto
from bot.logger import logger

class CryptoCallbackUI:
    """Telegram UI delivery helpers for crypto callback responses."""
    def __init__(self, *, query, context, menu, symbol: str):
        self.query, self.context, self.menu, self.symbol = query, context, menu, symbol

    @staticmethod
    def split_telegram_text(txt: str, limit: int = 3900) -> list[str]:
        raw = (txt or "").strip()
        if not raw: return []
        chunks, current = [], ""
        for line in raw.splitlines():
            candidate = line if not current else current + "\n" + line
            if len(candidate) <= limit:
                current = candidate; continue
            if current: chunks.append(current); current = ""
            if len(line) <= limit:
                current = line; continue
            plain = html.unescape(re.sub(r"<[^>]*>", "", line))
            while len(plain) > limit:
                chunks.append(plain[:limit].rstrip()); plain = plain[limit:]
            current = plain
        if current: chunks.append(current)
        return chunks

    async def send_full_text(self, txt: str, *, reply_to=None, reply_markup=None):
        chunks = self.split_telegram_text(txt)
        if not chunks: return
        target = reply_to or self.query.message
        for i, chunk in enumerate(chunks):
            kwargs = {"text": chunk, "parse_mode": "HTML"}
            if i == len(chunks) - 1 and reply_markup is not None: kwargs["reply_markup"] = reply_markup
            await target.reply_text(**kwargs)

    async def update_market_analysis_text(self, full_text: str):
        ids = list(self.context.user_data.get("market_analysis_text_ids") or [])
        chat_id = self.context.user_data.get("market_analysis_chat_id") or self.query.message.chat_id
        chunks = self.split_telegram_text(full_text) or ["داده کافی نیست."]
        bot = self.context.bot
        if ids:
            try: await bot.edit_message_text(chat_id=chat_id, message_id=ids[0], text=chunks[0], parse_mode="HTML", reply_markup=None)
            except Exception: pass
            for old_id in ids[1:]:
                try: await bot.delete_message(chat_id=chat_id, message_id=old_id)
                except Exception: pass
        else:
            m = await bot.send_message(chat_id=chat_id, text=chunks[0], parse_mode="HTML"); ids = [m.message_id]
        for chunk in chunks[1:]:
            m = await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML"); ids.append(m.message_id)
        for old_id in ids[:-1]:
            try: await bot.edit_message_reply_markup(chat_id=chat_id, message_id=old_id, reply_markup=None)
            except Exception: pass
        try: await bot.edit_message_reply_markup(chat_id=chat_id, message_id=ids[-1], reply_markup=self.menu)
        except Exception: pass
        self.context.user_data["market_analysis_text_ids"] = ids
        self.context.user_data["market_analysis_chat_id"] = chat_id

    async def edit_photo_caption(self, png: bytes | None, caption: str):
        msg = self.query.message
        full_input = (caption or "📈 نمودار تحلیل").strip()
        if len(full_input) > 1000 or "━━━━━━━━━━━━━━━━━━━━" in full_input or "تحلیل هوشمند" in full_input:
            try: await self.update_market_analysis_text(full_input)
            except Exception as exc: logger.debug("market analysis text update: %s", exc)
        cap = full_input.split("\n━━━━━━━━━━━━━━━━━━━━", 1)[0].strip()[:1000]
        try:
            photo_msg_id = self.context.user_data.get("market_chart_message_id")
            chat_id = self.context.user_data.get("market_chart_chat_id") or msg.chat_id
            if msg.photo: photo_msg_id, chat_id = msg.message_id, msg.chat_id
            if photo_msg_id:
                if png:
                    bio = BytesIO(png); bio.name = f"{self.symbol}_chart.png"
                    media = InputMediaPhoto(media=bio, caption=cap, parse_mode="HTML")
                    await self.context.bot.edit_message_media(chat_id=chat_id, message_id=photo_msg_id, media=media, reply_markup=None)
                else:
                    await self.context.bot.edit_message_caption(chat_id=chat_id, message_id=photo_msg_id, caption=cap, parse_mode="HTML", reply_markup=None)
        except Exception as exc: logger.warning("market chart same-message edit failed: %s", exc)

    async def edit_text(self, txt: str):
        text = (txt or "").strip() or "داده کافی نیست."
        msg = self.query.message
        try:
            if msg.photo: await msg.edit_caption(caption=msg.caption or "📈 نمودار تحلیل", parse_mode="HTML", reply_markup=None)
            await self.update_market_analysis_text(text)
        except Exception:
            try: await self.send_full_text(text, reply_to=msg, reply_markup=self.menu)
            except Exception as exc: logger.debug("crypto callback text fallback: %s", exc)
