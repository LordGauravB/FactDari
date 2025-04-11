USE master
GO

-- Drop the existing database if it exists
IF EXISTS (SELECT name FROM sys.databases WHERE name = N'FactsGenerator')
BEGIN
    ALTER DATABASE FactsGenerator SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE FactsGenerator;
END
GO

-- Create the database
CREATE DATABASE FactsGenerator
GO

USE FactsGenerator
GO

-- Create Tables
CREATE TABLE Categories (
    CategoryID INT PRIMARY KEY IDENTITY(1,1),
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(MAX),
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedDate DATETIME NOT NULL DEFAULT GETDATE(),
    LastModifiedDate DATETIME NOT NULL DEFAULT GETDATE()
)
GO

CREATE TABLE Facts (
    FactID INT PRIMARY KEY IDENTITY(1,1),
    CategoryID INT FOREIGN KEY REFERENCES Categories(CategoryID),
    FactText NVARCHAR(MAX) NOT NULL,
    ViewCount INT NOT NULL DEFAULT 0,
    IsVerified BIT NOT NULL DEFAULT 0,
    DateAdded DATETIME NOT NULL DEFAULT GETDATE(),
    LastModified DATETIME NOT NULL DEFAULT GETDATE()
)
GO

CREATE TABLE Tags (
    TagID INT PRIMARY KEY IDENTITY(1,1),
    TagName NVARCHAR(100) NOT NULL UNIQUE
)
GO

CREATE TABLE FactTags (
    FactID INT FOREIGN KEY REFERENCES Facts(FactID),
    TagID INT FOREIGN KEY REFERENCES Tags(TagID),
    PRIMARY KEY (FactID, TagID)
)
GO

-- Create SavedFacts table with spaced repetition columns
CREATE TABLE SavedFacts (
    SavedFactID INT PRIMARY KEY IDENTITY(1,1),
    FactID INT FOREIGN KEY REFERENCES Facts(FactID),
    DateSaved DATETIME NOT NULL DEFAULT GETDATE(),
    NextReviewDate DATE NOT NULL DEFAULT GETDATE(),
    CurrentInterval INT NOT NULL DEFAULT 1
)
GO

-- Create Stored Procedures
CREATE PROCEDURE [dbo].[AutoPopulateFactTags]
AS
BEGIN
    SET NOCOUNT ON;
    -- Temporary table to hold tag-keyword pairs
    CREATE TABLE #TagKeywords (
        TagID INT,
        Keyword NVARCHAR(100)
    );
    -- Populate the temporary table with Tags and their corresponding keywords
    INSERT INTO #TagKeywords (TagID, Keyword)
    SELECT TagID, TagName FROM Tags;
    -- Clear existing FactTags
    TRUNCATE TABLE FactTags;
    -- Insert new FactTags based on keyword matches (handling case insensitivity and multiple punctuation characters)
    INSERT INTO FactTags (FactID, TagID)
    SELECT DISTINCT f.FactID, tk.TagID
    FROM Facts f
    CROSS APPLY #TagKeywords tk
    WHERE ' ' + LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
          REPLACE(REPLACE(REPLACE(f.FactText, ',', ''), '"', ''), '''', ''), '(', ''), ')', ''), '.', ''), '?', ''), '!', ''), ';', ''), ':', ''), '-', '')) + ' '
      LIKE '% ' + LOWER(tk.Keyword) + ' %';
    -- Clean up
    DROP TABLE #TagKeywords;
    -- Output results limiting to 10 tags per fact
    WITH LimitedTags AS (
        SELECT 
            f.FactID,
            f.FactText,
            t.TagName,
            ROW_NUMBER() OVER (PARTITION BY f.FactID ORDER BY t.TagName) AS RowNum
        FROM Facts f
        LEFT JOIN FactTags ft ON f.FactID = ft.FactID
        LEFT JOIN Tags t ON ft.TagID = t.TagID
    )
    SELECT FactID, FactText, STRING_AGG(TagName, ', ') AS Tags
    FROM LimitedTags
    WHERE RowNum <= 10  -- Limiting to a maximum of 10 tags
    GROUP BY FactID, FactText
    ORDER BY FactID;
END
GO

CREATE PROCEDURE [dbo].[AutoPopulateSpecificFactTags]
    @FactID INT
AS
BEGIN
    SET NOCOUNT ON;
    -- Temporary table to hold tag-keyword pairs
    CREATE TABLE #TagKeywords (
        TagID INT,
        Keyword NVARCHAR(100)
    );
    -- Populate the temporary table with Tags and their corresponding keywords
    INSERT INTO #TagKeywords (TagID, Keyword)
    SELECT TagID, TagName FROM Tags;
    -- Delete existing FactTags for the specific FactID
    DELETE FROM FactTags WHERE FactID = @FactID;
    -- Insert new FactTags based on keyword matches for the specific FactID
    INSERT INTO FactTags (FactID, TagID)
    SELECT DISTINCT @FactID, tk.TagID
    FROM Facts f
    CROSS APPLY #TagKeywords tk
    WHERE f.FactID = @FactID 
      -- Remove commas, quotation marks, parentheses, and other common punctuation
      AND ' ' + LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
          REPLACE(REPLACE(REPLACE(f.FactText, ',', ''), '"', ''), '''', ''), '(', ''), ')', ''), '.', ''), '?', ''), '!', ''), ';', ''), ':', ''), '-', '')) + ' '
      LIKE '% ' + LOWER(tk.Keyword) + ' %';
    -- Clean up
    DROP TABLE #TagKeywords;
    -- Output results limiting to 10 tags per fact
    WITH LimitedTags AS (
        SELECT 
            f.FactID,
            f.FactText,
            t.TagName,
            ROW_NUMBER() OVER (PARTITION BY f.FactID ORDER BY t.TagName) AS RowNum
        FROM Facts f
        LEFT JOIN FactTags ft ON f.FactID = ft.FactID
        LEFT JOIN Tags t ON ft.TagID = t.TagID
        WHERE f.FactID = @FactID
    )
    SELECT FactID, FactText, STRING_AGG(TagName, ', ') AS Tags
    FROM LimitedTags
    WHERE RowNum <= 10  -- Limiting to a maximum of 10 tags
    GROUP BY FactID, FactText;
END
GO

-- Create a stored procedure for updating review schedule (Anki-style spaced repetition)
CREATE PROCEDURE UpdateReviewSchedule
    @SavedFactID INT,
    @Difficulty NVARCHAR(10)
AS
BEGIN
    DECLARE @NewInterval INT;
    DECLARE @CurrentInterval INT;
    
    -- Get current interval
    SELECT @CurrentInterval = CurrentInterval 
    FROM SavedFacts 
    WHERE SavedFactID = @SavedFactID;
    
    -- Calculate new interval based on difficulty
    IF @Difficulty = 'Hard'
    BEGIN
        -- For hard cards, reset or maintain the interval
        SET @NewInterval = IIF(@CurrentInterval <= 1, 1, @CurrentInterval);
    END
    ELSE IF @Difficulty = 'Medium'
    BEGIN
        -- For medium cards, increase by 50%
        SET @NewInterval = CEILING(@CurrentInterval * 1.5);
    END
    ELSE -- Easy
    BEGIN
        -- For easy cards, increase by 150%
        SET @NewInterval = CEILING(@CurrentInterval * 2.5);
    END
    
    -- Update the interval and next review date
    UPDATE SavedFacts
    SET CurrentInterval = @NewInterval,
        NextReviewDate = DATEADD(day, @NewInterval, GETDATE())
    WHERE SavedFactID = @SavedFactID;
    
    -- Return the updated values
    SELECT @NewInterval AS NewInterval, 
           CONVERT(VARCHAR(10), DATEADD(day, @NewInterval, GETDATE()), 120) AS NextReviewDate;
END
GO

-- Insert initial data

-- Add the API category
INSERT INTO Categories (CategoryName, Description)
VALUES ('API', 'Facts from external APIs');

-- Add some sample categories
INSERT INTO Categories (CategoryName, Description)
VALUES 
('Science', 'Scientific facts and discoveries'),
('History', 'Historical events and figures'),
('Geography', 'Places, landmarks, and geography'),
('Technology', 'Tech facts and innovations');

-- Add some sample tags
INSERT INTO Tags (TagName)
VALUES 
('Science'), ('History'), ('Geography'), ('Technology'),
('Space'), ('Animals'), ('Human Body'), ('Plants'),
('Ancient'), ('Modern'), ('War'), ('Inventions'),
('Countries'), ('Oceans'), ('Mountains'), ('Cities'),
('Computers'), ('Internet'), ('Gadgets'), ('Programming');

PRINT 'FactsGenerator database has been recreated with all tables and stored procedures.'
GO