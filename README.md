# AI Presentation Studio

Modulli Telegram bot: foydalanuvchi buyruqlari, admin paneli, tariflar, kvotalar, obunalar va to‘lovlar alohida paketlarda joylashgan.

## Ishga tushirish

1. Python 3.12 o‘rnating.
2. `python -m venv .venv` va `.venv\Scripts\Activate.ps1` bajaring.
3. `pip install -r requirements.txt` bajaring.
4. `.env.example` faylini `.env` ga nusxalang va `BOT_TOKEN`, `ADMIN_IDS` ni kiriting.
5. `python -m app` ni ishga tushiring. SQLite bazasi va boshlang‘ich Free/Basic/Pro/Premium tariflari avtomatik tayyorlanadi.

## Modul tuzilmasi

- `app/bot/` — Telegram buyruqlari, foydalanuvchi va admin interfeyslari.
- `app/services/` — monetizatsiya, foydalanish kvotasi va obuna qoidalari.
- `app/payments/` — to‘lov adapterlari; Telegram Stars integratsiyasi.
- `app/storage/` — SQLite ulanishi va sxema migratsiyalari.
- `tests/` — asosiy ruxsat, kvota, rejim, audit va takroriy to‘lov testlari.
- `docs/` — arxitektura va pullik rejimga o‘tish.

Bu papkada avvalgi AI Presentation Studio kodi bolmagani uchun, hozir mavzudan AI kontent va PPTX/DOCX/PDF yaratadigan asosiy oqim qoshildi. Taqdimot matni Gemini API bilan; referat, test va boshqa materiallar OpenAI API bilan yaratiladi. Server `.env` faylida `GEMINI_API_KEY` va `OPENAI_API_KEY` ni sozlang. Birinchi taqdimot bepul, keyingisi faol obunani talab qiladi.

## Til va hujjat dizayni

Interfeys tillari: O‘zbekcha, English, Русский, Türkçe. Birinchi `/start` da til tanlanadi; keyin `/language` bilan almashtiriladi. Hujjat tili interfeys tilidan alohida tanlanadi. Material turi `/create` orqali tanlanib, mavzu, sahifa/slayd soni, format va matn hajmi yig‘iladi. Bosh menyu emojili inline tugmalar bilan berilgan; maxsus salomlashuv stikerini admin `/set_welcome_sticker` buyrug‘ini stickerga reply qilib yuborib sozlashi mumkin.

Referat DOCX uslublarida Times New Roman belgilanadi. PDF uchun serverda qonuniy Times New Roman font fayli bo‘lishi shart: `TIMES_NEW_ROMAN_REGULAR` va ixtiyoriy `TIMES_NEW_ROMAN_BOLD` ni `.env` da ko‘rsating. Word sahifalash o‘zgarishi mumkin; LibreOffice o‘rnatilgan bo‘lsa DOCX sahifalari o‘lchanadi va konvertatsiya qilinadi. DOC faqat haqiqiy konvertor orqali yaratilishi mumkin; hozir DOCX yoki PDF taklif qilinadi.

Super Admin ID raqamlari maxfiy `.env` ichidagi `SUPER_ADMIN_IDS` orqali boshqariladi; bir nechta ID vergul bilan ajratiladi. Super Admin tarif/obuna va tarif kvotalaridan ozod, foydalanish statistikasi esa odatdagidek qayd etiladi.

Admin generatsiya sozlamalari `/admin` → bot sozlamalari → `/setting KALIT QIYMAT` orqali o‘zgaradi. `enabled_languages`, `enabled_formats`, `free_formats`, `min_pages`, `max_pages`, `min_font_pt`, `max_font_pt`, `presentation_max_slides`, `file_retention_days` qo‘llanadi. Taqdimotning bepul soni `presentation_free_generations` sozlamasi bilan belgilanadi (standart 1).

## To‘lov siyosati

Bot ichida sotiladigan raqamli xizmatlar uchun Telegram Stars (`XTR`) ishlatiladi. `TELEGRAM_STARS_ENABLED=false` bo‘lsa, checkout boshlanmaydi. Obuna faqat Telegram yuborgan `successful_payment` update’dagi charge ID, invoice payload, foydalanuvchi va summa tekshirilgandan so‘ng faollashadi. Takroriy charge ID bazadagi noyob cheklov bilan himoyalangan. To‘lov bo‘yicha yordam `/paysupport`; admin tasdiqlangan Stars to‘lovini `/refund PAYMENT_ID` bilan qaytarishi mumkin.

Rasmiy hujjatlar: [Telegram Stars bilan raqamli mahsulotlar](https://core.telegram.org/bots/payments-stars), [Bot API](https://core.telegram.org/bots/api).

## Bepul rejimdan pullikka o‘tish

1. Botni `FREE` rejimida sozlang va `/admin` paneliga faqat ishonchli Telegram ID’larni `ADMIN_IDS` orqali kiriting.
2. Birinchi taqdimot bepul, keyingi taqdimotlar uchun faol obuna zarur. Admin panelida `presentation_free_generations` qiymatini tekshiring. Tariflarni boshqarish menyusida pullik tarif narxi va faol holatini sozlang.
3. `.env` da `TELEGRAM_STARS_ENABLED=true` ni yoqing, test botida Telegram Stars invoice va muvaffaqiyatli payment oqimini tekshiring.
4. Admin → Monetizatsiya → `FREEMIUM` ni tanlab tasdiqlang. `PAID_ONLY` uchun Stars checkout yoqilgan, tarif faol bo‘lishi shart.
5. `python -m unittest discover -s tests -v` bilan tekshiring.

Admin buyruqlari: `/user ID`, `/block ID`, `/unblock ID`, `/limit ID SON`, `/grant ID TARIF KUN`, `/cancel_sub OBUNA_ID`, `/price TARIF XTR_NARX`, `/plan_active TARIF on|off`, `/trial KUN [TARIF]`, `/promo KOD TARIF CHEGIRMA_FOIZ MAX_ISHLATISH`, `/refund PAYMENT_ID`, `/broadcast MATN`.

Narx yangilanishi mavjud payment yozuvlariga ta’sir qilmaydi. Production’da `BOT_TOKEN`, admin ID’lari va ma’lumotlar bazasi fayli uchun zaxira nusxa hamda server monitoringini sozlang. Hozirgi backend SQLite: bitta bot instansiyasi va yengil foydalanishga mo‘ljallangan; ko‘p instansiyali deploymentdan oldin PostgreSQL backendiga migratsiya tavsiya qilinadi.

## English

Install with `python -m venv .venv`, activate it, run `pip install -r requirements.txt`, copy `.env.example` to `.env`, set `BOT_TOKEN`, `ADMIN_IDS`, `GEMINI_API_KEY`, and `OPENAI_API_KEY`, then start with `python -m app`. The interface supports Uzbek, English, Russian, and Turkish. `/language` changes the interface; document language is selected independently in `/create`. DOCX reports use Times New Roman styles. Set `TIMES_NEW_ROMAN_REGULAR` (and optionally `TIMES_NEW_ROMAN_BOLD`) to licensed font files for PDF export. DOC is never a renamed DOCX; use DOCX/PDF. Admin generation limits use `/admin` → Bot settings → `/setting KEY VALUE`.

## Русский

Установите Python 3.12, создайте виртуальное окружение, выполните `pip install -r requirements.txt`, скопируйте `.env.example` в `.env`, задайте `BOT_TOKEN`, `ADMIN_IDS` и `OPENAI_API_KEY`, затем запустите `python -m app`. Интерфейс поддерживает узбекский, английский, русский и турецкий языки. `/language` меняет язык интерфейса; язык документа выбирается отдельно в `/create`. В стилях DOCX задаётся Times New Roman. Для PDF настройте пути к лицензированным файлам шрифта через `TIMES_NEW_ROMAN_REGULAR` и `TIMES_NEW_ROMAN_BOLD`. DOC не создаётся переименованием DOCX: доступны DOCX/PDF. Лимиты администратора находятся в `/admin` → настройки бота → `/setting KEY VALUE`.

## Türkçe

Python 3.12 kurun, sanal ortam oluşturun, `pip install -r requirements.txt` çalıştırın, `.env.example` dosyasını `.env` olarak kopyalayıp `BOT_TOKEN`, `ADMIN_IDS`, `GEMINI_API_KEY` ve `OPENAI_API_KEY` değerlerini ekleyin; ardından `python -m app` ile başlatın. Arayüz Özbekçe, İngilizce, Rusça ve Türkçe destekler. `/language` arayüz dilini değiştirir; belge dili `/create` içinde ayrıca seçilir. DOCX stillerinde Times New Roman kullanılır. PDF için lisanslı font dosyalarını `TIMES_NEW_ROMAN_REGULAR` ve `TIMES_NEW_ROMAN_BOLD` ile tanımlayın. DOC, DOCX dosyasının adını değiştirerek oluşturulmaz; DOCX/PDF seçin. Yönetim limitleri `/admin` → bot ayarları → `/setting KEY VALUE` ile değiştirilir.
# Taqdimot_bot
