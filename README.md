<p align="center">
  <img src="docs/Logo_small.webp" alt="MintKit Logo" width="260">
</p>

<h1 align="center">MintKit Hub</h1>


## 1. Project Overview & Business Goals

<details>
  <summary>Click to expand <b>Project overview & goals</b></summary>

### What is MintKit Hub?

MintKit Hub is a Django-based website for **small service businesses** (salons, gyms, tutors, therapists, etc.).

It does three main things:

1. Lets a business owner **create an account** and basic **profile**  
2. Gives them tools to build a simple **public storefront page** (name, description, active/inactive)  
3. Handles **subscriptions via Stripe** so they can access a separate MintKit app where digital gift cards, event tickets and vouchers are created and managed.

The MintKit app itself lives at a separate URL (for example `studio.mintkit.co.uk`) and is treated as a **third-party integration** for this project. MintKit Hub only controls access and provides the link.

### How it works – simple flow

For a typical business owner:

1. They visit **MintKit Hub**, register and log in.  
2. They fill in their **business profile** and create their **storefront** (e.g. “Beauty Salon”).  
3. They can preview and activate their storefront, which becomes publicly visible at a URL like:

   `https://mintkit.co.uk/storefront/beauty-salon/`

4. From their **dashboard** they start a **Stripe subscription** (with trial options).  
5. Once subscribed (or during a free trial), a dedicated **“Studio” tab** becomes useful.  
   On that Studio page they can open the external MintKit app (for example `studio.mintkit.co.uk`)  
   where they create and manage digital gift cards, tickets and vouchers.  
6. Customers visit the public storefront to learn about the business and follow links to purchase those digital products.


This repository contains only the **Django / Python Hub part** that will be graded for the Code Institute project.

### Business Goals

- Provide small service businesses with an easy way to set up a **simple branded storefront page**.  
- Offer a **subscription-based access model** (via Stripe) so businesses can unlock digital gift card / ticket / voucher tools in the external MintKit app.  
- Give business owners a clean **dashboard** where they can see:
  - basic profile information  
  - storefront status  
  - trial / subscription status  
- Demonstrate a secure, maintainable Django application with clear separation between:
  - the core platform (this repository), and  
  - the third-party MintKit integration.  
- Lay the groundwork for future enhancements such as richer analytics, storefront themes and deeper, more automated integration with MintKit.

</details>



## 2. UX: Target Audience & User Stories

<details>
  <summary>Click to expand <b>UX summary & user stories</b></summary>

### Target audience

The primary users are:

- **Small business owners** who want a simple online presence and the ability to sell digital gift cards, tickets or vouchers without building a full website from scratch.
- **Their customers**, who only see the public storefront pages and follow links to buy or redeem digital products.
- **The site owner / admin** (me, as project owner) who manages plans, subscriptions and occasionally updates storefront content via Django admin.

MintKit Hub focuses on making the experience simple for a busy non-technical business owner:
- clear navigation (Home → Dashboard → Storefront → Subscription)
- forms that only ask for essential information
- clear feedback about whether their storefront is public and whether they currently have access to the MintKit app.


### Key User Stories

#### Business Owner

- As a business owner, I want to register and log in so that I can securely access my storefront and dashboard.
- As a business owner, I want to create and edit my storefront details (name, description, contact info, logo) so that my customers see accurate, professional information about my business.
- As a business owner, I want to subscribe to MintKit Hub using Stripe so that I can unlock access to the MintKit app and its digital product tools.
- As a business owner, I want to see my current subscription status (plan, renewal date, active/inactive) on my dashboard so that I know whether I still have access to MintKit features.
- As a business owner, I want a dedicated **Studio** tab so that I always know where to go to open the MintKit app and manage my digital products.

#### Customer

- As a customer, I want to view a business’s storefront page so that I can understand what services or products they offer.
- As a customer, I want to see key information (description, contact details, opening hours, links) so that I can decide if this business suits my needs.
- As a customer, I want a straightforward and trustworthy experience when I interact with the storefront so that I feel confident using it.

#### Site Admin

- As a site admin, I want to see a list of registered business accounts so that I can monitor who is using the platform.
- As a site admin, I want to quickly check a business owner’s subscription status so that I can help with support queries.
- As a site admin, I want the system to restrict access to MintKit features to subscribed users only so that the business model remains sustainable.

*A more detailed UX document (personas, wireframes, and any additional stories) can be added later in `docs/UX.md` and linked from this section.*

</details>


## 3. Data Model & ERD

<details>
  <summary>Click to expand <b>Data model & ERD details</b></summary>

### Data Model Overview

The data model for MintKit Hub is built around three main concepts:

1. **Users / Business Profiles** – who is using the platform.
2. **Storefronts** – how a business appears publicly.
3. **Subscriptions** – how access to the MintKit app is controlled via Stripe.

Django’s built-in `User` model is used for authentication, with additional project-specific models layered on top.

### Core Models (Planned)

> Note: Model names and fields may be refined slightly during implementation, but the core relationships will remain the same.

- **User** (Django built-in)
  - Handles authentication (username, email, password).
  - Related 1:1 to a `Profile`.

- **Profile**
  - Extends the `User` with business-related information.
  - Example fields:
    - `user` (OneToOneField to User)
    - `business_name`
    - `contact_email`
    - `logo` (optional)
    - `created_at`
  - Represents a business owner on the platform.

- **Storefront**
  - Represents the public-facing page for a business.
  - Example fields:
    - `profile` (OneToOneField or ForeignKey to Profile)
    - `slug` (used in URLs)
    - `headline`
    - `description`
    - `contact_details`
    - `is_active`
  - Used to display information to customers.

- **SubscriptionPlan**
  - Defines available subscription tiers.
  - Example fields:
    - `name` (e.g. Basic, Pro)
    - `price` (e.g. monthly cost)
    - `stripe_price_id` (link to Stripe pricing)
    - `description`
    - `is_active`
  - Allows the platform to offer different levels of service.

- **Subscription**
  - Connects a `Profile` to a `SubscriptionPlan` and tracks Stripe status.
  - Example fields:
    - `profile` (ForeignKey to Profile)
    - `plan` (ForeignKey to SubscriptionPlan)
    - `stripe_customer_id`
    - `stripe_subscription_id`
    - `status` (e.g. active, cancelled, past_due)
    - `start_date`
    - `end_date` (nullable for active subs)
  - Used to control whether a business owner can access the MintKit app.

- **MintKitAccess** (or similar integration model)
  - Stores any additional information needed to connect the user to the external MintKit app.
  - Example fields:
    - `profile` (OneToOneField to Profile)
    - `external_identifier` (e.g. ID used by MintKit)
    - `last_accessed_at`
  - This model keeps the integration concerns separate from core subscription logic.

### Relationships (High-Level)

- **User 1–1 Profile**  
  Each Django user has one profile with business-specific data.

- **Profile 1–1 / 1–* Storefront**  
  A profile owns one primary storefront (for this project).  
  (Could be extended to multiple storefronts in future.)

- **Profile *–* SubscriptionPlan via Subscription**  
  A profile can have one active subscription and possibly historical ones, each pointing to a plan.

- **Profile 1–1 MintKitAccess**  
  If a profile is connected to the external MintKit app, an integration record can store that link.

### Visual ERD

A Mermaid-based ERD is provided in [docs/ERD.md](docs/ERD.md), showing:

- `User` 1–1 `Profile`
- `Profile` 1–1 `Storefront`
- `Profile` 1–* `Subscription`
- `Subscription` *–1 `SubscriptionPlan`
- `Profile` 1–1 `MintKitAccess`

This matches the planned Django models described above.


</details>


## 4. Features

<details>
  <summary>Click to expand <b>Feature list</b></summary>

### Overview

MintKit Hub focuses on three main areas:

1. **Account & Access** – registration, login, and role-based access to the dashboard.
2. **Storefront Management** – letting business owners configure how their business appears publicly.
3. **Subscriptions & Integration** – using Stripe to control access to the external MintKit app.

The list below separates **core MVP features** (for this project) from **future enhancements** that are out of scope but planned.

---

### Core Features (MVP for this project)

#### 1. Authentication & Onboarding

- User registration with Django’s authentication system.
- Login and logout functionality with feedback messages.
- Basic profile setup for new business owners (business name, contact email, etc.).
- Access control so that only logged-in users can reach the dashboard and storefront management pages.

#### 2. Business Dashboard

- Authenticated dashboard page showing:
  - A welcome message and basic profile information.
  - Current subscription status (plan name, active/inactive).
  - Quick links to “Edit Storefront” and “Manage Subscription”.
- Clear messaging when a user is not yet subscribed and needs to start a plan.

#### 3. Storefront Management

- Create a storefront linked to the logged-in user’s profile.
- Edit storefront details:
  - Headline / description
  - Contact details
  - Optional logo or branding fields (if included)
- Toggle storefront **active/inactive**:
  - When **active**, the storefront is publicly visible to anyone (including unregistered visitors).
  - When **inactive**, the storefront is hidden from the public but still manageable by the business owner via the dashboard.
- Public storefront page accessible via a clean URL (e.g. `/storefront/<slug>/`).


#### 4. Stripe Subscription Integration & Trial Logic

- List of available subscription plans (e.g. Basic, Pro) with prices.
- Stripe Checkout integration to start a subscription:
  - User selects a plan.
  - Redirect to Stripe-hosted payment page.
  - Redirect back to success/cancel pages.
- Storage of relevant Stripe IDs on the `Subscription` model.
- Simple status display on the dashboard so the business owner can see if their subscription is active.
- **Trial behaviour:**
  - New users receive a time-limited free trial period (e.g. 14 days) during which they can still access the MintKit app without paying.
  - When a user starts a Stripe subscription, the plan is configured to include an initial free period (e.g. first month free), after which normal billing begins.


#### 5. External MintKit App Access

- A dedicated button/link on the dashboard that appears when the user has an active subscription.
- The link sends the user to the external MintKit app (e.g. `studio.mintkit.co.uk`) to manage gift cards, tickets, and vouchers.
- (Optional for this project) Store a simple integration record (`MintKitAccess` model) to track that the user has been connected.

#### 6. Admin & Maintenance

- Django admin configured for key models (Profile, Storefront, SubscriptionPlan, Subscription, MintKitAccess).
- Useful list/filter options in the admin to help with support (e.g. filter by subscription status).
- Basic error or info messages where appropriate (e.g. when a non-subscribed user tries to access subscriber-only features).

---

### Future / Stretch Features (Out of Scope for MVP)

These are ideas for future development and are not required for the initial Code Institute submission:

- Display of live sales or usage stats pulled from the external MintKit app.
- Allowing multiple storefronts per profile (for users with more than one business).
- Custom themes or templates for storefronts.
- Customer purchase flow directly inside the Django app, integrated with Stripe and/or MintKit.
- More advanced analytics on the dashboard (e.g. charts, trends, customer counts).

</details>


## 5. Technologies & Integrations (including Stripe & MintKit)

<details>
  <summary>Click to expand <b>Technologies & Integrations</b></summary>

### Core Technologies

- **Python 3** – main programming language for the backend.
- **Django** – main web framework used to implement the MintKit Hub application, including models, views, templates, and authentication.
- **HTML5** – structure of all pages.
- **CSS3** – styling and layout for the frontend (with a focus on responsiveness).
- **Bootstrap** (or similar CSS framework) – to speed up building a responsive and consistent UI.

### Database & Data Layer

- **SQLite** – default database for local development and testing.
- **(Planned) PostgreSQL** – database engine for production deployment (to be confirmed with hosting platform).
- **Django ORM** – used to define models and manage database queries.

### Stripe payments

- **Stripe Checkout** is used to handle subscription payments securely.  
- MintKit Hub never stores card data; it creates a **Checkout Session** and lets Stripe handle the card details.  
- The app stores only the minimum necessary Stripe IDs (customer, subscription, status) to know:
  - whether the user is in a **free trial**, and  
  - whether their subscription is currently **active**.

#### 5. External MintKit App Access

- A dedicated **Studio tab/page** available to logged-in business owners.
- The Studio page:
  - shows an **“Open MintKit Studio”** button when the user has trial or subscription access.
  - shows a clear message (and no active button) when the trial has ended and there is no active subscription.
- The “Open MintKit Studio” button links to the external MintKit app (e.g. `studio.mintkit.co.uk`) where gift cards, tickets, and vouchers are managed.
- (Optional for this project) Store a simple integration record (`MintKitAccess` model) to track that the user has been connected.



### Development & Tooling

- **Git** – version control.
- **GitHub** – remote repository hosting and project documentation (README, docs).
- **Virtual Environment** (`venv` or similar) – isolates Python dependencies for the project.
- **pip** – package manager for Python dependencies.

### Deployment (To Be Finalised)

The exact deployment stack will be documented once chosen (for example, a cloud platform that supports Django, PostgreSQL, and environment variables for Stripe keys). This section will be updated with:

- Hosting platform name.
- How static files are served.
- Any additional services involved in production.

### Third-Party Services, APIs & Scripts

MintKit Hub relies on a few external services and scripts:

- **Stripe Checkout & Stripe APIs**  
  Used to handle secure subscription payments for business owners. The Django backend communicates with Stripe’s API using the official Python SDK, and the frontend uses Stripe’s hosted Checkout pages for payment.

- **External MintKit App (3rd-party)**  
  A separately hosted application (for example at `studio.mintkit.co.uk`) that provides the actual tools for creating and managing digital gift cards, tickets, and vouchers. MintKit Hub does not contain this code; it simply controls access and links users to it.

- **(Planned) Analytics / Monitoring (optional)**  
  If added later (e.g. simple visit tracking or error monitoring), the chosen service and integration details will be documented here.

For a more detailed description of how Stripe and the external MintKit app fit together,
see [docs/STRIPE_MINTKIT_INTEGRATION.md](docs/STRIPE_MINTKIT_INTEGRATION.md).


</details>


## 6. Project Setup & Milestones

<details>
  <summary>Click to expand setup instructions & milestones</summary>

### Local Project Setup

These steps describe how to get MintKit Hub running locally for development.

1. **Clone the repository**

   ```bash
   git clone https://github.com/Oscar-Ivs/mintkit-hub.git
   cd mintkit-hub

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate


3. **Install dependencies**

(A requirements.txt file will be added as the project develops.)

```bash
pip install -r requirements.txt
python manage.py migrate
```

4. **Set environment variables**

Create a .env file (or use chosen method for environment variables) and add keys such as:

SECRET_KEY=your-secret-key-here

DEBUG=True

STRIPE_PUBLIC_KEY=pk_test_...

STRIPE_SECRET_KEY=sk_test_...

STRIPE_WEBHOOK_SECRET=whsec_...


In development, the project will use SQLite by default; production database configuration will be documented in the Deployment section.

5. **Apply migrations**

python manage.py migrate

6. **Create a superuser (for Django admin)**

python manage.py createsuperuser

7. **Run the development server**

python manage.py runserver

The site should now be accessible at http://127.0.0.1:8000/

## Project Milestones / Roadmap

This project will be built in small, focused milestones:

#### Milestone 1 – Project Skeleton

- Create Django project and core apps (e.g. `accounts`, `storefronts`, `subscriptions`, `core`).
- Configure base templates, navigation, and basic URL structure.
- Set up GitHub repo and initial documentation structure (`README`, `docs/`).

#### Milestone 2 – Accounts & Profiles

- Implement registration, login, and logout using Django auth.
- Create `Profile` model linked to the `User`.
- Build a simple profile page and initial dashboard.

#### Milestone 3 – Storefront Management

- Implement `Storefront` model and CRUD views.
- Allow business owners to create and edit their storefront.
- Add public storefront pages (active/inactive behaviour included).

#### Milestone 4 – Subscriptions & Stripe Integration

- Implement `SubscriptionPlan` and `Subscription` models.
- Connect to Stripe (test mode) using Stripe Checkout.
- Add trial logic and dashboard status display.
- Show/hide access to the external MintKit app based on trial/subscription status.

#### Milestone 5 – Polish, Testing & Deployment

- Refine UI, messages, and navigation.
- Document and run manual tests (plus any automated tests if included).
- Finalise deployment to the chosen hosting platform.
- Update README, testing docs, and CI criteria mapping.
</details>


## 7. Testing

<details>
  <summary>Click to expand <b>Testing summary</b></summary>

### Testing Approach

Testing for MintKit Hub will be a mix of:

- **Manual testing** of all core user flows (registration, login, storefront management, subscriptions, trial logic, and access to the external MintKit app).
- **Form and validation checks** to ensure invalid input is handled gracefully with clear error messages.
- **Access control checks** to confirm that only authorised users can access the dashboard and management pages, while public storefronts remain visible to everyone.
- **(Optional) Automated tests** for critical views, forms, and models if time allows.

A separate document `docs/TESTING.md` will contain full test cases, step-by-step procedures, and results (including screenshots if needed). This section in the README stays as a high-level summary.

---

### Key Areas Covered

- User registration, login, logout.
- Profile creation and editing (business details).
- Storefront creation, editing, and active/inactive toggle behaviour.
- Public storefront visibility rules:
  - Active storefronts visible to everyone.
  - Inactive storefronts only accessible to the owner (or admin).
- Dashboard behaviour:
  - Trial status display.
  - Subscription status display.
  - Show/hide MintKit access button based on trial/subscription.
- Stripe subscription flow in test mode:
  - Starting a checkout session.
  - Handling success and cancel redirects.
- Django admin access and basic model admin checks.
- General UI checks (navigation links, messages, and error handling).

---

### Example Manual Test Checklist

A more detailed version of this checklist will be expanded in `docs/TESTING.md`, but core tests will include:

- [ ] Register a new business owner account.
- [ ] Log in and log out successfully.
- [ ] Create and update a Profile (business name, contact details, etc.).
- [ ] Create a new Storefront and view it publicly while active.
- [ ] Set a Storefront to inactive and verify it is hidden from public visitors.
- [ ] Start the Stripe subscription process from the dashboard (test mode).
- [ ] Complete a Stripe test payment (or Stripe trial) and confirm subscription status updates.
- [ ] Verify that trial users and subscribed users can see the MintKit access button.
- [ ] Verify that users with no trial/subscription cannot access MintKit features.
- [ ] Check that restricted pages redirect unauthenticated users to the login page.

All individual test cases, expected outcomes, and results (pass/fail) will be documented in `docs/TESTING.md`.

</details>


## 8. Deployment

<details>
  <summary>Click to expand <b>Deployment overview</b></summary>

### Planned Hosting

For this project, the Django application will be deployed to **Heroku**, using a similar setup to the previous BookBase project:

- **Heroku Dyno** to run the Django app.
- **Heroku Postgres** as the production database.
- **Environment variables** on Heroku for sensitive settings (e.g. `SECRET_KEY`, Stripe keys, database URL).
- **Gunicorn** as the WSGI HTTP server.
- **Static files** handled via Django’s `collectstatic` (e.g. using WhiteNoise or a similar approach).

The exact app name and live URL will be added here after deployment.

---

### High-Level Deployment Steps (Planned)

A more detailed, step-by-step guide will be written once deployment is completed. At a high level, the process will be:

1. **Prepare the project for production**
   - Ensure `DEBUG = False` in the production settings.
   - Configure `ALLOWED_HOSTS` to include the Heroku app domain.
   - Add required packages to `requirements.txt` (e.g. `gunicorn`, any static file packages used).
   - Add a `Procfile` (e.g. `web: gunicorn mintkithub.wsgi`).

2. **Create and configure the Heroku app**
   - Create a new Heroku app from the command line or dashboard.
   - Attach a **Heroku Postgres** add-on for the production database.
   - Set environment variables in the Heroku dashboard (e.g. `SECRET_KEY`, `DATABASE_URL`, `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`).

3. **Deploy the code to Heroku**
   - Push the code to Heroku using Git.
   - Run database migrations on Heroku:
     - `python manage.py migrate`
   - Create a superuser for accessing the Django admin on production.

4. **Collect static files**
   - Run `python manage.py collectstatic` on Heroku.
   - Confirm that static files are being served correctly.

5. **Final checks**
   - Log in to the live site and verify core flows (registration, login, dashboard, storefront view).
   - Confirm that Stripe test mode works correctly in the deployed environment.

---

A dedicated `docs/DEPLOYMENT.md` file may be added later with full command examples and screenshots once the live deployment is complete.

</details>


## 9. Troubleshooting & Known Fixes

<details>
  <summary>Click to expand <b>Troubleshooting notes</b></summary>

### Purpose

This section collects recurring issues encountered during development and deployment of MintKit Hub, along with the fixes that were applied. It will be updated as new problems appear and are resolved.

### Common Issues (to be updated as they occur)

#### 1. Example placeholder – Django migrations error

- **Issue:** `django.db.utils.OperationalError` when running `python manage.py migrate`.
- **Cause:** Database not configured correctly or missing environment variables.
- **Fix:**  
  - Check that the correct database settings are in place for the current environment.  
  - Confirm that environment variables (e.g. `DATABASE_URL` on Heroku) are set.  
  - Re-run `python manage.py migrate`.

#### 2. Example placeholder – Static files not loading in production

- **Issue:** CSS and JS files not loading on the deployed site.
- **Cause:** Static files not collected or serving configuration incomplete.
- **Fix:**  
  - Run `python manage.py collectstatic` on the production environment.  
  - Confirm static files settings and, if using Heroku, ensure the chosen static file solution (e.g. WhiteNoise) is configured.

---

> **Note:** As development progresses, real issues and their solutions will be added here with short, clear descriptions:
> - What went wrong  
> - Why it happened  
> - How it was fixed  

</details>


## 10. Further Documentation (for assessors)

<details>
  <summary>Click to expand <b>Further Documentation</b></summary>

- **CI Assessment Criteria Mapping**  
  A detailed mapping between the Code Institute learning outcomes and MintKit Hub is provided in:  
  [docs/CI_CRITERIA.md](docs/CI_CRITERIA.md)  

- **Wireframes & screenshots**  
  Once the UI is more polished, this folder will also contain:
  - page wireframes (home page, dashboard, storefront)
  - a small set of screenshots from the deployed site  
  to help assessors quickly understand the layout and flows.
</details>