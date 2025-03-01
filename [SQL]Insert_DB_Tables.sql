USE FactsGenerator
GO

-- Insert categories into the Categories table
INSERT INTO Categories (CategoryName, Description)
VALUES 
    ('API', 'Facts related to APIs, their usage, and development.'),
    ('History', 'Historical events, dates, and significant figures.'),
    ('Science', 'Scientific facts, discoveries, and theories.'),
    ('Technology', 'Technological advancements, gadgets, and innovations.'),
    ('Nature', 'Facts about plants, animals, and natural phenomena.');

-- Verify that the records have been inserted
SELECT * FROM Categories;
GO

USE FactsGenerator
GO

-- Insert 100 one-word tags into the Tags table
INSERT INTO Tags (TagName)
VALUES
    ('Python'), ('History'), ('Science'), ('Biology'), ('Chemistry'),
    ('Physics'), ('Computers'), ('Java'), ('Internet'), ('API'),
    ('Algorithms'), ('Astronomy'), ('Space'), ('Evolution'), ('Climate'),
    ('Robots'), ('Innovation'), ('Medicine'), ('Energy'), ('Data'),
    ('Quantum'), ('Engineering'), ('Mathematics'), ('Statistics'), ('Blockchain'),
    ('Encryption'), ('Security'), ('Privacy'), ('Networks'), ('Software'),
    ('Hardware'), ('Databases'), ('Ethics'), ('Environment'),
    ('Ecosystems'), ('AI'), ('MachineLearning'), ('Neural'), ('DeepLearning'),
    ('Automation'), ('Cybersecurity'), ('Cloud'), ('Computing'), ('Servers'),
    ('Protocols'), ('SpaceX'), ('Tesla'), ('Communication'), ('Satellites'),
    ('Planets'), ('Stars'), ('Galaxies'), ('Gravity'), ('BlackHoles'),
    ('Time'), ('Speed'), ('Genetics'), ('Cells'), ('DNA'),
    ('Genes'), ('Ecology'), ('Marine'), ('Reptiles'), ('Birds'),
    ('Mammals'), ('Forests'), ('Agriculture'), ('Oceans'), ('Water'),
    ('Weather'), ('Hurricanes'), ('Earthquakes'), ('Volcanoes'), ('Mountains'),
    ('Rivers'), ('Lakes'), ('Deserts'), ('Tundra'), ('ClimateChange'),
    ('Renewable'), ('Solar'), ('Wind'), ('Nuclear'), ('Fossil'),
    ('Oil'), ('Gas'), ('Coal'), ('Carbon'), ('Emissions'),
    ('Sustainability'), ('Recycling'), ('Plastics'), ('Pollution'), ('Biodiversity'),
    ('Extinction'), ('Conservation');

-- Verify the inserted records
SELECT * FROM Tags;
GO


USE FactsGenerator
GO

-- Insert 5 facts for the 'History' category (CategoryID = 2)
INSERT INTO Facts (CategoryID, FactText, IsVerified)
VALUES
    (2, 'The Roman Empire was one of the largest empires in ancient history, lasting from 27 BC to 476 AD.', 1),
    (2, 'The Great Wall of China is over 13,000 miles long and was built over centuries.', 1),
    (2, 'The first successful flight by the Wright brothers was in 1903 in Kitty Hawk, North Carolina.', 1),
    (2, 'World War II lasted from 1939 to 1945 and involved most of the world’s major powers.', 1),
    (2, 'The Magna Carta, signed in 1215, is one of the most important documents in the development of democracy.', 1);

-- Insert 5 facts for the 'Science' category (CategoryID = 3)
INSERT INTO Facts (CategoryID, FactText, IsVerified)
VALUES
    (3, 'Water is the only substance that naturally exists in three states: solid, liquid, and gas.', 1),
    (3, 'The speed of light in a vacuum is approximately 299,792 kilometers per second.', 1),
    (3, 'DNA, or deoxyribonucleic acid, carries genetic information in living organisms.', 1),
    (3, 'The theory of evolution by natural selection was first formulated by Charles Darwin.', 1),
    (3, 'Photosynthesis is the process by which plants convert light energy into chemical energy.', 1);

-- Insert 5 facts for the 'Technology' category (CategoryID = 4)
INSERT INTO Facts (CategoryID, FactText, IsVerified)
VALUES
    (4, 'The first computer, ENIAC, was built in 1945 and weighed over 27 tons.', 1),
    (4, 'The internet was originally developed by the U.S. Department of Defense as a project called ARPANET.', 1),
    (4, 'Moore’s Law predicts that the number of transistors on a microchip doubles about every two years.', 1),
    (4, 'The first mobile phone call was made by Martin Cooper in 1973.', 1),
    (4, 'Artificial Intelligence (AI) is the simulation of human intelligence in machines.', 1);

-- Insert 5 facts for the 'Nature' category (CategoryID = 5)
INSERT INTO Facts (CategoryID, FactText, IsVerified)
VALUES
    (5, 'The Amazon rainforest produces 20% of the world’s oxygen supply.', 1),
    (5, 'Mount Everest is the tallest mountain on Earth, standing at 29,032 feet above sea level.', 1),
    (5, 'Oceans cover more than 70% of the Earth’s surface.', 1),
    (5, 'The Great Barrier Reef is the largest coral reef system in the world.', 1),
    (5, 'Polar bears have black skin under their white fur to absorb heat from the sun.', 1);

-- Verify the inserted records
SELECT * FROM Facts;
GO
