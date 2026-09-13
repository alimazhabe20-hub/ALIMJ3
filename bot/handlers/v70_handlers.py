from __future__ import annotations
import asyncio, re
from telegram import Update
from telegram.ext import ContextTypes
from bot.logger import logger
from bot.services.downloader import is_url, download, cleanup, user_message
from bot.services.v70_platform import *

MORE_DOWNLOAD_LABEL='📥 دانلودر فایل'

async def downloader_entry(update:Update,context:ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_for']='downloader_url'
    await update.message.reply_text('📥 دانلودر فایل حرفه‌ای\n\nلینک عمومی را بفرستید؛ YouTube، Instagram، TikTok، Facebook و بسیاری از سایت‌های دیگر و همچنین لینک مستقیم فایل پشتیبانی می‌شود.\n\n⚠️ محدودیت سایت، CAPTCHA، محتوای خصوصی یا ورود اجباری دور زده نمی‌شود. سقف ارسال مستقیم: ۴۸MB.')

async def handle_downloader_url(update:Update,context:ContextTypes.DEFAULT_TYPE,text:str)->bool:
    if not is_url(text): return False
    # Only activate after button or an explicit URL; this prevents stealing generic chat links.
    if context.user_data.get('waiting_for')!='downloader_url' and not re.search(r'(youtube|youtu\.be|instagram|tiktok|facebook|twitter|x\.com|vimeo|dailymotion)',text,re.I):
        return False
    context.user_data.pop('waiting_for',None)
    notice=await update.message.reply_text('⏬ در حال بررسی لینک و آماده‌سازی فایل…')
    result=None
    try:
        result=await download(text)
        path=result['path']
        await notice.edit_text(f"✅ آماده شد\n📄 {result['title']}\n📦 {result['size']/1024/1024:.1f} MB\n\nدر حال ارسال…")
        with open(path,'rb') as fh:
            await update.message.reply_document(document=fh,filename=result['title'][:120],caption='📥 دانلودر فایل • روز زیبا')
    except Exception as e:
        code=str(e) if str(e) in {'invalid_url','blocked_host','dns_error','rate_limited','site_blocked','access_restricted','unsupported','too_large','yt_dlp_missing','failed'} else 'failed'
        logger.warning('downloader failed: %s',code)
        await update.message.reply_text(user_message(code))
    finally:
        cleanup(result.get('path') if result else None)
        try: await notice.delete()
        except Exception: pass
    return True

async def v70_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    init_v70_tables(); await update.message.reply_text('🚀 V70 AI Platform فعال است.\n\nعامل خودکار، چندعاملی، بررسی واقعیت، منبع‌یابی، حافظه ۲، RAG، تحلیل سند، Code Agent، خودآزمایی، بازیابی خودکار، کارایی، امنیت، Workspace، بهینه‌ساز AI، شاخه مکالمه، وظایف زمان‌بندی‌شده، اعلان هوشمند، شخصی‌سازی و مانیتورینگ فعال هستند.')

async def v70_selftest_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🧪 نتیجه تست داخلی:\n'+str(self_test()))

async def v70_memory_command(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; args=' '.join(context.args or []).strip()
    if not args: await update.message.reply_text('🧠 /memory3 key=value برای ذخیره یا /memory3 list برای نمایش'); return
    if args.lower()=='list':
        rows=memories_v70(uid); await update.message.reply_text('🧠 حافظه ۲:\n'+('\n'.join(f'• {k}: {v}' for k,v in rows) if rows else 'خالی است.')); return
    if args.lower().startswith('forget '): forget_v70(uid,args[7:].strip()); await update.message.reply_text('🗑 حذف شد.'); return
    if '=' in args:
        k,v=args.split('=',1); remember_v70(uid,k.strip(),v.strip()); await update.message.reply_text('✅ در حافظه ذخیره شد.'); return
    await update.message.reply_text('فرمت: key=value')
