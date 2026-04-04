"""Task 3 verification — Production safety checks."""

from app.config import Settings


class TestProductionSafetyChecks:
    def test_production_with_auth_disabled_fails(self):
        s = Settings(
            app_env="production",
            auth_enabled=False,
            supabase_jwt_secret="real-secret",
            supabase_url="https://real.supabase.co",
        )
        errors = s.validate_production_config()
        assert any("AUTH_ENABLED" in e for e in errors)

    def test_production_with_placeholder_jwt_secret_fails(self):
        s = Settings(
            app_env="production",
            auth_enabled=True,
            supabase_jwt_secret="your-jwt-secret-from-supabase-settings",
            supabase_url="https://real.supabase.co",
        )
        errors = s.validate_production_config()
        assert any("SUPABASE_JWT_SECRET" in e for e in errors)

    def test_production_with_empty_jwt_secret_fails(self):
        s = Settings(
            app_env="production",
            auth_enabled=True,
            supabase_jwt_secret="",
            supabase_url="https://real.supabase.co",
        )
        errors = s.validate_production_config()
        assert any("SUPABASE_JWT_SECRET" in e for e in errors)

    def test_production_with_placeholder_url_fails(self):
        s = Settings(
            app_env="production",
            auth_enabled=True,
            supabase_jwt_secret="real-secret",
            supabase_url="https://your-project.supabase.co",
        )
        errors = s.validate_production_config()
        assert any("SUPABASE_URL" in e for e in errors)

    def test_production_with_valid_config_passes(self):
        s = Settings(
            app_env="production",
            auth_enabled=True,
            supabase_jwt_secret="real-secret-value-here",
            supabase_url="https://myproject.supabase.co",
        )
        errors = s.validate_production_config()
        assert errors == []

    def test_development_is_not_production(self):
        s = Settings(app_env="development")
        assert not s.is_production

    def test_production_is_production(self):
        s = Settings(app_env="production")
        assert s.is_production
