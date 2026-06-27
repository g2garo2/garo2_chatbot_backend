from dataclasses import dataclass


@dataclass(frozen=True)
class PlanConfig:
    key: str
    label: str
    price_inr: int
    chat_daily_limit: int | None
    translation_daily_limit: int
    image_upload_daily_limit: int
    image_generation_monthly_limit: int
    chat_provider: str
    text_provider: str
    image_provider: str
    features_note: str


FREE_PLAN = "free"
PLUS_PLAN = "plus"
PRO_PLAN = "pro"
ULTRA_PLAN = "ultra"

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "authenticated", "created"}
PAID_PLANS = {PLUS_PLAN, PRO_PLAN, ULTRA_PLAN}
SUBSCRIPTION_DOWNGRADE_STATUSES = {"cancelled", "halted", "expired", "completed", "failed"}

PLAN_CONFIGS: dict[str, PlanConfig] = {
    FREE_PLAN: PlanConfig(
        key=FREE_PLAN,
        label="Free",
        price_inr=0,
        chat_daily_limit=None,
        translation_daily_limit=8,
        image_upload_daily_limit=3,
        image_generation_monthly_limit=1,
        chat_provider="openrouter_free",
        text_provider="gemini",
        image_provider="gemini",
        features_note="Free chat uses OpenRouter free model. Translation and image features use Gemini.",
    ),
    PLUS_PLAN: PlanConfig(
        key=PLUS_PLAN,
        label="Plus",
        price_inr=100,
        chat_daily_limit=40,
        translation_daily_limit=40,
        image_upload_daily_limit=15,
        image_generation_monthly_limit=5,
        chat_provider="gemini",
        text_provider="gemini",
        image_provider="gemini",
        features_note="All AI features use Gemini.",
    ),
    PRO_PLAN: PlanConfig(
        key=PRO_PLAN,
        label="Pro",
        price_inr=299,
        chat_daily_limit=120,
        translation_daily_limit=120,
        image_upload_daily_limit=45,
        image_generation_monthly_limit=20,
        chat_provider="gemini",
        text_provider="gemini",
        image_provider="gemini",
        features_note="All AI features use Gemini.",
    ),
    ULTRA_PLAN: PlanConfig(
        key=ULTRA_PLAN,
        label="Ultra",
        price_inr=1099,
        chat_daily_limit=500,
        translation_daily_limit=500,
        image_upload_daily_limit=100,
        image_generation_monthly_limit=150,
        chat_provider="gemini",
        text_provider="gemini",
        image_provider="gemini",
        features_note="All AI features use Gemini.",
    ),
}


def get_plan_config(plan: str | None) -> PlanConfig:
    return PLAN_CONFIGS.get((plan or FREE_PLAN).lower(), PLAN_CONFIGS[FREE_PLAN])
