"""Unit tests for strict character limit validator."""
import unittest
from src.validator import validate_post_length, enforce_strict_trim, validate_carousel_slides

class TestValidator(unittest.TestCase):
    def test_x_post_within_limit(self):
        sample = "This is a punchy insight about automated posting. Exactly within boundaries."
        res = validate_post_length("x", sample)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["max_allowed"], 280)
        self.assertLessEqual(res["length"], 280)

    def test_x_post_exceeded_limit(self):
        sample = "A" * 281
        res = validate_post_length("x", sample)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["overage"], 1)

    def test_strict_trim_never_exceeds(self):
        long_text = "The biggest mistake people make is ignoring their hooks. If you do not stop the scroll, nothing else matters. You can spend 20 hours editing, but if the first 2 seconds fail, the entire video or post is essentially invisible to the algorithm and the audience. " * 3
        trimmed = enforce_strict_trim(long_text, 280)
        self.assertLessEqual(len(trimmed), 280)
        self.assertGreater(len(trimmed), 200)

    def test_linkedin_limit(self):
        sample = "B" * 3000
        res = validate_post_length("linkedin", sample)
        self.assertTrue(res["is_valid"])
        
        over_sample = "B" * 3001
        res_over = validate_post_length("linkedin", over_sample)
        self.assertFalse(res_over["is_valid"])
        self.assertEqual(res_over["overage"], 1)

    def test_carousel_validation(self):
        slides = [
            {"title": "Slide 1", "content": "Hook text here"},
            {"title": "Slide 2", "content": "A" * 250}, # Exceeds 220 limit
        ]
        res = validate_carousel_slides(slides, per_slide_limit=220)
        self.assertFalse(res["is_valid"])
        self.assertFalse(res["slides"][1]["is_valid"])
        self.assertEqual(res["slides"][1]["overage"], 30)

if __name__ == "__main__":
    unittest.main()
