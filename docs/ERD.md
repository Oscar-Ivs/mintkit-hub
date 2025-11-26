## Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USER {
        int id
        string username
        string email
        string password
    }

    PROFILE {
        int id
        string business_name
        string contact_email
        string logo
        datetime created_at
    }

    STOREFRONT {
        int id
        string slug
        string headline
        string description
        string contact_details
        boolean is_active
    }

    SUBSCRIPTIONPLAN {
        int id
        string name
        decimal price
        string stripe_price_id
        string description
        boolean is_active
    }

    SUBSCRIPTION {
        int id
        string stripe_customer_id
        string stripe_subscription_id
        string status
        datetime start_date
        datetime end_date
    }

    MINTKITACCESS {
        int id
        string external_identifier
        datetime last_accessed_at
    }

    %% Relationships
    USER ||--|| PROFILE : has
    PROFILE ||--o| STOREFRONT : owns
    PROFILE ||--o{ SUBSCRIPTION : "has subscriptions"
    SUBSCRIPTION }o--|| SUBSCRIPTIONPLAN : "uses plan"
    PROFILE ||--o| MINTKITACCESS : "integrates via"
