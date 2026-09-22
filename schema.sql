CREATE DATABASE IF NOT EXISTS crm_db;
USE crm_db;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_reps (
    rep_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE
);

CREATE TABLE IF NOT EXISTS accounts (
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

CREATE TABLE IF NOT EXISTS account_audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    account_name VARCHAR(255),
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    rep_id INT,
    task_type VARCHAR(100) NOT NULL,
    due_date DATETIME NOT NULL,
    remarks TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS deals (
    deal_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    rep_id INT,
    deal_value DECIMAL(10,2) DEFAULT 0.0,
    stage VARCHAR(50) DEFAULT 'None',
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

DROP TRIGGER IF EXISTS after_account_status_update;

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

SELECT 'crm_db schema initialized successfully!' AS status;
