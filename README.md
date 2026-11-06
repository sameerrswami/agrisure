# 🌱 AgriSure – Transparent Contract Farming Marketplace

AgriSure is an end-to-end, enterprise-grade **Contract Farming Marketplace** built with **Python 3.9, Django 4.2 LTS, Tailwind CSS, Alpine.js, HTMX, ReportLab, and Razorpay**.

It bridges the structural gap between smallholder Indian farmers and institutional agribusiness buyers (mills, food processors, exporters, and retail chains) by providing legal contract agreements, transparent two-way price negotiations, milestone-based escrow payments, GPS farm-gate mapping, multi-shipment delivery tracking, and administrative arbitration.

---

## 📋 Table of Contents

- [Problem Statement & Solution](#-problem-statement--solution)
- [System Architecture & Technology Stack](#-system-architecture--technology-stack)
- [Modular Application Structure](#-modular-application-structure)
- [Key Features & Capabilities](#-key-features--capabilities)
- [Security & Legal Compliance](#-security--legal-compliance)
- [Quick Start & Local Setup](#-quick-start--local-setup)
- [Demonstration Accounts & Test Logins](#-demonstration-accounts--test-logins)
- [End-to-End Business Workflows](#-end-to-end-business-workflows)
- [Production Deployment](#-production-deployment)
- [Automated Testing Suite](#-automated-testing-suite)
- [Health Check & Monitoring](#-health-check--monitoring)

---

## 🎯 Problem Statement & Solution

### The Challenge
Indian agriculture suffers from severe market uncertainty:
- **Price Volatility**: Farmers face bumper crop gluts and predatory post-harvest farmgate price crashes.
- **Fragmented Intermediaries**: Middlemen absorb up to 45% of value, leaving farmers with low margins.
- **Procurement Risks for Buyers**: Institutional food processors face unreliable supply volumes, uncertain quality grades, and delivery defaults.
- **Informal Agreements**: Oral commitments lead to unresolvable disputes when market spot prices fluctuate.

### The AgriSure Solution
AgriSure replaces informal verbal agreements with enforceable, transparent, digital contracts:
1. **Assured Off-Take**: Farmers lock in guaranteed prices and purchase volumes before sowing or harvesting.
2. **Quality Standards**: Contracts specify agreed parameters (moisture %, grain grade, organic certification).
3. **Escrow Financial Security**: Advance milestone deposits via Razorpay protect both parties before dispatch.
4. **Enforceable Legal Contracts**: Dual digital signatures backed by Section 10A of the Information Technology Act, 2000, with automated bilingual PDF generation.

---

## 🛠️ System Architecture & Technology Stack

AgriSure uses a modern, modular Django architecture designed for horizontal scalability, high reliability, and clean separation of concerns.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT / BROWSER INTERFACE                       │
│  Tailwind CSS  │  Alpine.js  │  HTMX Reactive UI  │  Chart.js  │ Leaflet│
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTPS / WSS
┌────────────────────────────────────▼───────────────────────────────────┐
│                     WSGI / ASGI APPLICATION LAYER                      │
│        Gunicorn (WSGI HTTP)        │      Daphne (Channels / ASGI)     │
│                 Django 4.2 LTS Application Framework                   │
└──────────────────┬─────────────────┬───────────────────┬───────────────┘
                   │                 │                   │
┌──────────────────▼──┐   ┌──────────▼────────┐   ┌──────▼───────────────┐
│ PERSISTENT DATABASE │   │ IN-MEMORY & CACHE │   │  EXTERNAL SERVICES   │
│   PostgreSQL 15     │   │   Redis 7 / Beat  │   │  Razorpay Gateway    │
│  (SQLite in dev)    │   │  Celery Workers   │   │  OpenStreetMap Tiles │
└─────────────────────┘   └───────────────────┘   └──────────────────────┘
```

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | Django | 4.2 LTS | Enterprise web framework, ORM, migrations, and routing |
| **Language** | Python | 3.9+ | Server runtime |
| **Relational Database** | PostgreSQL / SQLite | 15.x / 3.x | Transactional storage, relational constraints, foreign keys |
| **Static Asset Engine** | WhiteNoise | 6.7+ | Production static asset compression and caching |
| **CSS Architecture** | Tailwind CSS | 3.4 (CDN) | Emerald glassmorphism design system |
| **Frontend Micro-States**| Alpine.js | 3.13 | Modals, drawers, multi-tab switchers, dropdowns |
| **Dynamic UI Partials** | HTMX | 1.9 | Partial page swaps without full reload |
| **Mapping Engine** | Leaflet.js & OSM | 1.9.4 | Interactive farm coordinate picker and marketplace map |
| **Analytics & Metrics** | Chart.js | 4.4 | Dashboard analytics (earnings, crop split, contract volume) |
| **Document Generation** | ReportLab | 4.2+ | Digital bilingual contract agreements & GST payment receipts |
| **Payment Gateway** | Razorpay SDK | 2.0+ | Advance milestone deposits, balance escrow, webhooks |
| **Asynchronous Engine** | Celery & Redis | 5.3 / 7.x | Background notifications, digest processing, tasks |
| **ASGI / Real-Time** | Django Channels & Daphne | 4.0 / 4.1 | Direct participant messaging and socket coordination |
| **Containerization** | Docker & Compose | Multi-stage | Standardized development and production deployments |

---

## 🏛️ Modular Application Structure

AgriSure separates business domains into **16 independent Django applications**:

```
CA-Django/
├── agrisure/                    # Core project configuration
│   ├── settings.py              # Environment-driven settings with production security
│   ├── urls.py                  # Global routing table
│   ├── asgi.py                  # Real-time ASGI application
│   └── wsgi.py                  # Production WSGI application
│
├── apps/
│   ├── accounts/                # Custom User model, RBAC (Farmer, Buyer, Admin), KYC verification
│   ├── core/                    # Landing page, How-it-works, Terms, Health-check probe
│   ├── farmers/                 # Farmer profile, land records, irrigation facilities, dashboard
│   ├── buyers/                  # Buyer corporate profiles, procurement preferences, dashboard
│   ├── crops/                   # Crop listings, categories, photo galleries, stock tracking
│   ├── marketplace/             # Agricultural discovery, filters (state, price, grade), Leaflet map
│   ├── negotiations/            # 2-way offer/counter-offer engine, concurrency protection
│   ├── contracts/               # Contract state machine, dual digital signing, ReportLab PDF contracts
│   ├── payments/                # Razorpay checkout, HMAC-SHA256 verification, webhook processing, receipts
│   ├── deliveries/              # Multi-shipment dispatch, logistics carrier tracking, proof-of-delivery
│   ├── disputes/                # Dispute mediation dockets, evidence upload, administrator rulings
│   ├── reviews/                 # Post-contract fulfillment 5-star bilateral reviews and ratings
│   ├── messaging/               # Participant-isolated direct messaging conversations
│   ├── notifications/           # In-app real-time notification tray and event dispatch
│   ├── backoffice/              # Superuser Command Center, KYC approval queues, Chart.js analytics
│   └── audit/                   # Business-critical immutable event logs and administrative traces
│
├── static/                      # Custom CSS (glassmorphism), scripts, and assets
├── templates/                   # Semantic HTML5 templates organized by domain
├── Dockerfile                   # Multi-stage production container
├── docker-compose.yml           # Full-stack composition (Web, Postgres, Redis, Celery)
├── Procfile                     # Process definitions for PaaS hosting (PaaS / Heroku / Render)
├── requirements.txt             # Pinned production dependencies
└── seed_db.py                   # High-fidelity realistic Indian demonstration dataset seeder
```

---

## 🌟 Key Features & Capabilities

### 1. Farmer Operations & Farm Management
- **Complete Farmer Profile**: Agricultural land area (hectares/acres), soil type, irrigation sources (Tube well, Canal, Drip), farming methods (Organic, ZBNF, Conventional), and banking details.
- **KYC & Document Verification**: Upload 7/12 land extract, Aadhaar, Kisan Credit Card, or Organic certificates with status badges (`Not Submitted`, `Pending`, `Verified`, `Rejected`).
- **Interactive Farm Geolocation**: OpenStreetMap coordinate picker to position the farm gate on the map.
- **Agronomic Inventory Management**: Add crops with expected harvest windows, remaining quantities, quality specifications, and multiple gallery photographs.
- **Dynamic Farmer Dashboard**: Live statistics for total earnings, pending payments, active contracts, and incoming inquiries.

### 2. Buyer Procurement & Marketplace Discovery
- **Procurement Profiles**: GSTIN, company registration, preferred purchase commodities, delivery locations, and procurement volume requirements.
- **Advanced Marketplace Filtering**: Filter by category, organic status, quality grade, price range, state, district, and verified farmer badges.
- **Farm-Gate Map Search**: Leaflet-powered visual map showing crop listings with customized map pins, prices, and direct contract request buttons.
- **Wishlist & Produce Bookmarking**: Save produce to bookmarks for later negotiation or seasonal tracking.

### 3. Concurrency-Safe Price Negotiation Engine
- **Two-Way Counter-Offers**: Structured negotiation thread between farmer and buyer.
- **Database Row Locking**: Uses `select_for_update()` to prevent race conditions during offer acceptance.
- **Full Historical Audit Trail**: Retains every historical proposed price, quantity, delivery date, and negotiation memo.
- **One-Click Contract Generation**: Direct promotion of agreed terms into a formal binding contract.

### 4. Digital Legal Contracts & Bilingual ReportLab PDF
- **Dual Digital Signature Workflow**: Both parties sign digitally with legal timestamp recording, complying with Section 10A of the IT Act, 2000.
- **Dynamic ReportLab PDF Generator**: Generates professional, bilingual (English/Hindi) PDF contract agreements with contract identification watermarks, party particulars, crop specifications, payment milestones, and signature boxes.
- **Contract Versioning & Amendments**: Mutual amendment requests create versioned contract iterations (`v1` → `v2`).

### 5. Razorpay Payments & Financial Escrow
- **Milestone-Based Installments**: Support for advance payments (e.g. 20%), mid-harvest milestone payments (30%), and balance settlements (50%).
- **Server-Side HMAC-SHA256 Verification**: Tamper-proof payment signature validation via `RazorpayService`.
- **Idempotent Webhooks**: Asynchronous webhook handler (`/payments/webhook/`) verifying webhook signature headers and handling `payment.captured` events without double-crediting.
- **ReportLab PDF Payment Receipts**: Instant downloadable GST-compliant payment receipts.

### 6. Multi-Shipment Delivery Tracking & Proof-of-Delivery
- **Incremental Shipments**: Split large contracts across multiple dispatches.
- **Logistics Docket**: Track transport vehicle numbers, driver mobile numbers, dispatch dates, and transport notes.
- **Proof-of-Delivery (PoD)**: Buyer confirms received quantity and uploads weighbridge slips or delivery challan receipts.
- **Automatic Contract Fulfillment**: When cumulative confirmed deliveries equal contract quantity, contract transitions to `COMPLETED`.

### 7. Administrative Backoffice & Arbitration
- **Superuser Command Center**: 6 interactive Chart.js charts (GMV, monthly volume, crop distributions, dispute rates).
- **KYC Approval Queue**: Inspect farmer land extracts and buyer GSTIN certificates with one-click approval or rejection.
- **Dispute Docket**: Formal dispute management with evidence attachments, arbitration logs, and admin resolution rulings (Release Funds to Farmer / Refund Buyer / Split Escrow).
- **Audit Trails**: Immutable administrative activity tracking via `AdminAuditLog`.

### 8. Dual Theme System & Profile Management
- **Black & White (Dark / Light) Dual Theme**: Instant, zero-flicker theme switching with Tailwind CSS `darkMode: 'class'`, persistent `localStorage` sync, and system preference detection.
- **Profile Dropdown with One-Click Logout**: Dedicated user avatar menu in both public and dashboard headers with user info, role badge, theme switcher, and prominent **Log Out** button.
- **Profile Page Logout Actions**: Clear logout controls on general, farmer, and buyer profile pages.
- **Rich Agricultural Media**: Pillow-generated local sample media alongside high-definition Unsplash agricultural imagery fallbacks ensuring zero empty image placeholders across marketplace, wishlists, and produce details.


---

## 🔒 Security & Legal Compliance

- **Role-Based Access Control (RBAC)**: Enforced at both URL and view levels via `@farmer_required`, `@buyer_required`, and `@admin_required` decorators.
- **Object-Level Authorization**: Direct query verification prevents farmers or buyers from accessing unauthorized negotiations, contracts, messages, or payments.
- **Financial Security**: Zero storage of sensitive payment credentials (CVVs, PINs, card numbers). All payment interactions utilize Razorpay server-side verification.
- **Section 10A IT Act Compliance**: Electronic contract validity adherence through explicit mutual digital consents and cryptographic timestamp hashes.
- **Production Hardening**:
  - `SECURE_BROWSER_XSS_FILTER = True`
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`
  - `X_FRAME_OPTIONS = 'DENY'`
  - Automatic SSL redirect and HTTPS cookies when `DEBUG=False`.

---

## ⚡ Quick Start & Local Setup

### 1. Prerequisites
- Python 3.9, 3.10, or 3.11
- Git
- SQLite (pre-configured) or PostgreSQL 14+

### 2. Clone and Setup Environment
```bash
git clone https://github.com/your-org/agrisure.git
cd agrisure

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```
*(The default `.env` file uses SQLite and console email backend, ready to run immediately without external services).*

### 5. Apply Migrations
```bash
python3 manage.py migrate
```

### 6. Seed Realistic Indian Market Data
Populate categories, verified farmers, institutional buyers, crop listings, contracts, deliveries, payments, and reviews:
```bash
python3 seed_db.py
```

### 7. Run the Development Server
```bash
python3 manage.py runserver 127.0.0.1:8000
```
Open **http://127.0.0.1:8000/** in your web browser.

---

## 🔑 Demonstration Accounts & Test Logins

The database seeder provisions pre-configured user accounts representing each platform persona:

| Persona | Role | Email | Password | Primary Portal |
| :--- | :--- | :--- | :--- | :--- |
| **System Administrator** | Administrator | `admin@agrisure.in` | `AdminPassword123!` | `/backoffice/` |
| **Ramesh Kumar** | Verified Farmer | `ramesh.farmer@agrisure.in` | `FarmerPassword123!` | `/farmer/dashboard/` |
| **Suresh Patel** | Organic Farmer | `suresh.farmer@agrisure.in` | `FarmerPassword123!` | `/farmer/dashboard/` |
| **ITC Agri-Business** | Institutional Buyer | `procurement@itc-agri.in` | `BuyerPassword123!` | `/buyer/dashboard/` |
| **FreshPicks Retail** | Supermarket Buyer | `purchase@freshpicks.in` | `BuyerPassword123!` | `/buyer/dashboard/` |

---

## 🔄 End-to-End Business Workflows

### 🌾 The Farmer Journey
1. **Login & Profile Setup**: Log in as `ramesh.farmer@agrisure.in` → Visit Profile to inspect land records and KYC status.
2. **List Produce**: Navigate to *My Listings* → Click *Add New Crop* → Enter variety, harvest date, and quality parameters.
3. **Receive Negotiations**: Navigate to *Negotiations* → Review buyer counter-offers → Accept or propose alternative pricing.
4. **Sign Contract**: When agreed, open the Contract → Review terms and download preview PDF → Click *Sign Contract*.
5. **Dispatch Shipments**: After buyer deposits escrow, go to *Delivery Tracking* → Log vehicle number and dispatched quantity.
6. **Receive Escrow Settlement**: View payment receipts under *Payments & Receipts*.

### 🏢 The Buyer Journey
1. **Login & Explore Marketplace**: Log in as `procurement@itc-agri.in` → Open *Marketplace* or the *Interactive Map*.
2. **Filter & Bookmark**: Filter for `Organic Certified` Wheat or Cotton in Maharashtra/Gujarat → Add to Wishlist.
3. **Initiate Contract Offer**: Click *Request Contract* → Enter desired quantity (e.g. 200 quintals) and proposed price.
4. **Negotiate Terms**: Exchange comments and counter-offers until consensus is reached.
5. **Execute Contract & Pay Escrow**: Digitally sign agreement → Click *Pay Advance Escrow* → Complete Razorpay test checkout.
6. **Confirm Delivery & Review**: When truck arrives, verify weight slip → Click *Confirm Delivery* → Rate farmer 5 stars.

### 🛡️ The Administrator Journey
1. **Login to Command Center**: Log in as `admin@agrisure.in` → Visit `/backoffice/`.
2. **Platform Metrics**: Inspect live charts for Total GMV, Active Contracts, and Commodity Breakdown.
3. **KYC Verification**: Navigate to *Farmer KYC Queue* → Review uploaded 7/12 land extract → Click *Verify Farmer*.
4. **Dispute Resolution**: Open *Dispute Mediation Center* → Review buyer complaint & farmer dispatch notes → Issue binding settlement.

---

## 🚀 Production Deployment

### Option A: Render Cloud Deployment (1-Click Blueprint)
AgriSure comes pre-configured with [`render.yaml`](render.yaml) and [`build.sh`](build.sh) for zero-config automated deployment on Render:

1. Push your code to your **GitHub** repository.
2. Sign in to [Render Dashboard](https://dashboard.render.com/) and click **New + > Blueprint**.
3. Select your GitHub repository. Render will automatically parse `render.yaml` and provision:
   - Python Web Service (running Gunicorn with WhiteNoise static compression)
   - PostgreSQL 15 Managed Database
   - Redis 7 Instance
4. In the Render Web Service settings, enter your optional **Razorpay** keys (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`).
5. Render automatically executes `build.sh` (collectstatic + migrations) and launches the application.

---

### Option B: Vercel Serverless Deployment
AgriSure includes native [`vercel.json`](vercel.json) and [`build_files.sh`](build_files.sh) for serverless edge deployment on Vercel:

1. Install the Vercel CLI (`npm i -g vercel`) or import your repository directly at [vercel.com](https://vercel.com).
2. Set Environment Variables in your Vercel Project Settings:
   - `SECRET_KEY`: `<your-random-secret-key>`
   - `DEBUG`: `False`
   - `DATABASE_URL`: Your hosted PostgreSQL connection string (e.g., Supabase, Neon, or Railway)
   - `ALLOWED_HOSTS`: `.vercel.app`
3. Deploy via CLI or Git push:
   ```bash
   vercel --prod
   ```

---

### Option C: GitHub Actions CI/CD Pipeline
Continuous integration is configured in [`.github/workflows/django-ci.yml`](.github/workflows/django-ci.yml):
- Automatically triggers on every `push` and `pull_request` to `main` and `master`.
- Sets up Python 3.9, installs pinned dependencies, verifies `python manage.py check`, checks WhiteNoise `collectstatic`, and runs the entire automated test suite (`python manage.py test`).

---

### Option D: Multi-Container Docker Deployment (Self-Hosted)
AgriSure includes a production-ready `Dockerfile` and `docker-compose.yml`.

```bash
# Build and run the entire stack (PostgreSQL, Redis, Web, Celery)
docker-compose up --build -d

# Verify all containers are healthy
docker-compose ps

# Run database migrations and seeding inside the container
docker-compose exec web python manage.py migrate
docker-compose exec web python seed_db.py
```
The application will be live at `http://localhost:8000`.

---

### Option E: Cloud PaaS Deployment (Heroku / Railway)
The project includes a production `Procfile` configured for containerized web and background worker execution:

```
release: python manage.py migrate --noinput
web: gunicorn agrisure.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 60
worker: celery -A agrisure worker -l info --concurrency 2
beat: celery -A agrisure beat -l info
```


---

## 🧪 Automated Testing Suite

AgriSure features a comprehensive automated test suite testing model validations, RBAC isolation, state machines, financial calculations, and PDF generation across all apps.

```bash
# Run all automated tests
python3 manage.py test

# Run tests for specific modules
python3 manage.py test apps.contracts
python3 manage.py test apps.payments
python3 manage.py test apps.deliveries
python3 manage.py test apps.disputes
python3 manage.py test apps.backoffice
python3 manage.py test apps.marketplace
```

### Test Suite Execution Output
```
Found 53 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
.....................................................
----------------------------------------------------------------------
Ran 53 tests in ~60s

OK
Destroying test database for alias 'default'...
```

---

## 🩺 Health Check & Monitoring

AgriSure provides a dedicated, lightweight JSON health-check endpoint for container orchestrators (Kubernetes liveness/readiness probes), uptime monitors, and load balancers:

```http
GET /health/
```

### Healthy Response (`200 OK`)
```json
{
  "status": "healthy",
  "service": "agrisure-web",
  "version": "1.0.0",
  "database": "connected"
}
```

### Degraded Response (`503 Service Unavailable`)
```json
{
  "status": "degraded",
  "database": "error: connection to server on socket failed"
}
```

---

## 📄 License & Attribution

This project is built and maintained for agricultural empowerment and contract farming modernization. Distributed under the **MIT License**.
