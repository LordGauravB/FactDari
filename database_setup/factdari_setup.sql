-- FactDari Database Setup (no Tags; richer categories)
-- Simplified fact viewing system without spaced repetition

-- Step 1: Create the FactDari database if it doesn't exist
IF DB_ID('FactDari') IS NULL
    CREATE DATABASE FactDari;
GO

-- Step 2: Use FactDari
USE FactDari;
GO

-- Step 3: Drop tables if they exist (order matters due to FKs)
IF OBJECT_ID('ReviewLogs', 'U') IS NOT NULL DROP TABLE ReviewLogs;
IF OBJECT_ID('Facts', 'U') IS NOT NULL DROP TABLE Facts;
IF OBJECT_ID('Categories', 'U') IS NOT NULL DROP TABLE Categories;
GO

-- Step 4: Create Categories table
CREATE TABLE Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(255),
    IsActive BIT NOT NULL CONSTRAINT DF_Categories_IsActive DEFAULT 1,
    CreatedDate DATETIME NOT NULL CONSTRAINT DF_Categories_CreatedDate DEFAULT GETDATE()
);

-- Step 5: Create Facts table (no tag linkage)
CREATE TABLE Facts (
    FactID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryID INT NOT NULL
        CONSTRAINT FK_Facts_Categories
        REFERENCES Categories(CategoryID),
    Content NVARCHAR(MAX) NOT NULL,
    DateAdded DATE NOT NULL CONSTRAINT DF_Facts_DateAdded DEFAULT GETDATE(),
    LastViewedDate DATETIME NULL,
    ReviewCount INT NOT NULL CONSTRAINT DF_Facts_ReviewCount DEFAULT 0,
    TotalViews INT NOT NULL CONSTRAINT DF_Facts_TotalViews DEFAULT 0,
    IsFavorite BIT NOT NULL CONSTRAINT DF_Facts_IsFavorite DEFAULT 0,
    -- Mark facts you already know (easy)
    IsEasy BIT NOT NULL CONSTRAINT DF_Facts_IsEasy DEFAULT 0
);

-- Step 6: Create simplified ReviewLogs table
CREATE TABLE ReviewLogs (
    ReviewLogID INT IDENTITY(1,1) PRIMARY KEY,
    FactID INT NOT NULL,
    ReviewDate DATETIME NOT NULL,
    SessionDuration INT, -- seconds
    CONSTRAINT FK_ReviewLogs_Facts FOREIGN KEY (FactID)
        REFERENCES Facts(FactID) ON DELETE CASCADE
);

-- Helpful indexes for app queries
CREATE INDEX IX_Facts_CategoryID ON Facts(CategoryID);
CREATE INDEX IX_Facts_LastViewedDate ON Facts(LastViewedDate);
CREATE INDEX IX_ReviewLogs_FactID ON ReviewLogs(FactID);
CREATE INDEX IX_ReviewLogs_ReviewDate ON ReviewLogs(ReviewDate);
GO

/* Add a normalized, persisted computed column for duplicate prevention */
IF COL_LENGTH('dbo.Facts', 'ContentKey') IS NULL
BEGIN
  ALTER TABLE dbo.Facts
  ADD ContentKey AS CAST(
    LOWER(
      LTRIM(RTRIM(
        REPLACE(REPLACE(REPLACE(Content, CHAR(13), ' '), CHAR(10), ' '), CHAR(9), ' ')
      ))
    ) AS NVARCHAR(450)
  ) PERSISTED;
END

/* Create the unique index on the normalized key */
IF NOT EXISTS (
  SELECT 1
  FROM sys.indexes
  WHERE object_id = OBJECT_ID('dbo.Facts')
    AND name = 'UX_Facts_ContentKey'
)
BEGIN
  CREATE UNIQUE INDEX UX_Facts_ContentKey
  ON dbo.Facts(ContentKey);
END
GO

-- Step 7: Insert expanded categories
INSERT INTO Categories (CategoryName, Description)
VALUES
('General Knowledge', 'Broad facts and trivia across domains'),
('Science', 'Physics, chemistry, biology, materials, etc.'),
('History', 'Historical events, origins, and firsts'),
('Technology', 'Computing, engineering, and inventions'),
('Nature', 'General natural world topics'),
('Space & Astronomy', 'Planets, stars, spaceflight, cosmology'),
('Geography', 'Places, regions, physical geography, oceans'),
('Arts & Culture', 'Music, art, culture, media'),
('Mathematics', 'Numbers, patterns, calendars'),
('Health & Medicine', 'Anatomy, physiology, health facts'),
('Language & Linguistics', 'Words, etymology, writing systems'),
('Animals', 'Zoology and animal behavior'),
('Plants', 'Botany, plant biology, foods from plants'),
('Food & Drink', 'Culinary facts, ingredients, beverages'),
('Earth Science', 'Geology, weather, climate, plate tectonics');
GO

-- Step 8: Cache category IDs for readable inserts
DECLARE
  @Cat_General INT = (SELECT CategoryID FROM Categories WHERE CategoryName='General Knowledge'),
  @Cat_Science INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Science'),
  @Cat_History INT = (SELECT CategoryID FROM Categories WHERE CategoryName='History'),
  @Cat_Tech INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Technology'),
  @Cat_Nature INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Nature'),
  @Cat_Space INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Space & Astronomy'),
  @Cat_Geography INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Geography'),
  @Cat_ArtsCulture INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Arts & Culture'),
  @Cat_Math INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Mathematics'),
  @Cat_Health INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Health & Medicine'),
  @Cat_Language INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Language & Linguistics'),
  @Cat_Animals INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Animals'),
  @Cat_Plants INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Plants'),
  @Cat_FoodDrink INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Food & Drink'),
  @Cat_EarthScience INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Earth Science');

-- Step 9: Insert the original 5 sample facts (recategorized)
INSERT INTO Facts (CategoryID, Content, DateAdded, LastViewedDate, ReviewCount, TotalViews)
VALUES
(@Cat_Health, 'The human brain uses about 20% of the body''s total energy despite being only 2% of body weight.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'Water expands by about 9% when it freezes, which is why ice floats on water.', GETDATE(), NULL, 0, 0),
(@Cat_General, 'The Great Wall of China is not visible from space without aid, contrary to popular belief.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'The first computer bug was an actual moth found in a Harvard Mark II computer in 1947.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Octopuses have three hearts and blue blood.', GETDATE(), NULL, 0, 0);

-- Step 10: Insert the 100 additional interesting facts
INSERT INTO Facts (CategoryID, Content, DateAdded, LastViewedDate, ReviewCount, TotalViews)
VALUES
(@Cat_Space, 'A day on Venus is longer than its year because Venus rotates very slowly in the opposite direction.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Bananas are berries in botanical terms, while strawberries are not.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, 'Honey found in ancient tombs can still be edible because it is naturally low in water and acidic.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'The Eiffel Tower gets slightly taller in summer due to thermal expansion of its metal.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Wombats produce cube-shaped droppings that help keep them from rolling away.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'The Moon is slowly drifting away from Earth by a few centimeters each year.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Butterflies can taste using sensors on their feet.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'The International Space Station orbits Earth about sixteen times each day.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Saturn is less dense than water, so a hypothetical planet-sized bathtub could make it float.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'Rainbows are actually full circles; from the ground we usually see only an arc.', GETDATE(), NULL, 0, 0),
(@Cat_Language, 'The word "robot" comes from the Czech "robota," meaning forced labor.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Peanuts are legumes, not true nuts.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'Copper surfaces naturally kill many microbes through a process called contact killing.', GETDATE(), NULL, 0, 0),
(@Cat_General, 'The only letter not found in the name of any U.S. state is Q.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'In seahorses, the males carry the pregnancy and give birth.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Mars has two small moons named Phobos and Deimos.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, 'The Great Barrier Reef is the largest living structure on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Tardigrades, or water bears, can survive extreme conditions by entering a tun state.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Hummingbirds can hover and even fly backward.', GETDATE(), NULL, 0, 0),
(@Cat_Math, 'Sunflower seed patterns often follow Fibonacci spirals.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Polar bears have black skin beneath their white fur.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'A Martian day, called a sol, is about 24 hours and 39 minutes long.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Jupiter''s Great Red Spot is a giant storm larger than Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'Sound cannot travel through the vacuum of space because there is no medium.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Pineapples are multiple fruits formed when many flowers fuse together.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Some freshwater turtles can absorb oxygen through their cloaca when underwater.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'Lightning can strike the same place more than once.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, 'The Dead Sea is so salty that people float easily on its surface.', GETDATE(), NULL, 0, 0),
(@Cat_Health, 'The smallest bone in the human body is the stapes in the middle ear.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Cheetahs cannot roar like lions and tigers; they purr instead.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'A comet''s tail always points away from the Sun due to solar wind and radiation pressure.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, 'Antarctica is the largest desert on Earth by area.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Bats are the only mammals capable of sustained flight.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Frogs absorb water through their skin rather than drinking with their mouths.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'By weight, spider silk can be stronger than steel.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Tigers have striped skin as well as striped fur.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Orcas, or killer whales, are the largest members of the dolphin family.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Sunlight takes about eight minutes to reach Earth.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'Earth''s rotation is gradually slowing down, making days slightly longer over long timescales.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Crows can recognize human faces and remember how people treat them.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Dolphins use unique signature whistles that function like names.', GETDATE(), NULL, 0, 0),
(@Cat_History, 'Potatoes were first domesticated in the Andes of South America.', GETDATE(), NULL, 0, 0),
(@Cat_History, 'Carrots were commonly purple before orange varieties became popular in Europe.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Coast redwoods are among the tallest trees on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'The Sahara Desert was once greener, with lakes and grasslands in the distant past.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Olympus Mons on Mars is the tallest known volcano in the solar system.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Venus has thick clouds of sulfuric acid and a runaway greenhouse effect.', GETDATE(), NULL, 0, 0),
(@Cat_Health, 'An adult human skeleton typically has 206 bones.', GETDATE(), NULL, 0, 0),
(@Cat_Health, 'Cracking your knuckles has not been shown to cause arthritis.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'Dust from the Sahara helps fertilize the Amazon rainforest across the Atlantic.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, 'Coffee beans are the seeds of a fruit commonly called a coffee cherry.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, 'Cinnamon is made from the inner bark of trees in the genus Cinnamomum.', GETDATE(), NULL, 0, 0),
(@Cat_Language, 'The word "alphabet" comes from the first two Greek letters: alpha and beta.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'The first retail product scanned with a barcode in 1974 was a pack of chewing gum.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'The first 3D printer was developed in the 1980s using a process called stereolithography.', GETDATE(), NULL, 0, 0),
(@Cat_Language, 'The word "emoji" comes from Japanese and is unrelated to the English word "emotion."', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'LEGO bricks made in 1958 still interlock with modern bricks because the design has stayed consistent.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'Velcro was inspired by burrs that stuck to clothing and a dog''s fur, observed by Georges de Mestral.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'Bubble wrap was originally invented as a textured wallpaper before becoming packing material.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'Percy Spencer discovered microwave heating when a candy bar melted near a magnetron, leading to the microwave oven.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Honeybees communicate the location of flowers using a waggle dance.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Leafcutter ants cultivate fungi as their primary food source.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Fireflies produce light through a chemical reaction called bioluminescence.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'The platypus is one of the few mammals that lays eggs.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, 'The Amazon River carries more water than any other river in the world.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'The Andean condor has one of the largest wingspans of any land bird.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, 'The Andes is the longest continental mountain range on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'The Himalayas are still rising due to the collision of tectonic plates.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'Hawaii moves northwest a few centimeters each year because it sits on a moving tectonic plate.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'A "Blue Moon" commonly refers to the second full moon in a single calendar month.', GETDATE(), NULL, 0, 0),
(@Cat_Language, 'The dot above the letters i and j is called a tittle.', GETDATE(), NULL, 0, 0),
(@Cat_Language, 'The # symbol is also called an octothorpe.', GETDATE(), NULL, 0, 0),
(@Cat_Language, 'A palindrome reads the same forward and backward, like "racecar."', GETDATE(), NULL, 0, 0),
(@Cat_General, 'U.S. paper currency is primarily a blend of cotton and linen rather than wood pulp.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'The International Space Station is the largest human-made object in low Earth orbit.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Termites are more closely related to cockroaches than to ants.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Koalas have fingerprints so similar to humans that they can confuse forensic analysis.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Giraffes and humans both have seven neck vertebrae despite their different neck lengths.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'A group of flamingos is called a flamboyance.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Male pufferfish create intricate sand circles on the seafloor to attract mates.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Monarch butterflies migrate thousands of kilometers between North America and Mexico.', GETDATE(), NULL, 0, 0),
(@Cat_Math, 'A leap year helps keep the calendar aligned with Earth''s orbit around the Sun.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'Mercury is the only metal that is liquid at standard room temperature and pressure.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Glass frogs have transparent skin on their bellies that reveals their internal organs.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Sharks appear in the fossil record before trees existed.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, 'The deepest part of the ocean is the Challenger Deep in the Mariana Trench.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'Polaris will not always be the North Star because Earth''s axis slowly wobbles over time.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Many lizards can shed their tails to escape predators and later regenerate them.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Plants like the Venus flytrap capture insects to supplement scarce nutrients.', GETDATE(), NULL, 0, 0),
(@Cat_Health, 'The brain itself has no pain receptors; headaches arise from surrounding tissues and blood vessels.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'The ostrich is the tallest living bird and lays the largest eggs of any bird.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, 'A piano is considered both a string instrument and a percussion instrument.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'The modern internet traces its roots to ARPANET, a project started in the late 1960s.', GETDATE(), NULL, 0, 0),
(@Cat_Space, 'GPS satellites must account for relativity because time runs slightly differently in orbit.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, 'A cloud can weigh many tons because it contains vast numbers of tiny water droplets.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Mango trees are in the same plant family as cashews and pistachios.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, 'Tomatoes are fruits botanically but are often treated as vegetables in cooking.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Seahorses have prehensile tails that help them anchor to seagrass and corals.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Snakes collect scent particles on their tongues and deliver them to Jacobson''s (vomeronasal) organ to "smell."', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'A teaspoon of neutron star material would weigh billions of tons on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The Milky Way and Andromeda galaxies are on a collision course expected in about 4-5 billion years.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Pluto has a heart-shaped region called Tombaugh Regio.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'A year on Mercury lasts about 88 Earth days.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The Sun contains about 99.8% of the total mass of the solar system.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The Kuiper Belt beyond Neptune is filled with icy bodies including Pluto and Eris.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'A total solar eclipse is visible only along a narrow path where the Moon''s umbra reaches Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Space is not completely empty; it contains a sparse interstellar medium of gas and dust.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'On Mars, sunsets can appear blue because dust scatters red light more than blue.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Voyager 1 is the most distant human-made object from Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The ''dark side'' of the Moon is a misnomer; the far side receives sunlight too.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Light in a vacuum travels about 299,792 kilometers per second.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Absolute zero is 0 kelvin, equivalent to -273.15 degrees Celsius.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Glass is an amorphous solid rather than a crystalline solid.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Water is densest at about 4°C, which helps lakes freeze from the top down.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Under some conditions, hot water can freeze faster than cold water (the Mpemba effect).', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'The periodic table is ordered by atomic number, not atomic mass.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'A bolt of lightning can be several times hotter than the surface of the Sun.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Penicillin was discovered by Alexander Fleming in 1928.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'The Doppler effect explains the change in pitch of a passing siren and redshift of distant galaxies.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Some RNA molecules can catalyze reactions; these are called ribozymes.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Mitochondria and chloroplasts contain their own DNA.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'The human liver can regenerate portions of itself after injury.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Humans typically have 46 chromosomes in their somatic cells.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'An average adult has roughly five liters of blood.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'All regions of the tongue can detect basic tastes; the old ''tongue map'' is a myth.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Umami is recognized as a basic taste, often associated with glutamate.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'The skin is the largest organ of the human body by area.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Earwax helps protect and lubricate the ear canal and is influenced by genetics.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Axolotls exhibit neoteny, retaining juvenile features into adulthood.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Ravens are excellent mimics and can imitate human speech.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Most cats cannot taste sweetness due to a mutated taste receptor.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Blue whales are the largest animals known to have ever lived.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Camels have a transparent third eyelid that helps protect their eyes from blowing sand.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Penguins ''fly'' underwater using their flippers but cannot fly in the air.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Male emperor penguins incubate eggs on their feet under a brood pouch.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Pistol shrimp create a cavitation bubble with a snap that can stun prey.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Mantis shrimp have up to sixteen types of photoreceptors for color vision.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Owls can rotate their heads about 270 degrees in either direction.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'A group of crows is called a murder.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Chocolate can be toxic to dogs because it contains theobromine.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Saffron is made from the dried stigmas of the Crocus sativus flower.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'The heat of chili peppers is measured in Scoville Heat Units.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Almonds are the seeds of a drupe, not true nuts.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Cashews grow as seeds on the outside of the cashew apple.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Quinoa is a pseudocereal; it is a seed used like a grain.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Wheat and barley were among the first domesticated crops in the Fertile Crescent.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Tea is the most consumed beverage in the world after water.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Africa is the only continent that straddles all four hemispheres.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Canada has the longest coastline of any country.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Amazon River is the largest by discharge of water into the ocean.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Lake Baikal in Russia holds about one-fifth of the world''s unfrozen fresh surface water by volume.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Atacama Desert in Chile has areas that receive virtually no rainfall.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Angel Falls in Venezuela is the world''s tallest uninterrupted waterfall.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Sahara is the largest hot desert on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Iceland is known as the land of fire and ice for its volcanoes and glaciers.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Most of the world''s earthquakes and volcanoes occur along the Pacific Ring of Fire.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Tsunamis are most often caused by undersea earthquakes that displace large volumes of water.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Earth''s inner core is solid, while the outer core is liquid metal that helps generate the magnetic field.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Earth''s magnetic north pole wanders over time due to changes in the core.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Coral reefs are built by tiny animals called coral polyps that secrete calcium carbonate skeletons.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Karst landscapes with sinkholes form when water dissolves soluble rocks like limestone.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'The word ''quarantine'' comes from Italian ''quaranta giorni,'' meaning forty days.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'The English pangram ''The quick brown fox jumps over the lazy dog'' uses every letter of the alphabet.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Mandarin Chinese is a tonal language where pitch patterns change word meaning.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'English is a Germanic language with substantial Romance vocabulary due to historical contact.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Zero as a number and placeholder was developed in ancient India and spread via Arabic scholarship.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'A googol is the number 10 to the power of 100.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'There are infinitely many prime numbers, a fact proved by Euclid.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Pi (π) is an irrational and transcendental number.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'The golden ratio, about 1.618, appears in some growth patterns and geometric constructions.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'The QWERTY keyboard layout was designed to reduce jamming in early typewriters.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'The first website was created by Tim Berners-Lee and went online in 1991.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Moore''s Law observed that the number of transistors on a chip roughly doubled every two years.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Unicode assigns code points to characters to support writing systems worldwide.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Email existed before the World Wide Web.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'In English practice, a haiku is often written with a 5-7-5 syllable pattern.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Sushi refers to vinegared rice; raw fish is not required for sushi.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Bread rises because yeast ferments sugars, producing carbon dioxide.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Cheese is made by coagulating milk proteins, often using enzymes like rennet.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Sea otters use rocks as tools to crack open shellfish.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Elephants communicate using low-frequency rumbles that can travel long distances.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Geckos can walk on smooth walls thanks to microscopic hairs on their toes that exploit van der Waals forces.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Kangaroos cannot move their hind legs independently when moving slowly; they use their tail as a fifth limb.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The archerfish can shoot jets of water to knock insects off leaves into the water.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Bamboo can grow astonishingly fast, with some species growing over 30 centimeters in a day under ideal conditions.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Vanilla flavoring comes from the cured pods of orchids in the genus Vanilla.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Cacti store water in specialized tissues, allowing survival in arid environments.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'The corpse flower (Amorphophallus titanum) produces one of the largest and smelliest blooms.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Paper was invented in ancient China during the Han dynasty.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The printing press popularized by Johannes Gutenberg in the 15th century revolutionized information sharing.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Silk Road was a network of trade routes connecting East and West for centuries.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Rosetta Stone helped scholars decipher Egyptian hieroglyphs.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Mauna Kea in Hawaii is taller than Mount Everest when measured from its base on the ocean floor.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Most comets originate from the Oort Cloud and Kuiper Belt, distant reservoirs of icy bodies.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Neptune has some of the fastest winds in the solar system, reaching over 2,000 kilometers per hour.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Uranus rotates on its side with an axial tilt of about 98 degrees.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'A light-year is the distance light travels in one year, about 9.46 trillion kilometers.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Mars has a canyon system called Valles Marineris that stretches over 4,000 kilometers.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Earth’s seasons are caused by its axial tilt of roughly 23.5 degrees, not by distance from the Sun.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Auroras are produced when charged particles from the Sun interact with Earth’s magnetic field and atmosphere.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Many exoplanets have been discovered using the transit method, which detects tiny dips in a star’s brightness.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Halley’s Comet has an orbital period of about 76 years.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Mercury has an extremely thin exosphere rather than a substantial atmosphere.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The Moon is tidally locked to Earth, always showing the same face.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'DNA molecules typically form a double-helix structure.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Enzymes are biological catalysts that speed up chemical reactions in cells.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'The pH scale ranges from 0 to 14, with 7 being neutral.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Most of Earth’s freshwater is stored in glaciers and ice sheets.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'The speed of sound in air at about 20°C is roughly 343 meters per second.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Plasma is an ionized state of matter distinct from solid, liquid, and gas.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'In an isolated system, entropy tends to increase over time (the Second Law of Thermodynamics).', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Viruses require host cells to replicate and are not considered living by many definitions.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Catalysts lower the activation energy of reactions without being consumed.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Visible light spans wavelengths of about 400 to 700 nanometers.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'The Coriolis effect influences large-scale wind and ocean current patterns.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'The ozone layer absorbs most of the Sun’s harmful ultraviolet-B radiation.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'El Niño is a periodic warming of the central and eastern tropical Pacific that alters global weather.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'The water cycle circulates water through evaporation, condensation, and precipitation.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Earth is about 4.54 billion years old based on radiometric dating.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Fossils are most commonly preserved in sedimentary rocks.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'The moment magnitude scale is widely used to measure earthquake size.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Hurricanes, typhoons, and cyclones are the same kind of storm in different ocean basins.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Plate boundaries can be divergent, convergent, or transform.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'A rain shadow occurs when mountains block moist air, creating drier conditions on the leeward side.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Russia spans eleven time zones across its territory.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Nile River flows northward and empties into the Mediterranean Sea.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Mount Everest’s summit is about 8,849 meters above sea level.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Greenland is the world’s largest island that is not a continent.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Australia is both a country and a continent.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Danube River flows through more countries than any other river in Europe.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Lake Superior is the largest freshwater lake by surface area.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Mediterranean Sea connects to the Atlantic Ocean through the Strait of Gibraltar.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Monaco is one of the most densely populated countries in the world.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Himalayas form where the Indian Plate collides with the Eurasian Plate.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Wright brothers achieved the first sustained, powered flight in 1903 at Kitty Hawk.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Roman Empire used volcanic ash in concrete, contributing to its durability.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Magna Carta, sealed in 1215, limited the power of the English monarch.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The first modern Olympic Games were held in Athens in 1896.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Black Death in the 14th century drastically reduced Europe’s population.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Berlin Wall fell in 1989, symbolizing the end of the Cold War era.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Yuri Gagarin became the first human in space in 1961.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Apollo 11 astronauts first landed on the Moon in 1969.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Ancient Egyptians built pyramids as monumental royal tombs.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Code of Hammurabi is one of the earliest known law codes.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Transistors replaced vacuum tubes and enabled modern microelectronics.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'HTTP is the protocol that web browsers use to request and fetch web pages.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Open-source software allows anyone to inspect and modify the source code.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Machine learning systems learn patterns from data rather than explicit rules.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Binary numbers use only two digits: 0 and 1.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'A byte is a group of eight bits.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'GPS positioning uses trilateration from multiple satellite signals.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'QR codes store data in a two-dimensional matrix of modules.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Cloud computing provides on-demand computing resources over the internet.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'A compiler translates source code into machine code, while an interpreter executes it directly.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Red blood cells carry oxygen using the protein hemoglobin.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Vaccines train the immune system to recognize specific pathogens.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Insulin is a hormone that helps regulate blood glucose levels.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Antibiotics target bacteria and do not work against viruses.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Bees can see ultraviolet patterns on flowers that guide them to nectar.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Cats have a righting reflex that helps them land on their feet.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Peregrine falcons can exceed 300 km/h in a hunting dive.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Chameleons change color for communication and thermoregulation as well as camouflage.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Dolphins and bats use echolocation to navigate and hunt.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Giant pandas have a modified wrist bone that functions like a thumb.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Elephants have the largest brains of any land animal.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Octopuses are highly intelligent and can solve simple problems and puzzles.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Arctic foxes have seasonal coats that change from brown to white.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Sea stars can regenerate lost arms in many species.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Chlorophyll absorbs red and blue light and reflects green, giving plants their color.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Legumes often host nitrogen-fixing bacteria in root nodules.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Many plants form mycorrhizal partnerships with fungi to enhance nutrient uptake.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Apples can float in water because a significant portion of their volume is air.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Deciduous trees shed their leaves to conserve resources during unfavorable seasons.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Conifers bear seeds in cones and typically keep needle-like leaves year-round.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Dark chocolate contains flavonoids found in cocoa solids.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Baker’s yeast is a single-celled fungus used to leaven bread.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Olive oil is rich in the monounsaturated fatty acid oleic acid.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Lactose is the natural sugar in milk; many adults have reduced lactase enzyme levels.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Sourdough bread uses wild yeast and lactic acid bacteria for fermentation.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Fermentation can preserve foods by producing acids or alcohol that inhibit microbes.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'The ampersand symbol (&) originated as a ligature of the Latin word ''et''.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Writing systems include alphabets, abjads, abugidas, and logographies.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Loanwords enter a language through contact with other cultures.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'In English, word order helps indicate grammatical relationships (subject–verb–object).', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Euler’s number e is approximately 2.718281828 and arises in growth and decay models.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'The Pythagorean theorem states a² + b² = c² in right triangles.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'In Euclidean geometry, the interior angles of a triangle sum to 180 degrees.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Probability values range from 0 to 1, representing impossibility to certainty.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Factorials, denoted n!, grow very rapidly with n.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'The Fibonacci sequence begins 0, 1, 1, 2, 3, and so on.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'The Mona Lisa is displayed at the Louvre Museum in Paris.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'A standard modern piano has 88 keys.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'William Shakespeare wrote plays and poetry in Early Modern English.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Primary colors for additive light mixing are red, green, and blue.', GETDATE(), NULL, 0, 0);
GO

-- Step 11: Verify the setup
SELECT 'Categories' AS TableName, COUNT(*) AS RecordCount FROM Categories
UNION ALL SELECT 'Facts', COUNT(*) FROM Facts
UNION ALL SELECT 'ReviewLogs', COUNT(*) FROM ReviewLogs;
