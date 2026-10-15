import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from app.bot.admin import is_admin
from app.services.billing import BillingError, BillingService
from app.security import is_admin_id, is_super_admin_id
from app.config import _telegram_ids
from app.storage.database import Database
from app.i18n.catalog import LANGUAGES, STRINGS, language_keyboard, start_language_prompt, tr
from app.services.content import content_schema, OpenAIContentGenerator
from app.services.gemini import GeminiPresentationGenerator


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(self.temp.name + "/test.sqlite3")
        self.db.initialize()
        self.billing = BillingService(self.db)
        self.billing.register_user(10, "student", "Student")

    def tearDown(self):
        self.temp.cleanup()

    def test_only_configured_admin_is_authorized(self):
        admins = frozenset({99})
        self.assertTrue(is_admin_id(99, admins))
        self.assertFalse(is_admin_id(10, admins))

    def test_super_admin_ids_parse_multiple_ids_and_ignore_invalid_values(self):
        with patch.dict("os.environ",{"SUPER_ADMIN_IDS":"8829196715, 12345,invalid,,"}):
            self.assertEqual(_telegram_ids("SUPER_ADMIN_IDS"),frozenset({8829196715,12345}))
        self.assertTrue(is_super_admin_id(8829196715,frozenset({8829196715})))
        self.assertFalse(is_super_admin_id(10,frozenset({8829196715})))

    def test_admin_access_uses_numeric_id_not_username(self):
        settings=SimpleNamespace(admin_ids=frozenset(),super_admin_ids=frozenset({8829196715}))
        real_admin=SimpleNamespace(from_user=SimpleNamespace(id=8829196715,username="ordinary_name"))
        fake_admin=SimpleNamespace(from_user=SimpleNamespace(id=10,username="8829196715"))
        self.assertTrue(is_admin(real_admin,settings))
        self.assertFalse(is_admin(fake_admin,settings))

    def test_super_admin_bypasses_tariff_features_formats_and_quotas(self):
        with self.db.connect() as con:
            con.execute("UPDATE plans SET features='',daily_limit=0,monthly_limit=0,max_slides=1,allow_pdf=0,allow_pptx=0,tests_limit=0,examples_limit=0 WHERE code='free'")
        with patch("app.services.billing.is_super_admin_id",return_value=True):
            usage=self.billing.reserve_usage(10,"tests",slides=99,output_format="pdf",usage_type="presentation")
        self.assertGreater(usage,0)

    def test_super_admin_can_use_without_subscription_in_paid_only_mode(self):
        self.billing.set_mode("PAID_ONLY",99,True)
        with patch("app.services.billing.is_super_admin_id",return_value=True):
            usage=self.billing.reserve_usage(10,"generate",usage_type="report")
        self.assertGreater(usage,0)

    def test_super_admin_still_respects_block_and_system_format_safety(self):
        with patch("app.services.billing.is_super_admin_id",return_value=True):
            with self.db.connect() as con: con.execute("UPDATE users SET is_blocked=1 WHERE telegram_id=10")
            with self.assertRaises(BillingError): self.billing.reserve_usage(10,"generate")
            with self.db.connect() as con:
                con.execute("UPDATE users SET is_blocked=0 WHERE telegram_id=10")
                con.execute("UPDATE system_settings SET value='pptx,docx' WHERE key='enabled_formats'")
            with self.assertRaises(BillingError): self.billing.reserve_usage(10,"generate",output_format="pdf")

    def test_free_limit_is_enforced_atomically(self):
        for _ in range(3):
            self.billing.reserve_usage(10, "generate")
        with self.assertRaises(BillingError):
            self.billing.reserve_usage(10, "generate")

    def test_concurrent_requests_do_not_exceed_free_quota(self):
        barrier = threading.Barrier(8)
        outcomes = []
        def request():
            barrier.wait()
            try:
                self.billing.reserve_usage(10, "generate")
                outcomes.append(True)
            except BillingError:
                outcomes.append(False)
        threads = [threading.Thread(target=request) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(outcomes), 3)

    def test_paid_mode_guard_and_audit(self):
        with self.assertRaises(BillingError):
            self.billing.set_mode("PAID_ONLY", 99, False)
        self.billing.set_mode("FREEMIUM", 99, False)
        self.assertEqual(self.billing.get_mode(), "FREEMIUM")
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM admin_audit_logs WHERE admin_id=99").fetchone()[0], 1)

    def test_mode_switch_preserves_user_data(self):
        self.billing.set_mode("FREEMIUM", 99, False)
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM users WHERE telegram_id=10").fetchone()[0], 1)

    def test_interface_language_persists_and_content_schemas_exist(self):
        self.billing.set_language(10,"ru")
        self.assertEqual(self.billing.get_language(10),"ru")
        self.assertEqual(set(LANGUAGES),{"uz","en","ru","tr"})
        self.assertEqual(set(STRINGS["uz"]),set(STRINGS["en"]))
        self.assertEqual(set(STRINGS["en"]),set(STRINGS["ru"]))
        self.assertEqual(set(STRINGS["ru"]),set(STRINGS["tr"]))
        self.assertIn("{target}",tr("ready","en"))
        self.assertEqual(content_schema("presentation")["properties"]["slides"]["type"],"array")
        self.assertEqual(content_schema("tests")["properties"]["questions"]["type"],"array")

    def test_first_start_greeting_offers_all_four_languages(self):
        prompt=start_language_prompt()
        self.assertIn("Xush kelibsiz",prompt)
        self.assertIn("Welcome",prompt)
        self.assertIn("Добро пожаловать",prompt)
        self.assertIn("Hoş geldiniz",prompt)
        labels={button.text for row in language_keyboard().inline_keyboard for button in row}
        self.assertEqual(len(labels),4)

    def test_download_records_are_owner_scoped(self):
        path=Path(self.temp.name)/"owned.docx"; path.write_bytes(b"sample")
        file_id=self.billing.store_generated_file(10,str(path),"owned.docx","docx",1,30)
        self.assertIsNotNone(self.billing.get_owned_file(file_id,10))
        self.assertIsNone(self.billing.get_owned_file(file_id,11))

    def test_usage_failure_releases_quota_and_migrations_are_repeatable(self):
        with self.db.connect() as con: con.execute("UPDATE users SET free_limit_override=1 WHERE telegram_id=10")
        first=self.billing.reserve_usage(10,"generate")
        self.billing.complete_usage(first,succeeded=False,tokens=12)
        second=self.billing.reserve_usage(10,"generate")
        self.billing.complete_usage(second,succeeded=True,tokens=20)
        self.db.initialize()
        stats=self.billing.stats()
        self.assertEqual(stats["generations"],1)
        self.assertEqual(stats["ai_errors"],1)
        self.assertEqual(stats["tokens"],32)

    def test_free_plan_rejects_pdf_format(self):
        with self.assertRaises(BillingError):
            self.billing.reserve_usage(10,"generate",output_format="pdf")

    def test_first_presentation_is_free_and_next_requires_subscription(self):
        first=self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
        self.billing.complete_usage(first,succeeded=True,tokens=20)
        with self.assertRaisesRegex(BillingError,"payment_required"):
            self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")

    def test_failed_first_presentation_does_not_consume_free_use(self):
        first=self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
        self.billing.complete_usage(first,succeeded=False)
        second=self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
        self.assertGreater(second,first)

    def test_first_free_presentation_is_not_blocked_by_other_material_daily_quota(self):
        for _ in range(3):
            self.billing.reserve_usage(10,"generate",usage_type="report")
        presentation=self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
        self.assertGreater(presentation,0)

    def test_paid_subscription_allows_later_presentation_even_in_free_mode(self):
        first=self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
        self.billing.complete_usage(first,succeeded=True)
        payload,amount,_=self.billing.create_invoice(10,"basic")
        self.billing.confirm_stars_payment(user_id=10,payload=payload,charge_id="presentation-sub",amount=amount,currency="XTR")
        paid=self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
        self.assertGreater(paid,first)

    def test_concurrent_first_presentations_only_reserve_one_free_generation(self):
        barrier=threading.Barrier(8); outcomes=[]
        def request():
            barrier.wait()
            try:
                self.billing.reserve_usage(10,"generate",slides=8,output_format="pptx",usage_type="presentation")
                outcomes.append("free")
            except BillingError as exc:
                outcomes.append(str(exc))
        threads=[threading.Thread(target=request) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(outcomes.count("free"),1)
        self.assertEqual(outcomes.count("payment_required"),7)

    def test_gemini_presentation_json_is_parsed_and_slide_count_checked(self):
        import json
        material={"title":"Water","slides":[{"title":f"Slide {i}","bullets":["Point"],"speaker_notes":"Notes"} for i in range(5)],"sources":["unverified"]}
        response={"candidates":[{"content":{"parts":[{"text":json.dumps(material)}]}}],"usageMetadata":{"totalTokenCount":123}}
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return json.dumps(response).encode()
        with patch("app.services.gemini.urlopen",return_value=FakeResponse()):
            result,tokens=GeminiPresentationGenerator(api_key="test").generate(kind="presentation",topic="Water",language="en",size=5)
        self.assertEqual(len(result["slides"]),5)
        self.assertEqual(result["sources"],[])
        self.assertEqual(tokens,123)
        response["candidates"][0]["content"]["parts"][0]["text"]=json.dumps({**material,"slides":material["slides"][:-1]})
        with patch("app.services.gemini.urlopen",return_value=FakeResponse()):
            with self.assertRaisesRegex(Exception,"slide_count_mismatch"):
                GeminiPresentationGenerator(api_key="test").generate(kind="presentation",topic="Water",language="en",size=5)

    def test_structured_quiz_response_is_accepted_and_unverified_sources_removed(self):
        model_output={"title":"Quiz","questions":[{"question":f"Q{i}","options":["A","B","C","D"],"answer":"A","explanation":"Reason"} for i in range(10)]}
        response={"output":[{"type":"message","content":[{"type":"output_text","text":__import__("json").dumps(model_output)}]}],"usage":{"total_tokens":321}}
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return __import__("json").dumps(response).encode()
        with patch("app.services.content.urlopen",return_value=FakeResponse()):
            result,tokens=OpenAIContentGenerator(api_key="test").generate(kind="tests",topic="Water",language="uz",size=10)
        self.assertEqual(len(result["questions"]),10)
        self.assertEqual(tokens,321)

    def test_report_drops_unverified_model_bibliography(self):
        model_output={"title":"Paper","introduction":"Intro","chapters":[{"heading":"H","body":"Body"}],"conclusion":"End","bibliography":["Imaginary source https://fake.invalid/ref"]}
        response={"output":[{"type":"message","content":[{"type":"output_text","text":__import__("json").dumps(model_output)}]},{"type":"web_search_call","action":{"sources":[{"url":"https://verified.example/source"}]}}]}
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return __import__("json").dumps(response).encode()
        with patch("app.services.content.urlopen",return_value=FakeResponse()):
            result,_=OpenAIContentGenerator(api_key="test").generate(kind="report",topic="Water",language="en",size=4)
        self.assertEqual(result["bibliography"],[])

    def test_unverified_or_mismatched_payment_cannot_activate(self):
        payload, amount, _ = self.billing.create_invoice(10, "basic")
        with self.assertRaises(BillingError):
            self.billing.confirm_stars_payment(user_id=10, payload=payload, charge_id="charge", amount=amount+1, currency="XTR")
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 0)

    def test_confirmed_payment_is_idempotent(self):
        payload, amount, _ = self.billing.create_invoice(10, "basic")
        self.assertTrue(self.billing.confirm_stars_payment(user_id=10,payload=payload,charge_id="unique-charge",amount=amount,currency="XTR"))
        self.assertFalse(self.billing.confirm_stars_payment(user_id=10,payload=payload,charge_id="unique-charge",amount=amount,currency="XTR"))
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0], 1)

    def test_promo_discount_is_recorded_and_single_use(self):
        self.billing.create_promo("STUDENT", "basic", 50, 10, 99)
        payload, amount, _ = self.billing.create_invoice(10, "basic", promo_code="student")
        self.assertEqual(amount, 50)
        with self.assertRaises(BillingError):
            self.billing.create_invoice(10, "basic", promo_code="STUDENT")
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM promo_redemptions WHERE user_id=10").fetchone()[0], 1)

    def test_trial_only_attaches_on_first_registration(self):
        self.billing.set_trial(7, "basic", 99)
        self.billing.register_user(11, "new", "New")
        self.billing.register_user(11, "new", "New")
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id=11 AND status='trial'").fetchone()[0], 1)

    def test_refund_cancels_subscription_and_audits(self):
        payload, amount, _ = self.billing.create_invoice(10, "basic")
        self.billing.confirm_stars_payment(user_id=10,payload=payload,charge_id="refund-charge",amount=amount,currency="XTR")
        with self.db.connect() as con:
            payment_id=con.execute("SELECT id FROM payments WHERE invoice_payload=?",(payload,)).fetchone()[0]
        self.assertEqual(self.billing.begin_refund(payment_id),(10,"refund-charge"))
        self.billing.finish_refund(payment_id,True,99)
        with self.db.connect() as con:
            self.assertEqual(con.execute("SELECT status FROM payments WHERE id=?",(payment_id,)).fetchone()[0],"refunded")
            self.assertEqual(con.execute("SELECT status FROM subscriptions WHERE payment_id=?",(payment_id,)).fetchone()[0],"cancelled")

    def test_expired_subscription_does_not_grant_paid_feature(self):
        payload, amount, _ = self.billing.create_invoice(10, "basic")
        self.billing.confirm_stars_payment(user_id=10,payload=payload,charge_id="charge",amount=amount,currency="XTR")
        with self.db.connect() as con:
            con.execute("UPDATE subscriptions SET ends_at='2000-01-01T00:00:00+00:00'")
        self.billing.set_mode("FREEMIUM", 99, False)
        with self.assertRaises(BillingError):
            self.billing.reserve_usage(10, "pdf")


if __name__ == "__main__":
    unittest.main()
