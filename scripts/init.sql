-- NiceTool 最新数据库结构。仅用于初始化新数据库，不包含业务数据和外键。
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS tools (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project VARCHAR(100) NOT NULL,
    filename VARCHAR(200) NOT NULL,
    display_name VARCHAR(200) NOT NULL DEFAULT '',
    description VARCHAR(1000) NULL,
    current_version VARCHAR(50) NULL,
    tags VARCHAR(500) NULL,
    creator VARCHAR(100) NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME NULL,
    UNIQUE KEY uq_tool_project_filename (project, filename),
    KEY ix_tools_project (project)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tool_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tool_id INT NOT NULL,
    version VARCHAR(50) NOT NULL,
    content LONGTEXT NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    content_size INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'published',
    created_by VARCHAR(100) NOT NULL DEFAULT 'system',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uq_tool_version (tool_id, version),
    KEY ix_tool_versions_tool_id (tool_id),
    KEY ix_tool_versions_version (version),
    KEY ix_tool_versions_content_sha256 (content_sha256),
    KEY ix_tool_versions_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tool_lifecycle_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project VARCHAR(100) NOT NULL,
    tool_name VARCHAR(200) NOT NULL,
    action VARCHAR(100) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(100) NOT NULL DEFAULT '',
    actor_name VARCHAR(255) NOT NULL DEFAULT '',
    version VARCHAR(50) NULL,
    preview_key VARCHAR(128) NULL,
    content_sha256 VARCHAR(64) NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    message VARCHAR(1000) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_tle_tool (project, tool_name),
    KEY idx_tle_action (action),
    KEY idx_tle_actor (actor_type, actor_id),
    KEY idx_tle_version (version),
    KEY idx_tle_preview_key (preview_key),
    KEY idx_tle_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(100) NOT NULL DEFAULT 'local',
    subject VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    display_name VARCHAR(255) NULL,
    avatar_url VARCHAR(1000) NULL,
    `groups` VARCHAR(2000) NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    password_hash VARCHAR(512) NULL,
    must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL,
    KEY ix_auth_users_subject (subject),
    KEY ix_auth_users_username (username),
    KEY ix_auth_users_email (email),
    KEY ix_auth_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_identities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    email VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_auth_identity_provider_subject (provider, subject),
    KEY ix_auth_identities_user_id (user_id),
    KEY ix_auth_identities_provider (provider),
    KEY ix_auth_identities_subject (subject),
    KEY ix_auth_identities_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT 'default',
    token_hash VARCHAR(128) NOT NULL,
    token_prefix VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME NULL,
    expires_at DATETIME NULL,
    KEY ix_auth_tokens_user_id (user_id),
    KEY ix_auth_tokens_token_hash (token_hash),
    KEY ix_auth_tokens_token_prefix (token_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_device_authorizations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_code_hash VARCHAR(128) NOT NULL,
    user_code VARCHAR(16) NOT NULL,
    token_env VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    user_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    UNIQUE KEY uq_auth_device_authorizations_device_code_hash (device_code_hash),
    UNIQUE KEY uq_auth_device_authorizations_user_code (user_code),
    KEY ix_auth_device_authorizations_status (status),
    KEY ix_auth_device_authorizations_user_id (user_id),
    KEY ix_auth_device_authorizations_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_user_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_name VARCHAR(200) NOT NULL,
    UNIQUE KEY uq_auth_user_resource (user_id, resource_type, resource_name),
    KEY ix_auth_user_resources_user_id (user_id),
    KEY ix_auth_user_resources_resource_type (resource_type),
    KEY ix_auth_user_resources_resource_name (resource_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS variables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(191) NOT NULL,
    value TEXT NOT NULL,
    remark TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_variables_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS nicetool_environments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    url VARCHAR(500) NOT NULL,
    token_env VARCHAR(128) NOT NULL,
    production BOOLEAN NOT NULL DEFAULT FALSE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT NOT NULL DEFAULT 0,
    remark TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_nicetool_environments_name (name),
    KEY ix_nicetool_environments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS datasources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    `database` VARCHAR(100) NOT NULL,
    description VARCHAR(500) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    charset VARCHAR(50) NULL DEFAULT 'utf8mb4',
    pool_size INT NULL DEFAULT 10,
    max_overflow INT NULL DEFAULT 20,
    pool_timeout INT NULL DEFAULT 30,
    pool_recycle INT NULL DEFAULT 3600,
    auth_source VARCHAR(100) NULL DEFAULT 'admin',
    replica_set VARCHAR(100) NULL,
    min_pool_size INT NULL DEFAULT 0,
    max_pool_size INT NULL DEFAULT 100,
    timezone VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY ix_datasources_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS enum_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500) NULL DEFAULT '',
    `values` JSON NOT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY ix_enum_definitions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
