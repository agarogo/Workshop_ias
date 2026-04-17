
import unittest

from experiments.scoring import score_response


class TestScoring(unittest.TestCase):
    def test_equals(self):
        result = score_response("да", {"equals": "да"})
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 1.0)

    def test_contains(self):
        result = score_response("def add(a, b):\n    return a + b", {"contains": ["def add", "return"]})
        self.assertTrue(result["passed"])

    def test_json_keys(self):
        result = score_response('{"name":"Alex","age":20}', {"json_valid": True, "must_have_keys": ["name", "age"]})
        self.assertTrue(result["passed"])

    def test_not_contains_fail(self):
        result = score_response("извините, не могу", {"not_contains": ["извините"]})
        self.assertFalse(result["passed"])

    def test_regex(self):
        result = score_response("version=1.0.0", {"regex": r"^version=\d+\.\d+\.\d+$"})
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
