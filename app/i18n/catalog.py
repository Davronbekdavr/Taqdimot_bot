from __future__ import annotations

LANGUAGES = ("uz", "en", "ru", "tr")
TELEGRAM_LANGUAGE = {"uz": "uz", "en": "en", "ru": "ru", "tr": "tr"}
ADMIN_MENU_LABELS = {
    "uz": ["📊 Umumiy statistika","👥 Foydalanuvchilar","💳 Obunalar va to‘lovlar","⚙️ Tariflar","🎁 Bepul foydalanish","📈 AI sarfi","🧾 Audit jurnali","🔧 Monetizatsiya","⚙️ Bot sozlamalari","📣 E’lon yo‘riqnomasi","Admin paneli","Ruxsat yo‘q."],
    "en": ["📊 Statistics","👥 Users","💳 Subscriptions and payments","⚙️ Plans","🎁 Free usage","📈 AI usage","🧾 Audit log","🔧 Monetization","⚙️ Bot settings","📣 Announcement help","Admin panel","Access denied."],
    "ru": ["📊 Статистика","👥 Пользователи","💳 Подписки и платежи","⚙️ Тарифы","🎁 Бесплатный доступ","📈 Расход ИИ","🧾 Журнал действий","🔧 Монетизация","⚙️ Настройки бота","📣 Рассылка","Панель администратора","Нет доступа."],
    "tr": ["📊 İstatistikler","👥 Kullanıcılar","💳 Abonelikler ve ödemeler","⚙️ Paketler","🎁 Ücretsiz kullanım","📈 Yapay zekâ kullanımı","🧾 Denetim kaydı","🔧 Para kazanma","⚙️ Bot ayarları","📣 Duyuru yardımı","Yönetici paneli","Erişim reddedildi."],
}


def admin_labels(language: str) -> list[str]:
    return ADMIN_MENU_LABELS.get(language,ADMIN_MENU_LABELS["uz"])


STRINGS = {
    "uz": {
        "welcome": "✨ <b>AI Presentation Studio</b>\n\nTaqdimot, referat, matnli hujjat yoki test tayyorlaymiz. Boshlash uchun tur tanlang.",
        "choose_language": "🌐 Interfeys tilini tanlang:", "language_saved": "✅ Til saqlandi: O‘zbekcha.",
        "new_doc": "✨ Material yaratish", "language": "🌐 Til", "plans": "💎 Tariflar", "help": "❔ Yordam",
        "choose_type": "📚 Qanday material kerak?", "presentation": "📊 Taqdimot · PPTX", "report": "📄 Referat · DOCX/PDF",
        "document": "📝 Matnli hujjat · DOCX/PDF", "tests": "🧠 Testlar", "samples": "📚 Namunaviy material",
        "choose_content_language": "🌍 Hujjat qaysi tilda bo‘lsin? Bu interfeys tilingizdan alohida.",
        "topic": "✍️ Mavzuni yozing. Masalan: <i>Markaziy Osiyoda suv resurslarini boshqarish</i>",
        "slides": "🔢 Nechta slayd kerak? 5–20 oralig‘ida kiriting.", "pages": "📑 Nechta sahifa kerak? 1–50 oralig‘ida kiriting.",
        "font_size": "🔠 Asosiy matn o‘lchami qancha bo‘lsin? 10–16 pt. Standart: 14 pt.",
        "page_scope": "📏 Sahifa soni titul va mundarijani ham o‘z ichiga olsinmi?", "main_pages": "Faqat asosiy matn", "all_pages": "Hujjat jami",
        "format": "📦 Yuklab olish formatini tanlang:", "choose_level": "🎓 Ta’lim bosqichini kiriting yoki o‘tkazib yuboring.",
        "skip": "O‘tkazib yuborish", "cover": "🏫 Titul varag‘i kerak bo‘lsa, muassasa, talaba, guruh, fan va rahbarni bitta xabarda yozing. Bilmagan joyingizni qoldiring yoki o‘tkazing.",
        "design": "🎨 Taqdimot uslubini tanlang:", "design_modern": "Zamonaviy", "design_academic": "Akademik", "design_minimal": "Minimal",
        "working": "⏳ Material tayyorlanyapti. Bu biroz vaqt olishi mumkin.", "ready": "✅ Tayyor! So‘ralgan hajm: {target}; yakuniy sahifalar: {actual}.",
        "ready_docx": "✅ DOCX tayyor. Word’da sahifalash dasturga qarab o‘zgarishi mumkin.", "pdf_unavailable": "PDF yaratilmadi: serverda Times New Roman shrift fayllari sozlanmagan. DOCX faylini yuboryapman.",
        "bad_number": "⚠️ Son kiriting: {low}–{high}.", "bad_topic": "Mavzu juda qisqa. Iltimos, aniqroq mavzu yozing.",
        "failed": "❌ Fayl yaratilmadi. Keyinroq qayta urinib ko‘ring.", "ai_not_configured": "⚙️ AI xizmati sozlanmagan. Administrator OPENAI_API_KEY утгыг серверийн .env-д нэмэх шаардлагатай.",
        "help_text": "/create — материал yaratish\n/language — интерфейс tilini almashtirish\n/plans — tariflar\n/paysupport — to‘lov yordami\n\nDOC format to‘ғри DOCX faylini qayta nomlash orqali yaratilmaydi; tahrirlash uchun DOCX yoki PDF tanlang.",
        "not_allowed": "Bu format joriy tarifingizda mavjud emas.", "cancelled": "Yaratish jarayoni bekor qilindi.",
        "level_prompt": "Ta’lim bosqichini yozing (maktab, bakalavr, magistr) yoki o‘tkazing.",
        "download_note": "🛡 Fayl faqat sizga yuborildi. Saqlash muddati: {days} kun.",
        "pdf_conversion_unavailable": "PDF konvertori topilmadi. Tahrirlanadigan DOCX faylini yuboryapman.",
        "payment_confirmed": "✅ To‘lov tasdiqlandi; tarif faollashtirildi.", "payment_replayed": "ℹ️ Bu to‘lov avval qayta ishlangan.",
        "page_target_mismatch": "📏 So‘ralgan hajm {target} sahifa edi; yakuniy render {actual} sahifa chiqdi. Format o‘zgartirilmadi.",
        "plan_line": "<b>{name}</b> · {price} {currency} / {days} kun · kunlik {limit}", "buy_usage": "Ishlatish: /buy basic [PROMO]",
        "gemini_not_configured": "?? Gemini xizmati sozlanmagan. Administrator serverdagi .env fayliga GEMINI_API_KEY qo?shishi kerak.", "presentation_payment_required": "?? Birinchi taqdimot bepul foydalanildi. Keyingi taqdimotni yaratish uchun faol obuna kerak. Tariflarni ko?rish: /plans. To?lov yoqilgan bo?lsa, xarid: /buy basic", "payment_invalid": "Hisob-faktura yaroqsiz. Tariflar sahifasidan qayta boshlang.", "plan_unavailable": "Tarif yoki promo-kod mavjud emas.",
        "plans_intro": "💎 <b>Tariflar</b>", "payment_disabled": "To‘lovlar vaqtincha o‘chiq.",
    },
    "en": {
        "welcome": "✨ <b>AI Presentation Studio</b>\n\nCreate a presentation, essay, document, or quiz. Choose a type to begin.",
        "choose_language": "🌐 Choose your interface language:", "language_saved": "✅ Language saved: English.",
        "new_doc": "✨ Create material", "language": "🌐 Language", "plans": "💎 Plans", "help": "❔ Help",
        "choose_type": "📚 What would you like to create?", "presentation": "📊 Presentation · PPTX", "report": "📄 Academic paper · DOCX/PDF",
        "document": "📝 Text document · DOCX/PDF", "tests": "🧠 Quiz", "samples": "📚 Sample material",
        "choose_content_language": "🌍 Choose the document language. It is independent of your interface language.",
        "topic": "✍️ Enter a topic. Example: <i>Water resource management in Central Asia</i>",
        "slides": "🔢 How many slides? Enter a number from 5 to 20.", "pages": "📑 How many pages? Enter a number from 1 to 50.",
        "font_size": "🔠 Body text size in points? Enter 10–16. Default: 14 pt.",
        "page_scope": "📏 Should the page target include the cover and contents?", "main_pages": "Body only", "all_pages": "Whole document",
        "format": "📦 Choose a download format:", "choose_level": "🎓 Enter your education level or skip.",
        "skip": "Skip", "cover": "🏫 For a cover page, enter institution, student, group, course, and supervisor in one message. Leave unknown fields blank or skip.",
        "design": "🎨 Choose a presentation style:", "design_modern": "Modern", "design_academic": "Academic", "design_minimal": "Minimal",
        "working": "⏳ Creating your material. This may take a little while.", "ready": "✅ Done! Requested: {target}; actual pages in the selected scope: {actual}.",
        "ready_docx": "✅ DOCX ready. Word pagination may vary by application.", "pdf_unavailable": "PDF unavailable: Times New Roman font files are not configured on the server. Sending DOCX instead.",
        "bad_number": "⚠️ Enter a number from {low} to {high}.", "bad_topic": "The topic is too short. Please enter a more specific topic.",
        "failed": "❌ Could not create the file. Please try again later.", "ai_not_configured": "⚙️ AI is not configured. An administrator must set OPENAI_API_KEY in the server .env file.",
        "help_text": "/create — create material\n/language — change interface language\n/plans — plans\n/paysupport — payment support\n\nDOC is not created by renaming a DOCX file; choose DOCX or PDF instead.",
        "not_allowed": "This format is not included in your current plan.", "cancelled": "Creation cancelled.",
        "level_prompt": "Enter your education level (school, undergraduate, graduate) or skip.",
        "download_note": "🛡 This file was sent only to you. Retention: {days} days.", "plans_intro": "💎 <b>Plans</b>", "payment_disabled": "Payments are temporarily disabled.",
        "pdf_conversion_unavailable": "PDF conversion is unavailable. Sending the editable DOCX file instead.", "payment_confirmed": "✅ Payment confirmed; your plan is active.", "payment_replayed": "ℹ️ This payment was already processed.",
        "page_target_mismatch": "📏 Requested: {target} pages; final render: {actual}. The font size and layout were preserved.",
        "plan_line": "<b>{name}</b> · {price} {currency} / {days} days · {limit} per day", "buy_usage": "Usage: /buy basic [PROMO]",
        "gemini_not_configured": "?? Gemini is not configured. An administrator must set GEMINI_API_KEY in the server .env file.", "presentation_payment_required": "?? Your free presentation has been used. An active subscription is required for the next one. See /plans. If payments are enabled, buy with /buy basic", "payment_invalid": "Invoice validation failed. Start again from Plans.", "plan_unavailable": "Plan or promo code is unavailable.",
    },
    "ru": {
        "welcome": "✨ <b>AI Presentation Studio</b>\n\nСоздайте презентацию, реферат, документ или тест. Выберите тип материала.",
        "choose_language": "🌐 Выберите язык интерфейса:", "language_saved": "✅ Язык сохранён: русский.",
        "new_doc": "✨ Создать материал", "language": "🌐 Язык", "plans": "💎 Тарифы", "help": "❔ Помощь",
        "choose_type": "📚 Что создать?", "presentation": "📊 Презентация · PPTX", "report": "📄 Реферат · DOCX/PDF",
        "document": "📝 Текстовый документ · DOCX/PDF", "tests": "🧠 Тесты", "samples": "📚 Пример материала",
        "choose_content_language": "🌍 Выберите язык документа. Он не зависит от языка интерфейса.",
        "topic": "✍️ Введите тему. Например: <i>Управление водными ресурсами Центральной Азии</i>",
        "slides": "🔢 Сколько нужно слайдов? Введите число от 5 до 20.", "pages": "📑 Сколько нужно страниц? Введите число от 1 до 50.",
        "font_size": "🔠 Размер основного шрифта в пунктах? Введите 10–16. По умолчанию: 14 пт.",
        "page_scope": "📏 Включать титульный лист и содержание в число страниц?", "main_pages": "Только основной текст", "all_pages": "Весь документ",
        "format": "📦 Выберите формат файла:", "choose_level": "🎓 Укажите уровень образования или пропустите.",
        "skip": "Пропустить", "cover": "🏫 Для титульного листа укажите вуз, студента, группу, предмет и руководителя одним сообщением. Неизвестные поля оставьте пустыми или пропустите.",
        "design": "🎨 Выберите стиль презентации:", "design_modern": "Современный", "design_academic": "Академический", "design_minimal": "Минимализм",
        "working": "⏳ Материал создаётся. Это может занять немного времени.", "ready": "✅ Готово! Запрошено: {target}; страниц в выбранном объёме: {actual}.",
        "ready_docx": "✅ DOCX готов. Разбивка на страницы может отличаться в разных приложениях.", "pdf_unavailable": "PDF недоступен: на сервере не настроены файлы шрифта Times New Roman. Отправляю DOCX.",
        "bad_number": "⚠️ Введите число от {low} до {high}.", "bad_topic": "Слишком короткая тема. Уточните её, пожалуйста.",
        "failed": "❌ Не удалось создать файл. Попробуйте позже.", "ai_not_configured": "⚙️ ИИ не настроен. Администратору нужно добавить OPENAI_API_KEY в .env на сервере.",
        "help_text": "/create — создать материал\n/language — изменить язык интерфейса\n/plans — тарифы\n/paysupport — помощь с оплатой\n\nФормат DOC нельзя получить простым переименованием DOCX; выберите DOCX или PDF.",
        "not_allowed": "Этот формат не входит в ваш тариф.", "cancelled": "Создание отменено.",
        "level_prompt": "Укажите уровень образования (школа, бакалавриат, магистратура) или пропустите.",
        "download_note": "🛡 Файл отправлен только вам. Срок хранения: {days} дн.", "plans_intro": "💎 <b>Тарифы</b>", "payment_disabled": "Платежи временно отключены.",
        "pdf_conversion_unavailable": "Конвертация в PDF недоступна. Отправляю редактируемый DOCX.", "payment_confirmed": "✅ Платёж подтверждён; тариф активирован.", "payment_replayed": "ℹ️ Этот платёж уже обработан.",
        "page_target_mismatch": "📏 Запрошено: {target} стр.; итоговый документ: {actual} стр. Шрифт и макет сохранены.",
        "plan_line": "<b>{name}</b> · {price} {currency} / {days} дн. · {limit} в день", "buy_usage": "Формат: /buy basic [PROMO]",
        "gemini_not_configured": "?? Gemini ?? ????????. ?????????????? ????? ???????? GEMINI_API_KEY ? ????????? ???? .env.", "presentation_payment_required": "?? ?????????? ??????????? ??? ????????????. ??? ????????? ????? ???????? ????????. ??????: /plans. ???? ??????? ????????, ???????: /buy basic", "payment_invalid": "Счёт не прошёл проверку. Начните заново со страницы тарифов.", "plan_unavailable": "Тариф или промокод недоступен.",
    },
    "tr": {
        "welcome": "✨ <b>AI Presentation Studio</b>\n\nSunum, akademik ödev, belge veya test oluşturun. Başlamak için tür seçin.",
        "choose_language": "🌐 Arayüz dilinizi seçin:", "language_saved": "✅ Dil kaydedildi: Türkçe.",
        "new_doc": "✨ İçerik oluştur", "language": "🌐 Dil", "plans": "💎 Paketler", "help": "❔ Yardım",
        "choose_type": "📚 Ne oluşturmak istiyorsunuz?", "presentation": "📊 Sunum · PPTX", "report": "📄 Akademik ödev · DOCX/PDF",
        "document": "📝 Metin belgesi · DOCX/PDF", "tests": "🧠 Test", "samples": "📚 Örnek içerik",
        "choose_content_language": "🌍 Belgenin dilini seçin. Arayüz dilinden bağımsızdır.",
        "topic": "✍️ Konuyu yazın. Örnek: <i>Orta Asya’da su kaynaklarının yönetimi</i>",
        "slides": "🔢 Kaç slayt gerekiyor? 5–20 arasında bir sayı girin.", "pages": "📑 Kaç sayfa gerekiyor? 1–50 arasında bir sayı girin.",
        "font_size": "🔠 Ana metin punto boyutu? 10–16 girin. Varsayılan: 14 pt.",
        "page_scope": "📏 Sayfa hedefine kapak ve içindekiler dahil olsun mu?", "main_pages": "Yalnızca ana metin", "all_pages": "Tüm belge",
        "format": "📦 İndirme biçimini seçin:", "choose_level": "🎓 Eğitim seviyenizi yazın veya atlayın.",
        "skip": "Atla", "cover": "🏫 Kapak sayfası için kurum, öğrenci, grup, ders ve danışmanı tek mesajda yazın. Bilinmeyen alanları boş bırakın veya atlayın.",
        "design": "🎨 Sunum stilini seçin:", "design_modern": "Modern", "design_academic": "Akademik", "design_minimal": "Minimal",
        "working": "⏳ İçeriğiniz hazırlanıyor. Biraz sürebilir.", "ready": "✅ Hazır! İstenen: {target}; seçilen kapsamda sayfa: {actual}.",
        "ready_docx": "✅ DOCX hazır. Sayfalama kullanılan uygulamaya göre değişebilir.", "pdf_unavailable": "PDF kullanılamıyor: sunucuda Times New Roman yazı tipi dosyaları ayarlanmamış. DOCX gönderiyorum.",
        "bad_number": "⚠️ {low}–{high} arasında bir sayı girin.", "bad_topic": "Konu çok kısa. Lütfen daha açık bir konu yazın.",
        "failed": "❌ Dosya oluşturulamadı. Daha sonra yeniden deneyin.", "ai_not_configured": "⚙️ Yapay zekâ ayarlanmadı. Yönetici sunucudaki .env dosyasına OPENAI_API_KEY eklemelidir.",
        "help_text": "/create — içerik oluştur\n/language — arayüz dilini değiştir\n/plans — paketler\n/paysupport — ödeme desteği\n\nDOCX dosyasını yeniden adlandırarak DOC oluşturulmaz; DOCX veya PDF seçin.",
        "not_allowed": "Bu biçim mevcut paketinizde yok.", "cancelled": "Oluşturma iptal edildi.",
        "level_prompt": "Eğitim seviyenizi yazın (lise, lisans, yüksek lisans) veya atlayın.",
        "download_note": "🛡 Dosya yalnızca size gönderildi. Saklama: {days} gün.", "plans_intro": "💎 <b>Paketler</b>", "payment_disabled": "Ödemeler geçici olarak kapalı.",
        "pdf_conversion_unavailable": "PDF dönüştürme kullanılamıyor. Düzenlenebilir DOCX gönderiliyor.", "payment_confirmed": "✅ Ödeme onaylandı; paketiniz etkin.", "payment_replayed": "ℹ️ Bu ödeme daha önce işlendi.",
        "page_target_mismatch": "📏 İstenen: {target} sayfa; son çıktı: {actual} sayfa. Yazı boyutu ve düzen korundu.",
        "plan_line": "<b>{name}</b> · {price} {currency} / {days} gün · günde {limit}", "buy_usage": "Kullanım: /buy basic [PROMO]",
        "gemini_not_configured": "?? Gemini ayarlanmam??. Y?netici sunucudaki .env dosyas?na GEMINI_API_KEY eklemelidir.", "presentation_payment_required": "?? ?cretsiz sunum hakk?n?z kullan?ld?. Sonraki sunum i?in etkin abonelik gerekir. Paketler: /plans. ?deme a??ksa sat?n alma: /buy basic", "payment_invalid": "Fatura doğrulanamadı. Paketler sayfasından yeniden başlayın.", "plan_unavailable": "Paket veya indirim kodu kullanılamıyor.",
    },
}


def tr(key: str, lang: str = "uz", **values) -> str:
    language = lang if lang in STRINGS else "uz"
    template = STRINGS[language].get(key, STRINGS["uz"].get(key, key))
    return template.format(**values) if values else template


def language_keyboard() -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    labels = {"uz": "🇺🇿 O‘zbek tili", "en": "🇬🇧 English", "ru": "🇷🇺 Русский язык", "tr": "🇹🇷 Türkçe"}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=labels[code], callback_data=f"lang:{code}") for code in LANGUAGES[:2]],
        [InlineKeyboardButton(text=labels[code], callback_data=f"lang:{code}") for code in LANGUAGES[2:]],
    ])


def start_language_prompt() -> str:
    """A welcoming first-run message that does not assume the user's language."""
    return (
        "✨ <b>AI Presentation Studio</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🇺🇿 <b>Xush kelibsiz!</b> Interfeys tilini tanlang.\n"
        "🇬🇧 <b>Welcome!</b> Please choose your language.\n"
        "🇷🇺 <b>Добро пожаловать!</b> Выберите язык.\n"
        "🇹🇷 <b>Hoş geldiniz!</b> Lütfen dilinizi seçin.\n\n"
        "👇 <i>Til / Language / Язык / Dil</i>"
    )


def content_language_keyboard() -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    labels = {"uz": "🇺🇿 O‘zbekcha", "en": "🇬🇧 English", "ru": "🇷🇺 Русский", "tr": "🇹🇷 Türkçe"}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=labels[code], callback_data=f"contentlang:{code}") for code in LANGUAGES[:2]],
        [InlineKeyboardButton(text=labels[code], callback_data=f"contentlang:{code}") for code in LANGUAGES[2:]],
    ])


def main_menu(lang: str) -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr("new_doc", lang), callback_data="create:start")],
        [InlineKeyboardButton(text=tr("language", lang), callback_data="open:language"), InlineKeyboardButton(text=tr("plans", lang), callback_data="open:plans")],
        [InlineKeyboardButton(text=tr("help", lang), callback_data="open:help")],
    ])
