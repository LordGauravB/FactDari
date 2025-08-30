-- Step 1: Create the MemoDari database if it doesn't exist
IF DB_ID('MemoDari') IS NULL
    CREATE DATABASE MemoDari;
GO

-- Step 2: Use MemoDari
USE MemoDari;
GO

-- Step 3: Drop tables if they exist (order matters due to FKs)
IF OBJECT_ID('FactCardTags', 'U') IS NOT NULL DROP TABLE FactCardTags;
IF OBJECT_ID('ReviewLogs', 'U') IS NOT NULL DROP TABLE ReviewLogs;
IF OBJECT_ID('FactCards', 'U') IS NOT NULL DROP TABLE FactCards;
IF OBJECT_ID('Tags', 'U') IS NOT NULL DROP TABLE Tags;
IF OBJECT_ID('Categories', 'U') IS NOT NULL DROP TABLE Categories;
GO

-- Step 4: Create Categories table
CREATE TABLE Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL,
    Description NVARCHAR(255),
    IsActive BIT NOT NULL CONSTRAINT DF_Categories_IsActive DEFAULT 1,
    CreatedDate DATETIME NOT NULL CONSTRAINT DF_Categories_CreatedDate DEFAULT GETDATE()
);

-- Step 5: Create Tags table
CREATE TABLE Tags (
    TagID INT IDENTITY(1,1) PRIMARY KEY,
    TagName NVARCHAR(100) NOT NULL
);

-- Step 6: Create FactCards table
CREATE TABLE FactCards (
    FactCardID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryID INT FOREIGN KEY REFERENCES Categories(CategoryID),
    Question NVARCHAR(MAX) NOT NULL,
    Answer NVARCHAR(MAX) NOT NULL,
    NextReviewDate DATE NOT NULL CONSTRAINT DF_FactCards_NextReviewDate DEFAULT GETDATE(),
    CurrentInterval INT NOT NULL CONSTRAINT DF_FactCards_CurrentInterval DEFAULT 1,
    Mastery FLOAT NOT NULL CONSTRAINT DF_FactCards_Mastery DEFAULT 0.0,
    DateAdded DATE NOT NULL CONSTRAINT DF_FactCards_DateAdded DEFAULT GETDATE(),
    LastReviewDate DATE,
    Stability FLOAT NOT NULL CONSTRAINT DF_FactCards_Stability DEFAULT 0.0,
    Difficulty FLOAT NOT NULL CONSTRAINT DF_FactCards_Difficulty DEFAULT 0.3,
    State INT NOT NULL CONSTRAINT DF_FactCards_State DEFAULT 1,
    Lapses INT NOT NULL CONSTRAINT DF_FactCards_Lapses DEFAULT 0,
    ViewCount INT NOT NULL CONSTRAINT DF_FactCards_ViewCount DEFAULT 0
);

-- Step 7: Create FactCardTags table
CREATE TABLE FactCardTags (
    FactCardTagID INT IDENTITY(1,1) PRIMARY KEY,
    FactCardID INT NOT NULL,
    TagID INT NOT NULL,
    CONSTRAINT FK_FactCardTags_FactCards FOREIGN KEY (FactCardID)
        REFERENCES FactCards(FactCardID) ON DELETE CASCADE,
    CONSTRAINT FK_FactCardTags_Tags FOREIGN KEY (TagID)
        REFERENCES Tags(TagID)
);

-- Step 8: Create ReviewLogs table (with Interval and Rating included)
CREATE TABLE ReviewLogs (
    ReviewLogID INT IDENTITY(1,1) PRIMARY KEY,
    FactCardID INT NOT NULL,
    ReviewDate DATETIME NOT NULL,
    UserRating INT,
    IntervalBeforeReview INT,
    IntervalAfterReview INT,
    StabilityBefore FLOAT,
    StabilityAfter FLOAT,
    DifficultyBefore FLOAT,
    DifficultyAfter FLOAT,
    Rating INT,        -- <- Added
    Interval INT       -- <- Added
    ,CONSTRAINT FK_ReviewLogs_FactCards FOREIGN KEY (FactCardID)
        REFERENCES FactCards(FactCardID) ON DELETE CASCADE
);

-- Helpful indexes for app queries
CREATE INDEX IX_FactCards_NextReviewDate ON FactCards(NextReviewDate);
CREATE INDEX IX_FactCards_CategoryID ON FactCards(CategoryID);
CREATE INDEX IX_ReviewLogs_FactCardID ON ReviewLogs(FactCardID);
CREATE INDEX IX_FactCardTags_FactCardID ON FactCardTags(FactCardID);

-- Step 9: Insert categories
INSERT INTO Categories (CategoryName, Description, IsActive, CreatedDate)
VALUES 
('Programming', 'Computer programming and software development concepts', 1, GETDATE()),
('Science', 'Scientific facts and discoveries', 1, GETDATE()),
('History', 'Historical events and figures', 1, GETDATE());

-- Step 10: Insert tags
INSERT INTO Tags (TagName)
VALUES 
('JavaScript'),
('Physics'),
('Programming Concepts'),
('American History'),
('Biology'),
('Computer Science'),
('Fundamentals');

-- Step 11: Insert fact cards
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

-- Step 12: Associate tags with fact cards
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES 
(1, 1),
(1, 6),
(2, 2),
(2, 7),
(3, 3),
(3, 6),
(4, 4),
(4, 7),
(5, 5),
(5, 2),
(5, 7);

-- Step 13: Verify final ReviewLogs columns
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_NAME;
