USE master
GO

-- Drop the existing database if it exists
IF EXISTS (SELECT name FROM sys.databases WHERE name = N'FactDari')
BEGIN
    ALTER DATABASE FactDari SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE FactDari;
END
GO

-- Create the database
CREATE DATABASE FactDari
GO

USE FactDari
GO

-- Create Categories table
CREATE TABLE Categories (
    CategoryID INT PRIMARY KEY IDENTITY(1,1),
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(MAX),
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedDate DATETIME NOT NULL DEFAULT GETDATE()
)
GO

-- Create FactCards table
CREATE TABLE FactCards (
    FactCardID INT PRIMARY KEY IDENTITY(1,1),
    CategoryID INT FOREIGN KEY REFERENCES Categories(CategoryID),
    Question NVARCHAR(MAX) NOT NULL,
    Answer NVARCHAR(MAX) NOT NULL,
    DateAdded DATETIME NOT NULL DEFAULT GETDATE(),
    NextReviewDate DATE NOT NULL DEFAULT GETDATE(),
    CurrentInterval INT NOT NULL DEFAULT 1,
    ViewCount INT NOT NULL DEFAULT 0,
    Mastery FLOAT NOT NULL DEFAULT 0.0 -- 0.0 to 1.0 score of mastery
)
GO

-- Create Tags table
CREATE TABLE Tags (
    TagID INT PRIMARY KEY IDENTITY(1,1),
    TagName NVARCHAR(100) NOT NULL UNIQUE
)
GO

-- Create FactCardTags table
CREATE TABLE FactCardTags (
    FactCardID INT FOREIGN KEY REFERENCES FactCards(FactCardID) ON DELETE CASCADE,
    TagID INT FOREIGN KEY REFERENCES Tags(TagID),
    PRIMARY KEY (FactCardID, TagID)
)
GO

-- Create a stored procedure for updating review schedule (spaced repetition)
CREATE PROCEDURE UpdateReviewSchedule
    @FactCardID INT,
    @Difficulty NVARCHAR(10)
AS
BEGIN
    DECLARE @NewInterval INT;
    DECLARE @CurrentInterval INT;
    DECLARE @NewMastery FLOAT;
    DECLARE @CurrentMastery FLOAT;
    
    -- Get current interval and mastery
    SELECT @CurrentInterval = CurrentInterval, @CurrentMastery = Mastery 
    FROM FactCards 
    WHERE FactCardID = @FactCardID;
    
    -- Calculate new interval based on difficulty
    IF @Difficulty = 'Hard'
    BEGIN
        -- For hard cards, reset interval to 1
        SET @NewInterval = 1;
        -- Decrease mastery (min 0.0)
        SET @NewMastery = CASE WHEN @CurrentMastery - 0.1 < 0.0 THEN 0.0 ELSE @CurrentMastery - 0.1 END;
    END
    ELSE IF @Difficulty = 'Medium'
    BEGIN
        -- For medium cards, increase by 50%
        SET @NewInterval = CEILING(@CurrentInterval * 1.5);
        -- Slightly increase mastery
        SET @NewMastery = CASE WHEN @CurrentMastery + 0.05 > 1.0 THEN 1.0 ELSE @CurrentMastery + 0.05 END;
    END
    ELSE -- Easy
    BEGIN
        -- For easy cards, increase by 150%
        SET @NewInterval = CEILING(@CurrentInterval * 2.5);
        -- Significantly increase mastery
        SET @NewMastery = CASE WHEN @CurrentMastery + 0.15 > 1.0 THEN 1.0 ELSE @CurrentMastery + 0.15 END;
    END
    
    -- Update the interval, mastery, and next review date
    UPDATE FactCards
    SET CurrentInterval = @NewInterval,
        Mastery = @NewMastery,
        NextReviewDate = DATEADD(day, @NewInterval, GETDATE()),
        ViewCount = ViewCount + 1
    WHERE FactCardID = @FactCardID;
    
    -- Return the updated values
    SELECT @NewInterval AS NewInterval, 
           @NewMastery AS NewMastery,
           CONVERT(VARCHAR(10), DATEADD(day, @NewInterval, GETDATE()), 120) AS NextReviewDate;
END
GO

-- Add some sample categories
INSERT INTO Categories (CategoryName, Description)
VALUES 
('Science', 'Scientific facts and concepts'),
('History', 'Historical events and figures'),
('Geography', 'Places, landmarks, and geography'),
('Technology', 'Tech facts and innovations'),
('Languages', 'Language facts and vocabulary'),
('Mathematics', 'Mathematical concepts and formulas'),
('General Knowledge', 'General trivia and interesting facts'),
('DIY', 'Do-It-Yourself tips, tricks and information')
GO

-- Add some sample tags
INSERT INTO Tags (TagName)
VALUES 
('Important'), ('Review'), ('Difficult'), ('Easy'),
('Physics'), ('Biology'), ('Chemistry'), ('Ancient'), 
('Modern'), ('Europe'), ('Asia'), ('Computer Science'),
('Programming'), ('Vocabulary'), ('Grammar'), ('Algebra'),
('Geometry'), ('Calculus'), ('Trivia'), ('Fun Facts'), 
('Entertainment'), ('Useful'), ('Home Improvement'), ('Crafts'),
('Repairs'), ('Tools'), ('Gardening'), ('Cooking'), ('Life Hacks'), 
('Cleaning'), ('Health'), ('Animals'), ('Space'), ('Art'), ('Music'),
('Literature'), ('Sports'), ('Food'),('Astronomy'), ('Dinosaurs'), ('Elements'), ('Weather'), 
('Ancient History'), ('Medieval'), ('Renaissance'), ('World Wars'), 
('Mountains'), ('Rivers'), ('Deserts'), ('Islands'),
('Computers'), ('Internet'), ('Robotics'), ('Artificial Intelligence'),
('Etymology'), ('Writing Systems'), ('Language Families'),
('Famous Mathematicians'), ('Number Theory'), ('Probability')
GO

-- Get CategoryIDs
DECLARE @ScienceID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Science')
DECLARE @HistoryID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'History')
DECLARE @GeographyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Geography')
DECLARE @TechnologyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Technology')
DECLARE @LanguagesID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Languages')
DECLARE @MathematicsID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Mathematics')
DECLARE @GeneralKnowledgeID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'General Knowledge')
DECLARE @DIYID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'DIY')

-- Add General Knowledge fact cards
INSERT INTO FactCards (CategoryID, Question, Answer, NextReviewDate, CurrentInterval)
VALUES
-- General Knowledge facts
(@GeneralKnowledgeID, 'What is the smallest country in the world?', 'Vatican City is the smallest country in the world, with an area of approximately 44 hectares (109 acres).', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many bones are in the adult human body?', 'The adult human body has 206 bones.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the most abundant element in the universe?', 'Hydrogen is the most abundant element in the universe, making up about 75% of all matter.', GETDATE(), 1),
(@GeneralKnowledgeID, 'Which animal has the longest lifespan?', 'The Greenland shark has the longest known lifespan of any vertebrate, estimated to live up to 400-500 years.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only food that never spoils?', 'Honey is the only food that never spoils when stored properly. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many hearts does an octopus have?', 'An octopus has three hearts: two pump blood through the gills, while the third pumps blood through the body.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of the ocean has been explored?', 'Less than 5% of Earth''s oceans have been explored. We have better maps of the surface of Mars than of our ocean floor.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the most spoken language in the world?', 'Mandarin Chinese is the most spoken language in the world with over 1.1 billion native speakers.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the strongest muscle in the human body?', 'The masseter (jaw muscle) is the strongest muscle in the human body relative to its size, exerting a force of up to 200 pounds on the molars.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many possible moves are there in a game of chess?', 'There are more possible chess game variations (10^120) than atoms in the observable universe (10^80).', GETDATE(), 1),
(@GeneralKnowledgeID, 'How long does it take for light from the Sun to reach Earth?', 'It takes approximately 8 minutes and 20 seconds for light from the Sun to reach Earth, traveling at 186,282 miles per second.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only continent with no active volcanoes?', 'Australia is the only continent with no active volcanoes.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many taste buds does the average human tongue have?', 'The average human tongue has approximately 10,000 taste buds.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the loudest animal on Earth?', 'The sperm whale is the loudest animal on Earth, producing clicks that reach 230 decibels—louder than a rocket launch at 180 decibels.', GETDATE(), 1),
(@GeneralKnowledgeID, 'Which country has the most natural lakes?', 'Canada has the most natural lakes of any country, with over 2 million lakes—more than the rest of the world combined.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of flamingos called?', 'A group of flamingos is called a "flamboyance."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How fast can a sneeze travel?', 'A sneeze can travel at speeds up to 100 miles per hour and expel up to 100,000 droplets into the air.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only planet in our solar system that rotates clockwise?', 'Venus is the only planet in our solar system that rotates clockwise (retrograde rotation).', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of their lives do cats spend sleeping?', 'Cats spend approximately 70% of their lives sleeping, which is about 16 hours per day on average.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What was the first toy ever advertised on television?', 'Mr. Potato Head was the first toy ever advertised on television in 1952.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many muscles does it take to smile?', 'It takes 17 muscles to smile and 43 muscles to frown.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only food that includes all nine essential amino acids?', 'Quinoa is one of the few plant foods that is a complete protein, containing all nine essential amino acids.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many times does the average person blink in a day?', 'The average person blinks about 15-20 times per minute, which adds up to around 20,000 blinks per day.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only mammal that cannot jump?', 'The elephant is the only mammal that cannot jump due to its weight and bone structure.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How long does the human body completely replace itself with new cells?', 'The human body completely replaces itself with new cells every 7-10 years, though different tissues regenerate at different rates.', GETDATE(), 1),
(@DIYID, 'How can you remove a stripped screw?', 'Place a rubber band over the screw head before inserting the screwdriver. The rubber provides additional grip to remove the stripped screw.', GETDATE(), 1),
(@DIYID, 'What''s the best way to sharpen scissors at home?', 'Cut through several layers of aluminum foil multiple times to sharpen scissors. The aluminum acts as a mild abrasive that removes burrs and realigns the blades.', GETDATE(), 1),
(@DIYID, 'How can you remove permanent marker from a whiteboard?', 'Draw over the permanent marker with a dry-erase marker, then wipe it away before it dries. The solvents in the dry-erase marker will break down the permanent ink.', GETDATE(), 1),
(@DIYID, 'What''s the trick to hanging pictures perfectly level?', 'Place a dab of toothpaste on the back of the frame where the nail should go, press against the wall, and the toothpaste will mark the exact spot to place your nail.', GETDATE(), 1),
(@DIYID, 'How can you unclog a drain without chemicals?', 'Pour 1/2 cup baking soda followed by 1/2 cup vinegar down the drain, cover with a wet cloth, wait 5 minutes, then flush with hot water. The chemical reaction helps break down clogs.', GETDATE(), 1),
(@DIYID, 'What''s the secret to removing water stains from wood?', 'Mix equal parts white vinegar and olive oil, apply to the water stain with a cloth, and wipe in the direction of the wood grain. The vinegar removes the stain while the oil conditions the wood.', GETDATE(), 1),
(@DIYID, 'How can you keep cut avocados from turning brown?', 'Store the cut avocado with a large piece of onion in an airtight container. The sulfur compounds in the onion prevent oxidation without affecting the taste.', GETDATE(), 1),
(@DIYID, 'What''s the easiest way to clean a microwave?', 'Place a bowl with equal parts water and vinegar in the microwave, heat for 5 minutes, and let sit for 2 minutes. The steam will loosen dried food, making it easy to wipe clean.', GETDATE(), 1),
(@DIYID, 'How can you remove candle wax from carpet?', 'Place a paper bag or paper towel over the wax and iron on low heat. The wax will melt and transfer to the paper, leaving your carpet clean.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to eliminate ants?', 'Mix equal parts borax and sugar with water to make a paste. Place small amounts near ant trails. The sugar attracts ants, while the borax eliminates them as they take it back to their colony.', GETDATE(), 1),
(@DIYID, 'How can you make stainless steel appliances shine like new?', 'Apply a small amount of olive oil to a cloth and wipe in the direction of the grain. This removes fingerprints and adds a protective layer that prevents future smudges.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean shower glass doors?', 'Mix equal parts vinegar and dish soap in a spray bottle. Spray on doors, let sit for 30 minutes, then rinse. For maintenance, use a squeegee after each shower.', GETDATE(), 1),
(@DIYID, 'How can you keep paint from drying out between uses?', 'Place plastic wrap directly on the paint surface before sealing the can. This prevents air from reaching the paint and forming a skin.', GETDATE(), 1),
(@DIYID, 'What''s the secret to removing labels from glass jars?', 'Soak the jar in warm water with a tablespoon of baking soda for 30 minutes, then rub with olive oil to remove adhesive residue. The baking soda loosens the label, and the oil dissolves the glue.', GETDATE(), 1),
(@DIYID, 'How can you fix a squeaky door hinge?', 'Apply petroleum jelly or cooking spray directly to the hinge. The lubricant gets into the pin and bushings of the hinge, eliminating the friction that causes squeaking.', GETDATE(), 1),
(@DIYID, 'What''s the trick to removing pet hair from furniture?', 'Put on a slightly dampened rubber glove and run your hand over the furniture. The static and slight moisture will collect the hair into clumps that easily lift away.', GETDATE(), 1),
(@DIYID, 'How can you make your own natural all-purpose cleaner?', 'Mix 1 part white vinegar, 1 part water, lemon rind, and rosemary sprigs in a spray bottle. Let infuse for a week before using. The vinegar disinfects while the herbs provide a pleasant scent.', GETDATE(), 1),
(@DIYID, 'What''s the best way to ripen an avocado quickly?', 'Place the avocado in a paper bag with a banana or apple. These fruits release ethylene gas, which speeds up the ripening process, usually within 1-2 days.', GETDATE(), 1),
(@DIYID, 'How can you remove rust from tools?', 'Soak rusty tools in a solution of equal parts white vinegar and water for 24 hours, then scrub with a wire brush. The acetic acid in vinegar dissolves rust without damaging the metal.', GETDATE(), 1),
(@DIYID, 'What''s a simple way to test if plants need watering?', 'Insert your finger about an inch into the soil. If it feels dry at that depth, it''s time to water. This is more reliable than the appearance of the soil surface which can be misleading.', GETDATE(), 1),
(@DIYID, 'How can you extend the life of cut flowers?', 'Add 1/4 teaspoon bleach and 1 tablespoon sugar to the vase water. The bleach prevents bacterial growth while the sugar provides nutrients to the cut stems.', GETDATE(), 1),
(@DIYID, 'What''s the trick to cooking perfect rice every time?', 'Use the finger method: add rice to the pot, rinse, then add water until it reaches the first joint of your index finger when placed on top of the rice. This works regardless of the quantity of rice.', GETDATE(), 1),
(@DIYID, 'How can you remove crayon marks from walls?', 'Spray WD-40 on the crayon marks and wipe with a clean cloth, or use a paste of baking soda and water. The solvents in WD-40 break down the wax in crayons without damaging most paint.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to freshen smelly shoes?', 'Place dry tea bags in shoes overnight. The tannic acid and absorbent properties of tea bags neutralize odors and absorb moisture that causes bacteria growth.', GETDATE(), 1),
(@DIYID, 'How can you prevent cheese from molding too quickly?', 'Lightly butter the cut edge of hard cheese before storing. The butter creates a seal that prevents air from reaching the cheese, slowing mold growth while not affecting the taste.', GETDATE(), 1)
GO

-- Get the starting ID for our newly inserted fact cards
DECLARE @StartingFactCardID INT = (SELECT MIN(FactCardID) FROM FactCards WHERE CategoryID IN 
    (SELECT CategoryID FROM Categories WHERE CategoryName IN ('General Knowledge', 'DIY')))

-- Get Tag IDs for tagging the new fact cards
DECLARE @TriviaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Trivia')
DECLARE @FunFactsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Fun Facts')
DECLARE @EntertainmentID INT = (SELECT TagID FROM Tags WHERE TagName = 'Entertainment')
DECLARE @UsefulID INT = (SELECT TagID FROM Tags WHERE TagName = 'Useful')
DECLARE @HomeImprovementID INT = (SELECT TagID FROM Tags WHERE TagName = 'Home Improvement')
DECLARE @CraftsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Crafts')
DECLARE @RepairsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Repairs')
DECLARE @ToolsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Tools')
DECLARE @GardeningID INT = (SELECT TagID FROM Tags WHERE TagName = 'Gardening')
DECLARE @CookingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cooking')
DECLARE @LifeHacksID INT = (SELECT TagID FROM Tags WHERE TagName = 'Life Hacks')
DECLARE @CleaningID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cleaning')
DECLARE @HealthID INT = (SELECT TagID FROM Tags WHERE TagName = 'Health')
DECLARE @AnimalsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Animals')
DECLARE @SpaceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Space')
DECLARE @ArtID INT = (SELECT TagID FROM Tags WHERE TagName = 'Art')
DECLARE @MusicID INT = (SELECT TagID FROM Tags WHERE TagName = 'Music')
DECLARE @SportsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Sports')
DECLARE @FoodID INT = (SELECT TagID FROM Tags WHERE TagName = 'Food')

-- Add tags for General Knowledge fact cards
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES
-- Geography
(@StartingFactCardID, @TriviaID),
(@StartingFactCardID, @FunFactsID),

-- Human body
(@StartingFactCardID + 1, @TriviaID),
(@StartingFactCardID + 1, @HealthID),

-- Universe
(@StartingFactCardID + 2, @TriviaID),
(@StartingFactCardID + 2, @SpaceID),

-- Animals
(@StartingFactCardID + 3, @TriviaID),
(@StartingFactCardID + 3, @AnimalsID),
(@StartingFactCardID + 3, @FunFactsID),

-- Food
(@StartingFactCardID + 4, @TriviaID),
(@StartingFactCardID + 4, @FoodID),
(@StartingFactCardID + 4, @FunFactsID),

-- Octopus hearts
(@StartingFactCardID + 5, @TriviaID),
(@StartingFactCardID + 5, @AnimalsID),
(@StartingFactCardID + 5, @FunFactsID),

-- Ocean exploration
(@StartingFactCardID + 6, @TriviaID),
(@StartingFactCardID + 6, @FunFactsID),

-- Languages
(@StartingFactCardID + 7, @TriviaID),
(@StartingFactCardID + 7, @FunFactsID),

-- Jaw muscle
(@StartingFactCardID + 8, @TriviaID),
(@StartingFactCardID + 8, @HealthID),

-- Chess moves
(@StartingFactCardID + 9, @TriviaID),
(@StartingFactCardID + 9, @EntertainmentID),

-- Sunlight
(@StartingFactCardID + 10, @TriviaID),
(@StartingFactCardID + 10, @SpaceID),

-- Volcanoes
(@StartingFactCardID + 11, @TriviaID),
(@StartingFactCardID + 11, @FunFactsID),

-- Taste buds
(@StartingFactCardID + 12, @TriviaID),
(@StartingFactCardID + 12, @HealthID),

-- Loudest animal
(@StartingFactCardID + 13, @TriviaID),
(@StartingFactCardID + 13, @AnimalsID),
(@StartingFactCardID + 13, @FunFactsID),

-- Lakes
(@StartingFactCardID + 14, @TriviaID),
(@StartingFactCardID + 14, @FunFactsID),

-- Flamingos
(@StartingFactCardID + 15, @TriviaID),
(@StartingFactCardID + 15, @AnimalsID),
(@StartingFactCardID + 15, @FunFactsID),

-- Sneezing
(@StartingFactCardID + 16, @TriviaID),
(@StartingFactCardID + 16, @HealthID),
(@StartingFactCardID + 16, @FunFactsID),

-- Venus
(@StartingFactCardID + 17, @TriviaID),
(@StartingFactCardID + 17, @SpaceID),

-- Cats
(@StartingFactCardID + 18, @TriviaID),
(@StartingFactCardID + 18, @AnimalsID),
(@StartingFactCardID + 18, @FunFactsID),

-- First TV toy
(@StartingFactCardID + 19, @TriviaID),
(@StartingFactCardID + 19, @EntertainmentID),

-- Smiling muscles
(@StartingFactCardID + 20, @TriviaID),
(@StartingFactCardID + 20, @HealthID),

-- Quinoa
(@StartingFactCardID + 21, @TriviaID),
(@StartingFactCardID + 21, @FoodID),
(@StartingFactCardID + 21, @HealthID),

-- Blinking
(@StartingFactCardID + 22, @TriviaID),
(@StartingFactCardID + 22, @HealthID),

-- Elephant
(@StartingFactCardID + 23, @TriviaID),
(@StartingFactCardID + 23, @AnimalsID),
(@StartingFactCardID + 23, @FunFactsID),

-- Cell regeneration
(@StartingFactCardID + 24, @TriviaID),
(@StartingFactCardID + 24, @HealthID),

-- Now tag DIY fact cards
-- Starting with ID + 25 for DIY facts

-- Stripped screw
(@StartingFactCardID + 25, @ToolsID),
(@StartingFactCardID + 25, @RepairsID),
(@StartingFactCardID + 25, @LifeHacksID),

-- Scissors sharpening
(@StartingFactCardID + 26, @ToolsID),
(@StartingFactCardID + 26, @LifeHacksID),
(@StartingFactCardID + 26, @HomeImprovementID),

-- Marker whiteboard
(@StartingFactCardID + 27, @LifeHacksID),
(@StartingFactCardID + 27, @CleaningID),

-- Hanging pictures
(@StartingFactCardID + 28, @HomeImprovementID),
(@StartingFactCardID + 28, @LifeHacksID),

-- Unclog drain
(@StartingFactCardID + 29, @HomeImprovementID),
(@StartingFactCardID + 29, @CleaningID),
(@StartingFactCardID + 29, @LifeHacksID),

-- Water stains
(@StartingFactCardID + 30, @HomeImprovementID),
(@StartingFactCardID + 30, @LifeHacksID),
(@StartingFactCardID + 30, @CleaningID),

-- Avocados
(@StartingFactCardID + 31, @FoodID),
(@StartingFactCardID + 31, @CookingID),
(@StartingFactCardID + 31, @LifeHacksID),

-- Microwave cleaning
(@StartingFactCardID + 32, @CleaningID),
(@StartingFactCardID + 32, @HomeImprovementID),
(@StartingFactCardID + 32, @LifeHacksID),

-- Candle wax
(@StartingFactCardID + 33, @CleaningID),
(@StartingFactCardID + 33, @HomeImprovementID),
(@StartingFactCardID + 33, @LifeHacksID),

-- Ants
(@StartingFactCardID + 34, @HomeImprovementID),
(@StartingFactCardID + 34, @CleaningID),
(@StartingFactCardID + 34, @LifeHacksID),

-- Stainless steel
(@StartingFactCardID + 35, @CleaningID),
(@StartingFactCardID + 35, @HomeImprovementID),
(@StartingFactCardID + 35, @LifeHacksID),

-- Shower glass
(@StartingFactCardID + 36, @CleaningID),
(@StartingFactCardID + 36, @HomeImprovementID),
(@StartingFactCardID + 36, @LifeHacksID),

-- Paint
(@StartingFactCardID + 37, @HomeImprovementID),
(@StartingFactCardID + 37, @CraftsID),
(@StartingFactCardID + 37, @LifeHacksID),

-- Glass jars
(@StartingFactCardID + 38, @LifeHacksID),
(@StartingFactCardID + 38, @CleaningID),
(@StartingFactCardID + 38, @CraftsID),

-- Squeaky door
(@StartingFactCardID + 39, @RepairsID),
(@StartingFactCardID + 39, @HomeImprovementID),
(@StartingFactCardID + 39, @LifeHacksID),

-- Pet hair
(@StartingFactCardID + 40, @CleaningID),
(@StartingFactCardID + 40, @LifeHacksID),
(@StartingFactCardID + 40, @HomeImprovementID),

-- All-purpose cleaner
(@StartingFactCardID + 41, @CleaningID),
(@StartingFactCardID + 41, @HomeImprovementID),
(@StartingFactCardID + 41, @LifeHacksID),

-- Ripen avocado
(@StartingFactCardID + 42, @FoodID),
(@StartingFactCardID + 42, @CookingID),
(@StartingFactCardID + 42, @LifeHacksID),

-- Rust removal
(@StartingFactCardID + 43, @ToolsID),
(@StartingFactCardID + 43, @RepairsID),
(@StartingFactCardID + 43, @HomeImprovementID),

-- Plant watering
(@StartingFactCardID + 44, @GardeningID),
(@StartingFactCardID + 44, @LifeHacksID),

-- Cut flowers
(@StartingFactCardID + 45, @GardeningID),
(@StartingFactCardID + 45, @LifeHacksID),

-- Rice cooking
(@StartingFactCardID + 46, @CookingID),
(@StartingFactCardID + 46, @FoodID),
(@StartingFactCardID + 46, @LifeHacksID),

-- Crayon removal
(@StartingFactCardID + 47, @CleaningID),
(@StartingFactCardID + 47, @HomeImprovementID),
(@StartingFactCardID + 47, @LifeHacksID),

-- Smelly shoes
(@StartingFactCardID + 48, @CleaningID),
(@StartingFactCardID + 48, @LifeHacksID),
(@StartingFactCardID + 48, @HealthID),

-- Cheese mold
(@StartingFactCardID + 49, @FoodID),
(@StartingFactCardID + 49, @CookingID),
(@StartingFactCardID + 49, @LifeHacksID)
GO

PRINT 'Successfully added 50 new facts to the FactDari database!'


---------------------------------------------------
--- Second Insert Batch
---------------------------------------------------

USE FactDari
GO

-- Get CategoryIDs
DECLARE @ScienceID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Science')
DECLARE @HistoryID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'History')
DECLARE @GeographyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Geography')
DECLARE @TechnologyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Technology')
DECLARE @LanguagesID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Languages')
DECLARE @MathematicsID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Mathematics')

-- Add Science fact cards
INSERT INTO FactCards (CategoryID, Question, Answer, NextReviewDate, CurrentInterval)
VALUES
(@ScienceID, 'What is the smallest bone in the human body?', 'The stapes, located in the middle ear, is the smallest bone in the human body. It measures only about 3 millimeters in length.', GETDATE(), 1),
(@ScienceID, 'What is the speed of light in a vacuum?', 'The speed of light in a vacuum is approximately 299,792,458 meters per second.', GETDATE(), 1),
(@ScienceID, 'What is the hardest natural substance on Earth?', 'Diamond is the hardest naturally occurring substance on Earth, scoring 10 on the Mohs scale of mineral hardness.', GETDATE(), 1),
(@ScienceID, 'What percentage of DNA do humans share with chimpanzees?', 'Humans share approximately 98-99% of their DNA with chimpanzees.', GETDATE(), 1),
(@ScienceID, 'What are the three states of matter?', 'The three basic states of matter are solid, liquid, and gas. Plasma is often considered the fourth state.', GETDATE(), 1),
(@ScienceID, 'What is absolute zero in Celsius?', 'Absolute zero is -273.15 degrees Celsius, the theoretical temperature at which molecular motion stops completely.', GETDATE(), 1),
(@ScienceID, 'What is the chemical formula for water?', 'The chemical formula for water is H₂O, representing two hydrogen atoms bonded to one oxygen atom.', GETDATE(), 1),
(@ScienceID, 'What is the average human body temperature?', 'The average human body temperature is approximately 98.6°F (37°C).', GETDATE(), 1),
(@ScienceID, 'What is the most abundant gas in Earth''s atmosphere?', 'Nitrogen is the most abundant gas in Earth''s atmosphere, making up about 78% of the air we breathe.', GETDATE(), 1),
(@ScienceID, 'How many chromosomes do humans have?', 'Humans typically have 46 chromosomes arranged in 23 pairs.', GETDATE(), 1),

-- Add History fact cards
(@HistoryID, 'In what year did the Titanic sink?', 'The Titanic sank on April 15, 1912, after hitting an iceberg during her maiden voyage.', GETDATE(), 1),
(@HistoryID, 'Who was the first woman to win a Nobel Prize?', 'Marie Curie was the first woman to win a Nobel Prize in 1903 for her work in Physics, and later won a second Nobel Prize in Chemistry in 1911.', GETDATE(), 1),
(@HistoryID, 'When did World War II end?', 'World War II ended in Europe on May 8, 1945 (V-E Day) and in Asia on September 2, 1945 (V-J Day) with the formal surrender of Japan.', GETDATE(), 1),
(@HistoryID, 'Who wrote the Declaration of Independence?', 'Thomas Jefferson was the principal author of the Declaration of Independence, which was adopted by the Continental Congress on July 4, 1776.', GETDATE(), 1),
(@HistoryID, 'What ancient civilization built the pyramids of Giza?', 'The ancient Egyptians built the pyramids of Giza around 4,500 years ago during the Fourth Dynasty of the Old Kingdom.', GETDATE(), 1),
(@HistoryID, 'When did the Berlin Wall fall?', 'The Berlin Wall fell on November 9, 1989, marking a symbolic end to the Cold War.', GETDATE(), 1),
(@HistoryID, 'Who was the first human to walk on the moon?', 'Neil Armstrong was the first human to walk on the moon on July 20, 1969, during the Apollo 11 mission.', GETDATE(), 1),
(@HistoryID, 'When was the printing press invented?', 'Johannes Gutenberg invented the movable-type printing press around 1440, revolutionizing the spread of information.', GETDATE(), 1),
(@HistoryID, 'What was the Renaissance?', 'The Renaissance was a period of European cultural, artistic, political, and scientific "rebirth" spanning roughly the 14th to 17th centuries.', GETDATE(), 1),
(@HistoryID, 'When did the French Revolution begin?', 'The French Revolution began in 1789 with the Storming of the Bastille on July 14.', GETDATE(), 1),

-- Add Geography fact cards
(@GeographyID, 'What is the largest ocean on Earth?', 'The Pacific Ocean is the largest and deepest ocean on Earth, covering more than 60 million square miles.', GETDATE(), 1),
(@GeographyID, 'What is the longest river in the world?', 'The Nile River is the longest river in the world, flowing approximately 4,135 miles (6,650 km) through northeastern Africa.', GETDATE(), 1),
(@GeographyID, 'What is the tallest mountain in the world?', 'Mount Everest is the tallest mountain on Earth, with a peak that reaches 29,032 feet (8,849 meters) above sea level.', GETDATE(), 1),
(@GeographyID, 'What is the largest desert in the world?', 'The Antarctic Desert is the largest desert in the world, covering about 5.5 million square miles. The Sahara is the largest hot desert.', GETDATE(), 1),
(@GeographyID, 'What is the smallest country in the world by land area?', 'Vatican City is the smallest country in the world by land area, covering just 49 hectares (121 acres).', GETDATE(), 1),
(@GeographyID, 'What are the seven continents?', 'The seven continents are Asia, Africa, North America, South America, Antarctica, Europe, and Australia.', GETDATE(), 1),
(@GeographyID, 'What is the deepest point in the ocean?', 'The Challenger Deep in the Mariana Trench is the deepest known point in Earth''s oceans, at approximately 36,200 feet (11,034 meters) deep.', GETDATE(), 1),
(@GeographyID, 'What country has the most islands?', 'Sweden has the most islands of any country, with approximately 267,570 islands, though only about 1,000 are inhabited.', GETDATE(), 1),
(@GeographyID, 'What is the Great Barrier Reef?', 'The Great Barrier Reef is the world''s largest coral reef system, located off the coast of Australia, stretching for over 1,400 miles.', GETDATE(), 1),
(@GeographyID, 'What causes the Northern Lights?', 'The Northern Lights (Aurora Borealis) are caused by solar particles colliding with gases in Earth''s atmosphere, creating colorful displays of light.', GETDATE(), 1),

-- Add Technology fact cards
(@TechnologyID, 'When was the first iPhone released?', 'The first iPhone was released by Apple on June 29, 2007.', GETDATE(), 1),
(@TechnologyID, 'What does CPU stand for?', 'CPU stands for Central Processing Unit, the primary component of a computer that performs most of the processing.', GETDATE(), 1),
(@TechnologyID, 'Who created the World Wide Web?', 'Tim Berners-Lee created the World Wide Web in 1989 while working at CERN.', GETDATE(), 1),
(@TechnologyID, 'What does AI stand for?', 'AI stands for Artificial Intelligence, the simulation of human intelligence processes by machines.', GETDATE(), 1),
(@TechnologyID, 'What is the smallest unit of digital information?', 'The bit (binary digit) is the smallest unit of digital information, representing either 0 or 1.', GETDATE(), 1),
(@TechnologyID, 'What is cloud computing?', 'Cloud computing is the delivery of computing services—including storage, processing power, and applications—over the internet.', GETDATE(), 1),
(@TechnologyID, 'When was the first email sent?', 'The first email was sent by Ray Tomlinson in 1971, who also introduced the use of the @ symbol in email addresses.', GETDATE(), 1),
(@TechnologyID, 'What is Moore''s Law?', 'Moore''s Law states that the number of transistors on a microchip doubles approximately every two years, though the pace has slowed in recent years.', GETDATE(), 1),
(@TechnologyID, 'What does URL stand for?', 'URL stands for Uniform Resource Locator, the address used to access websites on the internet.', GETDATE(), 1),
(@TechnologyID, 'What is blockchain?', 'Blockchain is a distributed, decentralized digital ledger technology that records transactions across many computers so that records cannot be altered retroactively.', GETDATE(), 1),

-- Add Languages fact cards
(@LanguagesID, 'How many languages are spoken in the world today?', 'Approximately 7,000 languages are spoken around the world today, though many are endangered.', GETDATE(), 1),
(@LanguagesID, 'What is the oldest known written language?', 'Sumerian, written in cuneiform, is considered the oldest known written language, dating back to approximately 3200 BCE.', GETDATE(), 1),
(@LanguagesID, 'What is the most widely spoken language in the world by total speakers?', 'English is the most widely spoken language in the world by total speakers (native plus second language), with approximately 1.35 billion speakers.', GETDATE(), 1),
(@LanguagesID, 'What does "polyglot" mean?', 'A polyglot is a person who speaks, writes, or reads several languages.', GETDATE(), 1),
(@LanguagesID, 'What is a palindrome?', 'A palindrome is a word, phrase, number, or sequence that reads the same backward as forward, such as "madam" or "racecar."', GETDATE(), 1),
(@LanguagesID, 'Which language has the most words?', 'English has the largest vocabulary of any language, with over 170,000 words in current use and 47,000 obsolete words.', GETDATE(), 1),
(@LanguagesID, 'What is the hardest language to learn for English speakers?', 'Mandarin Chinese, Arabic, and Japanese are often considered among the hardest languages for native English speakers to learn.', GETDATE(), 1),
(@LanguagesID, 'What is an idiom?', 'An idiom is a phrase whose meaning cannot be determined by the literal definition of the phrase itself, such as "kick the bucket" or "break a leg."', GETDATE(), 1),
(@LanguagesID, 'What is the difference between a language and a dialect?', 'A language is a structured system of communication, while a dialect is a variety of a language that is characteristic of a particular group of speakers.', GETDATE(), 1),
(@LanguagesID, 'What is Esperanto?', 'Esperanto is the most widely spoken constructed international auxiliary language, created by L. L. Zamenhof in 1887 to foster peace and international understanding.', GETDATE(), 1),

-- Add Mathematics fact cards
(@MathematicsID, 'What is pi?', 'Pi (π) is the ratio of a circle''s circumference to its diameter, approximately equal to 3.14159. It is an irrational number.', GETDATE(), 1),
(@MathematicsID, 'What is the Pythagorean theorem?', 'The Pythagorean theorem states that in a right triangle, the square of the length of the hypotenuse equals the sum of the squares of the other two sides (a² + b² = c²).', GETDATE(), 1),
(@MathematicsID, 'What is a prime number?', 'A prime number is a natural number greater than 1 that cannot be formed by multiplying two smaller natural numbers.', GETDATE(), 1),
(@MathematicsID, 'What is the Fibonacci sequence?', 'The Fibonacci sequence is a series of numbers where each number is the sum of the two preceding ones, usually starting with 0 and 1 (0, 1, 1, 2, 3, 5, 8, 13, 21, ...).', GETDATE(), 1),
(@MathematicsID, 'What is the golden ratio?', 'The golden ratio is approximately 1.618 and is represented by the Greek letter phi (φ). It appears in geometry, art, architecture, and nature.', GETDATE(), 1),
(@MathematicsID, 'What is a fractal?', 'A fractal is a geometric figure that exhibits self-similarity, repeating the same pattern at different scales.', GETDATE(), 1),
(@MathematicsID, 'What is calculus?', 'Calculus is the mathematical study of continuous change, with two major branches: differential calculus and integral calculus.', GETDATE(), 1),
(@MathematicsID, 'What are the first 10 digits of the mathematical constant e?', 'The first 10 digits of the mathematical constant e (Euler''s number) are 2.7182818284.', GETDATE(), 1),
(@MathematicsID, 'What is a perfect square?', 'A perfect square is an integer that is the square of another integer, such as 1, 4, 9, 16, 25, etc.', GETDATE(), 1),
(@MathematicsID, 'What is the difference between mean, median, and mode?', 'Mean is the average of values, median is the middle value when arranged in order, and mode is the most frequently occurring value in a dataset.', GETDATE(), 1)
GO

-- Now let's add relevant tags to all the new fact cards

-- Get the starting ID for our newly inserted fact cards
DECLARE @StartingNewFactCardID INT = (SELECT MAX(FactCardID) - 59 FROM FactCards)

-- Get Tag IDs for tagging the new fact cards
DECLARE @ImportantID INT = (SELECT TagID FROM Tags WHERE TagName = 'Important')
DECLARE @PhysicsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Physics')
DECLARE @BiologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Biology')
DECLARE @ChemistryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Chemistry')
DECLARE @AncientID INT = (SELECT TagID FROM Tags WHERE TagName = 'Ancient')
DECLARE @ModernID INT = (SELECT TagID FROM Tags WHERE TagName = 'Modern')
DECLARE @EuropeID INT = (SELECT TagID FROM Tags WHERE TagName = 'Europe')
DECLARE @AsiaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Asia')
DECLARE @ComputerScienceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Computer Science')
DECLARE @ProgrammingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Programming')
DECLARE @VocabularyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Vocabulary')
DECLARE @GrammarID INT = (SELECT TagID FROM Tags WHERE TagName = 'Grammar')
DECLARE @AlgebraID INT = (SELECT TagID FROM Tags WHERE TagName = 'Algebra')
DECLARE @GeometryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Geometry')
DECLARE @CalculusID INT = (SELECT TagID FROM Tags WHERE TagName = 'Calculus')
DECLARE @TriviaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Trivia')
DECLARE @FunFactsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Fun Facts')
DECLARE @EntertainmentID INT = (SELECT TagID FROM Tags WHERE TagName = 'Entertainment')
DECLARE @HealthID INT = (SELECT TagID FROM Tags WHERE TagName = 'Health')
DECLARE @AnimalsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Animals')
DECLARE @SpaceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Space')
DECLARE @AstronomyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Astronomy')
DECLARE @WeatherID INT = (SELECT TagID FROM Tags WHERE TagName = 'Weather')
DECLARE @AncientHistoryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Ancient History')
DECLARE @MedievalID INT = (SELECT TagID FROM Tags WHERE TagName = 'Medieval')
DECLARE @RenaissanceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Renaissance')
DECLARE @WorldWarsID INT = (SELECT TagID FROM Tags WHERE TagName = 'World Wars')
DECLARE @MountainsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Mountains')
DECLARE @RiversID INT = (SELECT TagID FROM Tags WHERE TagName = 'Rivers')
DECLARE @DesertsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Deserts')
DECLARE @IslandsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Islands')
DECLARE @ComputersID INT = (SELECT TagID FROM Tags WHERE TagName = 'Computers')
DECLARE @InternetID INT = (SELECT TagID FROM Tags WHERE TagName = 'Internet')
DECLARE @RoboticsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Robotics')
DECLARE @ArtificialIntelligenceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Artificial Intelligence')
DECLARE @EtymologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Etymology')
DECLARE @WritingSystemsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Writing Systems')
DECLARE @LanguageFamiliesID INT = (SELECT TagID FROM Tags WHERE TagName = 'Language Families')
DECLARE @FamousMathematiciansID INT = (SELECT TagID FROM Tags WHERE TagName = 'Famous Mathematicians')
DECLARE @NumberTheoryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Number Theory')
DECLARE @ProbabilityID INT = (SELECT TagID FROM Tags WHERE TagName = 'Probability')

-- Add tags for Science fact cards (10 cards)
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES
-- Smallest bone
(@StartingNewFactCardID, @BiologyID),
(@StartingNewFactCardID, @ImportantID),
(@StartingNewFactCardID, @HealthID),

-- Speed of light
(@StartingNewFactCardID + 1, @PhysicsID),
(@StartingNewFactCardID + 1, @ImportantID),
(@StartingNewFactCardID + 1, @SpaceID),

-- Diamond
(@StartingNewFactCardID + 2, @ChemistryID),
(@StartingNewFactCardID + 2, @TriviaID),

-- Human DNA
(@StartingNewFactCardID + 3, @BiologyID),
(@StartingNewFactCardID + 3, @ImportantID),
(@StartingNewFactCardID + 3, @AnimalsID),

-- States of matter
(@StartingNewFactCardID + 4, @PhysicsID),
(@StartingNewFactCardID + 4, @ChemistryID),
(@StartingNewFactCardID + 4, @ImportantID),

-- Absolute zero
(@StartingNewFactCardID + 5, @PhysicsID),
(@StartingNewFactCardID + 5, @ImportantID),

-- Water formula
(@StartingNewFactCardID + 6, @ChemistryID),
(@StartingNewFactCardID + 6, @ImportantID),

-- Body temperature
(@StartingNewFactCardID + 7, @BiologyID),
(@StartingNewFactCardID + 7, @HealthID),

-- Atmosphere
(@StartingNewFactCardID + 8, @ChemistryID),
(@StartingNewFactCardID + 8, @ImportantID),
(@StartingNewFactCardID + 8, @WeatherID),

-- Chromosomes
(@StartingNewFactCardID + 9, @BiologyID),
(@StartingNewFactCardID + 9, @ImportantID),
(@StartingNewFactCardID + 9, @HealthID),

-- Add tags for History fact cards (10 cards)
-- Titanic
(@StartingNewFactCardID + 10, @ModernID),
(@StartingNewFactCardID + 10, @ImportantID),
(@StartingNewFactCardID + 10, @TriviaID),

-- Marie Curie
(@StartingNewFactCardID + 11, @ModernID),
(@StartingNewFactCardID + 11, @ImportantID),

-- World War II
(@StartingNewFactCardID + 12, @ModernID),
(@StartingNewFactCardID + 12, @ImportantID),
(@StartingNewFactCardID + 12, @WorldWarsID),

-- Declaration of Independence
(@StartingNewFactCardID + 13, @ModernID),
(@StartingNewFactCardID + 13, @ImportantID),

-- Pyramids
(@StartingNewFactCardID + 14, @AncientID),
(@StartingNewFactCardID + 14, @AncientHistoryID),
(@StartingNewFactCardID + 14, @ImportantID),

-- Berlin Wall
(@StartingNewFactCardID + 15, @ModernID),
(@StartingNewFactCardID + 15, @ImportantID),
(@StartingNewFactCardID + 15, @EuropeID),

-- Moon landing
(@StartingNewFactCardID + 16, @ModernID),
(@StartingNewFactCardID + 16, @ImportantID),
(@StartingNewFactCardID + 16, @SpaceID),

-- Printing press
(@StartingNewFactCardID + 17, @MedievalID),
(@StartingNewFactCardID + 17, @ImportantID),
(@StartingNewFactCardID + 17, @EuropeID),

-- Renaissance
(@StartingNewFactCardID + 18, @RenaissanceID),
(@StartingNewFactCardID + 18, @ImportantID),
(@StartingNewFactCardID + 18, @EuropeID),

-- French Revolution
(@StartingNewFactCardID + 19, @ModernID),
(@StartingNewFactCardID + 19, @ImportantID),
(@StartingNewFactCardID + 19, @EuropeID),

-- Add tags for Geography fact cards (10 cards)
-- Pacific Ocean
(@StartingNewFactCardID + 20, @ImportantID),
(@StartingNewFactCardID + 20, @TriviaID),

-- Nile River
(@StartingNewFactCardID + 21, @ImportantID),
(@StartingNewFactCardID + 21, @RiversID),

-- Mount Everest
(@StartingNewFactCardID + 22, @ImportantID),
(@StartingNewFactCardID + 22, @MountainsID),
(@StartingNewFactCardID + 22, @AsiaID),

-- Desert
(@StartingNewFactCardID + 23, @ImportantID),
(@StartingNewFactCardID + 23, @DesertsID),

-- Vatican City
(@StartingNewFactCardID + 24, @ImportantID),
(@StartingNewFactCardID + 24, @TriviaID),
(@StartingNewFactCardID + 24, @EuropeID),

-- Continents
(@StartingNewFactCardID + 25, @ImportantID),
(@StartingNewFactCardID + 25, @TriviaID),

-- Challenger Deep
(@StartingNewFactCardID + 26, @ImportantID),
(@StartingNewFactCardID + 26, @TriviaID),

-- Sweden islands
(@StartingNewFactCardID + 27, @ImportantID),
(@StartingNewFactCardID + 27, @IslandsID),
(@StartingNewFactCardID + 27, @EuropeID),

-- Great Barrier Reef
(@StartingNewFactCardID + 28, @ImportantID),
(@StartingNewFactCardID + 28, @TriviaID),
(@StartingNewFactCardID + 28, @AnimalsID),

-- Northern Lights
(@StartingNewFactCardID + 29, @ImportantID),
(@StartingNewFactCardID + 29, @WeatherID),
(@StartingNewFactCardID + 29, @PhysicsID),

-- Add tags for Technology fact cards (10 cards)
-- iPhone
(@StartingNewFactCardID + 30, @ModernID),
(@StartingNewFactCardID + 30, @ComputersID),

-- CPU
(@StartingNewFactCardID + 31, @ComputersID),
(@StartingNewFactCardID + 31, @ImportantID),
(@StartingNewFactCardID + 31, @ComputerScienceID),

-- WWW
(@StartingNewFactCardID + 32, @InternetID),
(@StartingNewFactCardID + 32, @ImportantID),
(@StartingNewFactCardID + 32, @ModernID),

-- AI
(@StartingNewFactCardID + 33, @ArtificialIntelligenceID),
(@StartingNewFactCardID + 33, @ImportantID),
(@StartingNewFactCardID + 33, @ComputerScienceID),

-- Bit
(@StartingNewFactCardID + 34, @ComputerScienceID),
(@StartingNewFactCardID + 34, @ImportantID),
(@StartingNewFactCardID + 34, @ComputersID),

-- Cloud computing
(@StartingNewFactCardID + 35, @ComputerScienceID),
(@StartingNewFactCardID + 35, @ImportantID),
(@StartingNewFactCardID + 35, @InternetID),

-- Email
(@StartingNewFactCardID + 36, @InternetID),
(@StartingNewFactCardID + 36, @ImportantID),
(@StartingNewFactCardID + 36, @ComputersID),

-- Moore's Law
(@StartingNewFactCardID + 37, @ComputerScienceID),
(@StartingNewFactCardID + 37, @ImportantID),
(@StartingNewFactCardID + 37, @ComputersID),

-- URL
(@StartingNewFactCardID + 38, @InternetID),
(@StartingNewFactCardID + 38, @ImportantID),
(@StartingNewFactCardID + 38, @VocabularyID),

-- Blockchain
(@StartingNewFactCardID + 39, @ComputerScienceID),
(@StartingNewFactCardID + 39, @ImportantID),
(@StartingNewFactCardID + 39, @ModernID),

-- Add tags for Languages fact cards (10 cards)
-- Languages count
(@StartingNewFactCardID + 40, @ImportantID),
(@StartingNewFactCardID + 40, @LanguageFamiliesID),
(@StartingNewFactCardID + 40, @TriviaID),

-- Oldest written language
(@StartingNewFactCardID + 41, @ImportantID),
(@StartingNewFactCardID + 41, @WritingSystemsID),
(@StartingNewFactCardID + 41, @AncientID),

-- Most spoken language
(@StartingNewFactCardID + 42, @ImportantID),
(@StartingNewFactCardID + 42, @LanguageFamiliesID),
(@StartingNewFactCardID + 42, @TriviaID),

-- Polyglot
(@StartingNewFactCardID + 43, @VocabularyID),
(@StartingNewFactCardID + 43, @EtymologyID),

-- Palindrome
(@StartingNewFactCardID + 44, @VocabularyID),
(@StartingNewFactCardID + 44, @GrammarID),

-- English words
(@StartingNewFactCardID + 45, @VocabularyID),
(@StartingNewFactCardID + 45, @TriviaID),

-- Hardest language
(@StartingNewFactCardID + 46, @ImportantID),
(@StartingNewFactCardID + 46, @LanguageFamiliesID),
(@StartingNewFactCardID + 46, @TriviaID),

-- Idiom
(@StartingNewFactCardID + 47, @VocabularyID),
(@StartingNewFactCardID + 47, @GrammarID),

-- Language vs dialect
(@StartingNewFactCardID + 48, @ImportantID),
(@StartingNewFactCardID + 48, @LanguageFamiliesID),

-- Esperanto
(@StartingNewFactCardID + 49, @ImportantID),
(@StartingNewFactCardID + 49, @ModernID),
(@StartingNewFactCardID + 49, @LanguageFamiliesID),

-- Add tags for Mathematics fact cards (10 cards)
-- Pi
(@StartingNewFactCardID + 50, @ImportantID),
(@StartingNewFactCardID + 50, @GeometryID),
(@StartingNewFactCardID + 50, @NumberTheoryID),

-- Pythagorean theorem
(@StartingNewFactCardID + 51, @ImportantID),
(@StartingNewFactCardID + 51, @GeometryID),

-- Prime number
(@StartingNewFactCardID + 52, @ImportantID),
(@StartingNewFactCardID + 52, @NumberTheoryID),

-- Fibonacci sequence
(@StartingNewFactCardID + 53, @ImportantID),
(@StartingNewFactCardID + 53, @NumberTheoryID),

-- Golden ratio
(@StartingNewFactCardID + 54, @ImportantID),
(@StartingNewFactCardID + 54, @GeometryID),
(@StartingNewFactCardID + 54, @NumberTheoryID),

-- Fractal
(@StartingNewFactCardID + 55, @ImportantID),
(@StartingNewFactCardID + 55, @GeometryID),

-- Calculus
(@StartingNewFactCardID + 56, @ImportantID),
(@StartingNewFactCardID + 56, @CalculusID),

-- Euler's number
(@StartingNewFactCardID + 57, @ImportantID),
(@StartingNewFactCardID + 57, @NumberTheoryID),
(@StartingNewFactCardID + 57, @CalculusID),

-- Perfect square
(@StartingNewFactCardID + 58, @ImportantID),
(@StartingNewFactCardID + 58, @NumberTheoryID),
(@StartingNewFactCardID + 58, @AlgebraID),

-- Mean, median, mode
(@StartingNewFactCardID + 59, @ImportantID),
(@StartingNewFactCardID + 59, @ProbabilityID)
GO

PRINT 'Successfully added 60 new facts to the FactDari database!'


---------------------------------------------------
--- Third Insert Batch
---------------------------------------------------
USE FactDari
GO

-- Get all CategoryIDs
DECLARE @ScienceID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Science')
DECLARE @HistoryID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'History')
DECLARE @GeographyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Geography')
DECLARE @TechnologyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Technology')
DECLARE @LanguagesID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Languages')
DECLARE @MathematicsID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Mathematics')
DECLARE @GeneralKnowledgeID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'General Knowledge')
DECLARE @DIYID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'DIY')

-- Add 40 more random facts across all categories
INSERT INTO FactCards (CategoryID, Question, Answer, NextReviewDate, CurrentInterval)
VALUES
-- Science (5 facts)
(@ScienceID, 'What is the half-life of Carbon-14?', 'Carbon-14 has a half-life of 5,730 years, making it useful for dating organic materials up to about 60,000 years old.', GETDATE(), 1),
(@ScienceID, 'What is the rarest blood type?', 'AB negative is the rarest blood type, found in only about 1% of the world''s population.', GETDATE(), 1),
(@ScienceID, 'How hot is the surface of the Sun?', 'The surface of the Sun (photosphere) is approximately 5,500°C (9,940°F).', GETDATE(), 1),
(@ScienceID, 'What is Newton''s First Law of Motion?', 'Newton''s First Law of Motion states that an object at rest stays at rest, and an object in motion stays in motion with the same speed and direction, unless acted upon by an external force.', GETDATE(), 1),
(@ScienceID, 'What is the human genome?', 'The human genome is the complete set of nucleic acid sequences for humans, encoded as DNA within the 23 chromosome pairs in cell nuclei and in a small DNA molecule found within mitochondria.', GETDATE(), 1),

-- History (5 facts)
(@HistoryID, 'When was the Great Fire of London?', 'The Great Fire of London occurred in September 1666, destroying over 13,000 houses and 87 churches including St. Paul''s Cathedral.', GETDATE(), 1),
(@HistoryID, 'Who was the first Emperor of China?', 'Qin Shi Huang was the first Emperor of China, reigning from 221 BCE to 210 BCE after unifying the seven warring states.', GETDATE(), 1),
(@HistoryID, 'When did the American Civil War end?', 'The American Civil War ended with the surrender of Confederate General Robert E. Lee to Union General Ulysses S. Grant at Appomattox Court House on April 9, 1865.', GETDATE(), 1),
(@HistoryID, 'What was the Magna Carta?', 'The Magna Carta was a charter of rights agreed to by King John of England in 1215, establishing the principle that everyone, including the king, was subject to the law.', GETDATE(), 1),
(@HistoryID, 'Who was Cleopatra?', 'Cleopatra VII was the last active ruler of the Ptolemaic Kingdom of Egypt, known for her relationships with Julius Caesar and Mark Antony, and her role in Roman politics.', GETDATE(), 1),

-- Geography (5 facts)
(@GeographyID, 'What is the capital of Brazil?', 'Brasília is the capital of Brazil, a planned city built specifically to serve as the capital in the central highlands of the country.', GETDATE(), 1),
(@GeographyID, 'What is the largest lake in Africa?', 'Lake Victoria is the largest lake in Africa and the second-largest freshwater lake in the world by surface area.', GETDATE(), 1),
(@GeographyID, 'Which mountain range separates Europe and Asia?', 'The Ural Mountains form a natural boundary between Europe and Asia, running approximately north to south through western Russia.', GETDATE(), 1),
(@GeographyID, 'What is the driest place on Earth?', 'The Atacama Desert in Chile is the driest place on Earth, with some areas having received no measurable rainfall for over 400 years.', GETDATE(), 1),
(@GeographyID, 'What are fjords?', 'Fjords are long, narrow, deep inlets of the sea between steep cliffs, typically formed by glacial erosion. They are most common in Norway, Chile, New Zealand, and Canada.', GETDATE(), 1),

-- Technology (5 facts)
(@TechnologyID, 'What is quantum computing?', 'Quantum computing uses quantum bits or qubits to perform computations that can potentially solve problems too complex for classical computers.', GETDATE(), 1),
(@TechnologyID, 'What is the difference between RAM and ROM?', 'RAM (Random Access Memory) is volatile memory used for temporary data storage during computer operation, while ROM (Read-Only Memory) is non-volatile memory that stores permanent data and instructions.', GETDATE(), 1),
(@TechnologyID, 'When was the first computer mouse invented?', 'The first computer mouse was invented by Douglas Engelbart in 1964. It was a wooden shell with two metal wheels and was called the "X-Y Position Indicator for a Display System."', GETDATE(), 1),
(@TechnologyID, 'What does HTML stand for?', 'HTML stands for HyperText Markup Language, the standard language used to create web pages and web applications.', GETDATE(), 1),
(@TechnologyID, 'What is the Internet of Things (IoT)?', 'The Internet of Things (IoT) refers to the network of physical objects embedded with sensors, software, and connectivity that enables them to connect and exchange data with other devices and systems over the internet.', GETDATE(), 1),

-- Languages (5 facts)
(@LanguagesID, 'What are the six official languages of the United Nations?', 'The six official languages of the United Nations are Arabic, Chinese, English, French, Russian, and Spanish.', GETDATE(), 1),
(@LanguagesID, 'What is the most widely spoken Romance language?', 'Spanish is the most widely spoken Romance language, with over 460 million native speakers worldwide.', GETDATE(), 1),
(@LanguagesID, 'What is a cognate?', 'A cognate is a word that has the same linguistic origin as another word. For example, the English word "night" and the German word "Nacht" are cognates.', GETDATE(), 1),
(@LanguagesID, 'What is onomatopoeia?', 'Onomatopoeia is the formation of a word from a sound associated with what is named, such as "buzz," "hiss," or "splash."', GETDATE(), 1),
(@LanguagesID, 'What is the study of meaning in language called?', 'Semantics is the branch of linguistics that studies the meaning of words, phrases, and sentences in language.', GETDATE(), 1),

-- Mathematics (5 facts)
(@MathematicsID, 'What is a logarithm?', 'A logarithm is the power to which a number must be raised to get another number. For example, the logarithm of 100 to the base 10 is 2, because 10² = 100.', GETDATE(), 1),
(@MathematicsID, 'What is the quadratic formula?', 'The quadratic formula, x = (-b ± √(b² - 4ac))/2a, solves the quadratic equation ax² + bx + c = 0 for the value of x.', GETDATE(), 1),
(@MathematicsID, 'What is a Venn diagram?', 'A Venn diagram is a diagram that shows all possible logical relations between a finite collection of sets, represented as overlapping circles.', GETDATE(), 1),
(@MathematicsID, 'What is the Riemann Hypothesis?', 'The Riemann Hypothesis is one of the most important unsolved problems in mathematics, concerning the distribution of prime numbers and the zeros of the Riemann zeta function.', GETDATE(), 1),
(@MathematicsID, 'What is a quaternion?', 'A quaternion is a four-dimensional complex number used to represent rotations in three-dimensional space, introduced by William Rowan Hamilton in 1843.', GETDATE(), 1),

-- General Knowledge (5 facts)
(@GeneralKnowledgeID, 'What is the largest organ in the human body?', 'The skin is the largest organ in the human body, with a total area of about 20 square feet in adults.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many elements are in the periodic table?', 'There are currently 118 confirmed elements in the periodic table, with elements 1-94 occurring naturally on Earth (though some only in trace amounts).', GETDATE(), 1),
(@GeneralKnowledgeID, 'What causes a rainbow?', 'Rainbows are caused by the reflection, refraction, and dispersion of light in water droplets, creating a spectrum of colors in the sky.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the most widely used spice in the world?', 'Black pepper is the most widely used spice in the world, native to South India and commonly used in cuisines worldwide.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the fastest land animal?', 'The cheetah is the fastest land animal, capable of reaching speeds up to 70 mph (113 km/h) in short bursts.', GETDATE(), 1),

-- DIY (5 facts)
(@DIYID, 'How can you naturally clean a coffee maker?', 'Run equal parts white vinegar and water through your coffee maker, followed by two cycles of clean water. The acidity of vinegar removes mineral buildup and kills bacteria.', GETDATE(), 1),
(@DIYID, 'What''s an easy way to remove water rings from wooden furniture?', 'Rub a mixture of equal parts olive oil and salt onto the water ring, let sit for 30 minutes, then wipe away. The oil rehydrates the wood while the salt absorbs moisture.', GETDATE(), 1),
(@DIYID, 'How can you keep brown sugar from hardening?', 'Place a piece of bread or a few marshmallows in the container with your brown sugar. They release moisture that keeps the sugar soft and prevents it from hardening.', GETDATE(), 1),
(@DIYID, 'What''s a simple way to clean grout between tiles?', 'Make a paste of baking soda and hydrogen peroxide, apply to grout lines, let sit for 10 minutes, then scrub with an old toothbrush. The combination lifts stains while killing mold and bacteria.', GETDATE(), 1),
(@DIYID, 'How can you easily remove stuck-on food from pots and pans?', 'Fill the pot with water and a tablespoon of dish soap, bring to a boil for 5-10 minutes. The heat and soap will soften the residue, making it easy to wipe away.', GETDATE(), 1)
GO

-- Get the starting ID for our newly inserted fact cards
DECLARE @StartingNewFactCardID INT = (SELECT MAX(FactCardID) - 39 FROM FactCards)

-- Get Tag IDs for tagging the new fact cards
DECLARE @ImportantID INT = (SELECT TagID FROM Tags WHERE TagName = 'Important')
DECLARE @PhysicsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Physics')
DECLARE @BiologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Biology')
DECLARE @ChemistryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Chemistry')
DECLARE @AncientID INT = (SELECT TagID FROM Tags WHERE TagName = 'Ancient')
DECLARE @ModernID INT = (SELECT TagID FROM Tags WHERE TagName = 'Modern')
DECLARE @EuropeID INT = (SELECT TagID FROM Tags WHERE TagName = 'Europe')
DECLARE @AsiaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Asia')
DECLARE @ComputerScienceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Computer Science')
DECLARE @ProgrammingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Programming')
DECLARE @VocabularyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Vocabulary')
DECLARE @GrammarID INT = (SELECT TagID FROM Tags WHERE TagName = 'Grammar')
DECLARE @AlgebraID INT = (SELECT TagID FROM Tags WHERE TagName = 'Algebra')
DECLARE @GeometryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Geometry')
DECLARE @CalculusID INT = (SELECT TagID FROM Tags WHERE TagName = 'Calculus')
DECLARE @TriviaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Trivia')
DECLARE @FunFactsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Fun Facts')
DECLARE @EntertainmentID INT = (SELECT TagID FROM Tags WHERE TagName = 'Entertainment')
DECLARE @HealthID INT = (SELECT TagID FROM Tags WHERE TagName = 'Health')
DECLARE @AnimalsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Animals')
DECLARE @SpaceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Space')
DECLARE @AstronomyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Astronomy')
DECLARE @WeatherID INT = (SELECT TagID FROM Tags WHERE TagName = 'Weather')
DECLARE @AncientHistoryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Ancient History')
DECLARE @MedievalID INT = (SELECT TagID FROM Tags WHERE TagName = 'Medieval')
DECLARE @RenaissanceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Renaissance')
DECLARE @WorldWarsID INT = (SELECT TagID FROM Tags WHERE TagName = 'World Wars')
DECLARE @MountainsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Mountains')
DECLARE @RiversID INT = (SELECT TagID FROM Tags WHERE TagName = 'Rivers')
DECLARE @DesertsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Deserts')
DECLARE @IslandsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Islands')
DECLARE @ComputersID INT = (SELECT TagID FROM Tags WHERE TagName = 'Computers')
DECLARE @InternetID INT = (SELECT TagID FROM Tags WHERE TagName = 'Internet')
DECLARE @RoboticsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Robotics')
DECLARE @ArtificialIntelligenceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Artificial Intelligence')
DECLARE @EtymologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Etymology')
DECLARE @WritingSystemsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Writing Systems')
DECLARE @LanguageFamiliesID INT = (SELECT TagID FROM Tags WHERE TagName = 'Language Families')
DECLARE @FamousMathematiciansID INT = (SELECT TagID FROM Tags WHERE TagName = 'Famous Mathematicians')
DECLARE @NumberTheoryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Number Theory')
DECLARE @ProbabilityID INT = (SELECT TagID FROM Tags WHERE TagName = 'Probability')
DECLARE @ElementsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Elements')
DECLARE @CleaningID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cleaning')
DECLARE @FoodID INT = (SELECT TagID FROM Tags WHERE TagName = 'Food')
DECLARE @CookingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cooking')
DECLARE @LifeHacksID INT = (SELECT TagID FROM Tags WHERE TagName = 'Life Hacks')
DECLARE @HomeImprovementID INT = (SELECT TagID FROM Tags WHERE TagName = 'Home Improvement')

-- Add tags for the new fact cards
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES
-- Science facts tags
-- Carbon-14
(@StartingNewFactCardID, @ChemistryID),
(@StartingNewFactCardID, @PhysicsID),
(@StartingNewFactCardID, @ImportantID),

-- Blood type
(@StartingNewFactCardID + 1, @BiologyID),
(@StartingNewFactCardID + 1, @HealthID),
(@StartingNewFactCardID + 1, @TriviaID),

-- Sun surface
(@StartingNewFactCardID + 2, @AstronomyID),
(@StartingNewFactCardID + 2, @SpaceID),
(@StartingNewFactCardID + 2, @ImportantID),

-- Newton's Law
(@StartingNewFactCardID + 3, @PhysicsID),
(@StartingNewFactCardID + 3, @ImportantID),

-- Human genome
(@StartingNewFactCardID + 4, @BiologyID),
(@StartingNewFactCardID + 4, @ImportantID),
(@StartingNewFactCardID + 4, @HealthID),

-- History facts tags
-- Great Fire of London
(@StartingNewFactCardID + 5, @ModernID),
(@StartingNewFactCardID + 5, @EuropeID),
(@StartingNewFactCardID + 5, @ImportantID),

-- First Emperor of China
(@StartingNewFactCardID + 6, @AncientID),
(@StartingNewFactCardID + 6, @AncientHistoryID),
(@StartingNewFactCardID + 6, @AsiaID),

-- American Civil War
(@StartingNewFactCardID + 7, @ModernID),
(@StartingNewFactCardID + 7, @ImportantID),

-- Magna Carta
(@StartingNewFactCardID + 8, @MedievalID),
(@StartingNewFactCardID + 8, @EuropeID),
(@StartingNewFactCardID + 8, @ImportantID),

-- Cleopatra
(@StartingNewFactCardID + 9, @AncientID),
(@StartingNewFactCardID + 9, @AncientHistoryID),
(@StartingNewFactCardID + 9, @ImportantID),

-- Geography facts tags
-- Brazil capital
(@StartingNewFactCardID + 10, @ImportantID),
(@StartingNewFactCardID + 10, @TriviaID),

-- Lake Victoria
(@StartingNewFactCardID + 11, @ImportantID),
(@StartingNewFactCardID + 11, @TriviaID),

-- Ural Mountains
(@StartingNewFactCardID + 12, @ImportantID),
(@StartingNewFactCardID + 12, @MountainsID),
(@StartingNewFactCardID + 12, @EuropeID),
(@StartingNewFactCardID + 12, @AsiaID),

-- Atacama Desert
(@StartingNewFactCardID + 13, @ImportantID),
(@StartingNewFactCardID + 13, @DesertsID),
(@StartingNewFactCardID + 13, @TriviaID),

-- Fjords
(@StartingNewFactCardID + 14, @ImportantID),
(@StartingNewFactCardID + 14, @TriviaID),

-- Technology facts tags
-- Quantum computing
(@StartingNewFactCardID + 15, @ImportantID),
(@StartingNewFactCardID + 15, @ComputerScienceID),
(@StartingNewFactCardID + 15, @ModernID),

-- RAM vs ROM
(@StartingNewFactCardID + 16, @ImportantID),
(@StartingNewFactCardID + 16, @ComputerScienceID),
(@StartingNewFactCardID + 16, @ComputersID),

-- Computer mouse
(@StartingNewFactCardID + 17, @ImportantID),
(@StartingNewFactCardID + 17, @ComputersID),
(@StartingNewFactCardID + 17, @ModernID),

-- HTML
(@StartingNewFactCardID + 18, @ImportantID),
(@StartingNewFactCardID + 18, @InternetID),
(@StartingNewFactCardID + 18, @ProgrammingID),

-- IoT
(@StartingNewFactCardID + 19, @ImportantID),
(@StartingNewFactCardID + 19, @ComputerScienceID),
(@StartingNewFactCardID + 19, @ModernID),

-- Languages facts tags
-- UN languages
(@StartingNewFactCardID + 20, @ImportantID),
(@StartingNewFactCardID + 20, @LanguageFamiliesID),
(@StartingNewFactCardID + 20, @ModernID),

-- Romance language
(@StartingNewFactCardID + 21, @ImportantID),
(@StartingNewFactCardID + 21, @LanguageFamiliesID),
(@StartingNewFactCardID + 21, @TriviaID),

-- Cognate
(@StartingNewFactCardID + 22, @ImportantID),
(@StartingNewFactCardID + 22, @VocabularyID),
(@StartingNewFactCardID + 22, @EtymologyID),

-- Onomatopoeia
(@StartingNewFactCardID + 23, @ImportantID),
(@StartingNewFactCardID + 23, @GrammarID),
(@StartingNewFactCardID + 23, @VocabularyID),

-- Semantics
(@StartingNewFactCardID + 24, @ImportantID),
(@StartingNewFactCardID + 24, @GrammarID),
(@StartingNewFactCardID + 24, @LanguageFamiliesID),

-- Mathematics facts tags
-- Logarithm
(@StartingNewFactCardID + 25, @ImportantID),
(@StartingNewFactCardID + 25, @AlgebraID),

-- Quadratic formula
(@StartingNewFactCardID + 26, @ImportantID),
(@StartingNewFactCardID + 26, @AlgebraID),

-- Venn diagram
(@StartingNewFactCardID + 27, @ImportantID),
(@StartingNewFactCardID + 27, @ProbabilityID),

-- Riemann Hypothesis
(@StartingNewFactCardID + 28, @ImportantID),
(@StartingNewFactCardID + 28, @NumberTheoryID),
(@StartingNewFactCardID + 28, @FamousMathematiciansID),

-- Quaternion
(@StartingNewFactCardID + 29, @ImportantID),
(@StartingNewFactCardID + 29, @GeometryID),
(@StartingNewFactCardID + 29, @FamousMathematiciansID),

-- General Knowledge facts tags
-- Skin
(@StartingNewFactCardID + 30, @ImportantID),
(@StartingNewFactCardID + 30, @BiologyID),
(@StartingNewFactCardID + 30, @HealthID),

-- Periodic table
(@StartingNewFactCardID + 31, @ImportantID),
(@StartingNewFactCardID + 31, @ChemistryID),
(@StartingNewFactCardID + 31, @ElementsID),

-- Rainbow
(@StartingNewFactCardID + 32, @ImportantID),
(@StartingNewFactCardID + 32, @PhysicsID),
(@StartingNewFactCardID + 32, @WeatherID),

-- Black pepper
(@StartingNewFactCardID + 33, @ImportantID),
(@StartingNewFactCardID + 33, @FoodID),
(@StartingNewFactCardID + 33, @TriviaID),

-- Cheetah
(@StartingNewFactCardID + 34, @ImportantID),
(@StartingNewFactCardID + 34, @AnimalsID),
(@StartingNewFactCardID + 34, @TriviaID),

-- DIY facts tags
-- Coffee maker cleaning
(@StartingNewFactCardID + 35, @CleaningID),
(@StartingNewFactCardID + 35, @LifeHacksID),
(@StartingNewFactCardID + 35, @HomeImprovementID),

-- Water rings
(@StartingNewFactCardID + 36, @CleaningID),
(@StartingNewFactCardID + 36, @LifeHacksID),
(@StartingNewFactCardID + 36, @HomeImprovementID),

-- Brown sugar
(@StartingNewFactCardID + 37, @FoodID),
(@StartingNewFactCardID + 37, @CookingID),
(@StartingNewFactCardID + 37, @LifeHacksID),

-- Grout cleaning
(@StartingNewFactCardID + 38, @CleaningID),
(@StartingNewFactCardID + 38, @LifeHacksID),
(@StartingNewFactCardID + 38, @HomeImprovementID),

-- Pot cleaning
(@StartingNewFactCardID + 39, @CleaningID),
(@StartingNewFactCardID + 39, @LifeHacksID),
(@StartingNewFactCardID + 39, @CookingID)
GO

PRINT 'Successfully added 40 more random facts across all categories to the FactDari database!'

---------------------------------------------------
--- Forth Insert Batch
---------------------------------------------------
USE FactDari
GO

-- Get all CategoryIDs
DECLARE @ScienceID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Science')
DECLARE @HistoryID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'History')
DECLARE @GeographyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Geography')
DECLARE @TechnologyID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Technology')
DECLARE @LanguagesID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Languages')
DECLARE @MathematicsID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'Mathematics')
DECLARE @GeneralKnowledgeID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'General Knowledge')
DECLARE @DIYID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'DIY')

-- Add 50 more random facts across all categories
INSERT INTO FactCards (CategoryID, Question, Answer, NextReviewDate, CurrentInterval)
VALUES
-- Science (7 facts)
(@ScienceID, 'What is the only metal that is liquid at room temperature?', 'Mercury is the only metal that remains in liquid form at room temperature.', GETDATE(), 1),
(@ScienceID, 'What are animals without backbones called?', 'Animals without backbones are called invertebrates, making up about 97% of all animal species.', GETDATE(), 1),
(@ScienceID, 'What is the Doppler effect?', 'The Doppler effect is the change in frequency of a wave in relation to an observer moving relative to the source of the wave, such as when an ambulance passes by.', GETDATE(), 1),
(@ScienceID, 'What is the largest internal organ in the human body?', 'The liver is the largest internal organ in the human body, weighing about 3 pounds in adults.', GETDATE(), 1),
(@ScienceID, 'What is the name for the process plants use to make food?', 'Photosynthesis is the process by which plants convert light energy into chemical energy to fuel their activities.', GETDATE(), 1),
(@ScienceID, 'What is the coldest place in the universe?', 'The Boomerang Nebula is the coldest place in the universe at just 1 Kelvin (-272.15°C), colder than the background radiation of space.', GETDATE(), 1),
(@ScienceID, 'What is the strongest naturally occurring acid?', 'Fluoroantimonic acid is the strongest naturally occurring acid, over a billion times stronger than sulfuric acid.', GETDATE(), 1),

-- History (7 facts)
(@HistoryID, 'Who was the first female Prime Minister of the United Kingdom?', 'Margaret Thatcher was the first female Prime Minister of the United Kingdom, serving from 1979 to 1990.', GETDATE(), 1),
(@HistoryID, 'What was the name of the first dynasty of Ancient Egypt?', 'The First Dynasty of Ancient Egypt was founded by King Narmer (also known as Menes) around 3100 BCE, unifying Upper and Lower Egypt.', GETDATE(), 1),
(@HistoryID, 'What was the shortest war in history?', 'The Anglo-Zanzibar War of 1896 is considered the shortest war in history, lasting only 38-45 minutes.', GETDATE(), 1),
(@HistoryID, 'Who invented the telephone?', 'Alexander Graham Bell is credited with inventing the first practical telephone and was awarded the first U.S. patent for it in 1876.', GETDATE(), 1),
(@HistoryID, 'What was the lost city of Machu Picchu?', 'Machu Picchu was an Incan citadel built in the 15th century in the Andes Mountains of Peru, abandoned during the Spanish conquest and rediscovered in 1911.', GETDATE(), 1),
(@HistoryID, 'When was the United Nations founded?', 'The United Nations was founded on October 24, 1945, after World War II to replace the League of Nations and promote international cooperation.', GETDATE(), 1),
(@HistoryID, 'Who was Joan of Arc?', 'Joan of Arc was a French peasant girl who led the French army to several important victories during the Hundred Years'' War and was later burned at the stake for heresy in 1431.', GETDATE(), 1),

-- Geography (7 facts)
(@GeographyID, 'What is the world''s largest coral reef system?', 'The Great Barrier Reef off the coast of Australia is the world''s largest coral reef system, stretching over 1,400 miles.', GETDATE(), 1),
(@GeographyID, 'What is the smallest independent country in the world by population?', 'Vatican City is the smallest independent country in the world by population, with fewer than 1,000 residents.', GETDATE(), 1),
(@GeographyID, 'What is the Ring of Fire?', 'The Ring of Fire is a horseshoe-shaped belt of intense seismic and volcanic activity encircling the Pacific Ocean, containing about 75% of the world''s active volcanoes.', GETDATE(), 1),
(@GeographyID, 'What is the average depth of the ocean?', 'The average depth of the ocean is about 12,100 feet (3,688 meters).', GETDATE(), 1),
(@GeographyID, 'Which is the largest freshwater lake in the world by volume?', 'Lake Baikal in Russia is the largest freshwater lake by volume, containing about 20% of the world''s unfrozen surface fresh water.', GETDATE(), 1),
(@GeographyID, 'What are barrier islands?', 'Barrier islands are long, narrow offshore deposits of sand that run parallel to the coast and protect the mainland from ocean waves and storms.', GETDATE(), 1),
(@GeographyID, 'What is the highest waterfall in the world?', 'Angel Falls in Venezuela is the world''s highest uninterrupted waterfall, with a height of 3,212 feet (979 meters).', GETDATE(), 1),

-- Technology (6 facts)
(@TechnologyID, 'What does API stand for in computer programming?', 'API stands for Application Programming Interface, a set of rules that allows different software applications to communicate with each other.', GETDATE(), 1),
(@TechnologyID, 'What does VPN stand for?', 'VPN stands for Virtual Private Network, a service that protects your internet connection and privacy online.', GETDATE(), 1),
(@TechnologyID, 'Who is considered the first computer programmer?', 'Ada Lovelace is considered the first computer programmer, having written an algorithm for Charles Babbage''s Analytical Engine in the 1840s.', GETDATE(), 1),
(@TechnologyID, 'What is the difference between hardware and software?', 'Hardware refers to the physical components of a computer system that you can touch, while software refers to the programs and applications that run on the hardware.', GETDATE(), 1),
(@TechnologyID, 'What is machine learning?', 'Machine learning is a branch of artificial intelligence focused on building applications that learn from data and improve their accuracy over time without being explicitly programmed.', GETDATE(), 1),
(@TechnologyID, 'What is a transistor?', 'A transistor is a semiconductor device used to amplify or switch electronic signals, forming the foundation of modern electronics and computing technology.', GETDATE(), 1),

-- Languages (6 facts)
(@LanguagesID, 'What language has the most phonemes?', 'The !Xóõ language, spoken in Southern Africa, has the most phonemes of any known language with 130 distinct sound units.', GETDATE(), 1),
(@LanguagesID, 'What is a lingua franca?', 'A lingua franca is a language systematically used to communicate between people who do not share a native language, such as English in international business.', GETDATE(), 1),
(@LanguagesID, 'What is the oldest continuously used alphabet?', 'The Hebrew alphabet is the oldest continuously used alphabet, dating back to around 1800 BCE.', GETDATE(), 1),
(@LanguagesID, 'What is a portmanteau word?', 'A portmanteau is a word blending the sounds and meanings of two others, such as "smog" (smoke + fog) or "brunch" (breakfast + lunch).', GETDATE(), 1),
(@LanguagesID, 'What language has the most words?', 'English is believed to have the most words of any language, with over 170,000 words in current use and 47,000 obsolete words.', GETDATE(), 1),
(@LanguagesID, 'What is code-switching?', 'Code-switching is the practice of alternating between two or more languages or language varieties in a single conversation.', GETDATE(), 1),

-- Mathematics (6 facts)
(@MathematicsID, 'What does the symbol ∞ represent?', 'The symbol ∞ represents infinity, a concept describing something without any bound or larger than any natural number.', GETDATE(), 1),
(@MathematicsID, 'What is a prime factorization?', 'Prime factorization is the decomposition of a number into a product of prime numbers, which are only divisible by 1 and themselves.', GETDATE(), 1),
(@MathematicsID, 'What is a transcendental number?', 'A transcendental number is a real or complex number that is not algebraic—that is, not a root of a non-zero polynomial with rational coefficients. Pi and e are examples.', GETDATE(), 1),
(@MathematicsID, 'What are the first five perfect numbers?', 'The first five perfect numbers are 6, 28, 496, 8128, and 33,550,336. A perfect number equals the sum of its proper divisors.', GETDATE(), 1),
(@MathematicsID, 'What is the Mandelbrot set?', 'The Mandelbrot set is a famous fractal set of points in the complex plane, known for generating intricate and infinitely complex boundary patterns.', GETDATE(), 1),
(@MathematicsID, 'What is the difference between correlation and causation?', 'Correlation indicates a relationship between two variables, while causation explicitly states that one variable leads to the occurrence of another.', GETDATE(), 1),

-- General Knowledge (6 facts)
(@GeneralKnowledgeID, 'What is the largest type of big cat in the world?', 'The Siberian tiger is the largest big cat in the world, weighing up to 660 pounds and measuring up to 10 feet in length.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of crows called?', 'A group of crows is called a "murder."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many tentacles does an octopus have?', 'An octopus has eight tentacles, which are actually arms with suction cups that they use for grabbing and tasting.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the largest type of penguin?', 'The Emperor Penguin is the largest type of penguin, standing up to 4 feet tall and weighing up to 100 pounds.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How long can a sloth stay underwater?', 'Sloths can hold their breath underwater for up to 40 minutes, slowing their heart rate to one-third its normal rate.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of Earth''s water is drinkable?', 'Only about 0.3% of Earth''s water is readily available freshwater suitable for human consumption.', GETDATE(), 1),

-- DIY (5 facts)
(@DIYID, 'How can you remove ink stains from clothing?', 'Apply rubbing alcohol to the ink stain using a cotton ball, blot (don''t rub) until the ink is lifted, then wash normally. The alcohol dissolves the ink without spreading it.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to remove odors from a refrigerator?', 'Place an open box of baking soda in the refrigerator to absorb odors. Replace it every three months for continuous freshness.', GETDATE(), 1),
(@DIYID, 'How can you extend the life of your razor blades?', 'Dry your razor thoroughly after each use and dip it in olive oil or rubbing alcohol. This prevents oxidation and mineral buildup that cause dullness.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean a microfiber couch?', 'For microfiber couches, use rubbing alcohol in a spray bottle, spray lightly, then brush with a clean white brush. The alcohol evaporates quickly without leaving water stains.', GETDATE(), 1),
(@DIYID, 'How can you get wrinkles out of clothes without an iron?', 'Hang wrinkled clothing in the bathroom during a hot shower. The steam will naturally release many wrinkles without the need for ironing.', GETDATE(), 1)
GO

-- Get the starting ID for our newly inserted fact cards
DECLARE @StartingNewFactCardID INT = (SELECT MAX(FactCardID) - 49 FROM FactCards)

-- Get Tag IDs for tagging the new fact cards
DECLARE @ImportantID INT = (SELECT TagID FROM Tags WHERE TagName = 'Important')
DECLARE @PhysicsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Physics')
DECLARE @BiologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Biology')
DECLARE @ChemistryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Chemistry')
DECLARE @AncientID INT = (SELECT TagID FROM Tags WHERE TagName = 'Ancient')
DECLARE @ModernID INT = (SELECT TagID FROM Tags WHERE TagName = 'Modern')
DECLARE @EuropeID INT = (SELECT TagID FROM Tags WHERE TagName = 'Europe')
DECLARE @AsiaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Asia')
DECLARE @ComputerScienceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Computer Science')
DECLARE @ProgrammingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Programming')
DECLARE @VocabularyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Vocabulary')
DECLARE @GrammarID INT = (SELECT TagID FROM Tags WHERE TagName = 'Grammar')
DECLARE @AlgebraID INT = (SELECT TagID FROM Tags WHERE TagName = 'Algebra')
DECLARE @GeometryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Geometry')
DECLARE @CalculusID INT = (SELECT TagID FROM Tags WHERE TagName = 'Calculus')
DECLARE @TriviaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Trivia')
DECLARE @FunFactsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Fun Facts')
DECLARE @EntertainmentID INT = (SELECT TagID FROM Tags WHERE TagName = 'Entertainment')
DECLARE @HealthID INT = (SELECT TagID FROM Tags WHERE TagName = 'Health')
DECLARE @AnimalsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Animals')
DECLARE @SpaceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Space')
DECLARE @AstronomyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Astronomy')
DECLARE @ElementsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Elements')
DECLARE @WeatherID INT = (SELECT TagID FROM Tags WHERE TagName = 'Weather')
DECLARE @AncientHistoryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Ancient History')
DECLARE @MedievalID INT = (SELECT TagID FROM Tags WHERE TagName = 'Medieval')
DECLARE @RenaissanceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Renaissance')
DECLARE @WorldWarsID INT = (SELECT TagID FROM Tags WHERE TagName = 'World Wars')
DECLARE @MountainsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Mountains')
DECLARE @RiversID INT = (SELECT TagID FROM Tags WHERE TagName = 'Rivers')
DECLARE @DesertsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Deserts')
DECLARE @IslandsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Islands')
DECLARE @ComputersID INT = (SELECT TagID FROM Tags WHERE TagName = 'Computers')
DECLARE @InternetID INT = (SELECT TagID FROM Tags WHERE TagName = 'Internet')
DECLARE @RoboticsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Robotics')
DECLARE @ArtificialIntelligenceID INT = (SELECT TagID FROM Tags WHERE TagName = 'Artificial Intelligence')
DECLARE @EtymologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Etymology')
DECLARE @WritingSystemsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Writing Systems')
DECLARE @LanguageFamiliesID INT = (SELECT TagID FROM Tags WHERE TagName = 'Language Families')
DECLARE @FamousMathematiciansID INT = (SELECT TagID FROM Tags WHERE TagName = 'Famous Mathematicians')
DECLARE @NumberTheoryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Number Theory')
DECLARE @ProbabilityID INT = (SELECT TagID FROM Tags WHERE TagName = 'Probability')
DECLARE @CleaningID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cleaning')
DECLARE @FoodID INT = (SELECT TagID FROM Tags WHERE TagName = 'Food')
DECLARE @CookingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cooking')
DECLARE @LifeHacksID INT = (SELECT TagID FROM Tags WHERE TagName = 'Life Hacks')
DECLARE @HomeImprovementID INT = (SELECT TagID FROM Tags WHERE TagName = 'Home Improvement')
DECLARE @DifficultiID INT = (SELECT TagID FROM Tags WHERE TagName = 'Difficult')
DECLARE @ReviewID INT = (SELECT TagID FROM Tags WHERE TagName = 'Review')

-- Add tags for the new fact cards
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES
-- Science facts tags
-- Mercury
(@StartingNewFactCardID, @ChemistryID),
(@StartingNewFactCardID, @ElementsID),
(@StartingNewFactCardID, @TriviaID),

-- Invertebrates
(@StartingNewFactCardID + 1, @BiologyID),
(@StartingNewFactCardID + 1, @AnimalsID),
(@StartingNewFactCardID + 1, @ImportantID),

-- Doppler effect
(@StartingNewFactCardID + 2, @PhysicsID),
(@StartingNewFactCardID + 2, @ImportantID),

-- Liver
(@StartingNewFactCardID + 3, @BiologyID),
(@StartingNewFactCardID + 3, @HealthID),
(@StartingNewFactCardID + 3, @ImportantID),

-- Photosynthesis
(@StartingNewFactCardID + 4, @BiologyID),
(@StartingNewFactCardID + 4, @ChemistryID),
(@StartingNewFactCardID + 4, @ImportantID),

-- Boomerang Nebula
(@StartingNewFactCardID + 5, @AstronomyID),
(@StartingNewFactCardID + 5, @SpaceID),
(@StartingNewFactCardID + 5, @FunFactsID),

-- Fluoroantimonic acid
(@StartingNewFactCardID + 6, @ChemistryID),
(@StartingNewFactCardID + 6, @ElementsID),
(@StartingNewFactCardID + 6, @DifficultiID),

-- History facts tags
-- Margaret Thatcher
(@StartingNewFactCardID + 7, @ModernID),
(@StartingNewFactCardID + 7, @EuropeID),
(@StartingNewFactCardID + 7, @ImportantID),

-- First Dynasty Egypt
(@StartingNewFactCardID + 8, @AncientID),
(@StartingNewFactCardID + 8, @AncientHistoryID),
(@StartingNewFactCardID + 8, @ImportantID),

-- Anglo-Zanzibar War
(@StartingNewFactCardID + 9, @ModernID),
(@StartingNewFactCardID + 9, @FunFactsID),
(@StartingNewFactCardID + 9, @TriviaID),

-- Telephone
(@StartingNewFactCardID + 10, @ModernID),
(@StartingNewFactCardID + 10, @ImportantID),

-- Machu Picchu
(@StartingNewFactCardID + 11, @MedievalID),
(@StartingNewFactCardID + 11, @ImportantID),

-- United Nations
(@StartingNewFactCardID + 12, @ModernID),
(@StartingNewFactCardID + 12, @ImportantID),
(@StartingNewFactCardID + 12, @WorldWarsID),

-- Joan of Arc
(@StartingNewFactCardID + 13, @MedievalID),
(@StartingNewFactCardID + 13, @EuropeID),
(@StartingNewFactCardID + 13, @ImportantID),

-- Geography facts tags
-- Great Barrier Reef
(@StartingNewFactCardID + 14, @ImportantID),
(@StartingNewFactCardID + 14, @TriviaID),

-- Vatican City
(@StartingNewFactCardID + 15, @ImportantID),
(@StartingNewFactCardID + 15, @EuropeID),
(@StartingNewFactCardID + 15, @TriviaID),

-- Ring of Fire
(@StartingNewFactCardID + 16, @ImportantID),
(@StartingNewFactCardID + 16, @TriviaID),

-- Ocean depth
(@StartingNewFactCardID + 17, @ImportantID),
(@StartingNewFactCardID + 17, @TriviaID),

-- Lake Baikal
(@StartingNewFactCardID + 18, @ImportantID),
(@StartingNewFactCardID + 18, @AsiaID),
(@StartingNewFactCardID + 18, @TriviaID),

-- Barrier islands
(@StartingNewFactCardID + 19, @ImportantID),
(@StartingNewFactCardID + 19, @TriviaID),

-- Angel Falls
(@StartingNewFactCardID + 20, @ImportantID),
(@StartingNewFactCardID + 20, @TriviaID),
(@StartingNewFactCardID + 20, @RiversID),

-- Technology facts tags
-- API
(@StartingNewFactCardID + 21, @ComputerScienceID),
(@StartingNewFactCardID + 21, @ProgrammingID),
(@StartingNewFactCardID + 21, @ImportantID),

-- VPN
(@StartingNewFactCardID + 22, @ComputerScienceID),
(@StartingNewFactCardID + 22, @InternetID),
(@StartingNewFactCardID + 22, @ImportantID),

-- Ada Lovelace
(@StartingNewFactCardID + 23, @ComputerScienceID),
(@StartingNewFactCardID + 23, @ImportantID),
(@StartingNewFactCardID + 23, @ModernID),

-- Hardware vs Software
(@StartingNewFactCardID + 24, @ComputerScienceID),
(@StartingNewFactCardID + 24, @ComputersID),
(@StartingNewFactCardID + 24, @ImportantID),

-- Machine learning
(@StartingNewFactCardID + 25, @ComputerScienceID),
(@StartingNewFactCardID + 25, @ArtificialIntelligenceID),
(@StartingNewFactCardID + 25, @ImportantID),

-- Transistor
(@StartingNewFactCardID + 26, @ComputerScienceID),
(@StartingNewFactCardID + 26, @PhysicsID),
(@StartingNewFactCardID + 26, @ImportantID),

-- Languages facts tags
-- !Xóõ language
(@StartingNewFactCardID + 27, @LanguageFamiliesID),
(@StartingNewFactCardID + 27, @TriviaID),
(@StartingNewFactCardID + 27, @FunFactsID),

-- Lingua franca
(@StartingNewFactCardID + 28, @LanguageFamiliesID),
(@StartingNewFactCardID + 28, @VocabularyID),
(@StartingNewFactCardID + 28, @ImportantID),

-- Hebrew alphabet
(@StartingNewFactCardID + 29, @WritingSystemsID),
(@StartingNewFactCardID + 29, @AncientID),
(@StartingNewFactCardID + 29, @ImportantID),

-- Portmanteau
(@StartingNewFactCardID + 30, @VocabularyID),
(@StartingNewFactCardID + 30, @GrammarID),
(@StartingNewFactCardID + 30, @ImportantID),

-- English words
(@StartingNewFactCardID + 31, @VocabularyID),
(@StartingNewFactCardID + 31, @LanguageFamiliesID),
(@StartingNewFactCardID + 31, @TriviaID),

-- Code-switching
(@StartingNewFactCardID + 32, @LanguageFamiliesID),
(@StartingNewFactCardID + 32, @GrammarID),
(@StartingNewFactCardID + 32, @ImportantID),

-- Mathematics facts tags
-- Infinity symbol
(@StartingNewFactCardID + 33, @ImportantID),
(@StartingNewFactCardID + 33, @NumberTheoryID),
(@StartingNewFactCardID + 33, @AlgebraID),

-- Prime factorization
(@StartingNewFactCardID + 34, @ImportantID),
(@StartingNewFactCardID + 34, @NumberTheoryID),
(@StartingNewFactCardID + 34, @AlgebraID),

-- Transcendental number
(@StartingNewFactCardID + 35, @ImportantID),
(@StartingNewFactCardID + 35, @NumberTheoryID),
(@StartingNewFactCardID + 35, @DifficultiID),

-- Perfect numbers
(@StartingNewFactCardID + 36, @ImportantID),
(@StartingNewFactCardID + 36, @NumberTheoryID),
(@StartingNewFactCardID + 36, @TriviaID),

-- Mandelbrot set
(@StartingNewFactCardID + 37, @ImportantID),
(@StartingNewFactCardID + 37, @GeometryID),
(@StartingNewFactCardID + 37, @DifficultiID),

-- Correlation vs causation
(@StartingNewFactCardID + 38, @ImportantID),
(@StartingNewFactCardID + 38, @ProbabilityID),

-- General Knowledge facts tags
-- Siberian tiger
(@StartingNewFactCardID + 39, @AnimalsID),
(@StartingNewFactCardID + 39, @TriviaID),
(@StartingNewFactCardID + 39, @FunFactsID),

-- Murder of crows
(@StartingNewFactCardID + 40, @AnimalsID),
(@StartingNewFactCardID + 40, @VocabularyID),
(@StartingNewFactCardID + 40, @FunFactsID),

-- Octopus tentacles
(@StartingNewFactCardID + 41, @AnimalsID),
(@StartingNewFactCardID + 41, @BiologyID),
(@StartingNewFactCardID + 41, @TriviaID),

-- Emperor Penguin
(@StartingNewFactCardID + 42, @AnimalsID),
(@StartingNewFactCardID + 42, @TriviaID),
(@StartingNewFactCardID + 42, @FunFactsID),

-- Sloth underwater
(@StartingNewFactCardID + 43, @AnimalsID),
(@StartingNewFactCardID + 43, @BiologyID),
(@StartingNewFactCardID + 43, @FunFactsID),

-- Earth's water
(@StartingNewFactCardID + 44, @TriviaID),
(@StartingNewFactCardID + 44, @ImportantID),

-- DIY facts tags
-- Ink stains
(@StartingNewFactCardID + 45, @CleaningID),
(@StartingNewFactCardID + 45, @LifeHacksID),
(@StartingNewFactCardID + 45, @HomeImprovementID),

-- Refrigerator odors
(@StartingNewFactCardID + 46, @CleaningID),
(@StartingNewFactCardID + 46, @LifeHacksID),
(@StartingNewFactCardID + 46, @HomeImprovementID),

-- Razor blades
(@StartingNewFactCardID + 47, @LifeHacksID),
(@StartingNewFactCardID + 47, @HomeImprovementID),

-- Microfiber couch
(@StartingNewFactCardID + 48, @CleaningID),
(@StartingNewFactCardID + 48, @LifeHacksID),
(@StartingNewFactCardID + 48, @HomeImprovementID),

-- Wrinkles without iron
(@StartingNewFactCardID + 49, @LifeHacksID),
(@StartingNewFactCardID + 49, @CleaningID),
(@StartingNewFactCardID + 49, @HomeImprovementID)
GO

PRINT 'Successfully added 50 new facts to the FactDari database!'

---------------------------------------------------
--- Fifth Insert Batch
---------------------------------------------------
USE FactDari
GO

-- Get CategoryIDs
DECLARE @GeneralKnowledgeID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'General Knowledge')
DECLARE @DIYID INT = (SELECT CategoryID FROM Categories WHERE CategoryName = 'DIY')

-- Add 50 more General Knowledge facts
INSERT INTO FactCards (CategoryID, Question, Answer, NextReviewDate, CurrentInterval)
VALUES
-- General Knowledge (50 facts)
(@GeneralKnowledgeID, 'What is the lifespan of a red blood cell?', 'Red blood cells have an average lifespan of about 120 days before being replaced.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How fast does a sneeze travel?', 'A sneeze can travel up to 100 miles per hour (160 km/h).', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the world''s most venomous spider?', 'The Sydney funnel-web spider is considered the world''s most venomous spider.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many times does the average person laugh per day?', 'The average adult laughs about 15 times per day.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of giraffes called?', 'A group of giraffes is called a "tower."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How much of our brains do we use?', 'Contrary to popular myth, humans use 100% of their brains, just not all at the same time.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the largest flower in the world?', 'The Rafflesia arnoldii is the largest individual flower, growing up to 3 feet in diameter.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many eyes does a bee have?', 'Bees have five eyes – three simple eyes on top of their head and two compound eyes.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of owls called?', 'A group of owls is called a "parliament."', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of Earth''s oxygen comes from the Amazon rainforest?', 'Approximately 20% of Earth''s oxygen is produced by the Amazon rainforest.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many muscles does it take to frown?', 'It takes 43 muscles to frown, more than twice as many as the 17 muscles needed to smile.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the smallest bird in the world?', 'The bee hummingbird is the smallest bird in the world, weighing less than 2 grams.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of rhinos called?', 'A group of rhinos is called a "crash."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many hearts does a worm have?', 'Earthworms have 5 pairs of hearts, for a total of 10 heart-like structures that pump blood.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only food that never spoils?', 'Pure honey never spoils if stored properly, thanks to its low water content and natural acidity.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How long is an elephant pregnant?', 'Elephants have the longest gestation period of any mammal, carrying their young for 22 months before giving birth.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the life expectancy of an eyelash?', 'The average lifespan of an eyelash is about 5 months (150 days).', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many times does the average person blink in a minute?', 'The average person blinks about 15-20 times per minute.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of jellyfish called?', 'A group of jellyfish is called a "bloom" or a "swarm."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How long does a camel go without drinking?', 'A camel can go up to a week without drinking water, and months without food.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many cells does the human body replace daily?', 'The human body replaces about 330 billion cells every day, or about 1% of all our cells.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the oldest tree in the world?', 'A Great Basin Bristlecone Pine known as "Methuselah" is over 4,850 years old, making it the oldest known non-clonal living tree.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of kangaroos called?', 'A group of kangaroos is called a "mob."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How much does a cloud weigh?', 'An average cumulus cloud weighs about 1.1 million pounds (500,000 kg) due to the water droplets it contains.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What animal has the longest lifespan?', 'The immortal jellyfish (Turritopsis dohrnii) can potentially live forever by reverting to an earlier stage of development when stressed.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many heartbeats does the average person have in a lifetime?', 'The average person has about 2.5 billion heartbeats in a lifetime of 70-80 years.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only continent with no active volcanoes?', 'Australia is the only continent with no active volcanoes.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of ravens called?', 'A group of ravens is called an "unkindness" or a "conspiracy."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How long does a human hair grow in a month?', 'Human hair grows about 1/2 inch (1.25 cm) per month on average.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the strongest muscle in the human body relative to its size?', 'The masseter (jaw muscle) is the strongest muscle in the human body relative to its size.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of pandas called?', 'A group of pandas is called an "embarrassment."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How far can a skunk spray?', 'A skunk can spray its potent odor up to 10 feet (3 meters).', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the world''s most common birthday?', 'September 9th is the most common birthday worldwide, with September being the most popular birth month.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of our bodies is water?', 'About 60% of the adult human body is water.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of butterflies called?', 'A group of butterflies is called a "kaleidoscope."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many times faster does sound travel through water than air?', 'Sound travels about 4.3 times faster through water than through air.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the only letter not used in any U.S. state name?', 'The letter "Q" is the only letter not used in any U.S. state name.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the most abundant element in the Earth''s crust?', 'Oxygen is the most abundant element in the Earth''s crust, making up about 46% of its mass.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many known species of insects exist?', 'There are approximately 1 million known species of insects, with estimates of total insect species ranging from 5-10 million.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of eagles called?', 'A group of eagles is called a "convocation."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many languages are at risk of extinction?', 'About 3,000 of the world''s 7,000 languages are considered endangered and at risk of extinction.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of the world''s plant and animal species live in rainforests?', 'Rainforests are home to approximately 50% of the world''s plant and animal species, despite covering less than 6% of Earth''s land surface.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of hedgehogs called?', 'A group of hedgehogs is called a "prickle."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many bones does a shark have?', 'Sharks have zero bones. Their skeletons are made of cartilage, not bone.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the most common surname in the world?', 'Wang (or Wong) is the most common surname in the world, with over 100 million people bearing this name.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What percentage of the ocean has been explored?', 'Less than 5% of the world''s oceans have been explored.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is a group of zebras called?', 'A group of zebras is called a "dazzle."', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many taste buds does the average human tongue have?', 'The average human tongue has about 10,000 taste buds.', GETDATE(), 1),
(@GeneralKnowledgeID, 'What is the fastest bird in the world?', 'The peregrine falcon is the fastest bird, able to reach speeds of over 240 mph (386 km/h) during its hunting dive.', GETDATE(), 1),
(@GeneralKnowledgeID, 'How many teeth does an adult human have?', 'An adult human has 32 teeth, including wisdom teeth.', GETDATE(), 1),

-- Add 50 more DIY facts
-- DIY (50 facts)
(@DIYID, 'How can you remove super glue from skin?', 'Soak the affected area in warm, soapy water, then gently peel apart the bonded skin. For stubborn areas, apply acetone-based nail polish remover.', GETDATE(), 1),
(@DIYID, 'What''s the easiest way to clean blinds?', 'Put an old sock on your hand, dip it in a mixture of equal parts vinegar and water, then slide your hand across each slat to trap dust and remove grime.', GETDATE(), 1),
(@DIYID, 'How can you remove gum from carpet?', 'Freeze the gum with ice cubes in a plastic bag for about 10 minutes, then shatter the hardened gum with a blunt object and vacuum the pieces.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to eliminate fruit flies?', 'Fill a small bowl with apple cider vinegar, add a drop of dish soap, and cover with plastic wrap with small holes. The flies are attracted to the vinegar but can''t escape.', GETDATE(), 1),
(@DIYID, 'How can you fix scratched wood furniture?', 'Rub a walnut, pecan, or almond over the scratch. The natural oils fill in and darken the scratch, effectively hiding minor damage.', GETDATE(), 1),
(@DIYID, 'What''s the best way to prevent chopping boards from warping?', 'After washing wooden chopping boards, dry them standing on edge rather than flat to allow even air circulation, preventing uneven drying that leads to warping.', GETDATE(), 1),
(@DIYID, 'How can you keep cookies soft?', 'Store cookies with a slice of bread. The cookies will absorb moisture from the bread, keeping them soft longer.', GETDATE(), 1),
(@DIYID, 'What''s an easy way to clean a coffee grinder?', 'Grind a handful of uncooked rice in your coffee grinder. The rice absorbs coffee oils and residue, leaving the grinder clean. Wipe out with a paper towel afterward.', GETDATE(), 1),
(@DIYID, 'How can you unstick a zipper?', 'Rub a pencil lead or bar of soap along the teeth of a stuck zipper. The graphite or soap acts as a lubricant without attracting dirt like oil-based products.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to deodorize shoes?', 'Fill a clean sock with baking soda, tie it off, and place in shoes overnight. The baking soda absorbs moisture and odors without leaving residue.', GETDATE(), 1),
(@DIYID, 'How can you fix a smartphone that won''t charge?', 'Carefully clean the charging port with a toothpick or compressed air to remove lint and debris that prevent proper connection with the charging cable.', GETDATE(), 1),
(@DIYID, 'What''s the best way to remove rust from cast iron?', 'Make a paste with equal parts salt and lemon juice, apply to rusted areas, let sit for 2 hours, then scrub with steel wool. The acid in lemon juice dissolves rust.', GETDATE(), 1),
(@DIYID, 'How can you prevent paint from dripping down the brush handle?', 'Wrap a rubber band around the paint can so it stretches across the open top. Wipe excess paint on the band when pulling the brush out.', GETDATE(), 1),
(@DIYID, 'What''s a quick way to dust ceiling fans?', 'Slide an old pillowcase over each fan blade, then pull back while applying light pressure. The dust is captured inside the pillowcase instead of falling on furniture.', GETDATE(), 1),
(@DIYID, 'How can you keep cut flowers fresh longer?', 'Add a crushed aspirin tablet or a quarter cup of soda (like Sprite) to vase water. Both contain compounds that extend bloom life.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean a blender?', 'Fill the blender halfway with warm water, add a drop of dish soap, and blend for 30 seconds. Rinse thoroughly for an easy clean without disassembly.', GETDATE(), 1),
(@DIYID, 'How can you get gum out of hair?', 'Apply peanut butter, olive oil, or mayonnaise to the gum and surrounding hair. The oils break down the gum''s stickiness, allowing it to slide out.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to repel ants?', 'Sprinkle cinnamon, coffee grounds, or chalk lines at entry points. Ants won''t cross these barriers because they disrupt their scent trails.', GETDATE(), 1),
(@DIYID, 'How can you prevent glasses from fogging up?', 'Rub a small amount of shaving cream on lenses, then wipe off completely. The residual film prevents condensation that causes fogging.', GETDATE(), 1),
(@DIYID, 'What''s the easiest way to clean stainless steel appliances?', 'Apply a small amount of baby oil or mineral oil with a microfiber cloth, wiping in the direction of the grain. The oil removes fingerprints and creates a protective barrier.', GETDATE(), 1),
(@DIYID, 'How can you keep paint brushes soft between uses?', 'Wrap paint brushes in plastic wrap or aluminum foil and store in the refrigerator to prevent them from drying out during breaks in multi-day projects.', GETDATE(), 1),
(@DIYID, 'What''s a simple way to test if eggs are fresh?', 'Place eggs in a bowl of water. Fresh eggs sink and lie horizontally, slightly older eggs stand upright, and bad eggs float to the surface.', GETDATE(), 1),
(@DIYID, 'How can you remove adhesive residue from glass?', 'Apply cooking oil or peanut butter to the residue, let sit for 20 minutes, then wipe away. The oils break down the adhesive without scratching the glass.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean jewelry at home?', 'Soak jewelry in a solution of 1 tablespoon salt, 1 tablespoon baking soda, and 1 cup warm water with a sheet of aluminum foil for 10 minutes. The chemical reaction removes tarnish.', GETDATE(), 1),
(@DIYID, 'How can you prevent cutting boards from retaining food odors?', 'Rub half a lemon over the board, sprinkle with salt, and let sit for 5 minutes before rinsing. The acid neutralizes odors while the salt acts as a mild abrasive.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to clean and polish wood furniture?', 'Mix 1/4 cup olive oil with 2 tablespoons lemon juice or vinegar. Apply with a soft cloth, let sit for 5 minutes, then buff to shine.', GETDATE(), 1),
(@DIYID, 'How can you remove sweat stains from hats?', 'Create a paste of equal parts baking soda and hydrogen peroxide, apply to stains, let sit for 30 minutes, then rinse thoroughly. The combination lifts and bleaches stains.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean a garbage disposal?', 'Freeze vinegar in ice cube trays, then run the cubes through the disposal. The ice helps clean the blades while the vinegar disinfects and removes odors.', GETDATE(), 1),
(@DIYID, 'How can you efficiently defrost meat?', 'Place frozen meat in a zip-top bag, squeeze out all air, and submerge in cold water. Change water every 30 minutes for faster defrosting without cooking edges.', GETDATE(), 1),
(@DIYID, 'What''s a simple way to fix a sagging couch?', 'Cut plywood to fit under cushions and place it between the mattress and box spring. The rigid support prevents further sagging and extends the couch''s life.', GETDATE(), 1),
(@DIYID, 'How can you remove sticker residue from plastic?', 'Apply cooking oil, let sit for 20 minutes, then wipe away with a damp cloth. For stubborn residue, use a paste of baking soda and oil as a gentle abrasive.', GETDATE(), 1),
(@DIYID, 'What''s the best way to keep paint from drying out?', 'Place plastic wrap directly on the paint surface before sealing the can. This creates an airtight barrier that prevents a skin from forming.', GETDATE(), 1),
(@DIYID, 'How can you fix a scratched DVD or CD?', 'Apply a small amount of toothpaste (not gel) to the scratched area and gently buff in a straight line from center to edge with a soft cloth. The mild abrasive fills in scratches.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to clean a shower head?', 'Fill a plastic bag with white vinegar, secure it around the shower head with a rubber band, and let soak overnight. The acid dissolves mineral deposits that block water flow.', GETDATE(), 1),
(@DIYID, 'How can you clean a burnt pot bottom?', 'Cover the bottom with baking soda, add vinegar until it fizzes, then add hot water and let sit for 30 minutes. The chemical reaction loosens burnt food for easy scrubbing.', GETDATE(), 1),
(@DIYID, 'What''s the easiest way to remove wine stains?', 'Immediately pour salt liberally over the stain, let it absorb the wine, then brush away. For dried stains, use a mixture of hydrogen peroxide and dish soap.', GETDATE(), 1),
(@DIYID, 'How can you deter cats from scratching furniture?', 'Apply double-sided tape to areas cats scratch. They dislike the sticky sensation and will avoid those spots. Remove once the habit is broken.', GETDATE(), 1),
(@DIYID, 'What''s a simple way to keep herbs fresh longer?', 'Treat herbs like flowers: trim stems, place in a glass with water, cover loosely with a plastic bag, and refrigerate. Change water every 2-3 days.', GETDATE(), 1),
(@DIYID, 'How can you remove permanent marker from a whiteboard?', 'Write over the permanent marker with a dry-erase marker, then wipe away both. The solvents in the dry-erase marker break down the permanent ink.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean a dirty oven?', 'Make a paste with 1/2 cup baking soda and water, coat oven surfaces, let sit overnight, then wipe away. Spray vinegar on any remaining residue for extra cleaning power.', GETDATE(), 1),
(@DIYID, 'How can you prevent freezer burn?', 'Double-wrap foods in freezer-safe bags, squeezing out all air before sealing. For ultimate protection, dip ice cream cartons in water and refreeze to create an ice seal.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to clean grout?', 'Make a paste of 3 parts baking soda to 1 part hydrogen peroxide, apply to grout lines with an old toothbrush, let sit for 10 minutes, then scrub and rinse clean.', GETDATE(), 1),
(@DIYID, 'How can you fix a creaky floor?', 'Sprinkle baby powder between floorboards and sweep into cracks. The powder lubricates the wood and eliminates friction that causes creaking.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean a cast iron skillet?', 'While still warm, scrub with coarse salt and a paper towel. The salt acts as an abrasive without damaging the seasoning, and doesn''t introduce moisture that causes rust.', GETDATE(), 1),
(@DIYID, 'How can you naturally clean a washing machine?', 'Run an empty hot water cycle with 2 cups of vinegar to eliminate odors and mineral buildup. Follow with another empty cycle to rinse.', GETDATE(), 1),
(@DIYID, 'What''s a simple way to organize tangled cables?', 'Thread cables through toilet paper tubes labeled with their function. The tubes keep cables separate and prevent tangling in storage.', GETDATE(), 1),
(@DIYID, 'How can you remove mildew smell from towels?', 'Wash towels in hot water with 1 cup of vinegar (no detergent), then run a second cycle with 1/2 cup baking soda. The vinegar kills mildew while baking soda neutralizes odors.', GETDATE(), 1),
(@DIYID, 'What''s the best way to clean makeup brushes?', 'Mix 1 tablespoon dish soap with 2 tablespoons olive oil in a shallow dish. Swirl brushes in the mixture, rinse under warm water, then reshape and air dry bristles down.', GETDATE(), 1),
(@DIYID, 'How can you keep produce fresh longer?', 'Line refrigerator drawers with paper towels to absorb excess moisture that accelerates spoilage. Replace weekly for maximum effectiveness.', GETDATE(), 1),
(@DIYID, 'What''s a natural way to clean a microwave?', 'Mix equal parts water and vinegar in a microwave-safe bowl, heat for 5 minutes, then let sit for 5 more minutes. The steam loosens food particles for easy wiping.', GETDATE(), 1),
(@DIYID, 'How can you keep wooden spoons from cracking?', 'Once a month, rub wooden utensils with mineral oil and let sit overnight. The oil penetrates the wood, preventing drying and cracking from repeated washing.', GETDATE(), 1)
GO

-- Get the starting ID for our newly inserted fact cards
DECLARE @StartingNewFactCardID INT = (SELECT MAX(FactCardID) - 99 FROM FactCards)

-- Get Tag IDs for tagging the new fact cards
DECLARE @TriviaID INT = (SELECT TagID FROM Tags WHERE TagName = 'Trivia')
DECLARE @FunFactsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Fun Facts')
DECLARE @EntertainmentID INT = (SELECT TagID FROM Tags WHERE TagName = 'Entertainment')
DECLARE @HealthID INT = (SELECT TagID FROM Tags WHERE TagName = 'Health')
DECLARE @AnimalsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Animals')
DECLARE @BiologyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Biology')
DECLARE @PhysicsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Physics')
DECLARE @ChemistryID INT = (SELECT TagID FROM Tags WHERE TagName = 'Chemistry')
DECLARE @ElementsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Elements')
DECLARE @WeatherID INT = (SELECT TagID FROM Tags WHERE TagName = 'Weather')
DECLARE @CleaningID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cleaning')
DECLARE @HomeImprovementID INT = (SELECT TagID FROM Tags WHERE TagName = 'Home Improvement')
DECLARE @CraftsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Crafts')
DECLARE @RepairsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Repairs')
DECLARE @ToolsID INT = (SELECT TagID FROM Tags WHERE TagName = 'Tools')
DECLARE @GardeningID INT = (SELECT TagID FROM Tags WHERE TagName = 'Gardening')
DECLARE @CookingID INT = (SELECT TagID FROM Tags WHERE TagName = 'Cooking')
DECLARE @LifeHacksID INT = (SELECT TagID FROM Tags WHERE TagName = 'Life Hacks')
DECLARE @FoodID INT = (SELECT TagID FROM Tags WHERE TagName = 'Food')
DECLARE @ImportantID INT = (SELECT TagID FROM Tags WHERE TagName = 'Important')
DECLARE @UsefulID INT = (SELECT TagID FROM Tags WHERE TagName = 'Useful')
DECLARE @EasyID INT = (SELECT TagID FROM Tags WHERE TagName = 'Easy')

-- Add tags for the new General Knowledge fact cards
INSERT INTO FactCardTags (FactCardID, TagID)
VALUES
-- General Knowledge tags
-- Red blood cell lifespan
(@StartingNewFactCardID, @BiologyID),
(@StartingNewFactCardID, @HealthID),
(@StartingNewFactCardID, @TriviaID),

-- Sneeze speed
(@StartingNewFactCardID + 1, @BiologyID),
(@StartingNewFactCardID + 1, @FunFactsID),
(@StartingNewFactCardID + 1, @TriviaID),

-- Venomous spider
(@StartingNewFactCardID + 2, @AnimalsID),
(@StartingNewFactCardID + 2, @TriviaID),

-- Laughing
(@StartingNewFactCardID + 3, @BiologyID),
(@StartingNewFactCardID + 3, @HealthID),
(@StartingNewFactCardID + 3, @FunFactsID),

-- Giraffes tower
(@StartingNewFactCardID + 4, @AnimalsID),
(@StartingNewFactCardID + 4, @TriviaID),
(@StartingNewFactCardID + 4, @FunFactsID),

-- Brain usage
(@StartingNewFactCardID + 5, @BiologyID),
(@StartingNewFactCardID + 5, @HealthID),
(@StartingNewFactCardID + 5, @ImportantID),

-- Largest flower
(@StartingNewFactCardID + 6, @TriviaID),
(@StartingNewFactCardID + 6, @FunFactsID),

-- Bee eyes
(@StartingNewFactCardID + 7, @AnimalsID),
(@StartingNewFactCardID + 7, @BiologyID),
(@StartingNewFactCardID + 7, @TriviaID),

-- Parliament of owls
(@StartingNewFactCardID + 8, @AnimalsID),
(@StartingNewFactCardID + 8, @TriviaID),
(@StartingNewFactCardID + 8, @FunFactsID),

-- Amazon oxygen
(@StartingNewFactCardID + 9, @TriviaID),
(@StartingNewFactCardID + 9, @ImportantID),

-- Frowning muscles
(@StartingNewFactCardID + 10, @BiologyID),
(@StartingNewFactCardID + 10, @TriviaID),
(@StartingNewFactCardID + 10, @FunFactsID),

-- Smallest bird
(@StartingNewFactCardID + 11, @AnimalsID),
(@StartingNewFactCardID + 11, @TriviaID),
(@StartingNewFactCardID + 11, @FunFactsID),

-- Crash of rhinos
(@StartingNewFactCardID + 12, @AnimalsID),
(@StartingNewFactCardID + 12, @TriviaID),
(@StartingNewFactCardID + 12, @FunFactsID),

-- Worm hearts
(@StartingNewFactCardID + 13, @AnimalsID),
(@StartingNewFactCardID + 13, @BiologyID),
(@StartingNewFactCardID + 13, @TriviaID),

-- Honey
(@StartingNewFactCardID + 14, @FoodID),
(@StartingNewFactCardID + 14, @TriviaID),
(@StartingNewFactCardID + 14, @FunFactsID),

-- Elephant pregnancy
(@StartingNewFactCardID + 15, @AnimalsID),
(@StartingNewFactCardID + 15, @BiologyID),
(@StartingNewFactCardID + 15, @TriviaID),

-- Eyelash lifespan
(@StartingNewFactCardID + 16, @BiologyID),
(@StartingNewFactCardID + 16, @TriviaID),
(@StartingNewFactCardID + 16, @HealthID),

-- Blinking
(@StartingNewFactCardID + 17, @BiologyID),
(@StartingNewFactCardID + 17, @HealthID),
(@StartingNewFactCardID + 17, @TriviaID),

-- Bloom of jellyfish
(@StartingNewFactCardID + 18, @AnimalsID),
(@StartingNewFactCardID + 18, @TriviaID),
(@StartingNewFactCardID + 18, @FunFactsID),

-- Camel water
(@StartingNewFactCardID + 19, @AnimalsID),
(@StartingNewFactCardID + 19, @BiologyID),
(@StartingNewFactCardID + 19, @TriviaID),

-- Cell replacement
(@StartingNewFactCardID + 20, @BiologyID),
(@StartingNewFactCardID + 20, @HealthID),
(@StartingNewFactCardID + 20, @TriviaID),

-- Oldest tree
(@StartingNewFactCardID + 21, @TriviaID),
(@StartingNewFactCardID + 21, @FunFactsID),

-- Mob of kangaroos
(@StartingNewFactCardID + 22, @AnimalsID),
(@StartingNewFactCardID + 22, @TriviaID),
(@StartingNewFactCardID + 22, @FunFactsID),

-- Cloud weight
(@StartingNewFactCardID + 23, @WeatherID),
(@StartingNewFactCardID + 23, @PhysicsID),
(@StartingNewFactCardID + 23, @TriviaID),

-- Immortal jellyfish
(@StartingNewFactCardID + 24, @AnimalsID),
(@StartingNewFactCardID + 24, @BiologyID),
(@StartingNewFactCardID + 24, @TriviaID),

-- Heartbeats
(@StartingNewFactCardID + 25, @BiologyID),
(@StartingNewFactCardID + 25, @HealthID),
(@StartingNewFactCardID + 25, @TriviaID),

-- Australia volcanoes
(@StartingNewFactCardID + 26, @TriviaID),
(@StartingNewFactCardID + 26, @FunFactsID),

-- Unkindness of ravens
(@StartingNewFactCardID + 27, @AnimalsID),
(@StartingNewFactCardID + 27, @TriviaID),
(@StartingNewFactCardID + 27, @FunFactsID),

-- Human hair growth
(@StartingNewFactCardID + 28, @BiologyID),
(@StartingNewFactCardID + 28, @HealthID),
(@StartingNewFactCardID + 28, @TriviaID),

-- Jaw muscle
(@StartingNewFactCardID + 29, @BiologyID),
(@StartingNewFactCardID + 29, @HealthID),
(@StartingNewFactCardID + 29, @TriviaID),

-- Embarrassment of pandas
(@StartingNewFactCardID + 30, @AnimalsID),
(@StartingNewFactCardID + 30, @TriviaID),
(@StartingNewFactCardID + 30, @FunFactsID),

-- Skunk spray
(@StartingNewFactCardID + 31, @AnimalsID),
(@StartingNewFactCardID + 31, @BiologyID),
(@StartingNewFactCardID + 31, @TriviaID),

-- Birthday
(@StartingNewFactCardID + 32, @TriviaID),
(@StartingNewFactCardID + 32, @FunFactsID),

-- Body water
(@StartingNewFactCardID + 33, @BiologyID),
(@StartingNewFactCardID + 33, @HealthID),
(@StartingNewFactCardID + 33, @TriviaID),

-- Kaleidoscope of butterflies
(@StartingNewFactCardID + 34, @AnimalsID),
(@StartingNewFactCardID + 34, @TriviaID),
(@StartingNewFactCardID + 34, @FunFactsID),

-- Sound in water
(@StartingNewFactCardID + 35, @PhysicsID),
(@StartingNewFactCardID + 35, @TriviaID),

-- US state names
(@StartingNewFactCardID + 36, @TriviaID),
(@StartingNewFactCardID + 36, @FunFactsID),
(@StartingNewFactCardID + 36, @EntertainmentID),

-- Earth's crust
(@StartingNewFactCardID + 37, @ChemistryID),
(@StartingNewFactCardID + 37, @ElementsID),
(@StartingNewFactCardID + 37, @TriviaID),

-- Insect species
(@StartingNewFactCardID + 38, @AnimalsID),
(@StartingNewFactCardID + 38, @BiologyID),
(@StartingNewFactCardID + 38, @TriviaID),

-- Convocation of eagles
(@StartingNewFactCardID + 39, @AnimalsID),
(@StartingNewFactCardID + 39, @TriviaID),
(@StartingNewFactCardID + 39, @FunFactsID),

-- Endangered languages
(@StartingNewFactCardID + 40, @TriviaID),
(@StartingNewFactCardID + 40, @ImportantID),

-- Rainforest species
(@StartingNewFactCardID + 41, @AnimalsID),
(@StartingNewFactCardID + 41, @BiologyID),
(@StartingNewFactCardID + 41, @ImportantID),

-- Prickle of hedgehogs
(@StartingNewFactCardID + 42, @AnimalsID),
(@StartingNewFactCardID + 42, @TriviaID),
(@StartingNewFactCardID + 42, @FunFactsID),

-- Shark bones
(@StartingNewFactCardID + 43, @AnimalsID),
(@StartingNewFactCardID + 43, @BiologyID),
(@StartingNewFactCardID + 43, @TriviaID),

-- Common surname
(@StartingNewFactCardID + 44, @TriviaID),
(@StartingNewFactCardID + 44, @FunFactsID),

-- Ocean exploration
(@StartingNewFactCardID + 45, @TriviaID),
(@StartingNewFactCardID + 45, @ImportantID),

-- Dazzle of zebras
(@StartingNewFactCardID + 46, @AnimalsID),
(@StartingNewFactCardID + 46, @TriviaID),
(@StartingNewFactCardID + 46, @FunFactsID),

-- Taste buds
(@StartingNewFactCardID + 47, @BiologyID),
(@StartingNewFactCardID + 47, @HealthID),
(@StartingNewFactCardID + 47, @TriviaID),

-- Fastest bird
(@StartingNewFactCardID + 48, @AnimalsID),
(@StartingNewFactCardID + 48, @TriviaID),
(@StartingNewFactCardID + 48, @FunFactsID),

-- Human teeth
(@StartingNewFactCardID + 49, @BiologyID),
(@StartingNewFactCardID + 49, @HealthID),
(@StartingNewFactCardID + 49, @TriviaID),

-- Add tags for the new DIY fact cards
-- Super glue removal
(@StartingNewFactCardID + 50, @LifeHacksID),
(@StartingNewFactCardID + 50, @HealthID),
(@StartingNewFactCardID + 50, @UsefulID),

-- Cleaning blinds
(@StartingNewFactCardID + 51, @CleaningID),
(@StartingNewFactCardID + 51, @HomeImprovementID),
(@StartingNewFactCardID + 51, @LifeHacksID),

-- Gum from carpet
(@StartingNewFactCardID + 52, @CleaningID),
(@StartingNewFactCardID + 52, @HomeImprovementID),
(@StartingNewFactCardID + 52, @LifeHacksID),

-- Fruit flies
(@StartingNewFactCardID + 53, @CleaningID),
(@StartingNewFactCardID + 53, @HomeImprovementID),
(@StartingNewFactCardID + 53, @LifeHacksID),

-- Scratched wood
(@StartingNewFactCardID + 54, @RepairsID),
(@StartingNewFactCardID + 54, @HomeImprovementID),
(@StartingNewFactCardID + 54, @LifeHacksID),

-- Chopping boards warping
(@StartingNewFactCardID + 55, @CookingID),
(@StartingNewFactCardID + 55, @HomeImprovementID),
(@StartingNewFactCardID + 55, @LifeHacksID),

-- Soft cookies
(@StartingNewFactCardID + 56, @FoodID),
(@StartingNewFactCardID + 56, @CookingID),
(@StartingNewFactCardID + 56, @LifeHacksID),

-- Coffee grinder cleaning
(@StartingNewFactCardID + 57, @CleaningID),
(@StartingNewFactCardID + 57, @CookingID),
(@StartingNewFactCardID + 57, @LifeHacksID),

-- Unstick zipper
(@StartingNewFactCardID + 58, @RepairsID),
(@StartingNewFactCardID + 58, @LifeHacksID),
(@StartingNewFactCardID + 58, @EasyID),

-- Shoe odor
(@StartingNewFactCardID + 59, @CleaningID),
(@StartingNewFactCardID + 59, @LifeHacksID),
(@StartingNewFactCardID + 59, @EasyID),

-- Smartphone charging
(@StartingNewFactCardID + 60, @RepairsID),
(@StartingNewFactCardID + 60, @LifeHacksID),
(@StartingNewFactCardID + 60, @UsefulID),

-- Cast iron rust
(@StartingNewFactCardID + 61, @CleaningID),
(@StartingNewFactCardID + 61, @CookingID),
(@StartingNewFactCardID + 61, @LifeHacksID),

-- Paint dripping
(@StartingNewFactCardID + 62, @HomeImprovementID),
(@StartingNewFactCardID + 62, @CraftsID),
(@StartingNewFactCardID + 62, @LifeHacksID),

-- Ceiling fans dusting
(@StartingNewFactCardID + 63, @CleaningID),
(@StartingNewFactCardID + 63, @HomeImprovementID),
(@StartingNewFactCardID + 63, @LifeHacksID),

-- Fresh flowers
(@StartingNewFactCardID + 64, @LifeHacksID),
(@StartingNewFactCardID + 64, @GardeningID),
(@StartingNewFactCardID + 64, @UsefulID),

-- Blender cleaning
(@StartingNewFactCardID + 65, @CleaningID),
(@StartingNewFactCardID + 65, @CookingID),
(@StartingNewFactCardID + 65, @LifeHacksID),

-- Gum in hair
(@StartingNewFactCardID + 66, @LifeHacksID),
(@StartingNewFactCardID + 66, @UsefulID),
(@StartingNewFactCardID + 66, @EasyID),

-- Repel ants
(@StartingNewFactCardID + 67, @HomeImprovementID),
(@StartingNewFactCardID + 67, @LifeHacksID),
(@StartingNewFactCardID + 67, @EasyID),

-- Glasses fogging
(@StartingNewFactCardID + 68, @LifeHacksID),
(@StartingNewFactCardID + 68, @UsefulID),
(@StartingNewFactCardID + 68, @EasyID),

-- Stainless steel cleaning
(@StartingNewFactCardID + 69, @CleaningID),
(@StartingNewFactCardID + 69, @HomeImprovementID),
(@StartingNewFactCardID + 69, @LifeHacksID),

-- Paint brushes
(@StartingNewFactCardID + 70, @HomeImprovementID),
(@StartingNewFactCardID + 70, @CraftsID),
(@StartingNewFactCardID + 70, @LifeHacksID),

-- Testing eggs
(@StartingNewFactCardID + 71, @FoodID),
(@StartingNewFactCardID + 71, @CookingID),
(@StartingNewFactCardID + 71, @LifeHacksID),

-- Adhesive residue
(@StartingNewFactCardID + 72, @CleaningID),
(@StartingNewFactCardID + 72, @HomeImprovementID),
(@StartingNewFactCardID + 72, @LifeHacksID),

-- Jewelry cleaning
(@StartingNewFactCardID + 73, @CleaningID),
(@StartingNewFactCardID + 73, @LifeHacksID),
(@StartingNewFactCardID + 73, @UsefulID),

-- Cutting board odors
(@StartingNewFactCardID + 74, @CleaningID),
(@StartingNewFactCardID + 74, @CookingID),
(@StartingNewFactCardID + 74, @LifeHacksID),

-- Wood furniture polish
(@StartingNewFactCardID + 75, @CleaningID),
(@StartingNewFactCardID + 75, @HomeImprovementID),
(@StartingNewFactCardID + 75, @LifeHacksID),

-- Sweat stains
(@StartingNewFactCardID + 76, @CleaningID),
(@StartingNewFactCardID + 76, @LifeHacksID),
(@StartingNewFactCardID + 76, @UsefulID),

-- Garbage disposal
(@StartingNewFactCardID + 77, @CleaningID),
(@StartingNewFactCardID + 77, @HomeImprovementID),
(@StartingNewFactCardID + 77, @LifeHacksID),

-- Defrost meat
(@StartingNewFactCardID + 78, @FoodID),
(@StartingNewFactCardID + 78, @CookingID),
(@StartingNewFactCardID + 78, @LifeHacksID),

-- Sagging couch
(@StartingNewFactCardID + 79, @RepairsID),
(@StartingNewFactCardID + 79, @HomeImprovementID),
(@StartingNewFactCardID + 79, @LifeHacksID),

-- Sticker residue
(@StartingNewFactCardID + 80, @CleaningID),
(@StartingNewFactCardID + 80, @LifeHacksID),
(@StartingNewFactCardID + 80, @UsefulID),

-- Keep paint fresh
(@StartingNewFactCardID + 81, @HomeImprovementID),
(@StartingNewFactCardID + 81, @CraftsID),
(@StartingNewFactCardID + 81, @LifeHacksID),

-- Scratched DVD
(@StartingNewFactCardID + 82, @RepairsID),
(@StartingNewFactCardID + 82, @LifeHacksID),
(@StartingNewFactCardID + 82, @UsefulID),

-- Clean shower head
(@StartingNewFactCardID + 83, @CleaningID),
(@StartingNewFactCardID + 83, @HomeImprovementID),
(@StartingNewFactCardID + 83, @LifeHacksID),

-- Burnt pot
(@StartingNewFactCardID + 84, @CleaningID),
(@StartingNewFactCardID + 84, @CookingID),
(@StartingNewFactCardID + 84, @LifeHacksID),

-- Wine stains
(@StartingNewFactCardID + 85, @CleaningID),
(@StartingNewFactCardID + 85, @LifeHacksID),
(@StartingNewFactCardID + 85, @UsefulID),

-- Cat scratching
(@StartingNewFactCardID + 86, @HomeImprovementID),
(@StartingNewFactCardID + 86, @LifeHacksID),
(@StartingNewFactCardID + 86, @UsefulID),

-- Fresh herbs
(@StartingNewFactCardID + 87, @FoodID),
(@StartingNewFactCardID + 87, @CookingID),
(@StartingNewFactCardID + 87, @LifeHacksID),

-- Permanent marker
(@StartingNewFactCardID + 88, @CleaningID),
(@StartingNewFactCardID + 88, @HomeImprovementID),
(@StartingNewFactCardID + 88, @LifeHacksID),

-- Dirty oven
(@StartingNewFactCardID + 89, @CleaningID),
(@StartingNewFactCardID + 89, @HomeImprovementID),
(@StartingNewFactCardID + 89, @LifeHacksID),

-- Freezer burn
(@StartingNewFactCardID + 90, @FoodID),
(@StartingNewFactCardID + 90, @CookingID),
(@StartingNewFactCardID + 90, @LifeHacksID),

-- Clean grout
(@StartingNewFactCardID + 91, @CleaningID),
(@StartingNewFactCardID + 91, @HomeImprovementID),
(@StartingNewFactCardID + 91, @LifeHacksID),

-- Creaky floor
(@StartingNewFactCardID + 92, @RepairsID),
(@StartingNewFactCardID + 92, @HomeImprovementID),
(@StartingNewFactCardID + 92, @LifeHacksID),

-- Cast iron skillet
(@StartingNewFactCardID + 93, @CleaningID),
(@StartingNewFactCardID + 93, @CookingID),
(@StartingNewFactCardID + 93, @LifeHacksID),

-- Washing machine
(@StartingNewFactCardID + 94, @CleaningID),
(@StartingNewFactCardID + 94, @HomeImprovementID),
(@StartingNewFactCardID + 94, @LifeHacksID),

-- Tangled cables
(@StartingNewFactCardID + 95, @HomeImprovementID),
(@StartingNewFactCardID + 95, @LifeHacksID),
(@StartingNewFactCardID + 95, @UsefulID),

-- Mildew towels
(@StartingNewFactCardID + 96, @CleaningID),
(@StartingNewFactCardID + 96, @LifeHacksID),
(@StartingNewFactCardID + 96, @UsefulID),

-- Makeup brushes
(@StartingNewFactCardID + 97, @CleaningID),
(@StartingNewFactCardID + 97, @HealthID),
(@StartingNewFactCardID + 97, @LifeHacksID),

-- Fresh produce
(@StartingNewFactCardID + 98, @FoodID),
(@StartingNewFactCardID + 98, @CookingID),
(@StartingNewFactCardID + 98, @LifeHacksID),

-- Microwave cleaning
(@StartingNewFactCardID + 99, @CleaningID),
(@StartingNewFactCardID + 99, @HomeImprovementID),
(@StartingNewFactCardID + 99, @LifeHacksID)
GO

PRINT 'Successfully added 50 General Knowledge facts and 50 DIY facts to the FactDari database!'