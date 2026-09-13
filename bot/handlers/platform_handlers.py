from __future__ import annotations
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import config
from bot.services.v61_v65_platform import *
from bot.logger import logger

async def features_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    f=features_snapshot()
    await update.message.reply_text(t(uid,"features")+"\n\n"+"\n".join("• "+x.replace("_"," ") for x in f["features"])+"\n\n🌐 فارسی • English • العربية\n🆓 Free")

async def watchlist_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; args=context.args
    if args and args[0].lower() in {"add","+","افزودن","إضافة"} and len(args)>1:
        sym=args[1]; add_watch(uid,sym," ".join(args[2:])); await update.message.reply_text(t(uid,"saved")); return
    if args and args[0].lower() in {"remove","-","حذف","إزالة"} and len(args)>1:
        await update.message.reply_text(t(uid,"removed") if remove_watch(uid,args[1]) else t(uid,"empty")); return
    rows=get_watchlist(uid)
    if not rows: await update.message.reply_text(t(uid,"empty")); return
    await update.message.reply_text(t(uid,"watch")+"\n\n"+"\n".join(f"• {s}"+(f" — {l}" if l else "") for s,l in rows))

async def alerts_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; args=context.args
    try:
        if args and args[0].lower() in {"add","افزودن","إضافة"} and len(args)>=3:
            sym=args[1].upper(); target=float(args[2]); direction=args[3].lower() if len(args)>3 else "above"
            if direction in {"بالا","فوق","above","up","أعلى"}: direction="above"
            elif direction in {"پایین","زیر","below","down","أدنى"}: direction="below"
            aid=add_alert(uid,sym,target,direction); await update.message.reply_text(f"{t(uid,'saved')} ID: {aid}"); return
        if args and args[0].lower() in {"remove","حذف","إزالة"} and len(args)>1:
            await update.message.reply_text(t(uid,"removed") if remove_alert(uid,int(args[1])) else t(uid,"empty")); return
    except Exception:
        await update.message.reply_text(t(uid,"bad")); return
    rows=get_alerts(uid)
    if not rows: await update.message.reply_text(t(uid,"empty")); return
    await update.message.reply_text(t(uid,"alerts")+"\n\n"+"\n".join(f"#{r[0]} • {r[1]} {r[3]} {r[2]}" for r in rows))

async def memory_v65_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; args=context.args
    if args and args[0].lower() in {"forget","حذف","انسَ","نسي"}:
        key=" ".join(args[1:]).strip() or None; n=forget(uid,key); await update.message.reply_text(t(uid,"removed") if n else t(uid,"empty")); return
    if args and len(args)>=2:
        key=args[0]; value=" ".join(args[1:]); remember(uid,key,value); await update.message.reply_text(t(uid,"saved")); return
    rows=memories(uid)
    if not rows: await update.message.reply_text(t(uid,"empty")); return
    await update.message.reply_text(t(uid,"memory")+"\n\n"+"\n".join(f"• {k}: {v}" for k,v,_ in rows))

async def platform_health_command(update:Update, context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    if uid not in getattr(config,"ADMIN_IDS",[]):
        await update.message.reply_text("⛔ Admin only"); return
    h=health_snapshot(); await update.message.reply_text("🩺 V65 Health\n"+"\n".join(f"• {k}: {v if not isinstance(v,dict) else 'available'}" for k,v in h.items()))
