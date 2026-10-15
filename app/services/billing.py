from datetime import datetime, timedelta, timezone
import secrets
import sqlite3
from app.security import is_super_admin_id


MODES = {"FREE", "FREEMIUM", "PAID_ONLY"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


class BillingError(Exception):
    pass


class BillingService:
    def __init__(self, db):
        self.db = db

    def register_user(self, telegram_id: int, username: str | None = None, first_name: str = "", language: str = "uz") -> None:
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            is_new = con.execute("SELECT 1 FROM users WHERE telegram_id=?", (telegram_id,)).fetchone() is None
            cur = con.execute("INSERT INTO users(telegram_id,username,first_name,last_active_at,language) VALUES(?,?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username,first_name=excluded.first_name,last_active_at=excluded.last_active_at", (telegram_id, username, first_name, iso(utcnow()),language))
            if is_new:
                trial_days = int(con.execute("SELECT value FROM system_settings WHERE key='trial_days'").fetchone()[0])
                if trial_days > 0:
                    plan_code = con.execute("SELECT value FROM system_settings WHERE key='trial_plan_code'").fetchone()[0]
                    plan = con.execute("SELECT id FROM plans WHERE code=? AND is_active=1", (plan_code,)).fetchone()
                    if plan:
                        now=utcnow()
                        con.execute("INSERT INTO subscriptions(user_id,plan_id,status,starts_at,ends_at) VALUES(?,?,?,?,?)", (telegram_id,plan["id"],"trial",iso(now),iso(now+timedelta(days=trial_days))))
            con.commit()

    def get_mode(self) -> str:
        with self.db.connect() as con:
            row = con.execute("SELECT value FROM system_settings WHERE key='monetization_mode'").fetchone()
        return row[0] if row else "FREE"

    def set_mode(self, mode: str, admin_id: int, stars_enabled: bool) -> None:
        mode = mode.upper()
        if mode not in MODES:
            raise BillingError("Noma’lum monetizatsiya rejimi")
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            paid = con.execute("SELECT COUNT(*) FROM plans WHERE is_active=1 AND price>0").fetchone()[0]
            if mode == "PAID_ONLY" and (not paid or not stars_enabled):
                con.rollback()
                raise BillingError("PAID_ONLY uchun faol pullik tarif va yoqilgan Telegram Stars kerak")
            previous = con.execute("SELECT value FROM system_settings WHERE key='monetization_mode'").fetchone()[0]
            con.execute("UPDATE system_settings SET value=? WHERE key='monetization_mode'", (mode,))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)", (admin_id, "monetization_mode_changed", f"{previous} -> {mode}"))
            con.commit()

    def get_language(self, user_id: int) -> str:
        with self.db.connect() as con:
            row=con.execute("SELECT language FROM users WHERE telegram_id=?",(user_id,)).fetchone()
        return row[0] if row and row[0] in {"uz","en","ru","tr"} else "uz"

    def language_selected(self, user_id: int) -> bool:
        with self.db.connect() as con:
            row=con.execute("SELECT language_selected FROM users WHERE telegram_id=?",(user_id,)).fetchone()
        return bool(row and row[0])

    def get_setting(self, key: str) -> str:
        with self.db.connect() as con:
            row=con.execute("SELECT value FROM system_settings WHERE key=?",(key,)).fetchone()
        return row[0] if row else ""

    def set_language(self, user_id: int, language: str) -> None:
        if language not in {"uz","en","ru","tr"}: raise BillingError("Unsupported language")
        with self.db.connect() as con:
            enabled=con.execute("SELECT value FROM system_settings WHERE key='enabled_languages'").fetchone()
            if enabled and language not in enabled[0].split(","): raise BillingError("Language is disabled")
            con.execute("UPDATE users SET language=?,language_selected=1 WHERE telegram_id=?",(language,user_id))

    def reserve_usage(self, user_id: int, feature: str, tokens: int | None = None, slides: int | None = None, output_format: str | None = None, usage_type: str = "") -> int:
        """Atomically authorize and record a successful generation reservation."""
        now = utcnow()
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            user = con.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,)).fetchone()
            if user is None:
                con.rollback()
                raise BillingError("Avval /start orqali ro‘yxatdan o‘ting")
            if user["is_blocked"]:
                con.rollback()
                raise BillingError("Hisobingiz bloklangan")
            super_admin = is_super_admin_id(user_id)
            mode = con.execute("SELECT value FROM system_settings WHERE key='monetization_mode'").fetchone()[0]
            subscription = con.execute("SELECT s.*,p.* FROM subscriptions s JOIN plans p ON p.id=s.plan_id WHERE s.user_id=? AND s.status IN ('active','trial') AND s.ends_at>? AND p.is_active=1 ORDER BY s.ends_at DESC LIMIT 1", (user_id, iso(now))).fetchone()
            plan = subscription
            is_free_presentation = False
            if usage_type == "presentation":
                free_row=con.execute("SELECT value FROM system_settings WHERE key='presentation_free_generations'").fetchone()
                free_generations=max(0,int(free_row[0])) if free_row else 1
                presentation_count=con.execute("SELECT COUNT(*) FROM usage_records WHERE user_id=? AND usage_type='presentation' AND success IN (1,2)",(user_id,)).fetchone()[0]
                if not super_admin and subscription is None and presentation_count >= free_generations:
                    con.rollback()
                    raise BillingError("payment_required")
                # A verified subscription grants its plan's presentation features even in FREE mode.
                plan=subscription if subscription is not None else con.execute("SELECT * FROM plans WHERE code='free' AND is_active=1").fetchone()
                is_free_presentation = subscription is None and not super_admin
            else:
                if mode == "PAID_ONLY" and plan is None and not super_admin:
                    con.rollback()
                    raise BillingError("Faol obuna talab qilinadi")
                if mode == "FREE" or (mode == "FREEMIUM" and plan is None):
                    plan = con.execute("SELECT * FROM plans WHERE code='free' AND is_active=1").fetchone()
            if super_admin and plan is None:
                plan=con.execute("SELECT * FROM plans WHERE is_active=1 ORDER BY CASE WHEN code='free' THEN 0 ELSE 1 END LIMIT 1").fetchone()
            if plan is None:
                con.rollback()
                raise BillingError("Faol tarif topilmadi")
            allowed = set(filter(None, plan["features"].split(",")))
            if feature not in allowed and not super_admin:
                con.rollback()
                raise BillingError("Bu imkoniyat tarifingizda yo‘q")
            if (feature == "pdf" and not plan["allow_pdf"] or feature == "pptx" and not plan["allow_pptx"]) and not super_admin:
                con.rollback()
                raise BillingError("Fayl formati tarifingizda yo‘q")
            if output_format:
                enabled=con.execute("SELECT value FROM system_settings WHERE key='enabled_formats'").fetchone()[0].split(",")
                if output_format not in enabled or output_format=="doc":
                    con.rollback()
                    raise BillingError("Bu fayl formati yoqilmagan. DOCX yoki PDF tanlang.")
                if (output_format=="pdf" and not plan["allow_pdf"] or output_format=="pptx" and not plan["allow_pptx"]) and not super_admin:
                    con.rollback()
                    raise BillingError("Bu format joriy tarifingizda mavjud emas")
                if plan["code"]=="free" and not super_admin:
                    free=con.execute("SELECT value FROM system_settings WHERE key='free_formats'").fetchone()[0].split(",")
                    if output_format not in free:
                        con.rollback()
                        raise BillingError("Bu format joriy tarifingizda mavjud emas")
            if slides is not None and slides > plan["max_slides"] and not super_admin:
                con.rollback()
                raise BillingError(f"Tarifingiz ko‘pi bilan {plan['max_slides']} slaydni qo‘llaydi")
            day_count = con.execute("SELECT COUNT(*) FROM usage_records WHERE user_id=? AND datetime(created_at)>=datetime(?) AND success IN (1,2)", (user_id, iso(now.replace(hour=0, minute=0, second=0, microsecond=0)))).fetchone()[0]
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_count = con.execute("SELECT COUNT(*) FROM usage_records WHERE user_id=? AND datetime(created_at)>=datetime(?) AND success IN (1,2)", (user_id, iso(month_start))).fetchone()[0]
            if feature in ("examples", "tests") and not super_admin:
                feature_limit = plan["examples_limit"] if feature == "examples" else plan["tests_limit"]
                feature_count = con.execute("SELECT COUNT(*) FROM usage_records WHERE user_id=? AND feature=? AND datetime(created_at)>=datetime(?) AND success IN (1,2)", (user_id,feature,iso(month_start))).fetchone()[0]
                if feature_count >= feature_limit:
                    con.rollback()
                    raise BillingError(f"Ushbu tarifda {feature} oylik limiti tugadi")
            daily_limit = user["free_limit_override"] if plan["code"] == "free" and user["free_limit_override"] is not None else plan["daily_limit"]
            if daily_limit is not None and day_count >= daily_limit and not is_free_presentation and not super_admin:
                con.rollback()
                raise BillingError("Kunlik limit tugadi")
            if plan["monthly_limit"] is not None and month_count >= plan["monthly_limit"] and not is_free_presentation and not super_admin:
                con.rollback()
                raise BillingError("Oylik limit tugadi")
            cursor=con.execute("INSERT INTO usage_records(user_id,feature,tokens,success,usage_type,output_format) VALUES(?,?,?,2,?,?)", (user_id, feature, tokens,usage_type,output_format or ""))
            con.execute("UPDATE users SET last_active_at=? WHERE telegram_id=?", (iso(now), user_id))
            con.commit()
            return cursor.lastrowid

    def complete_usage(self, usage_id: int, *, succeeded: bool, tokens: int | None = None) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE usage_records SET success=?,tokens=COALESCE(?,tokens) WHERE id=? AND success=2",(1 if succeeded else 0,tokens,usage_id))

    def store_generated_file(self, user_id: int, path: str, display_name: str, file_format: str, page_count: int | None, retention_days: int) -> str:
        file_id=secrets.token_hex(16)
        expiry=iso(utcnow()+timedelta(days=retention_days))
        with self.db.connect() as con:
            con.execute("INSERT INTO generated_files(id,user_id,file_path,display_name,format,page_count,expires_at) VALUES(?,?,?,?,?,?,?)",(file_id,user_id,path,display_name,file_format,page_count,expiry))
        return file_id

    def get_owned_file(self, file_id: str, user_id: int):
        with self.db.connect() as con:
            return con.execute("SELECT * FROM generated_files WHERE id=? AND user_id=? AND expires_at>?",(file_id,user_id,iso(utcnow()))).fetchone()

    def purge_expired_files(self, output_dir: str) -> int:
        root=__import__("pathlib").Path(output_dir).resolve()
        with self.db.connect() as con:
            rows=con.execute("SELECT id,file_path FROM generated_files WHERE expires_at<=?",(iso(utcnow()),)).fetchall()
            for row in rows:
                candidate=__import__("pathlib").Path(row["file_path"]).resolve()
                if candidate.is_relative_to(root): candidate.unlink(missing_ok=True)
            con.executemany("DELETE FROM generated_files WHERE id=?",[(row["id"],) for row in rows])
            return len(rows)

    def create_invoice(self, user_id: int, plan_code: str, test_mode: bool = True, promo_code: str | None = None) -> tuple[str, int, str]:
        payload = secrets.token_urlsafe(24)
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            plan = con.execute("SELECT * FROM plans WHERE code=? AND is_active=1 AND price>0", (plan_code,)).fetchone()
            if not plan:
                con.rollback()
                raise BillingError("Tarif sotuvda mavjud emas")
            amount = plan["price"]
            if promo_code:
                promo = con.execute("SELECT * FROM promo_codes WHERE code=? AND plan_id=? AND is_active=1", (promo_code.upper(), plan["id"])).fetchone()
                now = iso(utcnow())
                if not promo or (promo["starts_at"] and promo["starts_at"] > now) or (promo["ends_at"] and promo["ends_at"] <= now) or (promo["max_uses"] is not None and promo["uses"] >= promo["max_uses"]):
                    con.rollback()
                    raise BillingError("Promo-kod faol emas yoki limiti tugagan")
                if con.execute("SELECT 1 FROM promo_redemptions WHERE code=? AND user_id=?", (promo_code.upper(),user_id)).fetchone():
                    con.rollback()
                    raise BillingError("Bu promo-koddan avval foydalangansiz")
                amount = max(1, amount * (100-promo["discount_percent"]) // 100)
                con.execute("INSERT INTO promo_redemptions(code,user_id) VALUES(?,?)",(promo_code.upper(),user_id))
                con.execute("UPDATE promo_codes SET uses=uses+1 WHERE code=?",(promo_code.upper(),))
            con.execute("INSERT INTO payments(user_id,plan_id,provider,invoice_payload,amount,currency,status,test_mode) VALUES(?,?,?,?,?,?,?,?)", (user_id, plan["id"], "telegram_stars", payload, amount, "XTR", "pending", int(test_mode)))
            con.commit()
            return payload, amount, plan["name"]

    def create_promo(self, code: str, plan_code: str, discount: int, max_uses: int, admin_id: int) -> None:
        if not 1 <= discount <= 90 or max_uses < 1:
            raise BillingError("Chegirma 1-90%, foydalanish soni esa kamida 1 bo‘lsin")
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            plan=con.execute("SELECT id FROM plans WHERE code=? AND is_active=1 AND price>0",(plan_code.lower(),)).fetchone()
            if not plan:
                con.rollback()
                raise BillingError("Faol pullik tarif topilmadi")
            con.execute("INSERT INTO promo_codes(code,plan_id,discount_percent,max_uses) VALUES(?,?,?,?)",(code.upper(),plan["id"],discount,max_uses))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(admin_id,"promo_created",f"{code.upper()} {plan_code} {discount}% max={max_uses}"))
            con.commit()

    def create_plan(self, code: str, name: str, price: int, duration_days: int, daily_limit: int, monthly_limit: int, admin_id: int) -> None:
        if not code.replace("_", "").isalnum() or price < 0 or duration_days < 1 or daily_limit < 0 or monthly_limit < 0:
            raise BillingError("Tarif qiymatlari yaroqsiz")
        with self.db.connect() as con:
            con.execute("INSERT INTO plans(code,name,price,currency,duration_days,daily_limit,monthly_limit,features,max_slides,allow_pdf,allow_pptx) VALUES(?,?,?,'XTR',?,?,?,'generate,pptx',10,0,1)",(code.lower(),name,price,duration_days,daily_limit,monthly_limit))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(admin_id,"plan_created",f"{code.lower()} price={price} XTR"))

    def set_trial(self, days: int, plan_code: str, admin_id: int) -> None:
        if not 0 <= days <= 90:
            raise BillingError("Sinov muddati 0-90 kun bo‘lishi kerak")
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            plan=con.execute("SELECT 1 FROM plans WHERE code=? AND is_active=1",(plan_code.lower(),)).fetchone()
            if days and not plan:
                con.rollback()
                raise BillingError("Sinov uchun faol tarif topilmadi")
            con.execute("UPDATE system_settings SET value=? WHERE key='trial_days'",(str(days),))
            con.execute("UPDATE system_settings SET value=? WHERE key='trial_plan_code'",(plan_code.lower(),))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,details) VALUES(?,?,?)",(admin_id,"trial_settings_changed",f"{days} days plan={plan_code.lower()}"))
            con.commit()

    def begin_refund(self, payment_id: int) -> tuple[int,str]:
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            payment=con.execute("SELECT * FROM payments WHERE id=? AND provider='telegram_stars' AND status='confirmed'",(payment_id,)).fetchone()
            if not payment or not payment["provider_charge_id"]:
                con.rollback()
                raise BillingError("Tasdiqlangan qaytariladigan Stars to‘lovi topilmadi")
            con.execute("UPDATE payments SET status='refund_pending' WHERE id=?",(payment_id,))
            con.commit()
            return payment["user_id"],payment["provider_charge_id"]

    def finish_refund(self, payment_id: int, success: bool, admin_id: int) -> None:
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row=con.execute("SELECT user_id FROM payments WHERE id=? AND status='refund_pending'",(payment_id,)).fetchone()
            if not row:
                con.rollback()
                raise BillingError("Qaytarish amali topilmadi")
            con.execute("UPDATE payments SET status=?,refunded_at=CASE WHEN ? THEN ? ELSE refunded_at END WHERE id=?",("refunded" if success else "confirmed",int(success),iso(utcnow()),payment_id))
            if success:
                con.execute("UPDATE subscriptions SET status='cancelled' WHERE payment_id=?",(payment_id,))
            con.execute("INSERT INTO admin_audit_logs(admin_id,action,target_user_id,details) VALUES(?,?,?,?)",(admin_id,"payment_refunded" if success else "payment_refund_failed",row["user_id"],f"payment_id={payment_id}"))
            con.commit()

    def expire_subscriptions(self) -> int:
        with self.db.connect() as con:
            cur=con.execute("UPDATE subscriptions SET status='expired' WHERE status IN ('active','trial') AND ends_at<=?",(iso(utcnow()),))
            return cur.rowcount

    def due_reminders(self) -> list[tuple[int,int,str]]:
        now=utcnow()
        with self.db.connect() as con:
            rows=con.execute("SELECT id,user_id,ends_at FROM subscriptions WHERE status IN ('active','trial') AND reminder_sent=0 AND ends_at>? AND ends_at<=?",(iso(now),iso(now+timedelta(hours=24)))).fetchall()
            return [(r["id"],r["user_id"],r["ends_at"]) for r in rows]

    def mark_reminder_sent(self, subscription_id: int) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE subscriptions SET reminder_sent=1 WHERE id=? AND reminder_sent=0",(subscription_id,))

    def confirm_stars_payment(self, *, user_id: int, payload: str, charge_id: str, amount: int, currency: str) -> bool:
        """Idempotent settlement. Returns False for an already processed charge."""
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            payment = con.execute("SELECT * FROM payments WHERE invoice_payload=?", (payload,)).fetchone()
            if payment is None or payment["user_id"] != user_id or payment["amount"] != amount or payment["currency"] != currency:
                con.rollback()
                raise BillingError("To‘lov tafsilotlari mos kelmadi")
            if payment["status"] == "confirmed":
                if payment["provider_charge_id"] != charge_id:
                    con.rollback()
                    raise BillingError("To‘lov identifikatori mos kelmadi")
                con.rollback()
                return False
            if payment["status"] != "pending":
                con.rollback()
                raise BillingError("To‘lovni faollashtirish uchun kutilayotgan holatda bo‘lishi kerak")
            try:
                con.execute("UPDATE payments SET status='confirmed',provider_charge_id=?,confirmed_at=? WHERE id=? AND status='pending'", (charge_id, iso(utcnow()), payment["id"]))
            except sqlite3.IntegrityError as exc:
                con.rollback()
                raise BillingError("To‘lov identifikatori avval ishlatilgan") from exc
            plan = con.execute("SELECT duration_days FROM plans WHERE id=?", (payment["plan_id"],)).fetchone()
            now = utcnow()
            active = con.execute("SELECT ends_at FROM subscriptions WHERE user_id=? AND status IN ('active','trial') AND ends_at>? ORDER BY ends_at DESC LIMIT 1", (user_id, iso(now))).fetchone()
            start = now
            if active:
                start = datetime.fromisoformat(active["ends_at"])
            end = start + timedelta(days=plan["duration_days"])
            con.execute("INSERT INTO subscriptions(user_id,plan_id,status,starts_at,ends_at,payment_id) VALUES(?,?,?,?,?,?)", (user_id, payment["plan_id"], "active", iso(now), iso(end), payment["id"]))
            con.commit()
            return True

    def stats(self) -> dict[str, int]:
        self.expire_subscriptions()
        with self.db.connect() as con:
            values = {
                "users": "SELECT COUNT(*) FROM users",
                "new_today": "SELECT COUNT(*) FROM users WHERE created_at>=date('now')",
                "active_today": "SELECT COUNT(DISTINCT user_id) FROM usage_records WHERE created_at>=date('now')",
                "active_30d": "SELECT COUNT(DISTINCT user_id) FROM usage_records WHERE created_at>=datetime('now','-30 days')",
                "generations": "SELECT COUNT(*) FROM usage_records WHERE success=1",
                "ai_errors": "SELECT COUNT(*) FROM usage_records WHERE success=0",
                "tokens": "SELECT COALESCE(SUM(tokens),0) FROM usage_records",
                "pptx": "SELECT COUNT(*) FROM usage_records WHERE success=1 AND output_format='pptx'",
                "pdf": "SELECT COUNT(*) FROM usage_records WHERE success=1 AND output_format='pdf'",
                "tests": "SELECT COUNT(*) FROM usage_records WHERE success=1 AND usage_type='tests'",
                "examples": "SELECT COUNT(*) FROM usage_records WHERE success=1 AND usage_type='samples'",
                "confirmed_revenue_xtr": "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='confirmed' AND currency='XTR'",
                "paid_users": "SELECT COUNT(DISTINCT user_id) FROM subscriptions WHERE status='active' AND ends_at>datetime('now')",
                "free_users": "SELECT COUNT(*) FROM users WHERE NOT EXISTS(SELECT 1 FROM subscriptions s WHERE s.user_id=users.telegram_id AND s.status='active' AND s.ends_at>datetime('now'))",
            }
            return {key: con.execute(sql).fetchone()[0] for key, sql in values.items()}
