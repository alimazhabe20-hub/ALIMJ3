from typing import Any

# Auto-split part 15: update_summary
def update_summary(result: dict[str, Any], lang: str = "fa") -> str:
    status = result.get("status")
    current = result.get("current_version", VERSION)
    latest = result.get("latest_version", current)
    release = result.get("release") or {}
    notes = str(release.get("notes", "")).strip()
    severity = str(release.get("severity", "")).lower()
    if lang == "en":
        if status == "up_to_date": head = "🟢 Your bot is up to date."
        elif status == "update_available": head = f"🟡 Update available: v{latest} (current v{current})"
        elif status == "update_required": head = f"🔴 Update required: v{latest} (current v{current})"
        else: head = "⚪ Update status is unavailable. Configure UPDATE_MANIFEST_URL."
        lines = ["🔄 Update Center", head, f"Runtime: {'✅ healthy' if result.get('local_checks', {}).get('ok') else '⚠️ needs attention'}"]
        if severity: lines.append(f"Severity: {severity}")
        if notes: lines.append(f"Notes: {notes[:900]}")
        return "\n".join(lines)
    if lang == "ar":
        if status == "up_to_date": head = "🟢 البوت محدث إلى آخر إصدار."
        elif status == "update_available": head = f"🟡 يوجد تحديث: v{latest} (الحالي v{current})"
        elif status == "update_required": head = f"🔴 التحديث مطلوب: v{latest} (الحالي v{current})"
        else: head = "⚪ حالة التحديث غير متاحة. اضبط UPDATE_MANIFEST_URL."
        lines = ["🔄 مركز التحديث", head, f"حالة التشغيل: {'✅ سليمة' if result.get('local_checks', {}).get('ok') else '⚠️ تحتاج إلى مراجعة'}"]
        if severity: lines.append(f"الأهمية: {severity}")
        if notes: lines.append(f"ملاحظات: {notes[:900]}")
        return "\n".join(lines)
    if status == "up_to_date": head = "🟢 ربات شما به‌روز است."
    elif status == "update_available": head = f"🟡 بروزرسانی موجود است: v{latest} (نسخه فعلی v{current})"
    elif status == "update_required": head = f"🔴 بروزرسانی ضروری است: v{latest} (نسخه فعلی v{current})"
    else: head = "⚪ وضعیت بروزرسانی قابل دریافت نیست؛ UPDATE_MANIFEST_URL را تنظیم کنید."
    lines = ["🔄 مرکز بروزرسانی", head, f"سلامت اجرا: {'✅ سالم' if result.get('local_checks', {}).get('ok') else '⚠️ نیازمند بررسی'}"]
    if severity: lines.append(f"اهمیت: {severity}")
    if notes: lines.append(f"توضیحات: {notes[:900]}")
    return "\n".join(lines)
