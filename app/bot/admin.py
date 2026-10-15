from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.billing import BillingError, BillingService, iso, utcnow
from app.security import is_admin_id, is_super_admin_id
from app.i18n.catalog import admin_labels

router = Router(name="admin")


def is_admin(event, settings) -> bool:
    actor = event.from_user
    return bool(actor and (is_admin_id(actor.id, settings.admin_ids) or is_super_admin_id(actor.id, settings.super_admin_ids)))


def menu(lang: str = "uz") -> InlineKeyboardMarkup:
    labels=admin_labels(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=labels[0], callback_data="adm:stats"), InlineKeyboardButton(text=labels[1], callback_data="adm:users")],
        [InlineKeyboardButton(text=labels[2], callback_data="adm:subs"), InlineKeyboardButton(text=labels[3], callback_data="adm:plans")],
        [InlineKeyboardButton(text=labels[4], callback_data="adm:free"), InlineKeyboardButton(text=labels[5], callback_data="adm:usage")],
        [InlineKeyboardButton(text=labels[6], callback_data="adm:audit"), InlineKeyboardButton(text=labels[7], callback_data="adm:mode")],
        [InlineKeyboardButton(text=labels[8], callback_data="adm:settings")],
        [InlineKeyboardButton(text=labels[9], callback_data="adm:broadcast")],
    ])


@router.message(Command("admin"))
async def admin_home(message: Message, settings, db):
    if not is_admin(message, settings):
        await message.answer(admin_labels(BillingService(db).get_language(message.from_user.id))[11])
        return
    lang=BillingService(db).get_language(message.from_user.id)
    title="👑 Super Admin paneli" if is_super_admin_id(message.from_user.id,settings.super_admin_ids) else admin_labels(lang)[10]
    await message.answer(title, reply_markup=menu(lang))


@router.callback_query(F.data.startswith("adm:") & ~F.data.startswith("adm:modeconfirm:"))
async def admin_action(callback: CallbackQuery, db, settings):
    if not is_admin(callback, settings):
        await callback.answer(admin_labels(BillingService(db).get_language(callback.from_user.id))[11], show_alert=True)
        return
    lang=BillingService(db).get_language(callback.from_user.id)
    action = callback.data.split(":", 1)[1]
    billing = BillingService(db)
    if action == "stats":
        s = billing.stats()
        with db.connect() as con:
            subs = con.execute("SELECT status,COUNT(*) n FROM subscriptions GROUP BY status").fetchall()
            active = con.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active' AND ends_at>?", (iso(utcnow()),)).fetchone()[0]
            feature_rows = con.execute("SELECT feature,COUNT(*) n FROM usage_records WHERE success=1 GROUP BY feature").fetchall()
        status_text = ", ".join(f"{x['status']}: {x['n']}" for x in subs) or "yo‘q"
        feature_text = ", ".join(f"{x['feature']}: {x['n']}" for x in feature_rows) or "yo‘q"
        text = f"Foydalanuvchilar: {s['users']} (bepul: {s['free_users']}, pullik: {s['paid_users']})\nYangi bugun: {s['new_today']}\nFaol bugun: {s['active_today']}\nFaol 30 kunda: {s['active_30d']}\nFaol obunalar: {active}\nObunalar holati: {status_text}\nGeneratsiyalar: {s['generations']}\nPPTX: {s['pptx']} · PDF: {s['pdf']} · Testlar: {s['tests']} · Namunalar: {s['examples']}\nAI tokenlar: {s['tokens']} · xatolar: {s['ai_errors']}\nFunksiyalar: {feature_text}\nTasdiqlangan tushum: {s['confirmed_revenue_xtr']} XTR"
    elif action == "plans":
        with db.connect() as con:
            rows = con.execute("SELECT * FROM plans ORDER BY price").fetchall()
        text = "Tariflar:\n" + "\n".join(f"{p['code']} — {p['name']}: {p['price']} {p['currency']}; {'faol' if p['is_active'] else 'o‘chiq'}" for p in rows)
        text += "\nYangi tarif: /plan_create KOD NOM NARX_XTR KUN KUNLIK OYLIK\nMaydon: /plan_set TARIF MAYDON QIYMAT. Aktiv: /plan_active TARIF on|off"
    elif action == "subs":
        with db.connect() as con:
            payments=con.execute("SELECT id,user_id,amount,currency,status,created_at FROM payments ORDER BY id DESC LIMIT 8").fetchall()
            subscriptions=con.execute("SELECT s.id,s.user_id,p.code,s.status,s.ends_at FROM subscriptions s JOIN plans p ON p.id=s.plan_id ORDER BY s.id DESC LIMIT 8").fetchall()
        payment_text="\n".join(f"#{r['id']} user={r['user_id']} {r['amount']} {r['currency']} {r['status']} {r['created_at']}" for r in payments) or "to‘lov yo‘q"
        sub_text="\n".join(f"#{r['id']} user={r['user_id']} {r['code']} {r['status']} end={r['ends_at']}" for r in subscriptions) or "obuna yo‘q"
        text="So‘nggi to‘lovlar:\n"+payment_text+"\n\nSo‘nggi obunalar:\n"+sub_text+"\nQaytarish: /refund PAYMENT_ID"
    elif action == "settings":
        with db.connect() as con:
            rows=con.execute("SELECT key,value FROM system_settings WHERE key IN ('enabled_languages','enabled_formats','min_pages','max_pages','min_font_pt','max_font_pt','file_retention_days','free_formats','presentation_max_slides','presentation_free_generations') ORDER BY key").fetchall()
        text="Bot sozlamalari:\n"+"\n".join(f"{r['key']} = {r['value']}" for r in rows)+"\nO‘zgartirish: /setting KALIT QIYMAT"
    elif action == "mode":
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=m, callback_data=f"adm:modeconfirm:{m}")] for m in ("FREE", "FREEMIUM", "PAID_ONLY")])
        await callback.message.edit_text(f"Joriy rejim: {billing.get_mode()}. Tanlash va keyingi tasdiq monetizatsiya huquqlarini yangilaydi:", reply_markup=kb)
        await callback.answer()
        return
    elif action == "audit":
        with db.connect() as con:
            rows = con.execute("SELECT admin_id,action,target_user_id,details,created_at FROM admin_audit_logs ORDER BY id DESC LIMIT 10").fetchall()
        text = "Oxirgi amallar:\n" + ("\n".join(f"{r['created_at']} admin={r['admin_id']} {r['action']} user={r['target_user_id']} {r['details']}" for r in rows) or "hozircha yozuv yo‘q")
    else:
        text = {
            "users": "Foydalanuvchi: /user ID\nBloklash/ochish: /block ID | /unblock ID\nLimit: /limit ID SON",
            "subs": "Tarif berish: /grant ID TARIF KUN. To‘lovlar faqat Telegram tasdiqlagan update’dan yoziladi.",
            "usage": "Foydalanuvchi AI sarfi: /usage ID. Tokenlar generator provayderi ulanganidan so‘ng qayd qilinadi.",
            "free": "Bepul kunlik kvota: /limit TELEGRAM_ID KUNLIK_LIMIT",
            "broadcast": "E’lon yuborish: /broadcast Xabar matni",
            "settings": "Bot sozlamalari: /setting KALIT QIYMAT; salomlashuv stikerlarini qo‘shish: stickerga reply qilib /set_welcome_sticker; tozalash: /clear_welcome_stickers.",
        }.get(action, "Noma’lum bo‘lim")
    await callback.message.edit_text(text, reply_markup=menu(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:modeconfirm:"))
async def mode_confirm(callback: CallbackQuery, db, settings):
    if not is_admin(callback, settings):
        await callback.answer(admin_labels(BillingService(db).get_language(callback.from_user.id))[11], show_alert=True)
        return
    lang=BillingService(db).get_language(callback.from_user.id)
    mode = callback.data.rsplit(":", 1)[1]
    try:
        BillingService(db).set_mode(mode, callback.from_user.id, settings.telegram_stars_enabled)
        await callback.message.edit_text(f"Tasdiqlandi: rejim {mode}. Audit jurnaliga yozildi.", reply_markup=menu(lang))
    except BillingError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Tasdiqlandi")


async def authorized(message, settings) -> bool:
    if is_admin(message, settings):
        return True
    await message.answer("Ruxsat yo‘q.")
    return False


@router.message(Command("user"))
async def user_profile(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=2 or not p[1].isdigit(): await message.answer("Ishlatish: /user TELEGRAM_ID"); return
    uid=int(p[1])
    with db.connect() as con:
        user=con.execute("SELECT * FROM users WHERE telegram_id=?",(uid,)).fetchone()
        usage=con.execute("SELECT feature,COUNT(*) n FROM usage_records WHERE user_id=? GROUP BY feature",(uid,)).fetchall()
        subs=con.execute("SELECT p.name,s.status,s.ends_at FROM subscriptions s JOIN plans p ON p.id=s.plan_id WHERE s.user_id=? ORDER BY s.id DESC LIMIT 5",(uid,)).fetchall()
    if not user: await message.answer("Foydalanuvchi topilmadi."); return
    uses=', '.join('{}={}'.format(r['feature'],r['n']) for r in usage) or 'yo‘q'
    plans=', '.join('{} {} tugash={}'.format(r['name'],r['status'],r['ends_at']) for r in subs) or 'yo‘q'
    await message.answer(f"ID: {uid}\nUsername: @{user['username'] or '—'}\nIsm: {user['first_name']}\nBloklangan: {bool(user['is_blocked'])}\nRo‘yxat: {user['created_at']}\nOxirgi faollik: {user['last_active_at']}\nFoydalanish: {uses}\nObunalar: {plans}")


@router.message(Command(commands=["block", "unblock"]))
async def block_user(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=2 or not p[1].isdigit(): await message.answer("Ishlatish: /block ID yoki /unblock ID"); return
    uid=int(p[1]); blocked=int(p[0].split('@')[0]=='/block')
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur=con.execute("UPDATE users SET is_blocked=? WHERE telegram_id=?",(blocked,uid))
        if cur.rowcount: con.execute("INSERT INTO admin_audit_logs(admin_id,action,target_user_id,details) VALUES(?,?,?,?)",(message.from_user.id,"block_user" if blocked else "unblock_user",uid,"admin command"))
        con.commit()
    await message.answer("Bajarildi." if cur.rowcount else "Foydalanuvchi topilmadi.")


@router.message(Command("limit"))
async def change_limit(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=3 or not p[1].isdigit() or not p[2].isdigit(): await message.answer("Ishlatish: /limit ID KUNLIK_LIMIT"); return
    uid,limit=int(p[1]),int(p[2])
    with db.connect() as con:
        cur=con.execute("UPDATE users SET free_limit_override=? WHERE telegram_id=?",(limit,uid))
        if cur.rowcount: con.execute("INSERT INTO admin_audit_logs(admin_id,action,target_user_id,details) VALUES(?,?,?,?)",(message.from_user.id,"free_limit_changed",uid,str(limit)))
    await message.answer("Limit yangilandi." if cur.rowcount else "Foydalanuvchi topilmadi.")


@router.message(Command("grant"))
async def grant_plan(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=4 or not p[1].isdigit() or not p[3].isdigit(): await message.answer("Ishlatish: /grant ID TARIF KUN"); return
    uid,code,days=int(p[1]),p[2].lower(),int(p[3])
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        user=con.execute("SELECT 1 FROM users WHERE telegram_id=?",(uid,)).fetchone()
        plan=con.execute("SELECT id FROM plans WHERE code=? AND is_active=1",(code,)).fetchone()
        if user and plan:
            now=utcnow(); end=now+timedelta(days=days)
            con.execute("INSERT INTO subscriptions(user_id,plan_id,status,starts_at,ends_at) VALUES(?,?,?,?,?)",(uid,plan['id'],'active',iso(now),iso(end)))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,target_user_id,details) VALUES(?,?,?,?)",(message.from_user.id,"subscription_granted",uid,f"plan={code} days={days}"))
        con.commit()
    await message.answer("Tarif berildi." if user and plan else "Foydalanuvchi yoki tarif topilmadi.")


@router.message(Command("price"))
async def change_price(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=3 or not p[2].isdigit(): await message.answer("Ishlatish: /price TARIF XTR_NARX"); return
    with db.connect() as con:
        cur=con.execute("UPDATE plans SET price=?,currency='XTR' WHERE code=? AND code!='free'",(int(p[2]),p[1].lower()))
        if cur.rowcount: con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"plan_price_changed",f"{p[1]} -> {p[2]} XTR"))
    await message.answer("Narx saqlandi. Avvalgi tranzaksiyalar o‘zgarmaydi." if cur.rowcount else "Tarif topilmadi yoki Free narxini o‘zgartirib bo‘lmaydi.")


@router.message(Command("plan_create"))
async def create_plan(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split(maxsplit=6)
    if len(p)!=7 or not all(x.isdigit() for x in p[3:]): await message.answer("Ishlatish: /plan_create KOD NOM NARX_XTR KUN KUNLIK OYLIK"); return
    try:
        BillingService(db).create_plan(p[1],p[2],*map(int,p[3:]),admin_id=message.from_user.id)
        await message.answer("Tarif yaratildi. Boshqa limit va huquqlarni /plan_set bilan sozlang.")
    except BillingError as exc: await message.answer(str(exc))
    except Exception: await message.answer("Tarif kodi band yoki ma’lumotlar yaroqsiz.")


@router.message(Command("plan_active"))
async def plan_active(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=3 or p[2].lower() not in ('on','off'): await message.answer("Ishlatish: /plan_active TARIF on|off"); return
    enabled=int(p[2].lower()=='on')
    with db.connect() as con:
        cur=con.execute("UPDATE plans SET is_active=? WHERE code=? AND (code!='free' OR ?=1)",(enabled,p[1].lower(),enabled))
        if cur.rowcount: con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"plan_active_changed",f"{p[1]} {p[2]}"))
    await message.answer("Saqlandi." if cur.rowcount else "Tarif topilmadi yoki Free rejasini o‘chirish mumkin emas.")


@router.message(Command("plan_set"))
async def plan_set(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split(maxsplit=3)
    fields={"name","price","duration_days","daily_limit","monthly_limit","max_slides","allow_pdf","allow_pptx","examples_limit","tests_limit","features","ai_model"}
    if len(p)!=4 or p[2] not in fields: await message.answer("Ishlatish: /plan_set TARIF MAYDON QIYMAT. Maydonlar: "+", ".join(sorted(fields))); return
    field,value=p[2],p[3]
    if field in {"price","duration_days","max_slides","examples_limit","tests_limit","allow_pdf","allow_pptx"}:
        if not value.isdigit(): await message.answer("Bu maydon uchun butun son kiriting."); return
        value=int(value)
    elif field in {"daily_limit","monthly_limit"}:
        if value.lower()!="none" and not value.isdigit(): await message.answer("Limitga butun son yoki none kiriting."); return
        value=None if value.lower()=="none" else int(value)
    if field=="price" and value<0: await message.answer("Narx manfiy bo‘lishi mumkin emas."); return
    if field in {"allow_pdf","allow_pptx"} and value not in (0,1): await message.answer("Huquq qiymati 0 yoki 1 bo‘lsin."); return
    if field=="features": value=",".join(x.strip() for x in value.split(",") if x.strip())
    with db.connect() as con:
        cur=con.execute(f"UPDATE plans SET {field}=? WHERE code=? AND (code!='free' OR ?!='price')",(value,p[1].lower(),field))
        if cur.rowcount: con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"plan_field_changed",f"{p[1]} {field}={value}"))
    await message.answer("Tarif yangilandi." if cur.rowcount else "Tarif topilmadi yoki Free narxini o‘zgartirib bo‘lmaydi.")


@router.message(Command("setting"))
async def set_bot_setting(message: Message, db, settings):
    if not await authorized(message,settings): return
    p=(message.text or "").split(maxsplit=2)
    keys={"enabled_languages","enabled_formats","min_pages","max_pages","min_font_pt","max_font_pt","file_retention_days","free_formats","presentation_max_slides","presentation_free_generations"}
    if len(p)!=3 or p[1] not in keys: await message.answer("Ishlatish: /setting KALIT QIYMAT. Ruxsat etilgan kalitlar: "+", ".join(sorted(keys))); return
    key,value=p[1],p[2].strip()
    if key in {"enabled_languages","enabled_formats","free_formats"}:
        values=[x.strip() for x in value.split(",") if x.strip()]
        valid={"enabled_languages":{"uz","en","ru","tr"},"enabled_formats":{"pptx","docx","pdf"},"free_formats":{"pptx","docx","pdf"}}[key]
        if not values or not set(values)<=valid or len(values)!=len(set(values)): await message.answer("Qiymatlar vergul bilan ajratilsin; ruxsat etilganlari: "+", ".join(sorted(valid))); return
        value=",".join(values)
    else:
        try: number=int(value)
        except ValueError: await message.answer("Bu sozlama uchun butun son kiriting."); return
        ranges={"min_pages":(1,500),"max_pages":(1,500),"min_font_pt":(8,24),"max_font_pt":(8,24),"file_retention_days":(1,365),"presentation_max_slides":(5,100),"presentation_free_generations":(0,100)}
        low,high=ranges[key]
        if not low<=number<=high: await message.answer(f"Qiymat {low}–{high} oralig‘ida bo‘lsin."); return
        if key in {"min_pages","max_pages","min_font_pt","max_font_pt"}:
            mate={"min_pages":"max_pages","max_pages":"min_pages","min_font_pt":"max_font_pt","max_font_pt":"min_font_pt"}[key]
            with db.connect() as con: other=int(con.execute("SELECT value FROM system_settings WHERE key=?",(mate,)).fetchone()[0])
            if key.startswith("min_") and number>other or key.startswith("max_") and number<other:
                await message.answer(f"{key} boshqa chegaraya zid; hozirgi {mate}={other}."); return
        value=str(number)
    if key=="free_formats":
        with db.connect() as con: enabled=con.execute("SELECT value FROM system_settings WHERE key='enabled_formats'").fetchone()[0].split(",")
        if not set(value.split(","))<=set(enabled): await message.answer("Bepul formatlar yoqilgan formatlar ichida bo‘lishi kerak."); return
    with db.connect() as con:
        con.execute("INSERT INTO system_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
        con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"system_setting_changed",f"{key}={value}"))
    await message.answer(f"Saqlandi: {key} = {value}")


@router.message(Command("set_welcome_sticker"))
async def set_welcome_sticker(message: Message, db, settings):
    if not await authorized(message,settings): return
    sticker=message.sticker
    if not sticker and message.reply_to_message: sticker=message.reply_to_message.sticker
    if not sticker: await message.answer("Stickerning o‘ziga caption sifatida /set_welcome_sticker yozing yoki stickerga reply qiling."); return
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT value FROM system_settings WHERE key='welcome_sticker_file_ids'").fetchone()
        stickers=[value.strip() for value in (row[0] if row else "").replace("\n",",").split(",") if value.strip()]
        if sticker.file_id not in stickers: stickers.append(sticker.file_id)
        con.execute("INSERT INTO system_settings(key,value) VALUES('welcome_sticker_file_ids',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(",".join(stickers),))
        con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"welcome_sticker_added",f"Total welcome stickers: {len(stickers)}"))
        con.commit()
    await message.answer(f"✨ Salomlashuv stikeri saqlandi. Jami stikerlar: {len(stickers)}. Har bir yangi stickerga reply qilib /set_welcome_sticker yuboring.")


@router.message(Command("clear_welcome_stickers"))
async def clear_welcome_stickers(message: Message, db, settings):
    if not await authorized(message,settings): return
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM system_settings WHERE key='welcome_sticker_file_ids'")
        con.execute("DELETE FROM system_settings WHERE key='welcome_sticker_file_id'")
        con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"welcome_stickers_cleared","Welcome sticker list cleared"))
        con.commit()
    await message.answer("Salomlashuv stikerlar ro‘yxati tozalandi.")


@router.message(Command("usage"))
async def usage_profile(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=2 or not p[1].isdigit(): await message.answer("Ishlatish: /usage ID"); return
    with db.connect() as con:
        rows=con.execute("SELECT feature,COUNT(*) n,COALESCE(SUM(tokens),0) tokens,SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) errors FROM usage_records WHERE user_id=? GROUP BY feature",(int(p[1]),)).fetchall()
    await message.answer("\n".join(f"{r['feature']}: {r['n']} so‘rov, {r['tokens']} token, {r['errors']} xato" for r in rows) or "Foydalanish ma’lumoti yo‘q.")


@router.message(Command("broadcast"))
async def broadcast(message: Message, db, settings, bot):
    if not await authorized(message, settings): return
    body=(message.text or "").partition(" ")[2].strip()
    if not body: await message.answer("Ishlatish: /broadcast E’lon matni"); return
    with db.connect() as con: ids=[r[0] for r in con.execute("SELECT telegram_id FROM users WHERE is_blocked=0")]
    sent=failed=0
    for uid in ids:
        try: await bot.send_message(uid,body); sent+=1
        except Exception: failed+=1
    with db.connect() as con: con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(message.from_user.id,"broadcast",f"sent={sent} failed={failed}"))
    await message.answer(f"Yuborildi: {sent}; xato: {failed}.")


@router.message(Command("cancel_sub"))
async def cancel_subscription(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=2 or not p[1].isdigit(): await message.answer("Ishlatish: /cancel_sub OBUNA_ID"); return
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT user_id FROM subscriptions WHERE id=? AND status IN ('active','trial','pending_payment')",(int(p[1]),)).fetchone()
        if row:
            con.execute("UPDATE subscriptions SET status='cancelled' WHERE id=?",(int(p[1]),))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,target_user_id,details) VALUES(?,?,?,?)",(message.from_user.id,"subscription_cancelled",row["user_id"],f"subscription_id={p[1]}"))
        con.commit()
    await message.answer("Obuna bekor qilindi." if row else "Faol obuna topilmadi.")


@router.message(Command("trial"))
async def set_trial(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p) not in (2,3) or not p[1].isdigit(): await message.answer("Ishlatish: /trial KUN [TARIF]. 0 sinovni o‘chiradi."); return
    code=p[2] if len(p)==3 else "basic"
    try:
        BillingService(db).set_trial(int(p[1]),code,message.from_user.id)
        await message.answer(f"Yangi foydalanuvchilar uchun sinov: {p[1]} kun, {code}.")
    except BillingError as exc: await message.answer(str(exc))


@router.message(Command("promo"))
async def create_promo(message: Message, db, settings):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=5 or not p[3].isdigit() or not p[4].isdigit(): await message.answer("Ishlatish: /promo KOD TARIF CHEGIRMA_FOIZ MAX_ISHLATISH"); return
    try:
        BillingService(db).create_promo(p[1],p[2],int(p[3]),int(p[4]),message.from_user.id)
        await message.answer("Promo-kod yaratildi.")
    except BillingError as exc: await message.answer(str(exc))


@router.message(Command("refund"))
async def refund_payment(message: Message, db, settings, bot):
    if not await authorized(message, settings): return
    p=(message.text or "").split()
    if len(p)!=2 or not p[1].isdigit(): await message.answer("Ishlatish: /refund PAYMENT_ID"); return
    billing=BillingService(db)
    try:
        uid,charge_id=billing.begin_refund(int(p[1]))
    except BillingError as exc: await message.answer(str(exc)); return
    try:
        await bot.refund_star_payment(user_id=uid,telegram_payment_charge_id=charge_id)
    except Exception as exc:
        billing.finish_refund(int(p[1]),False,message.from_user.id)
        await message.answer(f"Telegram qaytarishni rad etdi; to‘lov o‘z holiga qaytdi. Tafsilot: {type(exc).__name__}")
        return
    billing.finish_refund(int(p[1]),True,message.from_user.id)
    await message.answer("Stars to‘lovi qaytarildi va u bilan bog‘liq obuna bekor qilindi.")
