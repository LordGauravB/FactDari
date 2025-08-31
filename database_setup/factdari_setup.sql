-- FactDari Database Setup
-- Simplified fact viewing system without spaced repetition

-- Step 1: Create the FactDari database if it doesn't exist
IF DB_ID('FactDari') IS NULL
    CREATE DATABASE FactDari;
GO

-- Step 2: Use FactDari
USE FactDari;
GO

-- Step 3: Drop tables if they exist (order matters due to FKs)
IF OBJECT_ID('FactTags', 'U') IS NOT NULL DROP TABLE FactTags;
IF OBJECT_ID('ReviewLogs', 'U') IS NOT NULL DROP TABLE ReviewLogs;
IF OBJECT_ID('Facts', 'U') IS NOT NULL DROP TABLE Facts;
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

-- Step 6: Create Facts table (simplified from FactCards)
CREATE TABLE Facts (
    FactID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryID INT FOREIGN KEY REFERENCES Categories(CategoryID),
    Content NVARCHAR(MAX) NOT NULL,  -- Single content field instead of Question/Answer
    DateAdded DATE NOT NULL CONSTRAINT DF_Facts_DateAdded DEFAULT GETDATE(),
    LastViewedDate DATETIME,
    ReviewCount INT NOT NULL CONSTRAINT DF_Facts_ReviewCount DEFAULT 0,
    TotalViews INT NOT NULL CONSTRAINT DF_Facts_TotalViews DEFAULT 0,
    IsFavorite BIT NOT NULL CONSTRAINT DF_Facts_IsFavorite DEFAULT 0
);

-- Step 7: Create FactTags table
CREATE TABLE FactTags (
    FactTagID INT IDENTITY(1,1) PRIMARY KEY,
    FactID INT NOT NULL,
    TagID INT NOT NULL,
    CONSTRAINT FK_FactTags_Facts FOREIGN KEY (FactID)
        REFERENCES Facts(FactID) ON DELETE CASCADE,
    CONSTRAINT FK_FactTags_Tags FOREIGN KEY (TagID)
        REFERENCES Tags(TagID)
);

-- Step 8: Create simplified ReviewLogs table
CREATE TABLE ReviewLogs (
    ReviewLogID INT IDENTITY(1,1) PRIMARY KEY,
    FactID INT NOT NULL,
    ReviewDate DATETIME NOT NULL,
    SessionDuration INT, -- Duration in seconds for this review session
    CONSTRAINT FK_ReviewLogs_Facts FOREIGN KEY (FactID)
        REFERENCES Facts(FactID) ON DELETE CASCADE
);

-- Helpful indexes for app queries
CREATE INDEX IX_Facts_CategoryID ON Facts(CategoryID);
CREATE INDEX IX_Facts_LastViewedDate ON Facts(LastViewedDate);
CREATE INDEX IX_ReviewLogs_FactID ON ReviewLogs(FactID);
CREATE INDEX IX_ReviewLogs_ReviewDate ON ReviewLogs(ReviewDate);
CREATE INDEX IX_FactTags_FactID ON FactTags(FactID);

-- Step 9: Insert default categories
INSERT INTO Categories (CategoryName, Description, IsActive, CreatedDate)
VALUES 
('General Knowledge', 'General facts and information', 1, GETDATE()),
('Science', 'Scientific facts and discoveries', 1, GETDATE()),
('History', 'Historical events and figures', 1, GETDATE()),
('Technology', 'Technology and computing facts', 1, GETDATE()),
('Nature', 'Facts about nature and the environment', 1, GETDATE());

-- Step 10: Insert sample tags
INSERT INTO Tags (TagName)
VALUES 
('Important'),
('Interesting'),
('Review Often'),
('Trivia'),
('Work Related'),
('Personal');

-- Step 11: Insert sample facts
INSERT INTO Facts (CategoryID, Content, DateAdded, LastViewedDate, ReviewCount, TotalViews)
VALUES
(1, 'The human brain uses about 20% of the body''s total energy despite being only 2% of body weight.', 
   GETDATE(), NULL, 0, 0),

(2, 'Water expands by about 9% when it freezes, which is why ice floats on water.', 
   GETDATE(), NULL, 0, 0),

(3, 'The Great Wall of China is not visible from space without aid, contrary to popular belief.', 
   GETDATE(), NULL, 0, 0),

(4, 'The first computer bug was an actual moth found in a Harvard Mark II computer in 1947.', 
   GETDATE(), NULL, 0, 0),

(5, 'Octopuses have three hearts and blue blood.', 
   GETDATE(), NULL, 0, 0);

-- Step 12: Associate some tags with facts
INSERT INTO FactTags (FactID, TagID)
VALUES 
(1, 2), -- Brain fact is "Interesting"
(2, 2), -- Water fact is "Interesting"
(3, 4), -- Great Wall is "Trivia"
(4, 2), -- Computer bug is "Interesting"
(4, 4), -- Computer bug is also "Trivia"
(5, 2); -- Octopus fact is "Interesting"

-- Step 13: Migration helper (if migrating from MemoDari)
-- This creates a view to help map old data to new structure
-- Uncomment and modify as needed for actual migration
/*
-- Create migration view for existing MemoDari data
CREATE VIEW MigrationHelper AS
SELECT 
    fc.FactCardID as OldID,
    fc.CategoryID,
    CONCAT('Q: ', fc.Question, CHAR(13) + CHAR(10) + CHAR(13) + CHAR(10) + 'A: ', fc.Answer) as Content,
    fc.DateAdded,
    fc.LastReviewDate as LastViewedDate,
    fc.ViewCount as TotalViews
FROM MemoDari.dbo.FactCards fc;
*/

-- Step 14: Verify the setup
SELECT 'Categories' as TableName, COUNT(*) as RecordCount FROM Categories
UNION ALL
SELECT 'Facts', COUNT(*) FROM Facts
UNION ALL
SELECT 'Tags', COUNT(*) FROM Tags
UNION ALL
SELECT 'FactTags', COUNT(*) FROM FactTags;