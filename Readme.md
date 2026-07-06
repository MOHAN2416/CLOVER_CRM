# 🚀 Clover CRM: Autonomous Multi-Tenant Enterprise Data & Intelligence Hub

Clover CRM is a high-performance, low-latency, multi-tenant B2B customer relationship management ecosystem engineered completely on an open-source local execution stack. The platform handles row-level data isolation for multiple sales tenants, features autonomous data compliance logging, hosts a continuous background thread task scheduler, runs public API lead-ingestion webhooks, and deploys local generative AI agents via asynchronous token streaming at the edge.

---

## 🏗️ Core System Architecture

The application is built around a decoupled, highly concurrent multi-threaded architecture designed to keep transaction latency minimal while processing resource-heavy local language models.

```text
              ┌────────────────────────────────────────┐
              │          Public Inbound Form           │
              │   (http://127.0.0.1:5000/join)         │
              └───────────────────┬────────────────────┘
                                  │
                                  ▼ (Asynchronous JSON HTTP POST)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               CLOVER CRM BACKEND CORE                                 │
│                                                                                        │
│ ┌─────────────────────────┐   ┌─────────────────────────┐   ┌────────────────────────┐ │
│ │   User Security Auth    │   │  External Webhook API   │   │  Local Inference Client│ │
│ │  (/login & /signup)     │   │   (/api/webhook/lead)   │   │  (Ollama Stream Core)  │ │
│ └───────────┬─────────────┘   └────────────┬────────────┘   └───────────▲────────────┘ │
└─────────────┼──────────────────────────────┼────────────────────────────┼──────────────┘
              │                              │                            │
              ▼                              ▼                            │ (Local Host Engine)
┌─────────────────────────────────────────────────────────────────────────┼──────────────┐
│                            DATABASE ENGINE                              │              │
│                                                                         │              │
│   ┌─────────────────────────────────────────────────────────┐           │              │
│   │               MySQL Connection Pool (Size=5)            │           │              │
│   │                                                         │           │              │
│   │  ┌────────────────┐    ┌─────────────────────────────┐  │    ┌──────▼──────────┐   │
│   │  │  users Table   │    │       accounts Table        │  │    │ qwen2.5:3b      │   │
│   │  └───────┬────────┘    │ (Row Isolated via rep_id)   │  │    │ -instruct       │   │
│   │          │             └──────────────┬──────────────┘  │    └─────────────────┘   │
│   │          ▼ Foreign Key                ▼                 │                          │
│   │  ┌────────────────────────────────────┴──────────────┐  │                          │
│   │  │  Native AFTER UPDATE Status Trigger               │  │                          │
│   │  └────────────────────┬──────────────────────────────┘  │                          │
│   │                       ▼                                 │                          │
│   │  ┌───────────────────────────────────────────────────┐  │                          │
│   │  │  account_audit_logs (Compliance Trail Ledger)     │  │                          │
│   │  └───────────────────────────────────────────────────┘  │                          │
│   └─────────────────────────────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┼──────────────┘
                                  ▲
                                  │ (Continuous SQL Polling Loops)
                       ┌──────────┴─────────────────────┐
                       │     Autonomous Background      │
                       │     Watchdog (scheduler.py)    │
                       └────────────────────────────────┘
```

---

## 🛠️ Deep-Dive Technical Feature Matrix

### 1. Multi-Tenant Row-Level Data Isolation (RBAC)
* **Security Primitives:** Complete User Session Guarding implemented using Flask signed encrypted sessions (`app.secret_key`).
* **Cryptographic Layer:** Passwords are fully hashed on ingress using salted PBKDF2 algorithms via `werkzeug.security` (`generate_password_hash` & `check_password_hash`). Raw text strings are never stored.
* **Isolation Guard:** All internal diagnostic and dashboard data loading vectors enforce parameter-driven SQL filtering bound strictly to the user context (`WHERE rep_id = %s`), completely eliminating data-bleeding anomalies between separate sales personnel (e.g., Mohan vs. Rohan).

### 2. Autonomous Compliance Auditing (Native DB Triggers)
* **Architecture Layer:** Deployed natively within the database kernel to guarantee unalterable integrity, fully bypassing application runtime faults.
* **Mechanism:** An `AFTER UPDATE` execution trigger monitors state migrations in the lifecycle metrics of client entries. If a customer status updates (e.g., from `Lead` to `Active Customer`), the hook executes an atomic write operation appending data parameters containing the prior state, subsequent state, client identifier, and accurate microsecond server timestamps into a separate `account_audit_logs` tracking ledger.

### 3. Edge-AI Agentic Workflows & Asynchronous Token Streaming
* **Local Hardware Target:** Alibaba's state-of-the-art **Qwen 2.5 3B-Instruct** large language model running locally via Ollama.
* **Latency Optimization:** Implements Server-Sent Events (SSE) token streaming logic. Instead of hanging the user interface during multi-second compute blocks, raw inference strings stream chunk-by-chunk directly onto the client viewport interface using asynchronous JavaScript stream readers (`TextDecoder()` loop parsing incoming binary fetch arrays).
* **Context Locking:** Deploys a rigorous structural system prompt container enforcing localized CRM context, completely stripping corporate bias and branding leaks.

### 4. Continuous Background Concurrency Daemon
* **Execution Vector:** Runs continuously within a detached worker terminal thread (`scheduler.py`), simulating real enterprise production cron job workers.
* **Optimization Layer:** Runs a light SQL polling operation every 10 seconds checking task horizons. The daemon detects uncompleted tasks whose deadlines have slipped behind current execution parameters and triggers systemic console alerts automatically, removing single-point failure liabilities from user page refreshes.

### 5. Automated Omni-Channel Inbound Webhooks
* **Interface Port:** Provides a clean, secure ingestion gateway via an active `/api/webhook/lead` endpoint.
* **Normalization Matrix:** Accepts data packages from front-facing public form fields (`/join`), extracts raw values, accounts for optional properties, balances statement variables, and commits records cleanly to the core connection pool.

---

## 🗄️ Relational Database Schema Architecture

The relational schema maps out strict physical foreign keys to maintain transactional integrity across tables:

```sql
-- Active Schema Context Initialization
CREATE DATABASE IF NOT EXISTS crm_db;
USE crm_db;

-- 1. Users Security Matrix Table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Core Accounts Lifecycle Table
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    company VARCHAR(255) DEFAULT 'Independent',
    source VARCHAR(100) DEFAULT 'Direct Inbound',
    status VARCHAR(50) DEFAULT 'Lead',
    rep_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account_rep FOREIGN KEY (rep_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 3. Permanent Compliance Audit Ledger
CREATE TABLE account_audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    account_name VARCHAR(255),
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- 4. Tasks Timeline Table
CREATE TABLE tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    due_date DATETIME NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- 5. Native Status Interception Change Trigger
DELIMITER $$
CREATE TRIGGER after_account_status_update
AFTER UPDATE ON accounts
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO account_audit_logs (account_id, account_name, old_status, new_status)
        VALUES (OLD.account_id, OLD.name, OLD.status, NEW.status);
    END IF;
END$$
DELIMITER ;
```

---

## 📂 Repository Directory Layout

```text
clover-crm/
│
├── app.py                  # Master Flask Application Core Router & API Gateway
├── db.py                   # Centralized High-Performance MySQL Connection Pool (Size=5)
├── scheduler.py            # Autonomous Task-Monitoring Background Watchdog Process
│
├── templates/              # Secure UI Interface Views
│   ├── login.html          # Clean Dark-Mode User Authentication Access Port
│   ├── signup.html         # Secure Password-Hashing Representative Sign Up Page
│   ├── index.html          # Premium Dark-Mode Hub Dashboard UI (Token Streaming Interface)
│   └── join.html           # Public Website Landing Page & Automated Form Webhook
│
└── static/                 # Stylesheets & Static Interface Configurations
```

---

## 🚀 Step-by-Step Production Deployment Guide

Ensure your environment is running Ubuntu 22.04 LTS or equivalent before setting up the stack.

### 1. Clone & Core Dependency Ingestion
```bash
sudo apt update
sudo apt install python3-pip mysql-server python3-dev -y
pip install flask mysql-connector-python werkzeug ollama
```

### 2. Provision Local AI Models via Ollama
```bash
# Pull down the high-performance 3B instruct layer
ollama pull qwen2.5:3b-instruct
```

### 3. Initialize the Multi-Threaded Architecture
To simulate a real multi-tenant production system, launch your application modules across two separate terminal tabs:

**Terminal Tab 1** (Flask API Gateway & AI Streaming Engine):
```bash
python app.py
```

**Terminal Tab 2** (Autonomous Task Watchdog Daemon Process):
```bash
python scheduler.py
```

---

## 🎯 Verification Framework for Live Evaluation

When presenting this project to the evaluation committee, execute this sequence to demonstrate full end-to-end functionality:

* **Access Authentication Enforcement:** Open `http://127.0.0.1:5000/`. Notice the application immediately blocks access and redirects you to the `/login` portal. Create an account for yourself, log in, and view your personalized workspace.
* **Live Automated Inbound Ingestion:** Open an Incognito Window and go to the public-facing landing page at `http://127.0.0.1:5000/join`. Submit a new lead entry. Check your primary admin dashboard window—the lead drops straight onto your active tables in real-time.
* **Real-Time Token Streaming Showcase:** Click "Draft Outreach" on a lead record. Watch the Qwen-2.5 local AI engine write tailored copy live on the dashboard UI, piece by piece, without any browser lag.
* **Database Isolation Proof:** Check your database console logs or show the `account_audit_logs` history table. Point out how the native MySQL trigger catches changes and logs them securely behind the scenes without needing any extra Python code.