  <img src="docs/Logo_small.webp" alt="MintKit Hub Logo" width="260">

## 1. Project Overview & Business Goals

<details>
  <summary>Click to expand <b>Project overview & goals</b></summary>

MintKit Hub is a Django-based web platform that helps small businesses create a simple online presence and connect to a separate MintKit application where they can design and manage digital gift cards, event tickets, and vouchers.

This repository contains the **Django / Python** part of the overall idea and is the part that will be graded for the Code Institute Full Stack Frameworks project. MintKit Hub handles user accounts, storefront management, Stripe subscriptions and a dashboard. Once subscribed, business owners can get full access to the MintKit app (e.g. at studio.mintkit.co.uk) from a link on their dashboard.

### Business Goals

- Provide small service businesses (e.g. salons, gyms, tutors) with an easy way to set up a simple branded storefront.
- Offer a subscription-based access model (via Stripe) so businesses can unlock tools for managing digital gift cards, tickets, and vouchers in the external MintKit app.
- Give business owners a clean dashboard where they can see their subscription status and basic information about their storefront.
- Demonstrate a secure, maintainable Django application with clear separation between the core platform (this project) and the third-party MintKit integration.
- Lay the groundwork for future enhancements such as richer analytics, more storefront customization options, and deeper integration with the external MintKit service.

</details>



## 2. UX: Target Audience & User Stories

<details>
  <summary>Click to expand <b>UX summary & user stories</b></summary>

### UX Overview

The UX focus of MintKit Hub is to make it easy for small business owners to set up a simple online presence, manage their subscription, and then seamlessly access the external MintKit app. Customers should be able to understand what a business offers and, in future iterations, purchase digital products without confusion.

### Target Audience

- **Business Owners** – small service-based businesses (e.g. beauty salons, gyms, tutors, local event organisers) who want a simple way to present their brand and access tools for managing digital gift cards, tickets, and vouchers.
- **Customers** – people visiting a business’s storefront to learn about services and, in future, buy digital products.
- **Site Admin** – the platform owner/administrator who manages the overall system and can monitor or support business users.

### Key User Stories

#### Business Owner

- As a business owner, I want to register and log in so that I can securely access my storefront and dashboard.
- As a business owner, I want to create and edit my storefront details (name, description, contact info, logo) so that my customers see accurate, professional information about my business.
- As a business owner, I want to subscribe to MintKit Hub using Stripe so that I can unlock access to the MintKit app and its digital product tools.
- As a business owner, I want to see my current subscription status (plan, renewal date, active/inactive) on my dashboard so that I know whether I still have access to MintKit features.
- As a business owner, I want a clear link from my dashboard to open the MintKit app so that I can quickly start creating or managing gift cards, tickets, and vouchers.

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


## 5. Technologies Used

<details>
  <summary>Click to expand <b>Technologies used</b></summary>

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

### Payments & External Services

- **Stripe** – handles subscription payments for business owners using Stripe Checkout and Stripe’s test mode during development.
- **External MintKit App** – a separate third-party application (e.g. hosted at `studio.mintkit.co.uk`) that business owners access after subscribing. It is **integrated**, but not part of this Django codebase.

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

python -m venv venv
## Windows
venv\Scripts\activate

3. **Install dependencies**

(A requirements.txt file will be added as the project develops.)

pip install -r requirements.txt

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


## 10. Stripe Integration & External MintKit App

<details>
  <summary>Click to expand <b>Stripe & MintKit integration details</b></summary>

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

</details>


## 11. CI Assessment Criteria Mapping

<details>
  <summary>Click to expand <b>CI assessment criteria mapping</b></summary>

This section provides a high-level mapping between the Code Institute **Full Stack Frameworks with Django** unit learning outcomes and how MintKit Hub addresses them. It is designed as a quick reference for assessors; further detail is available in the relevant README sections and docs.

---

### Learning Outcome 1  
Design, develop and implement a Full Stack Django application with a relational database, multiple apps, and an interactive front end.   

| Area / Criteria (summary) | How MintKit Hub addresses it |
|---------------------------|------------------------------|
| 1.1 Full Stack Django app with relational DB & multiple apps | Django project with separate apps such as `accounts`, `storefronts`, `subscriptions`, and `core`, all backed by a relational database (SQLite locally, Postgres on Heroku). |
| 1.2 Front-end design, UX & accessibility | Responsive templates using HTML, CSS and Bootstrap, with clear navigation (main menu, dashboard, storefront pages) and UX built around real user stories (business owner, customer, admin). |
| 1.3 Implementation of full stack features | Authentication, dashboard, storefront management, subscription logic, and integration with an external MintKit app provide an interactive full stack experience. |
| 1.4 Forms with validation | Django forms for registration/login, profile editing, and storefront creation/editing include validation and user feedback messages. |
| 1.5–1.8 Django structure, URLs & navigation | Django file structure follows conventions; URLs are defined consistently per app; a main navigation menu and shared base template are used across the site. |
| 1.9–1.10 Python logic & clean code | Business logic (trial status, subscription checks, storefront visibility rules) is implemented in views/models, using conditionals and loops where appropriate, with attention to clean, readable code. |
| 1.11 Testing procedures | Manual testing of key flows plus documented procedures in `docs/TESTING.md` (functional, UX, responsiveness, data behaviour), summarised in README Section 7. |

---

### Learning Outcome 2  
Design and implement a relational data model, application features and business logic to manage relational data.   

| Area / Criteria (summary) | How MintKit Hub addresses it |
|---------------------------|------------------------------|
| 2.1 Relational database schema | ERD designed with `User`, `Profile`, `Storefront`, `SubscriptionPlan`, `Subscription`, and `MintKitAccess` models and clear relationships, documented in Section 3 and `docs/ERD.md`. |
| 2.2 Two or more custom models | Multiple original Django models (`Profile`, `Storefront`, `SubscriptionPlan`, `Subscription`, `MintKitAccess`) go beyond the built-in `User`. |
| 2.3 Form for creating records | Storefront and profile forms allow users to create and update database records (in addition to auth forms). |
| 2.4 CRUD functionality | Business owners can create, read, update and (where appropriate) delete data such as storefronts or profile details; admin can manage all core models via Django admin. |
| Merit: describe schema in README | Section 3 and the ERD documentation describe the data model and relationships in a clear, structured way. |

---

### Learning Outcome 3  
Identify and apply authorisation, authentication and permission features.   

| Area / Criteria (summary) | How MintKit Hub addresses it |
|---------------------------|------------------------------|
| 3.1 Authentication & reason for login | Django auth used for registration/login; users must log in to create/manage storefronts, view dashboards and manage subscriptions. |
| 3.2 Login/register for anonymous users only | Registration and login pages are shown only to anonymous users; logged-in users are redirected appropriately. |
| 3.3 Prevent direct datastore access | Views are protected so non-admin users can only access their own data via the code (e.g. only the owner can edit their storefront); Django admin is restricted to superusers. |
| Permissions & roles | Dashboard and management views require authentication; public storefront pages are read-only and available to all, while internal management is restricted to owners/admin. |

---

### Learning Outcome 4  
Design, develop and integrate an e-commerce payment system (e.g. Stripe).   

| Area / Criteria (summary) | How MintKit Hub addresses it |
|---------------------------|------------------------------|
| 4.1 Django app with e-commerce using Stripe | The `subscriptions` app integrates with Stripe Checkout to handle subscription-based payments for business owners. |
| 4.2 Feedback on successful/failed purchases | Success and cancel pages (and dashboard messages) inform users whether the subscription process completed or was cancelled, with clear guidance on next steps. |
| Trial + subscription logic | Trial period and Stripe subscription status determine access to MintKit; this business logic is visible and testable via the dashboard. |

---

### Learning Outcome 5  
Use git-based version control, document development, and deploy to a cloud hosting platform.   

| Area / Criteria (summary) | How MintKit Hub addresses it |
|---------------------------|------------------------------|
| 5.1 Deployment | Final version deployed to Heroku with Postgres; deployment checked to match local development environment (Section 10 & `docs/DEPLOYMENT.md`). |
| 5.2 Clean deployed code | Deployed code free of commented-out blocks and broken internal links; navigation and URLs checked in testing. |
| 5.3 Security & settings | Sensitive data kept in environment variables (`SECRET_KEY`, Stripe keys, database URL); `DEBUG` off in production and `ALLOWED_HOSTS` configured. |
| 5.4 Git-based version control | Development history documented through regular, descriptive Git commits on GitHub, showing the project’s evolution. |
| 5.5–5.6 README & documentation | This README (plus `docs/` files) is structured, written in consistent Markdown, and documents purpose, UX, data schema, testing, and deployment, as required by the spec. |

</details>


