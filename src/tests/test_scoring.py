import unittest

from src.experiments.scoring import score_response


class TestScoring(unittest.TestCase):
    def test_fibonacci_recursive_checks(self):
        response = """def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)
"""
        checks = {
            "response_not_empty": True,
            "contains": ["def fibonacci_recursive", "return"],
            "regex": [
                r"fibonacci_recursive\(n\s*-\s*1\)",
                r"fibonacci_recursive\(n\s*-\s*2\)",
            ],
            "max_length": 700,
        }
        result = score_response(response, checks)
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 1.0)

    def test_gcd_euclid_checks(self):
        response = """def gcd(a, b):
    while b:
        a, b = b, a % b
    return a
"""
        checks = {
            "response_not_empty": True,
            "contains": ["def gcd", "return"],
            "regex": [
                r"while\s+b\s*!=\s*0|while\s+b\s*:",
                r"a\s*,\s*b\s*=\s*b\s*,\s*a\s*%\s*b|a\s*=\s*b.*%.*b",
            ],
            "max_length": 500,
        }
        result = score_response(response, checks)
        self.assertTrue(result["passed"])

    def test_json_algorithm_checks(self):
        response = '{"problem":"weighted shortest path","algorithm":"dijkstra","reason":"works for non-negative edges","complexity":"O((V+E) log V)"}'
        checks = {
            "response_not_empty": True,
            "json_valid": True,
            "must_have_keys": ["problem", "algorithm", "reason", "complexity"],
            "max_length": 500,
        }
        result = score_response(response, checks)
        self.assertTrue(result["passed"])

    def test_pushkin_text_checks(self):
        response = (
            "Пушкин занимает ключевое место в истории русской литературы, потому что именно он "
            "сделал литературный язык более живым, точным и выразительным. Его произведения до сих пор "
            "влияют на писателей, читателей и школьную программу. В романе «Евгений Онегин» особенно "
            "хорошо видно, как он соединяет психологическую глубину, иронию и ясность формы. "
            "Пушкин показал, что русская литература может быть одновременно национальной и универсальной. "
            "Поэтому его часто считают отправной точкой для многих авторов XIX века."
        )
        checks = {
            "response_not_empty": True,
            "contains": ["Пушкин"],
            "regex": [r"Онегин|Капитанская дочка|Руслан и Людмила|Борис Годунов"],
            "min_length": 220,
            "max_length": 900,
        }
        result = score_response(response, checks)
        self.assertTrue(result["passed"])

    def test_stack_queue_checks(self):
        response = (
            "Стек и очередь отличаются порядком обработки элементов. "
            "Стек работает по принципу LIFO: последним пришёл — первым вышел, как стопка тарелок. "
            "Очередь работает по принципу FIFO: первым пришёл — первым вышел, как люди в кассу. "
            "Обе структуры полезны, но применяются в разных сценариях."
        )
        checks = {
            "response_not_empty": True,
            "contains": ["стек", "очередь"],
            "regex": [r"LIFO|последним приш", r"FIFO|первым приш"],
            "min_length": 180,
            "max_length": 700,
        }
        result = score_response(response, checks)
        self.assertTrue(result["passed"])

    def test_json_missing_key_fails(self):
        response = '{"problem":"weighted shortest path","algorithm":"dijkstra","reason":"works"}'
        checks = {
            "json_valid": True,
            "must_have_keys": ["problem", "algorithm", "reason", "complexity"],
        }
        result = score_response(response, checks)
        self.assertFalse(result["passed"])

    def test_max_length_fails(self):
        response = "a" * 1000
        checks = {
            "response_not_empty": True,
            "max_length": 100,
        }
        result = score_response(response, checks)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()