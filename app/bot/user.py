import asyncio
import random
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, PreCheckoutQuery, FSInputFile

from app.documents.generator import DocumentError, DocumentGenerator
from app.i18n.catalog import LANGUAGES, content_language_keyboard, language_keyboard, main_menu, start_language_prompt, tr
from app.payments.telegram_stars import TelegramStarsAdapter
from app.services.billing import BillingError, BillingService
from app.services.content import ContentError, OpenAIContentGenerator
from app.services.gemini import GeminiPresentationGenerator

router = Router(name="user")


class CreateFlow(StatesGroup):
    choose_type = State()
    choose_content_language = State()
    topic = State()
    slides = State()
    pages = State()
    page_scope = State()
    font_size = State()
    output_format = State()
    education = State()
    cover = State()
    design = State()


def get_lang(db, user_id: int) -> str:
    return BillingService(db).get_language(user_id)


def type_keyboard(lang: str) -> InlineKeyboardMarkup:
    t=lambda key: tr(key,lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("presentation"),callback_data="create:type:presentation")],
        [InlineKeyboardButton(text=t("report"),callback_data="create:type:report")],
        [InlineKeyboardButton(text=t("document"),callback_data="create:type:document")],
        [InlineKeyboardButton(text=t("tests"),callback_data="create:type:tests"),InlineKeyboardButton(text=t("samples"),callback_data="create:type:samples")],
    ])


def simple_choice(prefix: str, values: list[tuple[str,str]], lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label,callback_data=f"{prefix}:{value}") for value,label in values]])


async def show_home(message: Message, db, settings, language_picker: bool = False):
    billing=BillingService(db); lang=billing.get_language(message.from_user.id)
    configured=billing.get_setting("welcome_sticker_file_ids")
    stickers=[value.strip() for value in configured.replace("\n",",").split(",") if value.strip()]
    legacy=billing.get_setting("welcome_sticker_file_id") or settings.welcome_sticker_file_id
    if legacy and legacy not in stickers: stickers.append(legacy)
    if stickers:
        try: await message.answer_sticker(random.choice(stickers))
        except Exception: pass
    if language_picker or not billing.language_selected(message.from_user.id):
        await message.answer(start_language_prompt(),reply_markup=language_keyboard(),parse_mode="HTML")
        return
    await message.answer(tr("welcome",lang),reply_markup=main_menu(lang),parse_mode="HTML")


@router.message(CommandStart())
async def start(message: Message, db, settings):
    telegram_lang=(message.from_user.language_code or "uz").lower().split("-")[0]
    if telegram_lang not in LANGUAGES: telegram_lang="uz"
    billing=BillingService(db)
    billing.register_user(message.from_user.id,message.from_user.username,message.from_user.first_name,telegram_lang)
    await show_home(message,db,settings)


@router.callback_query(F.data.startswith("lang:"))
async def choose_ui_language(callback: CallbackQuery, db):
    language=callback.data.split(":",1)[1]
    if language not in LANGUAGES:
        await callback.answer("Invalid language",show_alert=True); return
    if language not in BillingService(db).get_setting("enabled_languages").split(","):
        await callback.answer("This language is temporarily disabled.",show_alert=True); return
    billing=BillingService(db); billing.set_language(callback.from_user.id,language)
    await callback.message.edit_text(tr("welcome",language),reply_markup=main_menu(language),parse_mode="HTML")
    await callback.answer(tr("language_saved",language))


@router.callback_query(F.data=="open:language")
async def language_menu(callback: CallbackQuery, db):
    lang=get_lang(db,callback.from_user.id)
    await callback.message.edit_text(tr("choose_language",lang),reply_markup=language_keyboard())
    await callback.answer()


@router.callback_query(F.data=="open:help")
async def help_menu(callback: CallbackQuery, db):
    lang=get_lang(db,callback.from_user.id)
    await callback.message.edit_text(tr("help_text",lang),reply_markup=main_menu(lang))
    await callback.answer()


@router.message(Command("language", "lang"))
async def language_command(message: Message, db):
    await message.answer(tr("choose_language",get_lang(db,message.from_user.id)),reply_markup=language_keyboard())


@router.message(Command("help"))
async def help_command(message: Message, db):
    await message.answer(tr("help_text",get_lang(db,message.from_user.id)),reply_markup=main_menu(get_lang(db,message.from_user.id)))


@router.callback_query(F.data=="open:plans")
async def plans_button(callback: CallbackQuery, db):
    await send_plans(callback.message,db,get_lang(db,callback.from_user.id))
    await callback.answer()


@router.message(Command("plans"))
async def plans_command(message: Message, db):
    await send_plans(message,db,get_lang(db,message.from_user.id))


async def send_plans(message: Message, db, lang: str):
    with db.connect() as con:
        rows=con.execute("SELECT code,name,price,currency,duration_days,daily_limit FROM plans WHERE is_active=1 ORDER BY price").fetchall()
    if not rows: await message.answer("No active plans."); return
    lines=[tr("plan_line",lang,name=r['name'],price=r['price'],currency=r['currency'],days=r['duration_days'],limit=r['daily_limit'] if r['daily_limit'] is not None else "∞") for r in rows]
    await message.answer(tr("plans_intro",lang)+"\n\n"+"\n".join(lines)+"\n\n/buy basic",parse_mode="HTML")


@router.message(Command("buy"))
async def buy(message: Message, db, settings):
    lang=get_lang(db,message.from_user.id)
    if not settings.telegram_stars_enabled:
        await message.answer(tr("payment_disabled",lang)); return
    args=(message.text or "").split(maxsplit=2)
    if len(args)<2: await message.answer(tr("buy_usage",lang)); return
    adapter=TelegramStarsAdapter(BillingService(db),settings.telegram_stars_enabled,settings.payment_test_mode)
    try: payload,amount,name=adapter.create_invoice(message.from_user.id,args[1].lower(),args[2] if len(args)>2 else None)
    except BillingError: await message.answer(tr("plan_unavailable",lang)); return
    await message.answer_invoice(title=name,description=f"{name} subscription",payload=payload,provider_token="",currency="XTR",prices=[LabeledPrice(label=name,amount=amount)])


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, db):
    with db.connect() as con:
        payment=con.execute("SELECT * FROM payments WHERE invoice_payload=? AND user_id=? AND status='pending'",(query.invoice_payload,query.from_user.id)).fetchone()
    valid=payment and payment["amount"]==query.total_amount and payment["currency"]==query.currency=="XTR"
    lang=BillingService(db).get_language(query.from_user.id)
    await query.answer(ok=bool(valid),error_message=None if valid else tr("payment_invalid",lang))


@router.message(F.successful_payment)
async def successful_payment(message: Message, db):
    payment=message.successful_payment
    try:
        settled=TelegramStarsAdapter(BillingService(db),True,True).confirm(user_id=message.from_user.id,payload=payment.invoice_payload,charge_id=payment.telegram_payment_charge_id,amount=payment.total_amount,currency=payment.currency)
        lang=get_lang(db,message.from_user.id)
        await message.answer(tr("payment_confirmed",lang) if settled else tr("payment_replayed",lang))
    except BillingError:
        lang=get_lang(db,message.from_user.id); await message.answer("Payment validation failed. Use /paysupport.")


@router.message(Command("paysupport"))
async def paysupport(message: Message, db):
    lang=get_lang(db,message.from_user.id)
    text={"uz":"To‘lov yordami uchun administratorga chek va tranzaksiya sanasini yuboring.","en":"Send the receipt and transaction date to the administrator for payment help.","ru":"Для помощи с оплатой отправьте администратору чек и дату транзакции.","tr":"Ödeme yardımı için makbuzu ve işlem tarihini yöneticiye gönderin."}[lang]
    await message.answer(text)


async def begin_create(message: Message, state: FSMContext, db):
    await state.clear(); await state.set_state(CreateFlow.choose_type)
    await message.answer(tr("choose_type",get_lang(db,message.from_user.id)),reply_markup=type_keyboard(get_lang(db,message.from_user.id)))


@router.message(Command("create"))
async def create_command(message: Message, state: FSMContext, db):
    await begin_create(message,state,db)


@router.callback_query(F.data=="create:start")
async def create_button(callback: CallbackQuery, state: FSMContext, db):
    await state.clear(); await state.set_state(CreateFlow.choose_type)
    lang=get_lang(db,callback.from_user.id)
    await callback.message.edit_text(tr("choose_type",lang),reply_markup=type_keyboard(lang)); await callback.answer()


@router.callback_query(CreateFlow.choose_type,F.data.startswith("create:type:"))
async def choose_type(callback: CallbackQuery, state: FSMContext, db):
    kind=callback.data.split(":")[-1]
    if kind not in {"presentation","report","document","tests","samples"}:
        await callback.answer("Unknown material type",show_alert=True); return
    await state.update_data(kind=kind); await state.set_state(CreateFlow.choose_content_language)
    await callback.message.edit_text(tr("choose_content_language",get_lang(db,callback.from_user.id)),reply_markup=content_language_keyboard()); await callback.answer()


@router.callback_query(CreateFlow.choose_content_language,F.data.startswith("contentlang:"))
async def choose_content_language(callback: CallbackQuery, state: FSMContext, db):
    content_lang=callback.data.split(":")[-1]
    if content_lang not in LANGUAGES: await callback.answer("Invalid language",show_alert=True); return
    if content_lang not in BillingService(db).get_setting("enabled_languages").split(","):
        await callback.answer("This content language is temporarily disabled.",show_alert=True); return
    await state.update_data(content_language=content_lang); await state.set_state(CreateFlow.topic)
    await callback.message.edit_text(tr("topic",get_lang(db,callback.from_user.id)),parse_mode="HTML"); await callback.answer()


@router.message(CreateFlow.topic)
async def receive_topic(message: Message, state: FSMContext, db):
    topic=(message.text or "").strip(); lang=get_lang(db,message.from_user.id)
    if len(topic)<5 or len(topic)>300: await message.answer(tr("bad_topic",lang)); return
    await state.update_data(topic=topic)
    data=await state.get_data()
    if data["kind"]=="presentation":
        await state.set_state(CreateFlow.slides)
        maximum=int(BillingService(db).get_setting("presentation_max_slides") or "20")
        await message.answer(tr("slides",lang)+f" (5–{maximum})")
    elif data["kind"] in {"report","document","samples"}:
        await state.set_state(CreateFlow.pages)
        billing=BillingService(db); minimum=int(billing.get_setting("min_pages") or "1"); maximum=int(billing.get_setting("max_pages") or "50")
        await message.answer(tr("pages",lang)+f" ({minimum}–{maximum})")
    else:
        await state.update_data(size=10); await ask_format(message,state,lang)


@router.message(CreateFlow.slides)
async def receive_slides(message: Message, state: FSMContext, db):
    billing=BillingService(db); value=(message.text or "").strip(); maximum=int(billing.get_setting("presentation_max_slides") or "20")
    if not value.isdigit() or not 5<=int(value)<=maximum: await message.answer(tr("bad_number",get_lang(db,message.from_user.id),low=5,high=maximum)); return
    await state.update_data(size=int(value)); await state.set_state(CreateFlow.design)
    lang=get_lang(db,message.from_user.id)
    keyboard=simple_choice("design",[("modern",tr("design_modern",lang)),("academic",tr("design_academic",lang)),("minimal",tr("design_minimal",lang))],lang)
    await message.answer(tr("design",lang),reply_markup=keyboard)


@router.callback_query(CreateFlow.design,F.data.startswith("design:"))
async def receive_design(callback: CallbackQuery,state: FSMContext,db):
    await state.update_data(design=callback.data.split(":",1)[1]); await ask_format(callback.message,state,get_lang(db,callback.from_user.id)); await callback.answer()


@router.message(CreateFlow.pages)
async def receive_pages(message: Message,state: FSMContext,db):
    billing=BillingService(db); raw=(message.text or "").strip(); low=int(billing.get_setting("min_pages") or "1"); high=int(billing.get_setting("max_pages") or "50")
    if not raw.isdigit() or not low<=int(raw)<=high: await message.answer(tr("bad_number",get_lang(db,message.from_user.id),low=low,high=high)); return
    await state.update_data(size=int(raw)); await state.set_state(CreateFlow.page_scope)
    lang=get_lang(db,message.from_user.id); kb=simple_choice("scope",[("main",tr("main_pages",lang)),("whole",tr("all_pages",lang))],lang)
    await message.answer(tr("page_scope",lang),reply_markup=kb)


@router.callback_query(CreateFlow.page_scope,F.data.startswith("scope:"))
async def receive_scope(callback: CallbackQuery,state: FSMContext,db):
    await state.update_data(page_scope=callback.data.split(":",1)[1]); await state.set_state(CreateFlow.font_size)
    await callback.message.answer(tr("font_size",get_lang(db,callback.from_user.id))); await callback.answer()


@router.message(CreateFlow.font_size)
async def receive_font_size(message: Message,state: FSMContext,db):
    billing=BillingService(db); raw=(message.text or "").strip(); low=int(billing.get_setting("min_font_pt") or "10"); high=int(billing.get_setting("max_font_pt") or "16")
    if not raw.isdigit() or not low<=int(raw)<=high: await message.answer(tr("bad_number",get_lang(db,message.from_user.id),low=low,high=high)); return
    await state.update_data(font_size=int(raw)); await ask_format(message,state,get_lang(db,message.from_user.id))


async def ask_format(message: Message,state: FSMContext,lang: str):
    data=await state.get_data(); kind=data.get("kind")
    if kind=="presentation": options=[("pptx","📊 PPTX"),("pdf","📕 PDF")]
    elif kind=="tests": options=[("docx","📝 DOCX"),("pdf","📕 PDF")]
    else: options=[("docx","📝 DOCX"),("pdf","📕 PDF")]
    await state.set_state(CreateFlow.output_format)
    await message.answer(tr("format",lang),reply_markup=simple_choice("format",options,lang))


@router.callback_query(CreateFlow.output_format,F.data.startswith("format:"))
async def receive_format(callback: CallbackQuery,state: FSMContext,db,settings):
    file_format=callback.data.split(":",1)[1]
    if file_format not in {"pptx","docx","pdf"}: await callback.answer("Unsupported format",show_alert=True); return
    await state.update_data(output_format=file_format)
    data=await state.get_data(); lang=get_lang(db,callback.from_user.id)
    if data.get("kind") in {"report","document","samples"}:
        await state.set_state(CreateFlow.education); await callback.message.answer(tr("level_prompt",lang),reply_markup=skip_keyboard(lang))
    else:
        await callback.answer()
        await callback.message.answer(tr("working",lang)); await run_generation(callback,state,db,lang,settings)
        return
    await callback.answer()


def skip_keyboard(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr("skip",lang),callback_data="create:skip")]])


@router.callback_query(F.data=="create:skip")
async def skip_optional(callback: CallbackQuery,state: FSMContext,db,settings):
    current=await state.get_state(); lang=get_lang(db,callback.from_user.id)
    if current==CreateFlow.education.state:
        await state.update_data(education_level=""); await state.set_state(CreateFlow.cover)
        await callback.message.answer(tr("cover",lang),reply_markup=skip_keyboard(lang))
    elif current==CreateFlow.cover.state:
        await state.update_data(cover_details=""); await callback.answer()
        await callback.message.answer(tr("working",lang)); await run_generation(callback,state,db,lang,settings)
        return
    await callback.answer()


@router.message(CreateFlow.education)
async def receive_education(message: Message,state: FSMContext,db):
    await state.update_data(education_level=(message.text or "").strip()[:120]); await state.set_state(CreateFlow.cover)
    lang=get_lang(db,message.from_user.id); await message.answer(tr("cover",lang),reply_markup=skip_keyboard(lang))


@router.message(CreateFlow.cover)
async def receive_cover(message: Message,state: FSMContext,db,settings):
    await state.update_data(cover_details=(message.text or "").strip()[:1000]); lang=get_lang(db,message.from_user.id)
    await message.answer(tr("working",lang)); await run_generation(message,state,db,lang,settings)


async def run_generation(event,state: FSMContext,db,ui_lang: str,settings):
    user_id=event.from_user.id; billing=BillingService(db); data=await state.get_data()
    kind=data["kind"]; requested_feature={"tests":"tests","samples":"examples"}.get(kind,"generate")
    content_kind="tests" if kind=="tests" else "presentation" if kind=="presentation" else "report"
    try:
        reservation=billing.reserve_usage(user_id,requested_feature,slides=data.get("size") if kind=="presentation" else None,output_format=data["output_format"],usage_type=kind)
    except BillingError as exc:
        if str(exc)=="payment_required":
            await _reply(event,tr("presentation_payment_required",ui_lang))
        else:
            await _reply(event,tr("not_allowed",ui_lang))
        await state.clear(); return
    generated=[]
    try:
        generator=(GeminiPresentationGenerator(api_key=settings.gemini_api_key,model=settings.gemini_model)
                   if content_kind=="presentation" else OpenAIContentGenerator(api_key=settings.openai_api_key,model=settings.openai_model))
        gen_args=dict(kind=content_kind,topic=data["topic"],language=data["content_language"],size=data.get("size",10),font_size=data.get("font_size",14),education_level=data.get("education_level",""),cover_details=data.get("cover_details",""),design=data.get("design","modern"),page_scope=data.get("page_scope","main"))
        material,tokens=await asyncio.to_thread(generator.generate,**gen_args)
        docs=DocumentGenerator(settings.output_dir)
        actual_pages=None; file_page_count=None
        if content_kind=="presentation":
            if data["output_format"]=="pptx": path=await asyncio.to_thread(docs.presentation_pptx,material,data.get("design","modern"))
            else: path,actual_pages=await asyncio.to_thread(docs.presentation_pdf,material,data.get("design","modern")); file_page_count=actual_pages
        elif content_kind=="tests":
            path=await asyncio.to_thread(docs.tests_docx,material,data["content_language"])
            if data["output_format"]=="pdf":
                converted=await asyncio.to_thread(docs.libreoffice_pdf,path)
                if converted: path,actual_pages=converted; file_page_count=actual_pages
                else:
                    data["output_format"]="docx"; await _reply(event,tr("pdf_conversion_unavailable",ui_lang))
        elif data["output_format"]=="pdf":
            try:
                path,all_pages,body_pages=await asyncio.to_thread(docs.report_pdf,material,body_font_pt=data.get("font_size",14),cover_details=data.get("cover_details",""),language=data["content_language"])
                file_page_count=all_pages; actual_pages=body_pages if data.get("page_scope")=="main" else all_pages
                if actual_pages!=data.get("size"):
                    prior_path=path
                    gen_args.update(revision_feedback=f"The rendered document has {actual_pages} pages in the requested counting scope; target is {data['size']}. Adjust substantive material to approach the target without filler.",existing_material=material)
                    revised,more_tokens=await asyncio.to_thread(generator.generate,**gen_args)
                    new_path,new_all,new_body=await asyncio.to_thread(docs.report_pdf,revised,body_font_pt=data.get("font_size",14),cover_details=data.get("cover_details",""),language=data["content_language"])
                    prior_path.unlink(missing_ok=True); path=new_path; material=revised
                    file_page_count=new_all; actual_pages=new_body if data.get("page_scope")=="main" else new_all
                    tokens=(tokens or 0)+(more_tokens or 0)
            except DocumentError as exc:
                if "times_new_roman_" not in str(exc): raise
                path=await asyncio.to_thread(docs.report_docx,material,body_font_pt=data.get("font_size",14),cover_details=data.get("cover_details",""),language=data["content_language"])
                data["output_format"]="docx"
                await _reply(event,tr("pdf_unavailable",ui_lang))
        else:
            path=await asyncio.to_thread(docs.report_docx,material,body_font_pt=data.get("font_size",14),cover_details=data.get("cover_details",""),language=data["content_language"])
            converted=await asyncio.to_thread(docs.libreoffice_pdf,path)
            if converted:
                actual_pages=converted[1]; file_page_count=actual_pages; Path(converted[0]).unlink(missing_ok=True)
                if data.get("page_scope")=="whole" and actual_pages and actual_pages!=data.get("size"):
                    gen_args.update(revision_feedback=f"The rendered whole document has {actual_pages} pages; target is {data['size']}. Adjust substantive material without filler.",existing_material=material)
                    revised,more_tokens=await asyncio.to_thread(generator.generate,**gen_args)
                    revised_path=await asyncio.to_thread(docs.report_docx,revised,body_font_pt=data.get("font_size",14),cover_details=data.get("cover_details",""),language=data["content_language"])
                    path.unlink(missing_ok=True); path=revised_path; material=revised; tokens=(tokens or 0)+(more_tokens or 0)
                    converted=await asyncio.to_thread(docs.libreoffice_pdf,path)
                    if converted:
                        actual_pages=converted[1]; file_page_count=actual_pages; Path(converted[0]).unlink(missing_ok=True)
        generated.append(path)
        ext=data["output_format"]
        from app.documents.generator import safe_filename
        display_name=f"{safe_filename(material['title'])}.{ext}"
        retention=int(billing.get_setting("file_retention_days") or "30")
        file_id=billing.store_generated_file(user_id,str(path.resolve()),display_name,ext,file_page_count,retention)
        file_record=billing.get_owned_file(file_id,user_id)
        if not file_record or not Path(file_record["file_path"]).is_file(): raise DocumentError("generated_file_missing")
        target_message=event.message if isinstance(event,CallbackQuery) else event
        await target_message.answer_document(FSInputFile(file_record["file_path"],filename=display_name),caption=tr("download_note",ui_lang,days=retention))
        if content_kind=="presentation": await _reply(event,tr("ready",ui_lang,target=data["size"],actual=actual_pages if actual_pages is not None else "—"))
        elif ext=="docx":
            await _reply(event,tr("ready_docx",ui_lang))
            if data.get("page_scope")=="whole" and actual_pages and actual_pages!=data.get("size"):
                await _reply(event,tr("page_target_mismatch",ui_lang,target=data["size"],actual=actual_pages))
        elif actual_pages is not None:
            await _reply(event,tr("ready",ui_lang,target=data.get("size","—"),actual=actual_pages))
            if data.get("size") and actual_pages!=data["size"]:
                await _reply(event,tr("page_target_mismatch",ui_lang,target=data["size"],actual=actual_pages))
        billing.complete_usage(reservation,succeeded=True,tokens=tokens)
    except (ContentError,DocumentError,Exception) as exc:
        billing.complete_usage(reservation,succeeded=False)
        if isinstance(exc,ContentError) and str(exc)=="missing_gemini_api_key": response=tr("gemini_not_configured",ui_lang)
        elif isinstance(exc,ContentError) and str(exc)=="missing_api_key": response=tr("ai_not_configured",ui_lang)
        else: response=tr("failed",ui_lang)
        await _reply(event,response)
    finally:
        await state.clear()


async def _reply(event,text: str):
    if isinstance(event,CallbackQuery): await event.message.answer(text)
    else: await event.answer(text)


@router.message(Command("cancel"))
async def cancel(message: Message,state: FSMContext,db):
    await state.clear(); await message.answer(tr("cancelled",get_lang(db,message.from_user.id)))
