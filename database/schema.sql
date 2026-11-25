DROP DATABASE IF EXISTS pyask_db;
CREATE DATABASE pyask_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pyask_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NULL,
    bio VARCHAR(255) NULL,
    role ENUM('user', 'moderator', 'admin') NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

CREATE TABLE tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

-- Règle "1 à 3 tags par question" : vérifiée en Python
CREATE TABLE question_tags (
    question_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (question_id, tag_id),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    user_id INT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE answer_votes (
    user_id INT NOT NULL,
    answer_id INT NOT NULL,
    vote_value TINYINT NOT NULL CHECK (vote_value IN (-1, 1)),
    PRIMARY KEY (user_id, answer_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE
);

-- Règle "exactement un des deux liens non NULL" : vérifiée en Python
CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    question_id INT NULL,
    answer_id INT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE
);

-- Un signalement doit cibler exactement un contenu; les triggers l'imposent aussi.
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_id INT NOT NULL,
    question_id INT NULL,
    answer_id INT NULL,
    comment_id INT NULL,
    reason VARCHAR(255) NOT NULL,
    status ENUM('pending', 'reviewed', 'dismissed') NOT NULL DEFAULT 'pending',
    reviewed_by INT NULL,
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE,
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
);

CREATE TABLE hidden_content (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NULL,
    answer_id INT NULL,
    comment_id INT NULL,
    report_id INT NULL UNIQUE,
    moderator_id INT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    hidden_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_hidden_question (question_id),
    UNIQUE KEY uq_hidden_answer (answer_id),
    UNIQUE KEY uq_hidden_comment (comment_id),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE,
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL,
    FOREIGN KEY (moderator_id) REFERENCES users(id) ON DELETE RESTRICT
);

DELIMITER $$
CREATE TRIGGER reports_require_one_target_before_insert
BEFORE INSERT ON reports
FOR EACH ROW
BEGIN
    IF (
        (NEW.question_id IS NOT NULL) +
        (NEW.answer_id IS NOT NULL) +
        (NEW.comment_id IS NOT NULL)
    ) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A report must target exactly one content item';
    END IF;
END$$

CREATE TRIGGER reports_require_one_target_before_update
BEFORE UPDATE ON reports
FOR EACH ROW
BEGIN
    IF (
        (NEW.question_id IS NOT NULL) +
        (NEW.answer_id IS NOT NULL) +
        (NEW.comment_id IS NOT NULL)
    ) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A report must target exactly one content item';
    END IF;
END$$

CREATE TRIGGER hidden_content_requires_one_target_before_insert
BEFORE INSERT ON hidden_content
FOR EACH ROW
BEGIN
    IF (
        (NEW.question_id IS NOT NULL) +
        (NEW.answer_id IS NOT NULL) +
        (NEW.comment_id IS NOT NULL)
    ) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hidden content must target exactly one item';
    END IF;
END$$

CREATE TRIGGER hidden_content_requires_one_target_before_update
BEFORE UPDATE ON hidden_content
FOR EACH ROW
BEGIN
    IF (
        (NEW.question_id IS NOT NULL) +
        (NEW.answer_id IS NOT NULL) +
        (NEW.comment_id IS NOT NULL)
    ) <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Hidden content must target exactly one item';
    END IF;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE get_user_for_authentication(IN p_username VARCHAR(50))
BEGIN
    SELECT id, username, email, password_hash, role, full_name, bio, created_at
    FROM users
    WHERE username = p_username;
END$$
DELIMITER ;

INSERT INTO categories (name, description) VALUES
('Python', 'Questions liées au langage Python et ses bibliothèques'),
('Bases de données', 'MySQL, SQL, conception de schémas et requêtes'),
('Interfaces Graphiques', 'PyQt5, Tkinter et design d''applications desktop'),
('Général', 'Questions diverses sur le développement');

CREATE OR REPLACE VIEW question_statistics AS
SELECT
    q.id AS question_id,
    q.title,
    q.body,
    q.created_at,
    q.updated_at,
    u.id AS author_id,
    u.username AS author_username,
    u.role AS author_role,
    u.full_name AS author_full_name,
    c.id AS category_id,
    c.name AS category_name,
    c.description AS category_description,
    COALESCE(
        (
            SELECT GROUP_CONCAT(t.name ORDER BY t.name SEPARATOR ', ')
            FROM question_tags qt
            JOIN tags t ON t.id = qt.tag_id
            WHERE qt.question_id = q.id
        ),
        ''
    ) AS tags,
    (
        SELECT COUNT(*)
        FROM answers a
        WHERE a.question_id = q.id
    ) AS answer_count,
    (
        SELECT COALESCE(SUM(v.vote_value), 0)
        FROM answers a
        JOIN answer_votes v ON v.answer_id = a.id
        WHERE a.question_id = q.id
    ) AS vote_score
FROM questions q
JOIN users u ON u.id = q.user_id
JOIN categories c ON c.id = q.category_id;