# Arxitektura va cheklovlar

`app/services/gemini.py` Gemini `generateContent` REST API orqali faqat taqdimot matnini yaratadi. `app/services/content.py` OpenAI Responses API orqali referat, hujjat, test va namunalarni yaratadi. `app/documents/generator.py` PPTX hamda DOCX/PDF fayllarni yaratadi. Har bir fayl egasi bilan saqlanadi va faqat shu foydalanuvchiga yuboriladi.

Har bir generatsiyadan oldin `BillingService.reserve_usage()` kvotani atomar band qiladi; muvaffaqiyatda `complete_usage()` chaqiriladi. Birinchi taqdimot bepul va bir marta beriladi. Sukutdagi qiymat `presentation_free_generations=1`; admin `/setting presentation_free_generations SON` bilan boshqaradi. Muvaffaqiyatsiz generatsiya bepul urinishni sarflamaydi. Parallel sorovlar tranzaksiya bilan himoyalangan. Keyingi taqdimot uchun faol obuna talab qilinadi. Tasdiqlangan obuna `FREE` rejimida ham taqdimot yaratishga ruxsat beradi.

Har bir generatsiyadan oldin `BillingService.reserve_usage()` kvotani tekshirib atomar band qiladi; API va render muvaffaqiyatli tugaganda `complete_usage()` chaqiriladi. Muvaffaqiyatsiz band qilish kvotada qolmaydi. Taqdimot slaydlari soni va eksport formati server tomonida tekshiriladi.

Bot raqamli mahsulot sotgani uchun ichki checkout faqat Telegram Stars `XTR` asosida tuzilgan. Test/live farqi `PAYMENT_TEST_MODE` audit metama’lumoti hamda ishlatiladigan Telegram bot tokeni bilan boshqariladi. Haqiqiy sinov to‘lovlari uchun BotFather test muhitidan olingan alohida token ishlatiladi. `.env` maxfiy ma’lumotlarini repoga commit qilmang.

Hozirgi saqlash qatlami SQLite’da tranzaksiyalarni `BEGIN IMMEDIATE` bilan seriallashtiradi. Bitta bot nusxasi uchun mos. Bir nechta worker yoki yuqori trafik kerak bo‘lsa, shu repository/service interfeysini PostgreSQL’ga ko‘chirish zarur.

Super Admin ID lari `SUPER_ADMIN_IDS` konfiguratsiyasidan olinadi. `BillingService.reserve_usage()` serverdagi Telegram ID ni tekshiradi va Super Admin uchun reja, obuna, funksiya hamda tarif kvota cheklovlarini chetlab otadi. Foydalanish yozuvlari saqlanadi; bloklangan holat va texnik format cheklovlari baribir ishlaydi. Admin router har bir command hamda callbackda ID ni qayta tekshiradi.
