"""Payment abstraction. Swap the gateway with PAYMENT_PROVIDER without touching checkout code.

`MockGateway` is a sandbox: it never touches real money and never stores card data.
Add `RazorpayGateway` / `StripeGateway` by implementing `charge()` (server-side only,
secrets come from environment variables).
"""
import secrets
from dataclasses import dataclass
from decimal import Decimal

METHODS = {
    "card": "Card (test mode)",
    "upi": "UPI (test mode)",
    "cod": "Cash on delivery",
}


@dataclass
class PaymentResult:
    success: bool
    reference: str = ""
    status: str = "failed"   # succeeded | pending | failed
    message: str = ""


class Gateway:
    name = "base"

    def charge(self, amount: Decimal, method: str, details: dict) -> PaymentResult:  # pragma: no cover
        raise NotImplementedError


class MockGateway(Gateway):
    name = "mock"
    DECLINE_CARD = "4000000000000002"

    def charge(self, amount, method, details):
        ref = "MOCK_" + secrets.token_hex(6).upper()
        if method == "cod":
            return PaymentResult(True, ref, "pending", "Pay on delivery")
        if method == "card":
            digits = "".join(c for c in details.get("card_number", "") if c.isdigit())
            if len(digits) < 12:
                return PaymentResult(False, message="Enter a valid test card number (e.g. 4242 4242 4242 4242).")
            if digits == self.DECLINE_CARD:
                return PaymentResult(False, message="Card declined (test card). Try 4242 4242 4242 4242.")
        if method == "upi" and "@" not in details.get("upi_id", ""):
            return PaymentResult(False, message="Enter a valid UPI ID (e.g. test@upi).")
        return PaymentResult(True, ref, "succeeded", "Approved (sandbox)")


def get_gateway(app) -> Gateway:
    provider = app.config.get("PAYMENT_PROVIDER", "mock")
    if provider == "mock":
        return MockGateway()
    raise RuntimeError(f"Payment provider '{provider}' is not implemented. Add an adapter in services/payments.py.")
