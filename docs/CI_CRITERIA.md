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
| 4.1 Django app with e-commerce using Stripe | The `subscriptions` app integrates with Stripe (payments) — *in progress* to handle subscription-based payments for business owners. |
| 4.2 Feedback on successful/failed purchases | Success and cancel pages (and dashboard messages) inform users whether the subscription process completed or was cancelled, with clear guidance on next steps. |
| Trial + subscription logic | Trial period and Stripe (payments) — *in progress* status determine access to MintKit; this business logic is visible and testable via the dashboard. |

---

### Learning Outcome 5  
Use git-based version control, document development, and deploy to a cloud hosting platform.   

| Area / Criteria (summary) | How MintKit Hub addresses it |
|---------------------------|------------------------------|
| 5.1 Deployment | Final version deployed to Heroku with Postgres; deployment checked to match local development environment (Section 10 & [Deployment Documentation](README.md#10-deployment-and-local-development). |
| 5.2 Clean deployed code | Deployed code free of commented-out blocks and broken internal links; navigation and URLs checked in testing. |
| 5.3 Security & settings | Sensitive data kept in environment variables (`SECRET_KEY`, Stripe keys, database URL); `DEBUG` off in production and `ALLOWED_HOSTS` configured. |
| 5.4 Git-based version control | Development history documented through regular, descriptive Git commits on GitHub, showing the project’s evolution. |
| 5.5–5.6 README & documentation | This README (plus `docs/` files) is structured, written in consistent Markdown, and documents purpose, UX, data schema, testing, and deployment, as required by the spec. |
