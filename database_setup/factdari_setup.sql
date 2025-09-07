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
IF OBJECT_ID('AchievementUnlocks', 'U') IS NOT NULL DROP TABLE AchievementUnlocks;
IF OBJECT_ID('Achievements', 'U') IS NOT NULL DROP TABLE Achievements;
IF OBJECT_ID('GamificationProfile', 'U') IS NOT NULL DROP TABLE GamificationProfile;
IF OBJECT_ID('ReviewLogs', 'U') IS NOT NULL DROP TABLE ReviewLogs;
IF OBJECT_ID('ReviewSessions', 'U') IS NOT NULL DROP TABLE ReviewSessions;
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

-- Step 6: Create ReviewSessions table (for full session tracking)
CREATE TABLE ReviewSessions (
    SessionID INT IDENTITY(1,1) PRIMARY KEY,
    StartTime DATETIME NOT NULL,
    EndTime DATETIME NULL,
    DurationSeconds INT NULL,
    TimedOut BIT NOT NULL CONSTRAINT DF_ReviewSessions_TimedOut DEFAULT 0,
    -- Per-session action counters
    FactsAdded INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsAdded DEFAULT 0,
    FactsEdited INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsEdited DEFAULT 0,
    FactsDeleted INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsDeleted DEFAULT 0
);

-- Step 7: Create ReviewLogs table with per-view duration and optional session link
CREATE TABLE ReviewLogs (
    ReviewLogID INT IDENTITY(1,1) PRIMARY KEY,
    FactID INT NULL,
    ReviewDate DATETIME NOT NULL,
    SessionDuration INT, -- seconds
    SessionID INT NULL,
    TimedOut BIT NOT NULL CONSTRAINT DF_ReviewLogs_TimedOut DEFAULT 0,
    -- Action metadata (view/add/edit/delete) and snapshots to preserve history after deletes
    Action NVARCHAR(16) NOT NULL CONSTRAINT DF_ReviewLogs_Action DEFAULT 'view',
    FactEdited BIT NOT NULL CONSTRAINT DF_ReviewLogs_FactEdited DEFAULT 0,
    FactDeleted BIT NOT NULL CONSTRAINT DF_ReviewLogs_FactDeleted DEFAULT 0,
    FactContentSnapshot NVARCHAR(MAX) NULL,
    CategoryIDSnapshot INT NULL,
    CONSTRAINT FK_ReviewLogs_Facts FOREIGN KEY (FactID)
        REFERENCES Facts(FactID) ON DELETE SET NULL,
    CONSTRAINT FK_ReviewLogs_ReviewSessions FOREIGN KEY (SessionID)
        REFERENCES ReviewSessions(SessionID)
);

-- Step 8: Create GamificationProfile table (for user stats and XP/level tracking)
CREATE TABLE GamificationProfile (
    ProfileID INT IDENTITY(1,1) PRIMARY KEY,
    XP INT NOT NULL CONSTRAINT DF_GamificationProfile_XP DEFAULT 0,
    Level INT NOT NULL CONSTRAINT DF_GamificationProfile_Level DEFAULT 1,
    TotalReviews INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalReviews DEFAULT 0,
    TotalKnown INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalKnown DEFAULT 0,
    TotalFavorites INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalFavorites DEFAULT 0,
    TotalAdds INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalAdds DEFAULT 0,
    TotalEdits INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalEdits DEFAULT 0,
    TotalDeletes INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalDeletes DEFAULT 0,
    CurrentStreak INT NOT NULL CONSTRAINT DF_GamificationProfile_CurrentStreak DEFAULT 0,
    LongestStreak INT NOT NULL CONSTRAINT DF_GamificationProfile_LongestStreak DEFAULT 0,
    LastCheckinDate DATE NULL
);

-- Step 9: Create Achievements table (catalog of all possible achievements)
CREATE TABLE Achievements (
    AchievementID INT IDENTITY(1,1) PRIMARY KEY,
    Code NVARCHAR(64) NOT NULL UNIQUE,
    Name NVARCHAR(200) NOT NULL,
    Category NVARCHAR(32) NOT NULL,
    Threshold INT NOT NULL,
    RewardXP INT NOT NULL,
    IsHidden BIT NOT NULL CONSTRAINT DF_Achievements_IsHidden DEFAULT 0,
    CreatedDate DATETIME NOT NULL CONSTRAINT DF_Achievements_CreatedDate DEFAULT GETDATE()
);

-- Step 10: Create AchievementUnlocks table (tracks which achievements have been earned)
CREATE TABLE AchievementUnlocks (
    UnlockID INT IDENTITY(1,1) PRIMARY KEY,
    AchievementID INT NOT NULL
        CONSTRAINT FK_AchievementUnlocks_Achievements
        REFERENCES Achievements(AchievementID),
    UnlockDate DATETIME NOT NULL CONSTRAINT DF_AchievementUnlocks_UnlockDate DEFAULT GETDATE(),
    Notified BIT NOT NULL CONSTRAINT DF_AchievementUnlocks_Notified DEFAULT 0
);

-- Create unique index to ensure each achievement can only be unlocked once
CREATE UNIQUE INDEX UX_AchievementUnlocks_AchievementID ON AchievementUnlocks(AchievementID);

-- Helpful indexes for app queries
CREATE INDEX IX_Facts_CategoryID ON Facts(CategoryID);
CREATE INDEX IX_Facts_LastViewedDate ON Facts(LastViewedDate);
CREATE INDEX IX_ReviewLogs_FactID ON ReviewLogs(FactID);
CREATE INDEX IX_ReviewLogs_ReviewDate ON ReviewLogs(ReviewDate);
CREATE INDEX IX_ReviewLogs_SessionID ON ReviewLogs(SessionID);
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

-- Step 11: Insert expanded categories
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
('Earth Science', 'Geology, weather, climate, plate tectonics'),
('DIY', 'Everyday home hacks: cleaning, organizing, minor fixes');
GO

-- Step 12: Cache category IDs for readable inserts
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
  @Cat_EarthScience INT = (SELECT CategoryID FROM Categories WHERE CategoryName='Earth Science'),
  @Cat_DIY INT = (SELECT CategoryID FROM dbo.Categories WHERE CategoryName = 'DIY');


-- Step 13:  Insert Facts
INSERT INTO Facts (CategoryID, Content, DateAdded, LastViewedDate, ReviewCount, TotalViews)
VALUES
(@Cat_Animals, N'Mantis shrimp strikes reach extreme accelerations and create cavitation shockwaves that can stun prey.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Many ants farm aphids for honeydew, protecting and herding them like livestock.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Cuttlefish can change color and texture in milliseconds using chromatophores and skin papillae.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Post-menopausal female orcas often lead pods and boost offspring survival.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Elephants pass the mirror self-recognition test and have rituals around death.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'New Caledonian crows craft hooked tools from twigs or pandanus leaves to extract grubs.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The blue-ringed octopus carries tetrodotoxin potent enough to paralyze humans.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Vampire bats share regurgitated blood with roostmates that failed to feed.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Three-toed sloths descend about once a week to defecate at the base of their tree.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Giraffes have specialized valves and tight leg skin to manage extremely high blood pressure.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Hummingbirds can enter nightly torpor to conserve energy.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Wood frogs can survive freezing by flooding their tissues with glucose as a cryoprotectant.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Electric eels can deliver discharges over 600 volts to stun prey and deter threats.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Platypuses detect prey by electrolocation with receptors in their bills.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Sharks sense weak electric fields using organs called ampullae of Lorenzini.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Some sea snakes drink rain-formed freshwater lenses that briefly sit atop seawater.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Mudskippers breathe through skin and mouth lining and use fins to “walk” on land.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Atlantic puffins carry multiple fish crosswise thanks to a spiny tongue and hinged jaws.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Owls fly quietly due to serrated wing edges and velvety feathers that damp turbulence.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Many animals use countershading—dark above, light below—to blend into their surroundings.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Axolotls can regenerate limbs, spinal cord, and even parts of the heart and brain.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The star-nosed mole can identify prey in as little as 20 milliseconds.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Homing pigeons use multiple cues, including smell and Earth’s magnetic field.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Monarch butterflies store toxic cardenolides from milkweed as a defense.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Poison dart frogs acquire skin toxins from a specialized arthropod diet.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Komodo dragons have venom glands that affect blood clotting and blood pressure.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Chinchillas have extremely dense fur and keep clean with dust baths, not water.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Naked mole-rats are eusocial mammals with a single breeding queen and unusual pain insensitivity.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Seahorses can move their eyes independently and snap prey with elastic-powered heads.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'In many deep-sea anglerfish, tiny males fuse to females and become permanent mates.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Sea otters sometimes hold paws while resting to avoid drifting apart.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'African grey parrots can learn large vocabularies and show concept learning.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Pufferfish toxin (tetrodotoxin) is produced by symbiotic bacteria and accumulates in tissues.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Leaf-tailed geckos use extreme camouflage that mimics leaves, bark, and even moss.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Ant pheromone trails self-reinforce, guiding colonies along the shortest routes to food.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Honeybees warm brood by shivering and cool hives by fanning and evaporating water.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Polar bear fur is hollow and translucent while their skin is black to absorb heat.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Reindeer eyes shift from gold in summer to blue in winter to suit Arctic light levels.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Flamingos turn pink from carotenoids in algae and crustaceans they eat.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Many crabs can shed a limb to escape and later regenerate it.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Praying mantises can rotate their heads and have a single ultrasound-sensitive ear on the chest.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Wild kangaroos often show left-handedness during tasks like grooming and feeding.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Cat purrs span roughly 25–150 Hz and may aid bone and tissue healing.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'A dog’s nose print is unique enough to identify an individual.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Dolphins and some whales sleep with one brain hemisphere at a time.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Male cuttlefish can display different patterns on each side—courting on one, deterring rivals on the other.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Dragonflies are among the most successful predators, with capture rates near 90% or higher.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Queens of some ant species can live for decades, vastly outliving workers.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Termite mounds have vents and conduits that regulate temperature and gas exchange.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Spiders extend legs hydraulically by pumping hemolymph; flexing uses muscles.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Tarantulas defend by flicking barbed urticating hairs from their abdomen.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Scorpions fluoresce blue-green under ultraviolet light due to chemicals in their cuticle.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Horses can sleep standing using a stay apparatus, but need to lie down for REM sleep.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Some glass frogs have bones that fluoresce green under UV light.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Lungless salamanders breathe through their skin and mouth lining.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Schooling fish lower risk by confusing predators and diluting individual chance of capture.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Penguins porpoise from the water to breathe and reduce drag at speed.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Pigeons can learn to categorize objects and even distinguish letters with training.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Clownfish avoid anemone stings thanks to a protective mucus coating.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Hermit crabs swap shells in “vacancy chains” when a better fit appears.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Blue whale low-frequency calls can travel hundreds of kilometers through the ocean.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Great white sharks and some tunas keep core muscles warm (regional endothermy).', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Tunas use countercurrent heat exchangers to maintain elevated body temperatures.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The male seahorse’s brood pouch supplies oxygen and regulates salt for embryos.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Many cuckoos are brood parasites; their eggs mimic hosts and chicks may eject rivals.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Greater honeyguides lead humans to hives, then feed on leftover wax and larvae.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The vampire squid emits bioluminescent displays and mucus to evade predators.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Some Caribbean ostracods release bright blue bioluminescent clouds during courtship.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'New Zealand glow-worm larvae hang sticky silk lines lit by bioluminescence to trap prey.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Leafcutter bees cut neat circles from leaves and line brood cells with them.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Beavers build dams that create ponds and wetlands used by many other species.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Many sea stars evert their stomachs to digest prey outside their bodies.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Cleaner shrimp advertise with antennae and pick parasites from willing “client” fish.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Remoras hitchhike on sharks and turtles using a suction-disc dorsal fin.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Ocean sunfish (Mola mola) bask at the surface to warm after deep cold dives.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Some sea cucumbers expel sticky tubules or organs as a defense, then regenerate them.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Echidnas, like platypuses, are egg-laying mammals and have electroreceptors in the snout.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Northern mockingbirds can learn and mimic hundreds of natural and artificial sounds.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Arctic terns migrate from Arctic to Antarctic and back each year—one of the longest migrations.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Common swifts can remain airborne for months, sleeping and feeding on the wing.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The hoatzin ferments leaves in an enlarged crop, giving it a manure-like odor.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Parasitic lampreys attach with a toothed suction disc and rasp tissue and fluids.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Hagfish produce slime that rapidly expands in water and can clog predators’ gills.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Marine iguanas graze algae and sneeze out excess salt through nasal glands.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'A narwhal’s tusk is a sensory organ with millions of nerve endings.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The Etruscan shrew’s heart can beat over 1,000 times per minute.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'An ostrich’s eye is larger than its brain.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Vultures have very acidic stomachs (around pH 1–2) that neutralize dangerous microbes.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Parrotfish often sleep inside a mucus cocoon that may mask their scent from predators.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Moray eels have extendable pharyngeal jaws that pull prey into the throat.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'An octopus can squeeze through any opening larger than its beak because it lacks a rigid skeleton.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Argentine ants have formed vast supercolonies with mutually tolerant members across continents.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Male sticklebacks glue nests with a protein called spiggin and fan eggs with their fins.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Many sea turtles imprint on their natal beach and navigate back years later to nest.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Fleas jump by releasing energy stored in springy resilin pads.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Cheetahs can accelerate to highway speeds in just a few seconds, outpacing many sports cars.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Horses cannot vomit due to a strong cardiac sphincter and the angle of the esophagus to the stomach.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Rabbits are lagomorphs, not rodents; their teeth grow continuously and require wear.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Zebra stripes can deter biting flies by disrupting their landing cues.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Dung beetles can orient and navigate using the Milky Way’s glow to keep straight paths.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A thoroughly shuffled 52-card deck has 52! ≈ 8.07×10^67 possible orders—far more than the atoms on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Olympic “gold” medals are mostly silver with a thin layer of gold applied.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Scotland’s national animal is the unicorn.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The world’s shortest scheduled flight (Westray–Papa Westray, Orkney) can take under two minutes.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Sargasso Sea has no land boundaries; it is defined entirely by Atlantic Ocean currents.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The original London Bridge was moved to Lake Havasu City, Arizona, in 1971.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Alaska is both the westernmost and easternmost U.S. state because the Aleutians cross the 180th meridian.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'China spans five geographical time zones but keeps a single official time.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Several places use half- or quarter-hour time zones (e.g., India UTC+5:30; Nepal UTC+5:45).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Only two sovereign states have square national flags: Switzerland and Vatican City.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Nepal’s flag is the the only non-rectangular national flag (a double pennant).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Saint Lucia is the only country named after a woman (Saint Lucy).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Brazil is named after brazilwood (pau-brasil), historically harvested for red dye.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Two countries are doubly landlocked: Liechtenstein and Uzbekistan.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Welsh station Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch has one of the longest place names.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The interrobang (‽) is a punctuation mark proposed in 1962 combining a question and an exclamation.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The plastic tip on a shoelace is called an aglet.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The pleasant, earthy smell after rain is called petrichor.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'An airplane “black box” is actually bright orange to aid recovery.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'“Bluetooth” was named after Viking king Harald Bluetooth; the logo merges the runes for H and B.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Apollo missions left retroreflectors on the Moon that still let us measure the Earth–Moon distance by laser.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Hundred Years’ War lasted 116 years (1337–1453).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'In 1893 (Nix v. Hedden), the U.S. Supreme Court classified tomatoes as vegetables for tariffs.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A “baker’s dozen” means thirteen—an old safeguard against selling underweight bread.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Any month that starts on a Sunday will include a Friday the 13th.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'“D-Day” simply means the day an operation begins; the letter is not an acronym.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Mr. Potato Head (1952) was the first toy advertised on television.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The first domain name ever registered was symbolics.com in 1985.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Ray Tomlinson sent the first networked email in 1971 and chose “@” to separate user and host.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The longest word in many English dictionaries is pneumonoultramicroscopicsilicovolcanoconiosis.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The most common letter in English text is E.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'IKEA product names follow themes (e.g., sofas and coffee tables use Swedish place names; bookcases use occupations).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Monopoly property names were taken from streets in Atlantic City, New Jersey.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The five Olympic ring colors (plus white) were chosen so every nation’s flag contains at least one.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Space Shuttle’s external tank was left unpainted after early flights—saving ~270 kg—hence its orange color.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Snow looks white, but individual ice crystals are clear; snow’s whiteness comes from diffuse scattering of light.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Bananas are mildly radioactive due to the isotope potassium‑40.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'“Moonbows” (lunar rainbows) occur at night; they appear faint and often whitish.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'You cannot hum with your nose completely pinched closed—there’s nowhere for air to exit.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Papua New Guinea is home to 800+ living languages, the most of any country.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The longest mountain chain on Earth is the Mid‑Ocean Ridge, mostly underwater.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The deepest hole humans have drilled is the Kola Superdeep Borehole (about 12,262 meters).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The “Spanish flu” likely did not originate in Spain; Spain’s free press made it widely reported there.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'M&M stands for Mars & Murrie, the surnames of the founders.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Sea level is not uniform; gravity, currents, and temperature create regional differences in mean sea level.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'“Checkmate” comes from Persian “shāh māt,” often glossed as “the king is helpless.”', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Arabic numerals used today were developed in India and reached Europe via the Islamic world.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Most blue eyes contain little pigment; they look blue due to light scattering in the iris.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Book EANs use the “Bookland” prefixes 978 and 979 for ISBN‑13 barcodes.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'In Morse code, SOS (··· ––– ···) is not an abbreviation; it’s an easy‑to‑recognize distress signal.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Blue flames are typically hotter than yellow flames (more complete combustion).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Globally, blood type O is the most common.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Counting all sizes, a standard 8×8 chessboard contains 204 distinct squares (1×1 through 8×8).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Antarctica is the only continent with no native ant species.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Svalbard Global Seed Vault serves as a backup for the world’s crop diversity.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Punched cards used for the Jacquard loom influenced early programmable computing.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The classic soccer ball pattern is a truncated icosahedron (12 pentagons + 20 hexagons).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The word “deadline” originally referred to a line prisoners would be shot for crossing during the U.S. Civil War.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Leap‑year rule: years divisible by 4 are leap years, except centuries not divisible by 400.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Tides are strongest at full/new moon (spring tides) and weakest at quarter moons (neap tides).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The record low air temperature was −89.2 °C at Vostok Station, Antarctica (1983).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'RSVP comes from French “Répondez s’il vous plaît” (“Please reply”).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'No chemical element symbol uses the letter J.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'“Octopuses” is widely accepted; “octopi” treats a Greek word as if it were Latin.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A “score” means twenty; “four score and seven” equals eighty‑seven.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'In medieval Europe, a “moment” was 1/40 of an hour—90 seconds.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The modern Hawaiian alphabet counts 13 symbols (5 vowels, 7 consonants, plus the ʻokina glottal stop).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Tyrannosaurus rex lived closer in time to humans than to Stegosaurus.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The human eye can distinguish roughly ten million colors.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The smallest country by area is Vatican City (≈0.49 km²).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The largest country by area is Russia (≈17 million km²).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The world’s highest administrative capital is La Paz, Bolivia, at over 3,600 meters.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The sidereal day (Earth’s rotation relative to the stars) is about 23 h 56 m—shorter than 24 hours.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'In standard decks, the king of hearts is the only king without a mustache.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Humans experience a natural “nasal cycle,” where one nostril tends to flow more freely than the other, alternating over hours.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'BB in “BB gun” originally referred to the size of the shot (around 0.177 inch), not ball bearings per se.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Camels store fat—not water—in their humps.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A group of porcupines is called a prickle.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A tesseract is the four‑dimensional analog of a cube (a hypercube).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A googolplex is 10^(10^100), vastly larger than a googol (10^100).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Shakespeare is the earliest recorded source for many English words (e.g., “eyeball,” “lonely,” “swagger”).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Roman numerals have no symbol for zero.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Oranges often stay green in tropical climates even when ripe due to chlorophyll retention in the peel.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Earth’s atmosphere is roughly 78% nitrogen and 21% oxygen by volume.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Horseshoe crabs have blue blood due to copper‑based hemocyanin.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Pineapples typically take 18–24 months from planting to harvest.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'It takes roughly 40 liters of maple sap to produce 1 liter of maple syrup.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Nickel‑titanium (Nitinol) alloys can “remember” shapes and return after deformation when heated.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The “French” croissant descends from the Austrian kipferl and became popularized in France.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Kangaroo joeys are born tiny—about the size of a jellybean—and continue developing in the pouch.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Suez Canal has no locks because the Red Sea and Mediterranean are at similar mean sea levels.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The term “astronaut” is Greek‑derived (“star sailor”); the Russian “cosmonaut” means “universe sailor.”', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Chess grandmaster was formalized as a FIDE title in 1950.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The piano’s sustain pedal (right pedal) lifts all dampers, letting strings ring sympathetically.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Empire State Building has its own ZIP code (10118) due to mail volume.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'On maps, Greenland often looks huge due to Mercator projection distortion; it is much smaller than Africa in area.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The Great Emu War (1932) in Australia was a real military operation—emus proved surprisingly hard to control.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The heaviest naturally occurring element by atomic number is uranium (Z=92).', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The word “quiz” spread in the 18th–19th centuries; its origin is uncertain and much‑debated.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove red wine stains: blot (don''t rub), cover with salt to draw out moisture, rinse with cold water. For whites, a 1:1 mix of hydrogen peroxide and dish soap can help; avoid heat until the stain is gone.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Unclog a slow drain: pour ½ cup baking soda, then 1 cup warm vinegar; let foam 10–15 minutes, flush with hot water. Never mix with chemical drain cleaner.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Clean a microwave fast: heat a bowl of water with a splash of vinegar and lemon slices for 3–5 minutes; let steam sit, then wipe.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Pick up tiny broken glass shards with a slice of bread or duct tape after sweeping; double-bag the waste and label it.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Broken light bulb in a socket: switch off at the breaker, wear gloves/eye protection, and use needle-nose pliers to twist the metal base counter-clockwise. A cut potato can work only if power is OFF and the bulb is cool/dry—use with extreme care.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Neutralize fridge odours with an open pot of coffee grounds or baking soda on a shelf; replace monthly.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Clean blender safely: half-fill with warm water and a drop of dish soap, blend 20–30 seconds, rinse well.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove sticky labels/adhesive by warming with a hairdryer or rubbing a few drops of cooking oil; peel and wash the residue.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Organise scarves/belts using shower-curtain rings on a hanger for a compact, visible rack.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Use two pillow inserts in one cover for extra fullness on sofas or beds.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'De-fog bathroom mirrors: rub a small amount of shaving foam across the surface, then buff clean.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Shine taps and remove water spots with a vinegar-damp cloth, then rinse and dry. Don''t use on natural stone.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Descale a kettle: fill with a 1:1 vinegar-water mix, bring to a simmer/soak 20 minutes, rinse thoroughly. Check your manufacturer''s guidance first.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove hard-water haze from shower glass with a paste of baking soda and a little water; rinse and squeegee after showers to prevent buildup.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Clean showerheads: tie on a bag of vinegar so the head is submerged; soak a few hours or overnight, then rinse.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Deodorise shoes by sprinkling a little baking soda inside overnight or tuck dry tea bags in each shoe; avoid prolonged contact with delicate leather.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Freshen a mattress: sprinkle baking soda, let sit 30–60 minutes, then vacuum with an upholstery tool.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Stop squeaky door hinges with a tiny dab of silicone spray or petroleum jelly; wipe away excess to avoid drips.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Quiet a rattling cabinet/door: add felt bumpers or adhesive silicone dots at contact points.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Block draughts under doors with a rolled towel for a quick fix; install a door sweep or adhesive weather-strip for a longer-term solution.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Free a sticky zipper by rubbing the teeth with a graphite pencil or a sliver of candle wax.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Lift deodorant marks from clothing with a dry microfibre sponge or a tumble-dryer sheet.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Erase coffee/tea stains in mugs with a baking-soda paste; gentle scrub and rinse.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove chewing gum from fabric: harden with an ice pack, scrape off, then pre-treat residue with a little oil or stain remover before washing.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Pre-treat oil/grease stains on clothes with dishwashing liquid; gently work in and launder warm per care label.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Lift candle wax from fabric or carpet: let harden, pick off pieces, then use paper towel and a warm iron to absorb the rest.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove pet hair from upholstery/carpets using a damp rubber glove or a window squeegee.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Quick wrinkle release: hang clothes in a steamy bathroom or spritz with water and smooth by hand.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Keep bin liners from slipping: tie a small knot at the rim or stick two small adhesive hooks inside to catch the liner handles.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Deodorise bins: sprinkle baking soda in the base after washing and drying.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Deodorise and refresh wooden chopping boards: scrub with coarse salt and half a lemon, rinse, dry, then oil with food-safe mineral oil.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Clean stainless steel along the grain using a drop of dish soap and a microfibre cloth; avoid abrasive powders.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Stop a cutting board sliding by placing a damp paper towel or silicone mat underneath.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Reheat food evenly in the microwave by arranging it in a ring with a hole in the centre and covering; stir halfway.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Clean oven racks: soak in a bathtub with hot water and a dishwasher tablet; protect the tub with an old towel before scrubbing.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove limescale around taps by wrapping with a vinegar-soaked paper towel for 10–20 minutes, then wipe and rinse.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Brighten grout with a baking-soda paste and a small brush; avoid harsh acids that can damage grout.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Streak-free window cleaning: use a 1:1 vinegar-water mix and a microfibre cloth or squeegee; avoid direct sun.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Keep a paintbrush fresh between coats by wrapping it in cling film or foil and refrigerating for a few hours.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Catch drilling dust: fold a sticky note into a little shelf under the hole or hold a cup/vacuum nozzle beneath.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Find tiny dropped items (earrings, screws) with a vacuum hose covered by a stocking—objects get caught at the mesh.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Drive a stubborn screw by seating the correct bit and using a wide rubber band between bit and screw head for extra grip.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Quiet light squeaks in floorboards by sprinkling talcum powder into the gaps and sweeping it in.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Loosen a stuck jar lid with extra grip from a rubber glove, a jar-opener, or by running the lid under hot water to expand it.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Keep brown sugar soft by sealing it with a marshmallow or a slice of bread inside; remove once it re-softens.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Revive day-old bread: lightly sprinkle with water and warm in the oven for a few minutes to re-gelatinise the starches.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Prevent mirror fogging temporarily with a tiny drop of dish soap wiped thin and buffed until clear.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove crayon from painted walls by gently warming with a hairdryer and wiping, or use a baking-soda paste; test paint first.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Remove white water rings on finished wood by warming gently with a hairdryer and then rubbing a little olive oil or furniture wax; test first.', GETDATE(), NULL, 0, 0),
(@Cat_DIY, N'Pet hair on carpets lifts well with a window squeegee; pull towards you and vacuum the clumps.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Shannon estimated chess''s game-tree complexity around 10^120, vastly exceeding estimates of atoms in the observable universe.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'In standard real analysis, 0.999… equals 1 exactly — not just approximately.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'There are different sizes of infinity: the set of real numbers is "larger" than the set of integers.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'One gram of matter annihilating with one gram of antimatter would release about 1.8×10^14 joules — enough to power a city for days.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Boiling and freezing points depend on pressure: water can boil at room temperature in a vacuum.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'In microgravity, flames form cool, nearly spherical "diffusion flames" instead of tall cones.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Quantum tunneling lets particles cross energy barriers — it''s essential for nuclear fusion in stars like our Sun.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'The Monty Hall problem: switching doors doubles your chance of winning from 1/3 to 2/3.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Euler''s identity e^(iπ)+1=0 links five fundamental constants in a single elegant equation.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Sonoluminescence is light emitted by tiny bubbles collapsing in a liquid under sound waves.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Your head ages slightly faster than your feet because gravity slows time — a measurable general-relativity effect.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Astronauts can grow up to 5 cm taller in orbit as spinal discs decompress; they shrink back on Earth.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'If you could fold a paper 42 times (ignoring physics), it would be thick enough to reach the Moon.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'All the planets could fit side-by-side in the average Earth–Moon distance with room to spare.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'On Saturn’s moon Titan, rivers and rain are liquid hydrocarbons — mostly methane and ethane.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'On Neptune and Uranus, extreme pressures likely form "diamond rain" deep within the planets.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Black holes have temperatures: stellar-mass black holes are incredibly cold via Hawking radiation.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Neutron-star crust, nicknamed "nuclear pasta," may be the strongest known material in the universe.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'In space, without convection, heat doesn’t dissipate by rising air — thermal control is a major spacecraft challenge.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Astronomers can "see" baby planets by watching shadows and gaps carved into protoplanetary disks.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Cleopatra lived closer in time to today than to the building of the Great Pyramid of Giza.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Oxford University predates the Aztec capital Tenochtitlan by more than two centuries.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'In 1977, the "Wow!" signal — a strong narrowband radio burst — briefly hinted at a possible extraterrestrial source.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Roman concrete structures survived millennia partly thanks to volcanic ash that fosters self-healing minerals.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'In 1969, Apollo 12 astronauts accurately landed near Surveyor 3 — a spacecraft that had arrived two years earlier.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'The "immortal jellyfish" Turritopsis dohrnii can revert its adult cells back to a juvenile state.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Pistol shrimp snap so fast they create a cavitation bubble that briefly reaches temperatures like the Sun’s surface.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Lyrebirds can mimic chainsaws, car alarms, and camera shutters with startling accuracy.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Greenland sharks may live for over 400 years, making them among the longest-lived vertebrates.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Ant-controlling fungi (Ophiocordyceps) manipulate hosts to climb and clamp before a spore stalk erupts.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Bombardier beetles eject a hot, noxious spray from a chemical reaction chamber to deter predators.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Elysia chlorotica sea slugs "steal" chloroplasts from algae and photosynthesize for weeks.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Octopus arms have distributed neural control; an arm can execute complex motions semi-independently.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Hoatzin chicks have functional wing claws they use to clamber through branches.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Platypus milk contains antimicrobial peptides potent against resistant bacteria.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Pando, a clonal aspen grove in Utah, may be one of Earth’s heaviest and oldest living organisms.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Welwitschia, a desert plant, grows only two leaves that persist and fray for over a thousand years.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Rafflesia produces the world’s largest individual flower and smells like rotting meat.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Strangler figs germinate on other trees, sending roots down and eventually engulfing their hosts.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Some carnivorous plants like Nepenthes form "bat roost" pitchers that trade shelter for nutrient-rich guano.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Lake Nyos in Cameroon erupted carbon dioxide in 1986, suffocating thousands in a rare limnic eruption.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Lightning can fuse sand into branching glassy tubes called fulgurites.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'The Earth hums: microseisms from ocean waves make the planet continuously vibrate at low amplitudes.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Continents drift at about the rate fingernails grow — centimeters per year.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Catatumbo, Venezuela, has storms with lightning hundreds of nights per year at the same spot.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Dead Sea''s shoreline is Earth’s lowest land elevation, more than 400 meters below sea level.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Lake Hillier in Australia is naturally pink due to microorganisms and high salinity.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Trikala, Greece hosts a continuously operating "lithic" (stone) bridge used for centuries without mortar.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'There is a "boiling river" (Shanay-Timpishka) in the Peruvian Amazon that can reach ~90°C.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'At the equator, Earth’s rotation makes you weigh slightly less than at the poles.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'The Apollo Guidance Computer used rope memory literally woven by hand, with wires through or around cores to encode bits.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'A single modern smartphone contains materials sourced from dozens of elements across the periodic table.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Error-correcting memory (ECC) can detect and correct random bit flips caused by cosmic rays.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Hash collisions exist by the pigeonhole principle; cryptographic hashes just make finding them infeasible.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Captchas exploit tasks easy for humans but historically hard for machines — a line that keeps shifting.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'You shed around 30,000–40,000 skin cells every minute; most household dust includes human skin and fabric fibers.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Your stomach replaces its mucus layer about every few hours to safely contain hydrochloric acid.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Goosebumps are a vestigial reflex once useful for fluffing fur to trap heat and look larger to threats.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'The cornea receives oxygen directly from the air; it has no blood vessels.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Your nose can detect certain molecules at concentrations of parts per trillion.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Stonehenge predates the Great Pyramid; both align with celestial events.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'The golden ratio appears in some art and design, though its prevalence is often overstated.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Ancient Greek statues were once brightly painted; the pristine white look is a modern misconception.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Stradivarius violins owe their sound to craftsmanship and material properties more than a single "secret".', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Japanese kintsugi repairs broken pottery with lacquer and gold, highlighting cracks as part of the object''s history.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'English has no official regulating academy; usage and dictionaries co-evolve with speakers.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Emoji are encoded in Unicode as characters; their artwork varies by platform.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Whistled languages like Silbo Gomero transpose speech into whistles to carry over long distances.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Click consonants in some southern African languages are fully fledged speech sounds, not mere paralinguistic clicks.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Pangrams exist in many languages; perfect pangrams use each letter exactly once but are rare and awkward.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Fermented shark "hákarl" in Iceland is traditionally cured to remove toxic ammonia compounds.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Natto''s stringy texture comes from long polymers produced by Bacillus subtilis during fermentation.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Casu marzu is a Sardinian cheese that traditionally contains live insect larvae.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Saffron can cost thousands per kilogram because each flower yields just three stigmas.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Coffee''s crema is an emulsion of oils and CO₂ microbubbles formed under pressure.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The "new book smell" partly comes from lignin breakdown products similar to vanilla.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Crystal glass "sings" when you rub the rim because friction excites a resonant vibration.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Bamboo scaffolding can outperform steel in flexibility and weight for certain construction uses.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Underwater, a duck''s quack echoes — it''s just hard to notice in open spaces.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'A teaspoon of honey is the lifetime work of about 12 bees.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Thixotropic fluids like ketchup get less viscous when shaken or squeezed.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Non-Newtonian cornstarch "oobleck" behaves like a solid under impact and a liquid under slow stress.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Gallium melts in your hand: its melting point is about 29.8°C.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Sodium and potassium can explode on contact with water due to rapid hydrogen generation and heat.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Ferrofluids form spiky patterns in magnetic fields because of surface tension and magnetization forces.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Tide-driven "bores" like China’s Qiantang can send a wall of water upriver against the current.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Glacial isostatic rebound is still raising land in parts of Scandinavia and Canada since the last Ice Age.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Blue holes — deep marine sinkholes — host unique, low-oxygen ecosystems with layered water chemistry.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Magnetite crystals in some animals may aid navigation by sensing Earth’s magnetic field.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Large volcanic eruptions can cool global climate temporarily by injecting aerosols into the stratosphere.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Photolithography prints features on chips smaller than the wavelength of the light used via clever optics and resists.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'3D NAND flash stores data in dozens to hundreds of stacked layers to increase capacity.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Capturing a RAW photo records sensor data with minimal processing, preserving more latitude than JPEG.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'LiDAR measures distance by timing the return of laser pulses — useful for mapping and autonomy.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'High-altitude balloons can circumnavigate Earth by surfing stratospheric wind patterns.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Antikythera mechanism (c. 100 BCE) is an ancient Greek analog computer for predicting celestial events.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'In WWII, "ghost armies" used inflatable tanks and sound deception to mislead enemy reconnaissance.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Voyager''s Golden Records include directions to Earth encoded with pulsar timings and a hydrogen transition.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Ancient Romans used urine (ammonia) as a cleaning agent and in textile processing.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'Emperor penguins were once called "strange geese" by early Antarctic explorers unfamiliar with them.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Neutron stars can spin hundreds of times per second; the fastest known pulsars rotate over 700 times per second.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The Sun''s photosphere has a surface temperature of roughly 5,500°C.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Earth is the densest planet in the solar system.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'Meteorites are rocks from space that survive their fiery passage through Earth’s atmosphere to reach the ground.', GETDATE(), NULL, 0, 0),
(@Cat_Space, N'The term "albedo" describes how much sunlight a surface reflects; fresh snow has a very high albedo.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Graphene is a single layer of carbon atoms arranged in a hexagonal lattice with remarkable strength and conductivity.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Superconductors conduct electricity with zero resistance below a critical temperature.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'An alloy is a mixture of metals (or metal with another element) that often has improved properties.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Catalase is an enzyme that rapidly breaks down hydrogen peroxide into water and oxygen.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Brownian motion is the random movement of particles suspended in a fluid due to molecular collisions.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Loess is a windblown, fine-grained sediment that can create fertile soils.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'An alluvial fan forms where a high-gradient stream flattens, slows, and spreads typically at a mountain front.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Permafrost is ground that remains frozen for two or more consecutive years.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'A drumlin is a streamlined hill formed by glacial ice acting on underlying till.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Geodes are hollow, rounded rocks lined inside with mineral crystals like quartz or amethyst.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The deepest lake by maximum depth is Lake Baikal, reaching about 1,642 meters.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Strait of Malacca is one of the world’s busiest shipping lanes, linking the Indian and Pacific Oceans.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Himalayas help create the South Asian monsoon by blocking and lifting moist air masses.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'Mount Kilimanjaro is a free-standing stratovolcano in Tanzania with multiple ecological zones.', GETDATE(), NULL, 0, 0),
(@Cat_Geography, N'The Great Rift Valley is a vast trench that runs from Lebanon to Mozambique, formed by tectonic rifting.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'The prime number 2 is the only even prime.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'A perfect number equals the sum of its proper divisors; 6 and 28 are classic examples.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'Imaginary numbers involve the square root of −1, denoted i; complex numbers combine real and imaginary parts.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'In base-2 (binary), counting goes 1, 10, 11, 100, 101, and so on.', GETDATE(), NULL, 0, 0),
(@Cat_Math, N'A palindrome number reads the same forwards and backwards, such as 12321.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'White blood cells (leukocytes) are key players in immune defense against pathogens.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Hemostasis is the process that stops bleeding via blood vessel constriction, platelet plug, and coagulation.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Ligaments connect bone to bone, while tendons connect muscle to bone.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Your sense of balance is governed largely by the vestibular system in the inner ear.', GETDATE(), NULL, 0, 0),
(@Cat_Health, N'Circadian rhythms are roughly 24-hour biological cycles influencing sleep and hormone release.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Mechanical sound production in crickets comes from rubbing specialized wings together (stridulation).', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Male lions typically have manes, which may signal health and help in protection during fights.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Narwhals have a long spiral tusk that is an elongated upper left canine tooth.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Barn owls can hunt in near total darkness using highly sensitive hearing and facial discs that funnel sound.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Pronghorns are among the fastest land animals in the Western Hemisphere, adapted for sustained speed.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Stomata are microscopic pores on leaves that regulate gas exchange and water loss.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Xylem transports water and minerals upward; phloem distributes sugars throughout the plant.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Epiphytes like many orchids grow on other plants for support but are not parasitic.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Mangroves tolerate saline conditions and protect shorelines from erosion.', GETDATE(), NULL, 0, 0),
(@Cat_Plants, N'Ginkgo biloba is a living fossil, with a lineage dating back over 200 million years.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Brown rice retains its bran and germ, providing more fiber than white rice.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Umeboshi are Japanese salted, pickled plums known for their sour, salty flavor.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Ciabatta bread was developed in Italy in the 1980s to compete with French baguettes.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Ghee is clarified butter commonly used in South Asian cooking.', GETDATE(), NULL, 0, 0),
(@Cat_FoodDrink, N'Pectin, a soluble fiber in fruit, helps jams set when combined with sugar and acid.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'A hash function maps data to a fixed-size value; cryptographic hashes are designed to be collision-resistant.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'An operating system manages hardware resources and provides common services for programs.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Optical fiber transmits light through total internal reflection for high-bandwidth communication.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Public-key cryptography uses mathematically linked key pairs for encryption and digital signatures.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Error-correcting codes like Hamming codes detect and correct data transmission errors.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Library of Alexandria was an ancient center of scholarship in Egypt.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Bronze Age is named for the widespread use of bronze, an alloy of copper and tin.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Terracotta Army consists of thousands of life-size clay soldiers buried with China’s first emperor.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Inca used a system of knotted cords called quipu for recording information.', GETDATE(), NULL, 0, 0),
(@Cat_History, N'The Code of Justinian was a major compilation of Roman law under the Byzantine Emperor Justinian I.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Pointillism creates images from small dots of color that visually blend from a distance.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Gregorian chant is a form of plainchant used in medieval Western Christian liturgy.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Cubism, pioneered by Picasso and Braque, depicts subjects from multiple viewpoints simultaneously.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Haute couture refers to exclusive, custom-fitted high fashion.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Calligraphy is the art of beautiful handwriting with stylized, expressive lettering.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'An onomatopoeia is a word that imitates a sound, like "buzz" or "clang."', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Loanwords from French heavily entered English after the Norman Conquest of 1066.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'In linguistics, morphology studies word formation and structure.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'An autonym is a community''s own name for itself or its language.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Code-switching is the practice of alternating between languages or dialects in conversation.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Paper cuts hurt because they often occur in areas rich in nerve endings but poor in clotting tissue.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Zip codes in the U.S. were introduced in 1963 to improve mail sorting efficiency.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Airplane contrails are ice crystals forming from water vapor in engine exhaust in cold, moist air aloft.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'The "new car smell" comes from volatile organic compounds released by interior materials.', GETDATE(), NULL, 0, 0),
(@Cat_General, N'Quartz watches keep time using a vibrating quartz crystal driven by an electronic circuit.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Meerkats take turns acting as sentinels to watch for predators while others forage.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'An albatross can sleep while gliding, using dynamic soaring to travel long distances with minimal effort.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Bowerbirds build and decorate elaborate structures to attract mates.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Wolves communicate using howls that can carry for kilometers and coordinate pack activity.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, N'Platypus males have venomous spurs on their hind legs, used primarily in competition.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Diffraction is the bending and spreading of waves around obstacles or through narrow openings.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'An isomer is a compound with the same molecular formula but a different arrangement of atoms.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Polar molecules have uneven charge distribution, leading to dipole interactions.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Capacitance is the ability of a system to store electric charge per unit voltage; its SI unit is the farad.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'Hooke’s law states that, within elastic limits, extension is proportional to force applied.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'An oxbow lake forms when a meandering river cuts off a loop, creating a standalone water body.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Calderas are large volcanic depressions formed after major eruptions empty a magma chamber.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Yardangs are streamlined ridges sculpted by wind erosion in arid regions.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Laterite soils are rich in iron and aluminum, common in tropical regions with intense weathering.', GETDATE(), NULL, 0, 0),
(@Cat_EarthScience, N'Isostasy describes the gravitational equilibrium of Earth’s crust "floating" on the mantle.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Raster images store pixel grids; vector graphics store shapes defined by mathematics.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Lossless compression (e.g., PNG) preserves all data; lossy compression (e.g., JPEG) discards some to save space.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'A checksum is a value used to verify data integrity after storage or transmission.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Firmware is software embedded in hardware devices, providing low-level control.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, N'Latency is the delay before a transfer of data begins following an instruction; bandwidth is the rate of transfer.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Perspective in art creates the illusion of depth on a flat surface using vanishing points and horizon lines.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'The sonnet is a 14-line poem form with various rhyme schemes such as Shakespearean and Petrarchan.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Ballet originated in Italian Renaissance courts and later developed in France and Russia.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Ceramic glazes vitrify in a kiln, creating glossy, colored, and often waterproof surfaces.', GETDATE(), NULL, 0, 0),
(@Cat_ArtsCulture, N'Color temperature describes the hue of light sources; higher Kelvin values appear "cooler" and bluer.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'A homograph is a word that is spelled the same as another but may differ in pronunciation and meaning.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Phonetics studies the physical sounds of human speech; phonology examines their abstract patterns.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'Etymology investigates the origins and historical development of words.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'A rhetorical question is asked to make a point rather than to elicit an answer.', GETDATE(), NULL, 0, 0),
(@Cat_Language, N'A portmanteau blends parts of two words, like "smog" from smoke and fog.', GETDATE(), NULL, 0, 0),
(@Cat_Health, 'The human brain uses about 20% of the body''s total energy despite being only 2% of body weight.', GETDATE(), NULL, 0, 0),
(@Cat_Science, 'Water expands by about 9% when it freezes, which is why ice floats on water.', GETDATE(), NULL, 0, 0),
(@Cat_General, 'The Great Wall of China is not visible from space without aid, contrary to popular belief.', GETDATE(), NULL, 0, 0),
(@Cat_Tech, 'The first computer bug was an actual moth found in a Harvard Mark II computer in 1947.', GETDATE(), NULL, 0, 0),
(@Cat_Animals, 'Octopuses have three hearts and blue blood.', GETDATE(), NULL, 0, 0),
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
(@Cat_ArtsCulture, N'Primary colors for additive light mixing are red, green, and blue.', GETDATE(), NULL, 0, 0),
(@Cat_Science, N'If you could compress the Earth to the size of a marble, it would become a black hole due to its immense density.', GETDATE(), NULL, 0, 0);
GO

-- Step 14: Initialize GamificationProfile with a single row
INSERT INTO GamificationProfile (XP, Level)
VALUES (0, 1);
GO

-- Step 15: Insert achievement definitions
;WITH Seeds (Code, Name, Category, Threshold, RewardXP) AS (
    -- Known facts achievements
    SELECT 'KNOWN_5','Know 5 facts','known',5,10 UNION ALL
    SELECT 'KNOWN_10','Know 10 facts','known',10,15 UNION ALL
    SELECT 'KNOWN_50','Know 50 facts','known',50,25 UNION ALL
    SELECT 'KNOWN_100','Know 100 facts','known',100,50 UNION ALL
    SELECT 'KNOWN_300','Know 300 facts','known',300,100 UNION ALL
    SELECT 'KNOWN_500','Know 500 facts','known',500,150 UNION ALL
    SELECT 'KNOWN_1000','Know 1000 facts','known',1000,250 UNION ALL
    SELECT 'KNOWN_5000','Know 5000 facts','known',5000,600 UNION ALL
    SELECT 'KNOWN_10000','Know 10000 facts','known',10000,1000 UNION ALL
    SELECT 'KNOWN_30000','Know 30000 facts','known',30000,2500 UNION ALL
    SELECT 'KNOWN_50000','Know 50000 facts','known',50000,4000 UNION ALL
    SELECT 'KNOWN_100000','Know 100000 facts','known',100000,7000 UNION ALL
    -- Favorite facts achievements
    SELECT 'FAV_5','Favorite 5 facts','favorites',5,5 UNION ALL
    SELECT 'FAV_10','Favorite 10 facts','favorites',10,10 UNION ALL
    SELECT 'FAV_50','Favorite 50 facts','favorites',50,20 UNION ALL
    SELECT 'FAV_100','Favorite 100 facts','favorites',100,40 UNION ALL
    SELECT 'FAV_300','Favorite 300 facts','favorites',300,80 UNION ALL
    SELECT 'FAV_500','Favorite 500 facts','favorites',500,120 UNION ALL
    SELECT 'FAV_1000','Favorite 1000 facts','favorites',1000,200 UNION ALL
    SELECT 'FAV_5000','Favorite 5000 facts','favorites',5000,500 UNION ALL
    SELECT 'FAV_10000','Favorite 10000 facts','favorites',10000,900 UNION ALL
    SELECT 'FAV_30000','Favorite 30000 facts','favorites',30000,2200 UNION ALL
    SELECT 'FAV_50000','Favorite 50000 facts','favorites',50000,3500 UNION ALL
    SELECT 'FAV_100000','Favorite 100000 facts','favorites',100000,6000 UNION ALL
    -- Review achievements
    SELECT 'REV_5','Review 5 times','reviews',5,10 UNION ALL
    SELECT 'REV_10','Review 10 times','reviews',10,15 UNION ALL
    SELECT 'REV_50','Review 50 times','reviews',50,25 UNION ALL
    SELECT 'REV_100','Review 100 times','reviews',100,50 UNION ALL
    SELECT 'REV_300','Review 300 times','reviews',300,100 UNION ALL
    SELECT 'REV_500','Review 500 times','reviews',500,150 UNION ALL
    SELECT 'REV_1000','Review 1000 times','reviews',1000,250 UNION ALL
    SELECT 'REV_5000','Review 5000 times','reviews',5000,600 UNION ALL
    SELECT 'REV_10000','Review 10000 times','reviews',10000,1000 UNION ALL
    SELECT 'REV_30000','Review 30000 times','reviews',30000,2500 UNION ALL
    SELECT 'REV_50000','Review 50000 times','reviews',50000,4000 UNION ALL
    SELECT 'REV_100000','Review 100000 times','reviews',100000,7000 UNION ALL
    -- Add facts achievements
    SELECT 'ADD_5','Add 5 facts','adds',5,10 UNION ALL
    SELECT 'ADD_10','Add 10 facts','adds',10,15 UNION ALL
    SELECT 'ADD_50','Add 50 facts','adds',50,25 UNION ALL
    SELECT 'ADD_100','Add 100 facts','adds',100,50 UNION ALL
    SELECT 'ADD_300','Add 300 facts','adds',300,100 UNION ALL
    SELECT 'ADD_500','Add 500 facts','adds',500,150 UNION ALL
    SELECT 'ADD_1000','Add 1000 facts','adds',1000,250 UNION ALL
    SELECT 'ADD_5000','Add 5000 facts','adds',5000,600 UNION ALL
    SELECT 'ADD_10000','Add 10000 facts','adds',10000,1000 UNION ALL
    SELECT 'ADD_30000','Add 30000 facts','adds',30000,2500 UNION ALL
    SELECT 'ADD_50000','Add 50000 facts','adds',50000,4000 UNION ALL
    SELECT 'ADD_100000','Add 100000 facts','adds',100000,7000 UNION ALL
    -- Edit facts achievements
    SELECT 'EDIT_5','Edit 5 facts','edits',5,10 UNION ALL
    SELECT 'EDIT_10','Edit 10 facts','edits',10,15 UNION ALL
    SELECT 'EDIT_50','Edit 50 facts','edits',50,25 UNION ALL
    SELECT 'EDIT_100','Edit 100 facts','edits',100,50 UNION ALL
    SELECT 'EDIT_300','Edit 300 facts','edits',300,100 UNION ALL
    SELECT 'EDIT_500','Edit 500 facts','edits',500,150 UNION ALL
    SELECT 'EDIT_1000','Edit 1000 facts','edits',1000,250 UNION ALL
    SELECT 'EDIT_5000','Edit 5000 facts','edits',5000,600 UNION ALL
    SELECT 'EDIT_10000','Edit 10000 facts','edits',10000,1000 UNION ALL
    SELECT 'EDIT_30000','Edit 30000 facts','edits',30000,2500 UNION ALL
    SELECT 'EDIT_50000','Edit 50000 facts','edits',50000,4000 UNION ALL
    SELECT 'EDIT_100000','Edit 100000 facts','edits',100000,7000 UNION ALL
    -- Delete facts achievements
    SELECT 'DEL_5','Delete 5 facts','deletes',5,10 UNION ALL
    SELECT 'DEL_10','Delete 10 facts','deletes',10,15 UNION ALL
    SELECT 'DEL_50','Delete 50 facts','deletes',50,25 UNION ALL
    SELECT 'DEL_100','Delete 100 facts','deletes',100,50 UNION ALL
    SELECT 'DEL_300','Delete 300 facts','deletes',300,100 UNION ALL
    SELECT 'DEL_500','Delete 500 facts','deletes',500,150 UNION ALL
    SELECT 'DEL_1000','Delete 1000 facts','deletes',1000,250 UNION ALL
    SELECT 'DEL_5000','Delete 5000 facts','deletes',5000,600 UNION ALL
    SELECT 'DEL_10000','Delete 10000 facts','deletes',10000,1000 UNION ALL
    SELECT 'DEL_30000','Delete 30000 facts','deletes',30000,2500 UNION ALL
    SELECT 'DEL_50000','Delete 50000 facts','deletes',50000,4000 UNION ALL
    SELECT 'DEL_100000','Delete 100000 facts','deletes',100000,7000 UNION ALL
    -- Streak achievements (consecutive daily check-ins)
    SELECT 'STREAK_3','3-day review streak','streak',3,10 UNION ALL
    SELECT 'STREAK_7','7-day review streak','streak',7,20 UNION ALL
    SELECT 'STREAK_14','14-day review streak','streak',14,35 UNION ALL
    SELECT 'STREAK_30','30-day review streak','streak',30,75 UNION ALL
    SELECT 'STREAK_60','60-day review streak','streak',60,150 UNION ALL
    SELECT 'STREAK_90','90-day review streak','streak',90,250 UNION ALL
    SELECT 'STREAK_180','180-day review streak','streak',180,500 UNION ALL
    SELECT 'STREAK_365','365-day review streak','streak',365,1000
)
INSERT INTO Achievements (Code, Name, Category, Threshold, RewardXP, IsHidden, CreatedDate)
SELECT s.Code, s.Name, s.Category, s.Threshold, s.RewardXP, 0, GETDATE()
FROM Seeds s
LEFT JOIN Achievements a ON a.Code = s.Code
WHERE a.AchievementID IS NULL;
GO

-- Step 16: Verify the setup
SELECT 'Categories' AS TableName, COUNT(*) AS RecordCount FROM Categories
UNION ALL SELECT 'Facts', COUNT(*) FROM Facts
UNION ALL SELECT 'ReviewLogs', COUNT(*) FROM ReviewLogs
UNION ALL SELECT 'ReviewSessions', COUNT(*) FROM ReviewSessions
UNION ALL SELECT 'GamificationProfile', COUNT(*) FROM GamificationProfile
UNION ALL SELECT 'Achievements', COUNT(*) FROM Achievements
UNION ALL SELECT 'AchievementUnlocks', COUNT(*) FROM AchievementUnlocks;
