-- Do additional SQL setup that is not supported by Django
DROP VIEW IF EXISTS custom_student_problem_scores;

-- Django forces us to have an id column to act as primary key....
CREATE VIEW custom_student_problem_scores AS
    SELECT lab_problemattempt.student_id || '/' || lab_problemattempt.problem_id AS id,
           lab_problemattempt.student_id AS student_id,
           lab_problemattempt.problem_id AS problem_id,
           MAX(lab_problemattempt.score) AS score
    FROM lab_problemattempt
    GROUP BY lab_problemattempt.student_id, lab_problemattempt.problem_id
;
