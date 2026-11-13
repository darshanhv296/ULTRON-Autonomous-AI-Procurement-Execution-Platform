-- ============================================================================
-- ULTRON - Autonomous AI Procurement and Payment Agent
-- MySQL 8.0+ Relational Database Schema (ultron)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `ultron`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `ultron`;

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS `users` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `name` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `role` VARCHAR(64) NOT NULL DEFAULT 'ADMIN',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. OBJECTIVES TABLE (Procurement Requests)
CREATE TABLE IF NOT EXISTS `objectives` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `user_id` VARCHAR(64) NOT NULL,
  `title` VARCHAR(512) NOT NULL,
  `description` TEXT NOT NULL,
  `status` ENUM('DRAFT', 'PLANNING', 'EXECUTING', 'AWAITING_APPROVAL', 'APPROVED', 'COMPLETED', 'FAILED') NOT NULL DEFAULT 'PLANNING',
  `budget_limit` DECIMAL(12, 2) NULL DEFAULT NULL,
  `currency` VARCHAR(16) NOT NULL DEFAULT 'USD',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_objectives_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. CONSTRAINTS TABLE
CREATE TABLE IF NOT EXISTS `constraints` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `objective_id` VARCHAR(64) NOT NULL,
  `constraint_type` ENUM('max_budget', 'delivery_deadline', 'preferred_vendor', 'quality_tier', 'compliance') NOT NULL,
  `constraint_value` VARCHAR(512) NOT NULL,
  `is_hard_constraint` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_constraints_objective` FOREIGN KEY (`objective_id`) REFERENCES `objectives` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. MISSIONS TABLE (Multi-Agent Execution Workflows)
CREATE TABLE IF NOT EXISTS `missions` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `objective_id` VARCHAR(64) NOT NULL,
  `status` ENUM('IDLE', 'RUNNING', 'COMPLETED', 'REPLANNING', 'FAILED') NOT NULL DEFAULT 'IDLE',
  `current_stage` VARCHAR(255) NOT NULL,
  `agent_assigned` VARCHAR(128) NOT NULL,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL DEFAULT NULL,
  CONSTRAINT `fk_missions_objective` FOREIGN KEY (`objective_id`) REFERENCES `objectives` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. PRODUCT SNAPSHOTS TABLE (Channel3 & Catalog Products)
CREATE TABLE IF NOT EXISTS `product_snapshots` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `external_id` VARCHAR(128) NOT NULL,
  `source` VARCHAR(64) NOT NULL DEFAULT 'Channel3',
  `title` VARCHAR(512) NOT NULL,
  `description` TEXT NOT NULL,
  `price` DECIMAL(12, 2) NOT NULL,
  `currency` VARCHAR(16) NOT NULL DEFAULT 'USD',
  `vendor` VARCHAR(255) NOT NULL,
  `category` VARCHAR(128) NOT NULL,
  `image_url` VARCHAR(1024) NOT NULL,
  `product_url` VARCHAR(1024) NULL DEFAULT NULL,
  `rating` DECIMAL(3, 2) NOT NULL DEFAULT 4.50,
  `in_stock` TINYINT(1) NOT NULL DEFAULT 1,
  `specs_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. PURCHASE PLANS TABLE
CREATE TABLE IF NOT EXISTS `plans` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `objective_id` VARCHAR(64) NOT NULL,
  `version` INT NOT NULL DEFAULT 1,
  `status` ENUM('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'SUPERSEDED', 'PAID') NOT NULL DEFAULT 'SUBMITTED',
  `total_amount` DECIMAL(12, 2) NOT NULL,
  `currency` VARCHAR(16) NOT NULL DEFAULT 'USD',
  `notes` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_plans_objective` FOREIGN KEY (`objective_id`) REFERENCES `objectives` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. PLAN ITEMS TABLE
CREATE TABLE IF NOT EXISTS `plan_items` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `plan_id` VARCHAR(64) NOT NULL,
  `product_snapshot_id` VARCHAR(64) NOT NULL,
  `title` VARCHAR(512) NOT NULL,
  `unit_price` DECIMAL(12, 2) NOT NULL,
  `quantity` INT NOT NULL DEFAULT 1,
  `total_price` DECIMAL(12, 2) NOT NULL,
  `currency` VARCHAR(16) NOT NULL DEFAULT 'USD',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_plan_items_plan` FOREIGN KEY (`plan_id`) REFERENCES `plans` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. APPROVALS TABLE (Human Governance Checkpoints)
CREATE TABLE IF NOT EXISTS `approvals` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `plan_id` VARCHAR(64) NOT NULL,
  `plan_version` INT NOT NULL DEFAULT 1,
  `approver_name` VARCHAR(255) NOT NULL,
  `approver_role` VARCHAR(128) NOT NULL,
  `status` ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
  `approved_amount` DECIMAL(12, 2) NOT NULL,
  `currency` VARCHAR(16) NOT NULL DEFAULT 'USD',
  `comments` TEXT NOT NULL,
  `decided_at` DATETIME NULL DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_approvals_plan` FOREIGN KEY (`plan_id`) REFERENCES `plans` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. PAYMENT ORDERS TABLE (PayPal Sandbox Transactions & Fulfillment Lifecycle)
CREATE TABLE IF NOT EXISTS `payment_orders` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `plan_id` VARCHAR(64) NOT NULL,
  `approval_id` VARCHAR(64) NOT NULL,
  `paypal_order_id` VARCHAR(128) NOT NULL,
  `capture_id` VARCHAR(128) NULL DEFAULT NULL,
  `amount` DECIMAL(12, 2) NOT NULL,
  `currency` VARCHAR(16) NOT NULL DEFAULT 'USD',
  `environment` VARCHAR(32) NOT NULL DEFAULT 'sandbox',
  `status` ENUM('CREATED', 'PAYER_ACTION_REQUIRED', 'APPROVED', 'COMPLETED', 'VOIDED', 'FAILED', 'CANCELLED', 'REFUNDED', 'UNVERIFIED') NOT NULL DEFAULT 'CREATED',
  `checkout_url` VARCHAR(1024) NULL DEFAULT NULL,
  `payment_metadata` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_paypal_order_id` (`paypal_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. AI RUNS TABLE (OpenRouter / Groq Agent Execution Telemetry)
CREATE TABLE IF NOT EXISTS `ai_runs` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `objective_id` VARCHAR(64) NULL DEFAULT NULL,
  `mission_id` VARCHAR(64) NULL DEFAULT NULL,
  `provider` VARCHAR(64) NOT NULL,
  `model` VARCHAR(128) NOT NULL,
  `agent_role` VARCHAR(128) NOT NULL,
  `prompt_summary` TEXT NOT NULL,
  `response_summary` TEXT NOT NULL,
  `tokens_used` INT NOT NULL DEFAULT 0,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `status` ENUM('SUCCESS', 'FALLBACK_USED', 'FAILED') NOT NULL DEFAULT 'SUCCESS',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. OBJECTIVE EVENTS TABLE (Immutable Audit Trail)
CREATE TABLE IF NOT EXISTS `objective_events` (
  `id` VARCHAR(64) NOT NULL PRIMARY KEY,
  `objective_id` VARCHAR(64) NOT NULL,
  `event_type` VARCHAR(128) NOT NULL,
  `actor` VARCHAR(128) NOT NULL,
  `message` TEXT NOT NULL,
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_objective_events_obj` (`objective_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- INITIAL SEED DATA (Protected Historical PayPal Sandbox Records & Admin User)
-- ============================================================================
INSERT IGNORE INTO `users` (`id`, `name`, `email`, `role`) VALUES
('usr-admin-01', 'Demo Administrator', 'demo@example.invalid', 'CHIEF_PROCUREMENT_ARCHITECT');
