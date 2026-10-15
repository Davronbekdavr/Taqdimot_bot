import importlib.util
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.documents.generator import DocumentGenerator


REPORT={
    "title":"Water Management",
    "introduction":"An introduction to the subject.",
    "chapters":[{"heading":"Regional Context","body":"A meaningful chapter body."}],
    "conclusion":"A concise conclusion.",
    "bibliography":[],
}
PRESENTATION={"title":"Water Management","slides":[
    {"title":"Context","bullets":["Shared water systems","Regional cooperation"],"speaker_notes":"Introduce the subject."},
    {"title":"Next Steps","bullets":["Measure use","Share data"],"speaker_notes":"Summarize."},
]}


@unittest.skipUnless(importlib.util.find_spec("docx") and importlib.util.find_spec("pptx"), "install document dependencies from requirements.txt")
class OfficeDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.generator=DocumentGenerator(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_docx_is_real_and_styles_use_times_new_roman(self):
        path=self.generator.report_docx(REPORT,body_font_pt=14,language="en")
        self.assertTrue(zipfile.is_zipfile(path))
        with zipfile.ZipFile(path) as archive:
            styles=archive.read("word/styles.xml").decode("utf-8")
            document=archive.read("word/document.xml").decode("utf-8")
        self.assertGreaterEqual(styles.count("Times New Roman"),3)
        self.assertIn("TOC",document)
        self.assertIn("PAGE",document)

    def test_pptx_slide_count_matches_request_without_extra_cover_slide(self):
        from pptx import Presentation
        path=self.generator.presentation_pptx(PRESENTATION,"modern")
        self.assertTrue(zipfile.is_zipfile(path))
        self.assertEqual(len(Presentation(path).slides),2)


@unittest.skipUnless(importlib.util.find_spec("reportlab") and importlib.util.find_spec("pypdf") and os.getenv("TIMES_NEW_ROMAN_REGULAR"), "install PDF dependencies and configure the licensed Times New Roman font path")
class PdfDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.generator=DocumentGenerator(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_report_pdf_is_valid_and_returns_rendered_page_counts(self):
        from pypdf import PdfReader
        path,total,body=self.generator.report_pdf(REPORT,body_font_pt=14,language="en")
        self.assertGreaterEqual(total,1)
        self.assertGreaterEqual(body,1)
        self.assertEqual(len(PdfReader(str(path)).pages),total)


if __name__=="__main__": unittest.main()
