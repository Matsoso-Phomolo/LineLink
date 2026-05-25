# MoPay Onboarding Checklist

LineLink is prepared for MoPay onboarding without storing wallet PINs, card secrets, or provider credentials in Git.

## Business Details

- Business name: LineLink
- Payment use case: Rental management and accommodation marketplace payments for tenants, deposits, rent, and landlord subscriptions.
- Support email: phomolomatsoso@gmail.com
- Support phone: +266 57260714 / +266 63355656
- Expected transaction volume: to be confirmed during MoPay merchant onboarding

## Documents To Prepare

- Business registration documents
- Platform owner identification
- Bank settlement account confirmation
- Proof of business address
- Privacy policy URL
- Terms of service URL

## Production URLs

- Frontend: https://linelink-three.vercel.app
- Backend: https://linelink.onrender.com
- Webhook: https://linelink.onrender.com/payments/callback/mopay
- Return URL: https://linelink-three.vercel.app

## Render Environment Variables

Use Render environment variables only. Never commit real values.

```env
MOPAY_BASE_URL=https://provider-url-from-mopay
MOPAY_API_KEY=provided-by-mopay
MOPAY_MERCHANT_ID=provided-by-mopay
MOPAY_WEBHOOK_SECRET=provided-by-mopay
MOPAY_CALLBACK_URL=https://linelink.onrender.com/payments/callback/mopay
MOPAY_RETURN_URL=https://linelink-three.vercel.app
MOPAY_ENVIRONMENT=sandbox
```

## Security Notes

- LineLink never asks tenants or landlords for M-Pesa/EcoCash PINs.
- Customers confirm payments only through MoPay, wallet prompts, USSD, or official provider apps.
- Webhooks should be signed with `MOPAY_WEBHOOK_SECRET`.
- Duplicate webhooks are ignored using event and transaction idempotency checks.
- Raw provider callback payloads are stored for audit/debugging, without wallet PINs or card secrets.
