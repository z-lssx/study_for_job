import unittest

from pydantic import SecretStr

from app.config import Settings


class SettingsTests(unittest.TestCase):
    def test_sophnet_key_is_used_as_deepseek_fallback(self):
        settings = Settings(
            deepseek_model="configured-model",
            sophnet_api_key=SecretStr("sophnet-secret"),
        )

        self.assertEqual("https://www.sophnet.com/api/open-apis/v1", settings.deepseek_base_url)
        self.assertEqual("sophnet-secret", settings.resolved_deepseek_api_key)
        self.assertTrue(settings.deepseek_configured)

    def test_explicit_deepseek_key_takes_precedence(self):
        settings = Settings(
            deepseek_model="configured-model",
            deepseek_api_key=SecretStr("explicit-secret"),
            sophnet_api_key=SecretStr("sophnet-secret"),
        )

        self.assertEqual("explicit-secret", settings.resolved_deepseek_api_key)


if __name__ == "__main__":
    unittest.main()
