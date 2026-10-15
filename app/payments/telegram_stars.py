from app.services.billing import BillingService


class TelegramStarsAdapter:
    name = "telegram_stars"

    def __init__(self, billing: BillingService, enabled: bool, test_mode: bool):
        self.billing = billing
        self._enabled = enabled
        self.test_mode = test_mode

    def enabled(self) -> bool:
        return self._enabled

    def create_invoice(self, user_id: int, plan_code: str, promo_code: str | None = None):
        if not self._enabled:
            raise RuntimeError("Telegram Stars integration is disabled")
        return self.billing.create_invoice(user_id, plan_code, self.test_mode, promo_code)

    def confirm(self, *, user_id: int, payload: str, charge_id: str, amount: int, currency: str) -> bool:
        if not self._enabled:
            raise RuntimeError("Telegram Stars integration is disabled")
        return self.billing.confirm_stars_payment(user_id=user_id, payload=payload, charge_id=charge_id, amount=amount, currency=currency)
