"""Tests for the deterministic journalism checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp_server.analysis import (  # noqa: E402
    analyze_prose,
    check_facts,
    check_quotes,
    compare_voice,
    diff_meaning,
)


class ProseAnalysisTests(unittest.TestCase):
    def test_flags_machine_phrasing_and_invented_interiority(self) -> None:
        text = (
            "In today's fast-paced world, the council plays a crucial role.\n\n"
            "She felt a wave of relief as the room fell silent."
        )
        result = analyze_prose(text)
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("ai-opener", rules)
        self.assertIn("invented-interiority", rules)
        self.assertIn("unsupported-scene", rules)
        self.assertGreaterEqual(result["severity_totals"]["high"], 2)
        self.assertNotIn(result["signal"], {"", None})

    def test_flags_unattributed_claims(self) -> None:
        result = analyze_prose("Experts say the program works. Studies show it helps.")
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("unsourced-attribution", rules)

    def test_flags_uniform_rhythm(self) -> None:
        sentence = "The council met on Monday to discuss the plan again today."
        result = analyze_prose(" ".join([sentence] * 10))
        rules = {finding["rule"] for finding in result["findings"]}
        self.assertIn("monotonous-rhythm", rules)
        self.assertEqual(result["stats"]["sentence_length_stdev"], 0.0)

    def test_reports_stats_and_disclaimer(self) -> None:
        result = analyze_prose("The council met on Monday. It approved the budget.")
        self.assertEqual(result["stats"]["sentences"], 2)
        self.assertIn("cannot verify", result["disclaimer"])

    def test_findings_are_capped_but_counts_complete(self) -> None:
        text = "It is important to note that this happened. " * 12
        result = analyze_prose(text, max_findings=3)
        self.assertLessEqual(len(result["findings"]), 3)
        self.assertGreater(result["finding_counts"]["slop-phrase"], 3)

    def test_voice_comparison_measures_both_texts(self) -> None:
        sample = "We walked home. It rained. Nobody minded much, honestly."
        draft = "The administration subsequently determined that the precipitation necessitated an adjustment."
        result = compare_voice(sample, draft)
        self.assertIn("deltas", result)
        self.assertGreater(result["draft"]["avg_sentence_words"], result["sample"]["avg_sentence_words"])
        self.assertTrue(result["notes"])

    def test_empty_text_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze_prose("   ")


class QuotationTests(unittest.TestCase):
    source = (
        "Marisol Reyes said: \"We will keep running the shuttle if the council releases the funds.\"\n"
        "She added that the pilot carried 120 students."
    )

    def test_exact_quote_is_found(self) -> None:
        draft = 'Reyes said, "We will keep running the shuttle if the council releases the funds."'
        result = check_quotes(draft, self.source)
        self.assertEqual(result["quotes"][0]["status"], "exact")
        self.assertEqual(result["summary"]["exact"], 1)

    def test_altered_quote_reports_difference(self) -> None:
        draft = 'Reyes said, "We will keep running the shuttle if the council finds the funds."'
        result = check_quotes(draft, self.source)
        quote = result["quotes"][0]
        self.assertEqual(quote["status"], "altered")
        self.assertTrue(quote["differences"])
        changed = " ".join(d["in_draft"] for d in quote["differences"])
        self.assertIn("finds", changed)

    def test_missing_quote_is_not_found_not_fabricated(self) -> None:
        draft = 'Reyes said, "The budget was approved unanimously by the board."'
        result = check_quotes(draft, self.source)
        self.assertEqual(result["quotes"][0]["status"], "not_found")
        self.assertIn("not evidence", result["handling"])
        self.assertIn("missing record", result["disclaimer"])

    def test_short_quotes_are_flagged(self) -> None:
        draft = 'One student said "it is hard" and left.'
        result = check_quotes(draft, 'A student said "it is hard" yesterday.')
        self.assertTrue(result["quotes"][0]["short"])

    def test_source_required(self) -> None:
        with self.assertRaises(ValueError):
            check_quotes('He said "x y z".', "")


class FactLocatorTests(unittest.TestCase):
    def test_number_absent_from_source_is_listed(self) -> None:
        result = check_facts("The pilot carried 120 students in Grade 11.", "The pilot carried many students.")
        self.assertIn("120", result["numbers_not_in_source"])
        self.assertIn("locator", result["handling"])

    def test_number_present_in_source_is_not_listed(self) -> None:
        result = check_facts("The pilot carried 120 students.", "Notes: 120 students joined the pilot.")
        self.assertNotIn("120", result["numbers_not_in_source"])

    def test_times_are_treated_as_numbers(self) -> None:
        result = check_facts("Dismissal moved to 4:30 p.m. on November 3.", "Dismissal moved to 4:30 p.m.")
        self.assertNotIn("4:30", result["numbers_not_in_source"])


class MeaningDiffTests(unittest.TestCase):
    original = (
        "The pilot carried 120 students. \"We will keep it,\" Reyes said. "
        "The change may affect commuters."
    )

    def test_lost_number_and_quote_raise_risk(self) -> None:
        edited = 'The pilot carried students. "We will keep it," Reyes said.'
        result = diff_meaning(self.original, edited)
        self.assertEqual(result["risk"], "high")
        self.assertIn("120", result["lost_numbers"])

    def test_unchanged_copy_is_low_risk(self) -> None:
        result = diff_meaning(self.original, self.original)
        self.assertEqual(result["risk"], "low")
        self.assertEqual(result["lost_numbers"], [])

    def test_lost_qualifier_is_reported(self) -> None:
        with_qualifier = "The change may affect commuters who wait at the gate every afternoon."
        without = "The change affects commuters who wait at the gate every afternoon."
        result = diff_meaning(with_qualifier, without)
        self.assertIn("qualifier_density", result)
        self.assertLess(result["qualifier_density"]["delta"], 0)


class FilipinoProseTests(unittest.TestCase):
    """The pattern lists must fire on Filipino/Tagalog drafts, not only English."""

    def test_flags_filipino_formulaic_opener_and_slop(self) -> None:
        text = (
            "Sa kasalukuyang panahon, ang proyekto ay nagsisilbing susi sa tagumpay. "
            "Mahalagang tandaan na hindi lamang ito proyekto kundi pati na rin pangako."
        )
        rules = {finding["rule"] for finding in analyze_prose(text)["findings"]}
        self.assertIn("ai-opener", rules)
        self.assertIn("slop-phrase", rules)

    def test_flags_filipino_invented_interiority_and_scene(self) -> None:
        text = (
            "Nakaramdam siya ng kaba habang naghihintay. "
            "Kumalabog ang kanyang puso at nanginginig ang kanyang boses. "
            "Biglang natahimik ang buong bulwagan."
        )
        rules = {finding["rule"] for finding in analyze_prose(text)["findings"]}
        self.assertIn("invented-interiority", rules)
        self.assertIn("invented-reaction", rules)
        self.assertIn("unsupported-scene", rules)

    def test_flags_filipino_unattributed_and_hedged_claims(self) -> None:
        text = (
            "Ayon sa mga eksperto, malaki ang naitulong ng programa. "
            "Sinasabi ng mga guro na maraming estudyante ang natulungan. "
            "Maaaring posibleng tumaas pa ito sa susunod na taon."
        )
        rules = {finding["rule"] for finding in analyze_prose(text)["findings"]}
        self.assertIn("unsourced-attribution", rules)
        self.assertIn("hedge-stack", rules)
        self.assertIn("vague-quantifier", rules)

    def test_lost_filipino_qualifier_is_reported(self) -> None:
        with_qualifier = "Maaaring maapektuhan ang mga mag-aaral na naghihintay sa gate tuwing hapon."
        without = "Maapektuhan ang mga mag-aaral na naghihintay sa gate tuwing hapon."
        result = diff_meaning(with_qualifier, without)
        self.assertLess(result["qualifier_density"]["delta"], 0)
        self.assertEqual(result["qualifier_density"]["edited"], 0.0)

    def test_filipino_stopwords_are_not_reported_as_names(self) -> None:
        result = check_facts("Ayon Sa Mga Eksperto, tumaas ang presyo ng bigas.", "Tumaas ang presyo ng bigas.")
        self.assertEqual(result["names_not_in_source"], [])


if __name__ == "__main__":
    unittest.main()
