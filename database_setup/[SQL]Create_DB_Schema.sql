-- Clear existing data
DELETE FROM FactCardTags;
DELETE FROM ReviewLogs;
DELETE FROM FactCards;
DELETE FROM Tags;
DELETE FROM Categories;

-- Reset identity columns
DBCC CHECKIDENT ('FactCards', RESEED, 0);
DBCC CHECKIDENT ('Tags', RESEED, 0);
DBCC CHECKIDENT ('Categories', RESEED, 0);
DBCC CHECKIDENT ('ReviewLogs', RESEED, 0);

-- Step 1: Insert categories
INSERT INTO Categories (CategoryName, Description, IsActive, CreatedDate)
VALUES 
('Programming', 'Computer programming and software development concepts', 1, GETDATE()),
('Science', 'Scientific facts and discoveries', 1, GETDATE()),
('History', 'Historical events and figures', 1, GETDATE());

-- Step 2: Insert tags
INSERT INTO Tags (TagName)
VALUES 
('JavaScript'),
('Physics'),
('Programming Concepts'),
('American History'),
('Biology'),
('Computer Science'),
('Fundamentals');

-- Step 3: Insert fact cards with CORRECTED stability values
INSERT INTO FactCards 
(CategoryID, Question, Answer, NextReviewDate, CurrentInterval, Mastery, DateAdded, 
 LastReviewDate, Stability, Difficulty, State, Lapses, ViewCount)
VALUES
(1, 'What is the difference between == and === in JavaScript?', 
   '== compares values with type coercion, while === compares both values and types without coercion.', 
   GETDATE(), 1, 0.0, GETDATE(), NULL, 0.1, 0.3, 1, 0, 0),

(2, 'What is the Heisenberg Uncertainty Principle?', 
   'It states that we cannot simultaneously know both the position and momentum of a particle with perfect accuracy. The more precisely we know one, the less precisely we can know the other.', 
   GETDATE(), 1, 0.0, GETDATE(), NULL, 0.1, 0.3, 1, 0, 0),

(1, 'What is a closure in programming?', 
   'A closure is a function that retains access to variables from its parent scope, even after the parent function has returned.', 
   GETDATE(), 1, 0.0, GETDATE(), NULL, 0.1, 0.3, 1, 0, 0),

(3, 'When was the Declaration of Independence signed?', 
   'The Declaration of Independence was signed on July 4, 1776, although many historians believe most signatures were actually added in August.', 
   GETDATE(), 1, 0.0, GETDATE(), NULL, 0.1, 0.3, 1, 0, 0),

(2, 'What is the difference between DNA and RNA?', 
   'DNA is double-stranded and uses thymine, while RNA is single-stranded and uses uracil instead of thymine. DNA stores genetic information, while RNA helps in protein synthesis.', 
   GETDATE(), 1, 0.0, GETDATE(), NULL, 0.1, 0.3, 1, 0, 0);

-- Step 4: Associate tags with fact cards
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES 
(1, 1),        -- JavaScript equality + JavaScript tag
(1, 6),        -- JavaScript equality + Computer Science tag
(2, 2),        -- Heisenberg + Physics tag
(2, 7),        -- Heisenberg + Fundamentals tag
(3, 3),        -- Closures + Programming Concepts tag
(3, 6),        -- Closures + Computer Science tag
(4, 4),        -- Declaration + American History tag
(4, 7),        -- Declaration + Fundamentals tag
(5, 5),        -- DNA/RNA + Biology tag
(5, 2),        -- DNA/RNA + Physics tag
(5, 7);        -- DNA/RNA + Fundamentals tag