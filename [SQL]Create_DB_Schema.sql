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

CREATE TABLE SavedFacts (
    SavedFactID INT PRIMARY KEY IDENTITY(1,1),
    FactID INT FOREIGN KEY REFERENCES Facts(FactID),
    DateSaved DATETIME NOT NULL DEFAULT GETDATE()
)
GO

-- Add MasteryLevel column to SavedFacts table
ALTER TABLE SavedFacts
ADD MasteryLevel INT NOT NULL DEFAULT 0;
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

-- Create a stored procedure to update mastery level
CREATE PROCEDURE UpdateMasteryLevel
    @SavedFactID INT,
    @Increment INT
AS
BEGIN
    UPDATE SavedFacts
    SET MasteryLevel = CASE
        WHEN MasteryLevel + @Increment < 0 THEN 0
        WHEN MasteryLevel + @Increment > 100 THEN 100
        ELSE MasteryLevel + @Increment
    END
    WHERE SavedFactID = @SavedFactID;
END
GO
    
PRINT 'FactsGenerator database has been recreated with all tables and stored procedures.'
