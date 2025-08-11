# models.payment

A comprehensive payment processing system supporting multiple payment methods, transaction tracking, fraud detection, and refund management with integration to external payment providers.

Dependencies: @../core/database[Base], @./order[Order], @./user[User]

Requirements:
- Process payments through multiple providers (Stripe, PayPal, etc.)
- Track payment lifecycle from pending to completion/failure
- Support partial and full refunds with reason tracking
- Implement fraud detection and risk scoring
- Securely store payment method information (tokenized)
- Maintain comprehensive audit trail of all transactions
- Generate unique payment references for tracking

Model Structure:
- Primary key: id (Integer)
- Unique reference: payment_reference (indexed, 100 chars)
- Foreign keys: order_id (orders.id), user_id (users.id)
- Payment details: amount (decimal 10,2), currency (default USD), payment_method enum, status enum
- Provider integration: provider_transaction_id, provider_name, provider_response (JSON)
- Processing timestamps: processed_at, failed_at, refunded_at
- Refund tracking: refund_amount, refund_reason, failure_reason
- Card info (tokenized): card_last_four, card_brand, card_exp_month/year
- Fraud detection: risk_score, is_flagged, flagged_reason
- Audit: created_at, updated_at timestamps

Payment Status Enum:
- PENDING: Payment initiated but not yet processed
- PROCESSING: Currently being processed by payment provider
- COMPLETED: Successfully processed and funds captured
- FAILED: Payment failed due to insufficient funds, declined card, etc.
- CANCELLED: Payment cancelled before processing
- REFUNDED: Full refund issued
- PARTIALLY_REFUNDED: Partial refund issued

Payment Method Enum:
- CREDIT_CARD, DEBIT_CARD: Card-based payments
- PAYPAL: PayPal integration
- STRIPE: Direct Stripe processing
- BANK_TRANSFER: ACH/wire transfers
- CRYPTO: Cryptocurrency payments

Business Logic:
- generate_payment_reference(): Create unique reference for tracking
- is_successful(): Check if payment completed successfully
- can_be_refunded(): Validate refund eligibility and timing
- calculate_refundable_amount(): Determine available refund amount
- process_payment(): Execute payment through selected provider
- process_refund(): Issue full or partial refund with reason
- mark_as_completed(): Update status with provider response
- mark_as_failed(): Record failure with reason and timestamp
- get_by_reference(): Find payment by unique reference
- get_user_payments(): Retrieve payment history for user
- get_successful_payments_total(): Calculate total successful payments

Additional Notes:
- Multi-provider support enables payment method diversity
- Comprehensive transaction tracking for audit compliance
- Fraud detection helps prevent chargebacks
- Secure card data handling with tokenization
- Refund management supports customer service operations