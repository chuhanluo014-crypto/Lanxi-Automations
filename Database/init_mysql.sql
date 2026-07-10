CREATE DATABASE IF NOT EXISTS xhs_ip_lab
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE xhs_ip_lab;

CREATE TABLE IF NOT EXISTS xhs_samples (
  id INT NOT NULL,
  note_id VARCHAR(80) NOT NULL DEFAULT '',
  url VARCHAR(1200) NOT NULL DEFAULT '',
  title TEXT NULL,
  content MEDIUMTEXT NULL,

  author_id VARCHAR(160) NOT NULL DEFAULT '',
  author_name VARCHAR(255) NOT NULL DEFAULT '',

  likes INT UNSIGNED NOT NULL DEFAULT 0,
  comments INT UNSIGNED NOT NULL DEFAULT 0,
  collects INT UNSIGNED NOT NULL DEFAULT 0,

  tags TEXT NULL,
  images TEXT NULL,
  local_image_path TEXT NULL,

  scraped_at DATETIME NULL,
  media_type VARCHAR(50) NOT NULL DEFAULT '',
  push_time DATE NULL,

  topic VARCHAR(255) NOT NULL DEFAULT '',
  scene VARCHAR(255) NOT NULL DEFAULT '',
  emotion VARCHAR(255) NOT NULL DEFAULT '',
  hook VARCHAR(255) NOT NULL DEFAULT '',
  reusable_structure VARCHAR(255) NOT NULL DEFAULT '',
  risk_level VARCHAR(50) NOT NULL DEFAULT '',
  keep_status VARCHAR(50) NOT NULL DEFAULT '',
  notes TEXT NULL,
  review_status VARCHAR(50) NOT NULL DEFAULT '',

  imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uq_xhs_samples_note_id (note_id),
  KEY idx_xhs_samples_author_name (author_name),
  KEY idx_xhs_samples_push_time (push_time),
  KEY idx_xhs_samples_keep_status (keep_status),
  KEY idx_xhs_samples_review_status (review_status),
  KEY idx_xhs_samples_risk_level (risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

