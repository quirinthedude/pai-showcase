import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from core.database import open_db, rebuild_fts
from core.rag import QueryPlan, assess_evidence, build_fts_query, build_query_plan, retrieve


class RagTests(unittest.TestCase):
    def test_build_query_plan_extracts_phrases_and_filters_common_question_words(self):
        plan = build_query_plan('"our control" what is in our control?')

        self.assertEqual(plan.phrases, ["our control"])
        self.assertEqual(plan.terms, ["our", "control"])

    def test_build_fts_query_uses_exact_phrase_with_term_fallback(self):
        plan = QueryPlan(
            raw_query='"our control"',
            phrases=["our control"],
            terms=["our", "control"],
        )

        self.assertEqual(build_fts_query(plan), '"our control" OR (our AND control)')

    def test_assess_evidence_requires_quoted_phrase_to_match(self):
        contexts = [{"text": "Foo appears in this chunk, and bar appears later in the same chunk."}]

        self.assertEqual(assess_evidence('"foo bar"', contexts), "WEAKLY_GROUNDED")

    def test_assess_evidence_accepts_exact_quoted_phrase(self):
        contexts = [{"text": "This chunk directly discusses foo bar as a combined phrase."}]

        self.assertEqual(assess_evidence('"foo bar"', contexts), "GROUNDED")

    def test_assess_evidence_refuses_context_without_overlap(self):
        contexts = [{"text": "Some things are in our control and others are not."}]

        self.assertEqual(assess_evidence("chocolate cake recipe", contexts), "INSUFFICIENT_CONTEXT")

    def test_retrieve_ranks_exact_phrase_above_loose_term_match(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            con = open_db(Path(tmp_dir) / "showcase.db")
            with contextlib.redirect_stdout(io.StringIO()):
                rebuild_fts(
                    con,
                    [
                        {
                            "doc_title": "Loose Match",
                            "source": "test",
                            "path": "loose.md",
                            "text": (
                                "Our attention matters when we think about "
                                "control and judgment."
                            ),
                        },
                        {
                            "doc_title": "Exact Match",
                            "source": "test",
                            "path": "exact.md",
                            "text": "Some things are in our control and others are not.",
                        },
                    ],
                )

            _, contexts = retrieve(con, '"our control"', k=2)
            con.close()

        self.assertEqual(
            [context["doc_title"] for context in contexts],
            ["Exact Match", "Loose Match"],
        )


if __name__ == "__main__":
    unittest.main()
