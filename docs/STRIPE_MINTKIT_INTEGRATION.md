### Overview

MintKit Hub uses **Stripe** to manage subscription payments for business owners.  
Access to the external **MintKit app** (e.g. at `studio.mintkit.co.uk`) is controlled by:

- A **time-limited trial period**, and  
- The **status of the user’s Stripe subscription**.

The external MintKit app itself is treated as a **third-party service** and is **not part of this Django codebase**. This repository focuses on authentication, storefronts, subscription logic, and access control.

---

### Stripe Subscription Flow (High Level)

1. **Choose a plan**  
   - The business owner sees one or more `SubscriptionPlan` options (e.g. Basic / Pro).

2. **Start Stripe Checkout**  
   - From the dashboard, the user selects a plan and clicks a “Subscribe” button.
   - The Django backend creates a Stripe Checkout Session (in test mode during development).
   - The user is redirected to the Stripe-hosted payment page.

3. **Payment / Stripe trial period**  
   - Stripe handles card details securely (MintKit Hub never stores card numbers).
   - The chosen plan may include an initial **free month** configured in Stripe.
   - On success, Stripe redirects back to a success page; on cancel, back to a cancel page.

4. **Update subscription status**  
   - MintKit Hub stores the relevant Stripe IDs on the `Subscription` model (e.g. `stripe_customer_id`, `stripe_subscription_id`, `status`).
   - The dashboard uses this data to show whether the subscription is active and whether the user should have access to the MintKit app.

(If webhooks are implemented, they will be used to keep the subscription `status` in sync with Stripe events such as payment succeeded, cancelled, or expired.)

---

### Trial & Access Logic

MintKit Hub supports a generous trial approach designed to encourage experimentation:

- **Initial application trial (before Stripe subscription)**  
  - New business owners receive a time-limited **free trial** (for example, 14 days) during which they can still access the MintKit app via MintKit Hub without paying.
  - A field such as `trial_ends_at` on the `Profile` model is used to control this.

- **Stripe subscription with free period**  
  - When the user decides to subscribe, the Stripe plan is configured with an initial **free month**, so the first billing date is in the future.
  - The `Subscription` model stores the Stripe status and any relevant dates (e.g. start date, next billing date).

- **Access rules on the dashboard**

  The dashboard will typically behave as follows:

  - **State A – Trial active, no subscription yet**  
    - Show trial countdown (e.g. “You have X days left of your free trial”).  
    - Show **MintKit access button**.  
    - Encourage upgrade (e.g. “Subscribe now and get your first month free via Stripe.”).

  - **State B – Subscription active**  
    - Show current plan and next charge/renewal date.  
    - Show **MintKit access button**.  
    - Provide a link to manage the subscription (e.g. via Stripe customer portal or support).

  - **State C – Trial expired and no active subscription**  
    - Explain that the trial has ended.  
    - Hide the MintKit access button.  
    - Show a clear call-to-action to start a Stripe subscription.

These rules ensure that the UI clearly communicates whether the user currently has access to MintKit or needs to subscribe.

---

### External MintKit App Integration

- The MintKit app is hosted separately (for example at `studio.mintkit.co.uk`) and is considered a **third-party** application.
- MintKit Hub does **not** contain the MintKit app source code; it only controls access and provides links.
- When a user is allowed access (trial or subscription state):

  - The dashboard displays a button such as **“Open MintKit App”**.
  - Clicking the button redirects the user to the external MintKit URL.
  - Optionally, a simple integration model (`MintKitAccess`) can store an `external_identifier` or timestamp for when the user last accessed MintKit.

For the purposes of the Code Institute project, this integration is treated as:

- A clear example of **using a third-party service** alongside Django and Stripe.
- Out of scope for Django unit testing (MintKit’s internal behaviour is not tested here).
- Clearly separated in documentation so it is understood what belongs to this repo and what does not.

---

### Security & Data Handling Notes

- All payment card data is handled directly by **Stripe**. MintKit Hub never stores card numbers or CVV codes.
- Only the minimum necessary Stripe identifiers are stored in the database (e.g. customer ID, subscription ID, status).
- Any future enhancement such as signed URLs, tokens, or SSO for MintKit access will be documented separately, but are not strictly required for this project.
## Pricing Page: Monthly vs Annual Billing

The Pricing page passes the billing choice as a query param (`billing=monthly` or `billing=annual`). The checkout endpoint reads this value and chooses the matching Stripe **Price ID**.

To avoid a full page refresh when switching between monthly/annual on the Pricing page, the UI uses a small vanilla JS helper that:

- Updates the current URL in the address bar (`history.replaceState`)
- Updates any checkout links on the page (anchors with `.js-billing-link`) so they always include `billing=...`

```html
<script>
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("mk-billing-toggle");
  if (!toggle) return;

  function setBilling(billing) {
    // Update address bar without refreshing the page
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("billing", billing);
      window.history.replaceState({}, "", url);
    } catch (e) {}

    // Update any checkout links that must carry billing=...
    document.querySelectorAll(".js-billing-link").forEach(function (a) {
      try {
        const u = new URL(a.getAttribute("href"), window.location.origin);
        u.searchParams.set("billing", billing);
        a.setAttribute("href", u.pathname + u.search + u.hash);
      } catch (e) {}
    });
  }

  setBilling(toggle.checked ? "annual" : "monthly");

  toggle.addEventListener("change", function () {
    setBilling(toggle.checked ? "annual" : "monthly");
  });
});
</script>
```

**Template note:** add `.js-billing-link` to plan buttons that point to the checkout view (e.g. the Basic “Upgrade” button).
