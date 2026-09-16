CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','operador','consulta') NOT NULL DEFAULT 'consulta',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash CHAR(64) PRIMARY KEY,
    user_id INT NOT NULL,
    csrf_token VARCHAR(100) NOT NULL,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS auth_attempts (
    bucket CHAR(64) PRIMARY KEY,
    attempts INT NOT NULL DEFAULT 0,
    window_start DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auth_setup_lock (id INT PRIMARY KEY) ENGINE=InnoDB;
INSERT IGNORE INTO auth_setup_lock (id) VALUES (1);
