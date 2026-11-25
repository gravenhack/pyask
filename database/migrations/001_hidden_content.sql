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
