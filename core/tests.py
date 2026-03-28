from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import LearningWord, UserImprovement, UserWordProgress
from .totp import generate_totp_code


class AdminLoginTotpTests(TestCase):
    @override_settings(
        ADMIN_ACCESS_EMAIL="enricosaccon96@gmail.com",
    )
    def test_missing_access_code_is_rejected(self) -> None:
        response = self.client.post(reverse("admin_login"), {})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "This field is required.", status_code=400)
        self.assertNotContains(response, "enricosaccon96@gmail.com", status_code=400)

    @override_settings(
        ADMIN_ACCESS_TOTP_SECRET="",
        ADMIN_ACCESS_EMAIL="enricosaccon96@gmail.com",
    )
    def test_missing_totp_secret_is_rejected(self) -> None:
        with (
            patch("core.views.issue_admin_access_token") as issue_token_mock,
            patch("core.views.send_admin_access_email") as send_email_mock,
        ):
            response = self.client.post(reverse("admin_login"), {"access_code": "123456"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ADMIN_ACCESS_TOTP_SECRET is not configured.")
        issue_token_mock.assert_not_called()
        send_email_mock.assert_not_called()

    @override_settings(
        ADMIN_PANEL_PASSWORD="panel-password",
        ADMIN_ACCESS_EMAIL="enricosaccon96@gmail.com",
        ADMIN_ACCESS_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        ADMIN_ACCESS_TOTP_WINDOW=1,
    )
    def test_wrong_totp_code_does_not_send_email(self) -> None:
        with (
            patch("core.views.issue_admin_access_token") as issue_token_mock,
            patch("core.views.send_admin_access_email") as send_email_mock,
        ):
            response = self.client.post(reverse("admin_login"), {"access_code": "000000"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid authentication code.")
        issue_token_mock.assert_not_called()
        send_email_mock.assert_not_called()

    @override_settings(
        ADMIN_ACCESS_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        ADMIN_ACCESS_TOTP_WINDOW=1,
        ADMIN_PANEL_PASSWORD="panel-password",
        ADMIN_ACCESS_EMAIL="enricosaccon96@gmail.com",
    )
    def test_valid_totp_code_sends_email(self) -> None:
        fixed_time = 1_710_000_000
        code = generate_totp_code("JBSWY3DPEHPK3PXP", for_time=fixed_time)
        access_url = "https://example.com/admin?access_token=raw-token"
        with (
            patch("core.totp.time.time", return_value=fixed_time),
            patch("core.views.issue_admin_access_token", return_value=(object(), "raw-token")) as issue_token_mock,
            patch("core.views.build_admin_access_url", return_value=access_url) as build_url_mock,
            patch("core.views.send_admin_access_email") as send_email_mock,
        ):
            response = self.client.post(reverse("admin_login"), {"access_code": code}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin access link sent.")
        issue_token_mock.assert_called_once_with("enricosaccon96@gmail.com")
        build_url_mock.assert_called_once_with("raw-token")
        send_email_mock.assert_called_once_with(
            recipient_email="enricosaccon96@gmail.com",
            access_url=access_url,
        )


class AdminLogoutTests(TestCase):
    def test_admin_logout_clears_admin_session(self) -> None:
        session = self.client.session
        session["admin_panel_ok"] = True
        session["admin_pending_token_id"] = 123
        session.save()

        response = self.client.post(reverse("admin_logout"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin session ended.")
        session = self.client.session
        self.assertNotIn("admin_panel_ok", session)
        self.assertNotIn("admin_pending_token_id", session)


class VocabularyFeatureTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="scholar@example.com",
            email="scholar@example.com",
            password="very-secure-password",
        )

    def test_vocabulary_pages_require_authentication(self) -> None:
        self.assertEqual(self.client.get(reverse("vocabulary_lexicon")).status_code, 302)
        self.assertEqual(self.client.get(reverse("vocabulary_test")).status_code, 302)
        self.assertEqual(self.client.get(reverse("spelling_test")).status_code, 302)
        self.assertEqual(self.client.get(reverse("lesson_world")).status_code, 302)

    def test_lexicon_allows_adding_word(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("vocabulary_lexicon"),
            {"term": "Der Entwurf", "translation": "Draft", "target_language": "EN"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Word added to your lexicon.")
        self.assertTrue(
            LearningWord.objects.filter(language="German", article="Der", word="Entwurf").exists()
        )
        self.assertTrue(
            UserWordProgress.objects.filter(
                user=self.user,
                word__language="German",
                word__article="Der",
                word__word="Entwurf",
            ).exists()
        )

    def test_lexicon_is_user_scoped(self) -> None:
        user_model = get_user_model()
        other_user = user_model.objects.create_user(
            username="peer@example.com",
            email="peer@example.com",
            password="very-secure-password",
        )

        self.client.force_login(self.user)
        self.client.post(
            reverse("vocabulary_lexicon"),
            {"term": "Der Entwurf", "translation": "Draft", "target_language": "EN"},
            follow=True,
        )

        self.client.force_login(other_user)
        response = self.client.get(reverse("vocabulary_lexicon"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Der Entwurf")

    def test_vocabulary_test_submission_returns_score(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("vocabulary_test"))
        self.assertEqual(response.status_code, 200)

        rows = response.context["test_rows"][:3]
        payload = {"word_id": []}
        for row in rows:
            payload["word_id"].append(str(row["id"]))
            payload[f"type_{row['id']}"] = row["expected_type"]
            payload[f"translation_{row['id']}"] = row["translation"]

        submit_response = self.client.post(reverse("vocabulary_test"), payload, follow=True)
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, "Score")

    def test_spelling_test_submission_returns_score(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("spelling_test"))
        self.assertEqual(response.status_code, 200)

        rows = response.context["test_rows"][:3]
        payload = {"word_id": [], "action": "submit"}
        for row in rows:
            payload["word_id"].append(str(row["id"]))
            payload[f"transcription_{row['id']}"] = row["display_word"]
            payload[f"type_{row['id']}"] = row["expected_type"]
            payload[f"translation_{row['id']}"] = row["translation"]

        submit_response = self.client.post(reverse("spelling_test"), payload, follow=True)
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, "Spelling score")

    def test_world_module_submission_records_progress(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("lesson_world"))
        self.assertEqual(response.status_code, 200)

        submit_response = self.client.post(
            reverse("lesson_world"),
            {
                "continent": "europe",
                "country": "DE",
                "nation": "Deutschland",
                "nationality": "Deutsche",
                "language": "Deutsch",
            },
            follow=True,
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, "has been marked as completed")
        self.assertTrue(
            UserImprovement.objects.filter(
                user=self.user,
                category="world_module:DE",
                score_delta=3,
            ).exists()
        )
        self.assertGreater(submit_response.context["continent_progress_percent"], 0)

    def test_world_module_learning_mode_exposes_all_countries(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("lesson_world"))
        self.assertEqual(response.status_code, 200)

        countries = response.context["countries"]
        self.assertGreaterEqual(len(countries), 20)
        codes = {country["code"] for country in countries}
        self.assertIn("DE", codes)
        self.assertIn("AU", codes)
        self.assertFalse(response.context["is_test_mode"])

    def test_world_module_test_mode_uses_ten_country_pool_and_name_scoring(self) -> None:
        self.client.force_login(self.user)

        for code in [
            "DE", "FR", "ES", "IT", "AT", "CN", "JP", "IN", "KR", "MA",
        ]:
            UserImprovement.objects.get_or_create(
                user=self.user,
                category=f"world_learning:{code}",
                defaults={"score_delta": 0, "encrypted_note": ""},
            )

        response = self.client.get(reverse("lesson_world"), {"mode": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_test_mode"])

        pool_codes = response.context["test_pool_codes"]
        self.assertEqual(len(pool_codes), 10)
        countries = response.context["countries"]
        self.assertEqual(len(countries), 10)

        target_code = pool_codes[0]
        target_country = next(country for country in countries if country["code"] == target_code)
        submit_response = self.client.post(
            reverse("lesson_world"),
            {
                "mode": "test",
                "test_pool": ",".join(pool_codes),
                "continent": target_country["continent_slug"],
                "country": target_code,
                "nation": target_country["nation_answers"][0],
                "nationality": "",
                "language": "",
            },
            follow=True,
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertContains(submit_response, "marked as completed")
        self.assertTrue(
            UserImprovement.objects.filter(
                user=self.user,
                category=f"world_module:{target_code}",
                score_delta=3,
            ).exists()
        )

    def test_world_module_add_learning_country_by_english_name(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("lesson_world"),
            {
                "action": "add_learning_country",
                "learning_country_name": "Japan",
                "learning_nationality_masculine": "Japaner",
                "learning_nationality_feminine": "Japanerin",
                "learning_language": "Japanisch",
                "mode": "learn",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "added to your learning list")
        entry = UserImprovement.objects.filter(
            user=self.user,
            category="world_learning:JP",
        ).first()
        self.assertIsNotNone(entry)
        payload = json.loads(entry.encrypted_note)
        self.assertEqual(payload["nationality_masculine"], "Japaner")
        self.assertEqual(payload["nationality_feminine"], "Japanerin")
        self.assertEqual(payload["language"], "Japanisch")
        self.assertIn("JP", response.context["learning_country_codes"])

    def test_world_module_add_learning_country_requires_all_fields(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("lesson_world"),
            {
                "action": "add_learning_country",
                "learning_country_name": "Japan",
                "learning_nationality_masculine": "Japaner",
                "learning_nationality_feminine": "",
                "learning_language": "Japanisch",
                "mode": "learn",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please provide country, nationality masculine, nationality feminine, and language.")
        self.assertFalse(
            UserImprovement.objects.filter(
                user=self.user,
                category="world_learning:JP",
            ).exists()
        )


class LLMApiTests(TestCase):
    def setUp(self) -> None:
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="llm-user@example.com",
            email="llm-user@example.com",
            password="very-secure-password",
        )

    def test_llm_api_requires_authentication(self) -> None:
        response = self.client.post(
            reverse("llm_chat_api"),
            data=json.dumps({"prompt": "Hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Authentication required.")

    def test_llm_api_validates_payload(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("llm_chat_api"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Provide either 'prompt'", response.json()["error"])

    @override_settings(OPENAI_API_KEY="test-api-key")
    def test_llm_api_dispatches_to_service(self) -> None:
        self.client.force_login(self.user)
        with patch("core.views.generate_llm_response") as generate_mock:
            generate_mock.return_value = {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "response": "Hallo!",
                "usage": {"total_tokens": 7},
            }
            response = self.client.post(
                reverse("llm_chat_api"),
                data=json.dumps(
                    {
                        "prompt": "Say hello in German",
                        "provider": "openai",
                        "temperature": 0.2,
                        "max_tokens": 128,
                    }
                ),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["response"], "Hallo!")
        generate_mock.assert_called_once()
        kwargs = generate_mock.call_args.kwargs
        self.assertEqual(kwargs["provider"], "openai")
        self.assertEqual(kwargs["model"], "gpt-4.1-mini")
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": "Say hello in German"}])
