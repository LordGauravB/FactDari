-- Step 0: Switch to master to perform database operations
USE master;
GO

-- Step 1: Drop FactDari if it exists (Hard Reset)
IF DB_ID('FactDari') IS NOT NULL
BEGIN
    -- Kick out any active connections immediately so we can drop it
    ALTER DATABASE FactDari SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE FactDari;
END
GO

-- Step 2: Create the Database
CREATE DATABASE FactDari;
GO
USE FactDari;
GO

-- Step 3: Drop tables if they exist (order matters due to FKs)
IF OBJECT_ID('AchievementUnlocks', 'U') IS NOT NULL DROP TABLE AchievementUnlocks;
IF OBJECT_ID('AIUsageLogs', 'U') IS NOT NULL DROP TABLE AIUsageLogs;
IF OBJECT_ID('ReviewLogs', 'U') IS NOT NULL DROP TABLE ReviewLogs;
IF OBJECT_ID('ReviewSessions', 'U') IS NOT NULL DROP TABLE ReviewSessions;
IF OBJECT_ID('ProfileFacts', 'U') IS NOT NULL DROP TABLE ProfileFacts;
IF OBJECT_ID('Achievements', 'U') IS NOT NULL DROP TABLE Achievements;
IF OBJECT_ID('Facts', 'U') IS NOT NULL DROP TABLE Facts;
IF OBJECT_ID('Categories', 'U') IS NOT NULL DROP TABLE Categories;
IF OBJECT_ID('GamificationProfile', 'U') IS NOT NULL DROP TABLE GamificationProfile;
GO

-- Step 4: Create GamificationProfile table (user identity and lifetime counters)
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
    TotalAITokens INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalAITokens DEFAULT 0,
    TotalAICost DECIMAL(19,9) NOT NULL CONSTRAINT DF_GamificationProfile_TotalAICost DEFAULT 0,
    CurrentStreak INT NOT NULL CONSTRAINT DF_GamificationProfile_CurrentStreak DEFAULT 0,
    LongestStreak INT NOT NULL CONSTRAINT DF_GamificationProfile_LongestStreak DEFAULT 0,
    LastCheckinDate DATE NULL
);

-- Step 5: Create Categories table
CREATE TABLE Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(255),
    IsActive BIT NOT NULL CONSTRAINT DF_Categories_IsActive DEFAULT 1,
    CreatedDate DATETIME NOT NULL CONSTRAINT DF_Categories_CreatedDate DEFAULT GETDATE(),
    CreatedBy INT NOT NULL CONSTRAINT DF_Categories_CreatedBy DEFAULT 1
        CONSTRAINT FK_Categories_CreatedBy REFERENCES GamificationProfile(ProfileID)
);

-- Step 6: Create Facts table (no tag linkage)
CREATE TABLE Facts (
    FactID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryID INT NOT NULL
        CONSTRAINT FK_Facts_Categories
        REFERENCES Categories(CategoryID),
    Content NVARCHAR(MAX) NOT NULL,
    DateAdded DATE NOT NULL CONSTRAINT DF_Facts_DateAdded DEFAULT GETDATE(),
    TotalViews INT NOT NULL CONSTRAINT DF_Facts_TotalViews DEFAULT 0,
    CreatedBy INT NOT NULL CONSTRAINT DF_Facts_CreatedBy DEFAULT 1
        CONSTRAINT FK_Facts_CreatedBy REFERENCES GamificationProfile(ProfileID)
);

-- Step 7: Create ProfileFacts table (per-profile state for facts)
CREATE TABLE ProfileFacts (
    ProfileFactID INT IDENTITY(1,1) PRIMARY KEY,
    ProfileID INT NOT NULL
        CONSTRAINT FK_ProfileFacts_Profile
        REFERENCES GamificationProfile(ProfileID),
    FactID INT NOT NULL
        CONSTRAINT FK_ProfileFacts_Fact
        REFERENCES Facts(FactID) ON DELETE CASCADE,
    PersonalReviewCount INT NOT NULL CONSTRAINT DF_ProfileFacts_PersonalReviewCount DEFAULT 0,
    IsFavorite BIT NOT NULL CONSTRAINT DF_ProfileFacts_IsFavorite DEFAULT 0,
    IsEasy BIT NOT NULL CONSTRAINT DF_ProfileFacts_IsEasy DEFAULT 0,
    LastViewedByUser DATETIME NULL,
    KnownSince DATETIME NULL,
    CONSTRAINT UX_ProfileFacts_Profile_Fact UNIQUE (ProfileID, FactID)
);
CREATE INDEX IX_ProfileFacts_ProfileID ON ProfileFacts(ProfileID);
CREATE INDEX IX_ProfileFacts_FactID ON ProfileFacts(FactID);

-- Step 8: Create ReviewSessions table (for full session tracking)
CREATE TABLE ReviewSessions (
    SessionID INT IDENTITY(1,1) PRIMARY KEY,
    ProfileID INT NOT NULL CONSTRAINT DF_ReviewSessions_ProfileID DEFAULT 1,
    StartTime DATETIME NOT NULL,
    EndTime DATETIME NULL,
    DurationSeconds INT NULL,
    TimedOut BIT NOT NULL CONSTRAINT DF_ReviewSessions_TimedOut DEFAULT 0,
    -- Per-session action counters
    FactsAdded INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsAdded DEFAULT 0,
    FactsEdited INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsEdited DEFAULT 0,
    FactsDeleted INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsDeleted DEFAULT 0,
    CONSTRAINT FK_ReviewSessions_Profile
        FOREIGN KEY (ProfileID) REFERENCES GamificationProfile(ProfileID)
);

-- Step 9: Create ReviewLogs table with per-view duration and optional session link
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

-- Step 10: Create AIUsageLogs table to track AI spend per fact/session and profile
CREATE TABLE AIUsageLogs (
    AIUsageID INT IDENTITY(1,1) PRIMARY KEY,
    FactID INT NULL,
    SessionID INT NULL,
    ProfileID INT NOT NULL CONSTRAINT DF_AIUsageLogs_ProfileID DEFAULT 1,
    OperationType NVARCHAR(32) NOT NULL CONSTRAINT DF_AIUsageLogs_OperationType DEFAULT 'EXPLANATION', -- EXPLANATION | TRANSLATION | IMAGE_GEN | etc.
    Status NVARCHAR(16) NOT NULL CONSTRAINT DF_AIUsageLogs_Status DEFAULT 'SUCCESS', -- SUCCESS | FAILED
    ModelName NVARCHAR(200) NULL,
    Provider NVARCHAR(100) NULL,
    InputTokens INT NULL,
    OutputTokens INT NULL,
    TotalTokens AS (ISNULL(InputTokens, 0) + ISNULL(OutputTokens, 0)) PERSISTED,
    Cost DECIMAL(19,9) NULL, -- store USD equivalent cost for the call
    CurrencyCode CHAR(3) NOT NULL CONSTRAINT DF_AIUsageLogs_CurrencyCode DEFAULT 'USD',
    LatencyMs INT NULL,
    ReadingDurationSec INT NOT NULL CONSTRAINT DF_AIUsageLogs_ReadingDurationSec DEFAULT 0, -- time user spent reading AI output (seconds)
    CreatedAt DATETIME NOT NULL CONSTRAINT DF_AIUsageLogs_CreatedAt DEFAULT GETDATE(),
    CONSTRAINT FK_AIUsageLogs_Facts FOREIGN KEY (FactID)
        REFERENCES Facts(FactID) ON DELETE SET NULL,
    CONSTRAINT FK_AIUsageLogs_Profile FOREIGN KEY (ProfileID)
        REFERENCES GamificationProfile(ProfileID),
    CONSTRAINT FK_AIUsageLogs_ReviewSessions FOREIGN KEY (SessionID)
        REFERENCES ReviewSessions(SessionID) ON DELETE SET NULL
);

-- Step 11: Create Achievements table (catalog of all possible achievements)
CREATE TABLE Achievements (
    AchievementID INT IDENTITY(1,1) PRIMARY KEY,
    Code NVARCHAR(64) NOT NULL UNIQUE,
    Name NVARCHAR(200) NOT NULL,
    Category NVARCHAR(32) NOT NULL,
    Threshold INT NOT NULL,
    RewardXP INT NOT NULL,
    CreatedDate DATETIME NOT NULL CONSTRAINT DF_Achievements_CreatedDate DEFAULT GETDATE()
);

-- Step 12: Create AchievementUnlocks table (tracks which achievements have been earned)
CREATE TABLE AchievementUnlocks (
    UnlockID INT IDENTITY(1,1) PRIMARY KEY,
    AchievementID INT NOT NULL
        CONSTRAINT FK_AchievementUnlocks_Achievements
        REFERENCES Achievements(AchievementID),
    ProfileID INT NOT NULL CONSTRAINT DF_AchievementUnlocks_ProfileID DEFAULT 1,
    UnlockDate DATETIME NOT NULL CONSTRAINT DF_AchievementUnlocks_UnlockDate DEFAULT GETDATE(),
    Notified BIT NOT NULL CONSTRAINT DF_AchievementUnlocks_Notified DEFAULT 0,
    CONSTRAINT FK_AchievementUnlocks_Profile
        FOREIGN KEY (ProfileID) REFERENCES GamificationProfile(ProfileID)
);

-- Create unique index to ensure each achievement can only be unlocked once per profile
CREATE UNIQUE INDEX UX_AchievementUnlocks_Profile_Achievement ON AchievementUnlocks(ProfileID, AchievementID);

-- Helpful indexes for app queries
CREATE INDEX IX_Facts_CategoryID ON Facts(CategoryID);
CREATE INDEX IX_ReviewSessions_ProfileID ON ReviewSessions(ProfileID);
CREATE INDEX IX_ReviewLogs_FactID ON ReviewLogs(FactID);
CREATE INDEX IX_ReviewLogs_ReviewDate ON ReviewLogs(ReviewDate);
CREATE INDEX IX_ReviewLogs_SessionID ON ReviewLogs(SessionID);
CREATE INDEX IX_AIUsageLogs_FactID ON AIUsageLogs(FactID);
CREATE INDEX IX_AIUsageLogs_SessionID ON AIUsageLogs(SessionID);
CREATE INDEX IX_AIUsageLogs_ProfileID ON AIUsageLogs(ProfileID);
CREATE INDEX IX_AIUsageLogs_CreatedAt ON AIUsageLogs(CreatedAt);
GO

-- Seed default profile (ProfileID = 1) before inserting categories/facts
IF NOT EXISTS (SELECT 1 FROM GamificationProfile)
BEGIN
    INSERT INTO GamificationProfile (XP, Level)
    VALUES (0, 1);
END;
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

-- Step 12: Insert expanded categories
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

-- Step 13: Cache category IDs for readable inserts
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


-- Step 14:  Insert Facts
INSERT INTO Facts (CategoryID, Content, DateAdded, TotalViews, CreatedBy)
VALUES
(@Cat_General, N'Ada Lovelace''s 1843 notes described a general-purpose algorithm for Babbage''s engine — she''s often called the first computer programmer.', GETDATE(), 0, 1),
(@Cat_General, N'The word “algorithm” traces to the mathematician al-Khwarizmi; medieval Latin renderings of his name became “algorismus/algorithmus.”', GETDATE(), 0, 1),
(@Cat_General, N'The first adhesive postage stamp was Britain''s Penny Black, issued in 1840.', GETDATE(), 0, 1),
(@Cat_General, N'A-series paper sizes (A0, A1, A2… A4) keep the same √2 aspect ratio; A4 is 210×297 mm.', GETDATE(), 0, 1),
(@Cat_General, N'Post-it Notes resulted from pairing a very weak, pressure-sensitive adhesive with paper — a “failed” super-glue turned useful.', GETDATE(), 0, 1),
(@Cat_General, N'The Statue of Liberty''s green color is a patina on thin copper sheets (about 2–3 mm) over an iron frame.', GETDATE(), 0, 1),
(@Cat_General, N'The 1883 Krakatoa eruption was so loud pressure waves circled the Earth multiple times.', GETDATE(), 0, 1),
(@Cat_General, N'In a double rainbow the secondary arc has its colors reversed compared with the primary.', GETDATE(), 0, 1),
(@Cat_General, N'The sky appears blue due to Rayleigh scattering; at sunset longer paths through air scatter blue away, leaving reds and oranges.', GETDATE(), 0, 1),
(@Cat_General, N'Magenta isn’t a single-wavelength spectral color; it''s a perception from the brain bridging red and violet.', GETDATE(), 0, 1),
(@Cat_General, N'Polarized sunglasses cut glare by filtering horizontally polarized light reflected from water, roads, and snow.', GETDATE(), 0, 1),
(@Cat_General, N'Jet lag often feels worse when flying east because most human body clocks naturally run slightly longer than 24 hours.', GETDATE(), 0, 1),
(@Cat_General, N'Microwave ovens commonly operate around 2.45 GHz and heat food by dielectric losses in polar molecules like water.', GETDATE(), 0, 1),
(@Cat_General, N'“Wi-Fi” is a coined brand name — it does not literally stand for “wireless fidelity.”', GETDATE(), 0, 1),
(@Cat_General, N'Credit-card numbers include a Luhn checksum digit to catch common entry errors.', GETDATE(), 0, 1),
(@Cat_General, N'The metre is defined via the speed of light: the distance light travels in vacuum in 1/299,792,458 of a second.', GETDATE(), 0, 1),
(@Cat_General, N'On standard dice, opposite faces sum to seven (1–6, 2–5, 3–4).', GETDATE(), 0, 1),
(@Cat_General, N'Eight perfect “out-shuffles” of a 52-card deck return it to original order.', GETDATE(), 0, 1),
(@Cat_General, N'Vikings did not wear horned helmets; that image comes from 19th-century opera costumes.', GETDATE(), 0, 1),
(@Cat_General, N'Bulls are dichromats; it''s the movement of the cape, not the red color, that provokes them.', GETDATE(), 0, 1),
(@Cat_General, N'“Venomous” means an animal injects toxin (e.g., via fangs or stingers); “poisonous” means toxin is harmful if eaten or touched.', GETDATE(), 0, 1),
(@Cat_General, N'The largest organism by area may be an Armillaria “humongous fungus” spanning several square kilometers in Oregon.', GETDATE(), 0, 1),
(@Cat_General, N'AM and PM stand for ante meridiem and post meridiem — before and after midday.', GETDATE(), 0, 1),
(@Cat_General, N'Many Arabic scripts are written right-to-left, but numerals are typically written left-to-right.', GETDATE(), 0, 1),
(@Cat_General, N'The $ symbol likely evolved from a ligature of “PS,” an abbreviation for the Spanish peso.', GETDATE(), 0, 1),
(@Cat_General, N'“Big Ben” is actually the nickname of the Great Bell; the tower is officially Elizabeth Tower.', GETDATE(), 0, 1),
(@Cat_General, N'“OK” gained popularity in 1839 from a newspaper joke about “oll korrect”; its exact origin has multiple tales.', GETDATE(), 0, 1),
(@Cat_General, N'The alphabet used in English descends from the Phoenician script via Greek and Latin, with Greek adding explicit vowels.', GETDATE(), 0, 1),
(@Cat_General, N'Lunisolar calendars add leap months because twelve lunar months are about 11 days shorter than a solar year.', GETDATE(), 0, 1),
(@Cat_General, N'The Gregorian calendar (1582) refined leap-year rules to correct drift; countries adopted it at different times.', GETDATE(), 0, 1),
(@Cat_General, N'Many clock faces use IIII instead of IV for 4, for visual symmetry and tradition.', GETDATE(), 0, 1),
(@Cat_General, N'Mandarin Chinese has the largest number of native speakers of any language.', GETDATE(), 0, 1),
(@Cat_General, N'In chess setup, each queen starts on a square of her own color — “queen on her color.”', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Baking powder is often double‑acting: one reaction when wet, another in oven heat.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Honey is not recommended for infants under one year due to botulism risk.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Cooked rice should be cooled quickly and kept cold to avoid Bacillus cereus growth before reheating.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Best‑before indicates quality; use‑by indicates safety—heed use‑by dates on perishable foods.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Adding salt early draws out moisture in vegetables (osmosis) and deepens flavour integration.', GETDATE(), 0, 1),
(@Cat_Space, N'Trojan asteroids share a planet’s orbit at the stable L4 and L5 points; Jupiter hosts vast swarms.', GETDATE(), 0, 1),
(@Cat_Space, N'The radial‑velocity method detects exoplanets by stellar Doppler shifts from gravitational wobbles.', GETDATE(), 0, 1),
(@Cat_Space, N'Transit timing variations (TTVs) can uncover additional planets in multi‑planet systems.', GETDATE(), 0, 1),
(@Cat_Space, N'Enceladus vents water‑rich plumes that feed Saturn’s E ring and contain salts and organics.', GETDATE(), 0, 1),
(@Cat_Space, N'Comets have two main tails: a straight ion tail and a curved dust tail; both point generally away from the Sun.', GETDATE(), 0, 1),
(@Cat_Space, N'Asteroids are mostly rocky/metallic; comets contain more ices and develop comae/tails when heated.', GETDATE(), 0, 1),
(@Cat_DIY, N'Clean a washing machine: run a hot empty cycle with white vinegar, wipe the door gasket and clean the filter.', GETDATE(), 0, 1),
(@Cat_DIY, N'Deep‑clean a dishwasher: place a cup of vinegar on the top rack and run hot; clear food from the filter and spray arms.', GETDATE(), 0, 1),
(@Cat_DIY, N'Chill wine without dilution by using frozen grapes as ice cubes.', GETDATE(), 0, 1),
(@Cat_DIY, N'Improve radiator efficiency by placing reflective foil behind it (do not cover vents).', GETDATE(), 0, 1),
(@Cat_DIY, N'Clean window tracks with an old toothbrush and vacuum; finish with cotton buds and mild cleaner.', GETDATE(), 0, 1),
(@Cat_DIY, N'Wash a mildewed shower curtain with baking soda and a few towels for scrubbing action, then rinse with vinegar.', GETDATE(), 0, 1),
(@Cat_Tech, N'HTTP caching uses Cache‑Control, ETag, and Last‑Modified headers for freshness and validation.', GETDATE(), 0, 1),
(@Cat_Tech, N'Idempotency keys in APIs prevent duplicate effects when clients retry requests.', GETDATE(), 0, 1),
(@Cat_Science, N'In 2015, LIGO made the first direct detection of gravitational waves from merging black holes.', GETDATE(), 0, 1),
(@Cat_Science, N'Photosynthesis releases oxygen by splitting water in the light reactions, not from CO₂.', GETDATE(), 0, 1),
(@Cat_Science, N'An acid’s strength is quantified by pKₐ; a lower pKₐ indicates a stronger acid.', GETDATE(), 0, 1),
(@Cat_Science, N'Isotopes are atoms with the same number of protons but different numbers of neutrons.', GETDATE(), 0, 1),
(@Cat_Science, N'Sound travels faster in liquids and solids than in gases because particles are closer together.', GETDATE(), 0, 1),
(@Cat_Science, N'Human stomach acid typically has a pH between about 1 and 3.', GETDATE(), 0, 1),
(@Cat_Science, N'DNA repair pathways such as mismatch repair and nucleotide excision repair fix many errors.', GETDATE(), 0, 1),
(@Cat_Science, N'Kepler’s first law: planets orbit the Sun in ellipses with the Sun at one focus.', GETDATE(), 0, 1),
(@Cat_Science, N'Earth’s ocean tides arise mainly from the Moon’s gravity producing differential forces.', GETDATE(), 0, 1),
(@Cat_Science, N'Bird lungs use air sacs for near-unidirectional airflow, enabling efficient gas exchange.', GETDATE(), 0, 1),
(@Cat_Science, N'When CO₂ dissolves in water it forms carbonic acid, an important buffer in blood chemistry.', GETDATE(), 0, 1),
(@Cat_Science, N'Antibiotics target bacterial-specific processes (e.g., cell walls, 70S ribosomes).', GETDATE(), 0, 1),
(@Cat_Tech, N'DNS resolves domain names to IP addresses using a distributed, cached hierarchy of name servers.', GETDATE(), 0, 1),
(@Cat_Tech, N'IPv6 uses 128-bit addresses, vastly expanding the address space beyond IPv4’s 32-bit limits.', GETDATE(), 0, 1),
(@Cat_Tech, N'CI/CD pipelines automate building, testing, and deploying changes for faster, safer releases.', GETDATE(), 0, 1),
(@Cat_Tech, N'The CAP theorem: in the presence of partitions, a system must choose between strong consistency and availability.', GETDATE(), 0, 1),
(@Cat_Tech, N'ACID transactions ensure atomicity, consistency, isolation, and durability in databases.', GETDATE(), 0, 1),
(@Cat_Tech, N'Idempotent API operations can be retried safely because repeated calls produce the same effect.', GETDATE(), 0, 1),
(@Cat_Tech, N'Indexes (e.g., B-trees) accelerate reads at the cost of extra storage and slower writes/updates.', GETDATE(), 0, 1),
(@Cat_Tech, N'MapReduce models large-scale data processing as parallel map and reduce phases.', GETDATE(), 0, 1),
(@Cat_Tech, N'Inverted indexes map terms to posting lists of documents and power full-text search.', GETDATE(), 0, 1),
(@Cat_Tech, N'UTF-8 encodes Unicode in one to four bytes and is backward-compatible with ASCII.', GETDATE(), 0, 1),
(@Cat_Tech, N'WebSockets enable full-duplex communication between browsers and servers over a single TCP connection.', GETDATE(), 0, 1),
(@Cat_Tech, N'GraphQL lets clients request precisely the fields they need in a single query against a schema.', GETDATE(), 0, 1),
(@Cat_Tech, N'SSD controllers perform wear leveling and garbage collection to extend flash lifespan.', GETDATE(), 0, 1),
(@Cat_Tech, N'RAID 1 mirrors data; RAID 5 stripes with parity; RAID 0 stripes without redundancy.', GETDATE(), 0, 1),
(@Cat_Tech, N'GPUs excel at data-parallel workloads with thousands of simple cores and high memory bandwidth.', GETDATE(), 0, 1),
(@Cat_Tech, N'Bluetooth Low Energy targets short-range, low-power links; Wi‑Fi targets higher bandwidth and range.', GETDATE(), 0, 1),
(@Cat_Tech, N'Edge computing processes data near its source to reduce latency and bandwidth usage.', GETDATE(), 0, 1),
(@Cat_Tech, N'WebAssembly executes near-native code in the browser for performance-critical components.', GETDATE(), 0, 1),
(@Cat_Tech, N'Zero-knowledge proofs let someone prove a statement is true without revealing the secret itself.', GETDATE(), 0, 1),
(@Cat_Tech, N'Homomorphic encryption allows computations to be performed directly on encrypted data.', GETDATE(), 0, 1),
(@Cat_Tech, N'Hash tables map keys to buckets via a hash function to achieve average O(1) lookups.', GETDATE(), 0, 1),
(@Cat_Tech, N'Distributed ledgers use consensus and cryptography to order transactions without a central clock.', GETDATE(), 0, 1),
(@Cat_Tech, N'Feature stores maintain curated ML features for consistent training and real-time serving.', GETDATE(), 0, 1),
(@Cat_Tech, N'Vector databases index embeddings for approximate nearest-neighbor similarity search.', GETDATE(), 0, 1),
(@Cat_Tech, N'Dynamic voltage and frequency scaling (DVFS) reduces CPU/GPU power use during light workloads.', GETDATE(), 0, 1),
(@Cat_Animals, N'Mantis shrimp strikes reach extreme accelerations and create cavitation shockwaves that can stun prey.', GETDATE(), 0, 1),
(@Cat_Animals, N'Elephants pass the mirror self-recognition test and have rituals around death.', GETDATE(), 0, 1),
(@Cat_Animals, N'The blue-ringed octopus carries tetrodotoxin potent enough to paralyze humans.', GETDATE(), 0, 1),
(@Cat_Animals, N'Three-toed sloths descend about once a week to defecate at the base of their tree.', GETDATE(), 0, 1),
(@Cat_Animals, N'Giraffes have specialized valves and tight leg skin to manage extremely high blood pressure.', GETDATE(), 0, 1),
(@Cat_Animals, N'Electric eels can deliver discharges over 600 volts to stun prey and deter threats.', GETDATE(), 0, 1),
(@Cat_Animals, N'Some sea snakes drink rain-formed freshwater lenses that briefly sit atop seawater.', GETDATE(), 0, 1),
(@Cat_Animals, N'Owls fly quietly due to serrated wing edges and velvety feathers that damp turbulence.', GETDATE(), 0, 1),
(@Cat_Animals, N'The star-nosed mole can identify prey in as little as 20 milliseconds.', GETDATE(), 0, 1),
(@Cat_Animals, N'Homing pigeons use multiple cues, including smell and Earth’s magnetic field.', GETDATE(), 0, 1),
(@Cat_Animals, N'Poison dart frogs acquire skin toxins from a specialized arthropod diet.', GETDATE(), 0, 1),
(@Cat_Animals, N'Komodo dragons have venom glands that affect blood clotting and blood pressure.', GETDATE(), 0, 1),
(@Cat_Animals, N'Naked mole-rats are eusocial mammals with a single breeding queen and unusual pain insensitivity.', GETDATE(), 0, 1),
(@Cat_Animals, N'Seahorses can move their eyes independently and snap prey with elastic-powered heads.', GETDATE(), 0, 1),
(@Cat_Animals, N'In many deep-sea anglerfish, tiny males fuse to females and become permanent mates.', GETDATE(), 0, 1),
(@Cat_Animals, N'Sea otters sometimes hold paws while resting to avoid drifting apart.', GETDATE(), 0, 1),
(@Cat_Animals, N'African grey parrots can learn large vocabularies and show concept learning.', GETDATE(), 0, 1),
(@Cat_Animals, N'Leaf-tailed geckos use extreme camouflage that mimics leaves, bark, and even moss.', GETDATE(), 0, 1),
(@Cat_Animals, N'Ant pheromone trails self-reinforce, guiding colonies along the shortest routes to food.', GETDATE(), 0, 1),
(@Cat_Animals, N'Polar bear fur is hollow and translucent while their skin is black to absorb heat.', GETDATE(), 0, 1),
(@Cat_Animals, N'Reindeer eyes shift from gold in summer to blue in winter to suit Arctic light levels.', GETDATE(), 0, 1),
(@Cat_Animals, N'Flamingos turn pink from carotenoids in algae and crustaceans they eat.', GETDATE(), 0, 1),
(@Cat_Animals, N'Many crabs can shed a limb to escape and later regenerate it.', GETDATE(), 0, 1),
(@Cat_Animals, N'Praying mantises can rotate their heads and have a single ultrasound-sensitive ear on the chest.', GETDATE(), 0, 1),
(@Cat_Animals, N'Cat purrs span roughly 25–150 Hz and may aid bone and tissue healing.', GETDATE(), 0, 1),
(@Cat_Animals, N'A dog’s nose print is unique enough to identify an individual.', GETDATE(), 0, 1),
(@Cat_Animals, N'Dolphins and some whales sleep with one brain hemisphere at a time.', GETDATE(), 0, 1),
(@Cat_Animals, N'Dragonflies are among the most successful predators, with capture rates near 90% or higher.', GETDATE(), 0, 1),
(@Cat_Animals, N'Queens of some ant species can live for decades, vastly outliving workers.', GETDATE(), 0, 1),
(@Cat_Animals, N'Scorpions fluoresce blue-green under ultraviolet light due to chemicals in their cuticle.', GETDATE(), 0, 1),
(@Cat_Animals, N'Horses can sleep standing using a stay apparatus, but need to lie down for REM sleep.', GETDATE(), 0, 1),
(@Cat_Animals, N'Some glass frogs have bones that fluoresce green under UV light.', GETDATE(), 0, 1),
(@Cat_Animals, N'Pigeons can learn to categorize objects and even distinguish letters with training.', GETDATE(), 0, 1),
(@Cat_Animals, N'Hermit crabs swap shells in “vacancy chains” when a better fit appears.', GETDATE(), 0, 1),
(@Cat_Animals, N'Blue whale low-frequency calls can travel hundreds of kilometers through the ocean.', GETDATE(), 0, 1),
(@Cat_Animals, N'Great white sharks and some tunas keep core muscles warm (regional endothermy).', GETDATE(), 0, 1),
(@Cat_Animals, N'The vampire squid emits bioluminescent displays and mucus to evade predators.', GETDATE(), 0, 1),
(@Cat_Animals, N'Beavers build dams that create ponds and wetlands used by many other species.', GETDATE(), 0, 1),
(@Cat_Animals, N'Echidnas, like platypuses, are egg-laying mammals and have electroreceptors in the snout.', GETDATE(), 0, 1),
(@Cat_Animals, N'Northern mockingbirds can learn and mimic hundreds of natural and artificial sounds.', GETDATE(), 0, 1),
(@Cat_Animals, N'Arctic terns migrate from Arctic to Antarctic and back each year—one of the longest migrations.', GETDATE(), 0, 1),
(@Cat_Animals, N'Common swifts can remain airborne for months, sleeping and feeding on the wing.', GETDATE(), 0, 1),
(@Cat_Animals, N'The Etruscan shrew’s heart can beat over 1,000 times per minute.', GETDATE(), 0, 1),
(@Cat_Animals, N'An ostrich’s eye is larger than its brain.', GETDATE(), 0, 1),
(@Cat_Animals, N'Vultures have very acidic stomachs (around pH 1–2) that neutralize dangerous microbes.', GETDATE(), 0, 1),
(@Cat_Animals, N'An octopus can squeeze through any opening larger than its beak because it lacks a rigid skeleton.', GETDATE(), 0, 1),
(@Cat_Animals, N'Argentine ants have formed vast supercolonies with mutually tolerant members across continents.', GETDATE(), 0, 1),
(@Cat_Animals, N'Many sea turtles imprint on their natal beach and navigate back years later to nest.', GETDATE(), 0, 1),
(@Cat_Animals, N'Fleas jump by releasing energy stored in springy resilin pads.', GETDATE(), 0, 1),
(@Cat_Animals, N'Cheetahs can accelerate to highway speeds in just a few seconds, outpacing many sports cars.', GETDATE(), 0, 1),
(@Cat_Animals, N'Horses cannot vomit due to a strong cardiac sphincter and the angle of the esophagus to the stomach.', GETDATE(), 0, 1),
(@Cat_Animals, N'Rabbits are lagomorphs, not rodents; their teeth grow continuously and require wear.', GETDATE(), 0, 1),
(@Cat_Animals, N'Zebra stripes can deter biting flies by disrupting their landing cues.', GETDATE(), 0, 1),
(@Cat_Animals, N'Dung beetles can orient and navigate using the Milky Way’s glow to keep straight paths.', GETDATE(), 0, 1),
(@Cat_General, N'A thoroughly shuffled 52-card deck has 52! ≈ 8.07×10^67 possible orders—far more than the atoms on Earth.', GETDATE(), 0, 1),
(@Cat_General, N'Olympic “gold” medals are mostly silver with a thin layer of gold applied.', GETDATE(), 0, 1),
(@Cat_General, N'Scotland’s national animal is the unicorn.', GETDATE(), 0, 1),
(@Cat_General, N'The world’s shortest scheduled flight (Westray–Papa Westray, Orkney) can take under two minutes.', GETDATE(), 0, 1),
(@Cat_General, N'The original London Bridge was moved to Lake Havasu City, Arizona, in 1971.', GETDATE(), 0, 1),
(@Cat_General, N'China spans five geographical time zones but keeps a single official time.', GETDATE(), 0, 1),
(@Cat_General, N'Several places use half- or quarter-hour time zones (e.g., India UTC+5:30; Nepal UTC+5:45).', GETDATE(), 0, 1),
(@Cat_General, N'Only two sovereign states have square national flags: Switzerland and Vatican City.', GETDATE(), 0, 1),
(@Cat_General, N'Nepal’s flag is the the only non-rectangular national flag (a double pennant).', GETDATE(), 0, 1),
(@Cat_General, N'Saint Lucia is the only country named after a woman (Saint Lucy).', GETDATE(), 0, 1),
(@Cat_General, N'Brazil is named after brazilwood (pau-brasil), historically harvested for red dye.', GETDATE(), 0, 1),
(@Cat_General, N'Two countries are doubly landlocked: Liechtenstein and Uzbekistan.', GETDATE(), 0, 1),
(@Cat_General, N'The Welsh station Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch has one of the longest place names.', GETDATE(), 0, 1),
(@Cat_General, N'The interrobang (‽) is a punctuation mark proposed in 1962 combining a question and an exclamation.', GETDATE(), 0, 1),
(@Cat_General, N'The plastic tip on a shoelace is called an aglet.', GETDATE(), 0, 1),
(@Cat_General, N'The pleasant, earthy smell after rain is called petrichor.', GETDATE(), 0, 1),
(@Cat_General, N'An airplane “black box” is actually bright orange to aid recovery.', GETDATE(), 0, 1),
(@Cat_General, N'“Bluetooth” was named after Viking king Harald Bluetooth; the logo merges the runes for H and B.', GETDATE(), 0, 1),
(@Cat_General, N'Apollo missions left retroreflectors on the Moon that still let us measure the Earth–Moon distance by laser.', GETDATE(), 0, 1),
(@Cat_General, N'The Hundred Years’ War lasted 116 years (1337–1453).', GETDATE(), 0, 1),
(@Cat_General, N'A “baker’s dozen” means thirteen—an old safeguard against selling underweight bread.', GETDATE(), 0, 1),
(@Cat_General, N'Any month that starts on a Sunday will include a Friday the 13th.', GETDATE(), 0, 1),
(@Cat_General, N'“D-Day” simply means the day an operation begins; the letter is not an acronym.', GETDATE(), 0, 1),
(@Cat_General, N'Mr. Potato Head (1952) was the first toy advertised on television.', GETDATE(), 0, 1),
(@Cat_General, N'The first domain name ever registered was symbolics.com in 1985.', GETDATE(), 0, 1),
(@Cat_General, N'Ray Tomlinson sent the first networked email in 1971 and chose “@” to separate user and host.', GETDATE(), 0, 1),
(@Cat_General, N'The longest word in many English dictionaries is pneumonoultramicroscopicsilicovolcanoconiosis.', GETDATE(), 0, 1),
(@Cat_General, N'The most common letter in English text is E.', GETDATE(), 0, 1),
(@Cat_General, N'IKEA product names follow themes (e.g., sofas and coffee tables use Swedish place names; bookcases use occupations).', GETDATE(), 0, 1),
(@Cat_General, N'Monopoly property names were taken from streets in Atlantic City, New Jersey.', GETDATE(), 0, 1),
(@Cat_General, N'The five rings represent the continents, while the colors (including the white background) were chosen because every nation’s flag contains at least one of them.', GETDATE(), 0, 1),
(@Cat_General, N'The Space Shuttle’s external tank was left unpainted after early flights—saving ~270 kg—hence its orange color.', GETDATE(), 0, 1),
(@Cat_General, N'Snow looks white, but individual ice crystals are clear; snow’s whiteness comes from diffuse scattering of light.', GETDATE(), 0, 1),
(@Cat_General, N'Bananas are mildly radioactive due to the isotope potassium‑40.', GETDATE(), 0, 1),
(@Cat_General, N'“Moonbows” (lunar rainbows) occur at night; they appear faint and often whitish.', GETDATE(), 0, 1),
(@Cat_General, N'You cannot hum with your nose completely pinched closed—there’s nowhere for air to exit.', GETDATE(), 0, 1),
(@Cat_General, N'Papua New Guinea is home to 800+ living languages, the most of any country.', GETDATE(), 0, 1),
(@Cat_General, N'The longest mountain chain on Earth is the Mid‑Ocean Ridge, mostly underwater.', GETDATE(), 0, 1),
(@Cat_General, N'The deepest hole humans have drilled is the Kola Superdeep Borehole (about 12,262 meters).', GETDATE(), 0, 1),
(@Cat_General, N'The “Spanish flu” likely did not originate in Spain; Spain’s free press made it widely reported there.', GETDATE(), 0, 1),
(@Cat_General, N'M&M stands for Mars & Murrie, the surnames of the founders.', GETDATE(), 0, 1),
(@Cat_General, N'“Checkmate” comes from Persian “shāh māt,” often glossed as “the king is helpless.”', GETDATE(), 0, 1),
(@Cat_General, N'Arabic numerals used today were developed in India and reached Europe via the Islamic world.', GETDATE(), 0, 1),
(@Cat_General, N'Most blue eyes contain little pigment; they look blue due to light scattering in the iris.', GETDATE(), 0, 1),
(@Cat_General, N'In Morse code, SOS (··· ––– ···) is not an abbreviation; it’s an easy‑to‑recognize distress signal.', GETDATE(), 0, 1),
(@Cat_General, N'Blue flames are typically hotter than yellow flames (more complete combustion).', GETDATE(), 0, 1),
(@Cat_General, N'Globally, blood type O is the most common.', GETDATE(), 0, 1),
(@Cat_General, N'Counting all sizes, a standard 8×8 chessboard contains 204 distinct squares (1×1 through 8×8).', GETDATE(), 0, 1),
(@Cat_General, N'Antarctica is the only continent with no native ant species.', GETDATE(), 0, 1),
(@Cat_General, N'The Svalbard Global Seed Vault serves as a backup for the world’s crop diversity.', GETDATE(), 0, 1),
(@Cat_General, N'Punched cards used for the Jacquard loom influenced early programmable computing.', GETDATE(), 0, 1),
(@Cat_General, N'The classic soccer ball pattern is a truncated icosahedron (12 pentagons + 20 hexagons).', GETDATE(), 0, 1),
(@Cat_General, N'The word “deadline” originally referred to a line prisoners would be shot for crossing during the U.S. Civil War.', GETDATE(), 0, 1),
(@Cat_General, N'Leap‑year rule: years divisible by 4 are leap years, except centuries not divisible by 400.', GETDATE(), 0, 1),
(@Cat_General, N'Tides are strongest at full/new moon (spring tides) and weakest at quarter moons (neap tides).', GETDATE(), 0, 1),
(@Cat_General, N'The record low air temperature was −89.2 °C at Vostok Station, Antarctica (1983).', GETDATE(), 0, 1),
(@Cat_General, N'RSVP comes from French “Répondez s’il vous plaît” (“Please reply”).', GETDATE(), 0, 1),
(@Cat_General, N'No chemical element symbol uses the letter J.', GETDATE(), 0, 1),
(@Cat_General, N'A “score” means twenty; “four score and seven” equals eighty‑seven.', GETDATE(), 0, 1),
(@Cat_General, N'In medieval Europe, a “moment” was 1/40 of an hour—90 seconds.', GETDATE(), 0, 1),
(@Cat_General, N'The modern Hawaiian alphabet counts 13 symbols (5 vowels, 7 consonants, plus the ʻokina glottal stop).', GETDATE(), 0, 1),
(@Cat_General, N'Tyrannosaurus rex lived closer in time to humans than to Stegosaurus.', GETDATE(), 0, 1),
(@Cat_General, N'The human eye can distinguish roughly ten million colors.', GETDATE(), 0, 1),
(@Cat_General, N'The smallest country by area is Vatican City (≈0.49 km²).', GETDATE(), 0, 1),
(@Cat_General, N'The largest country by area is Russia (≈17 million km²).', GETDATE(), 0, 1),
(@Cat_General, N'The world’s highest administrative capital is La Paz, Bolivia, at over 3,600 meters.', GETDATE(), 0, 1),
(@Cat_General, N'The sidereal day (Earth’s rotation relative to the stars) is about 23 h 56 m—shorter than 24 hours.', GETDATE(), 0, 1),
(@Cat_General, N'In standard decks, the king of hearts is the only king without a mustache.', GETDATE(), 0, 1),
(@Cat_General, N'Humans experience a natural “nasal cycle,” where one nostril tends to flow more freely than the other, alternating over hours.', GETDATE(), 0, 1),
(@Cat_General, N'BB in “BB gun” originally referred to the size of the shot (around 0.177 inch), not ball bearings per se.', GETDATE(), 0, 1),
(@Cat_General, N'Camels store fat—not water—in their humps.', GETDATE(), 0, 1),
(@Cat_General, N'A group of porcupines is called a prickle.', GETDATE(), 0, 1),
(@Cat_General, N'A tesseract is the four‑dimensional analog of a cube (a hypercube).', GETDATE(), 0, 1),
(@Cat_General, N'A googolplex is 10^(10^100), vastly larger than a googol (10^100).', GETDATE(), 0, 1),
(@Cat_General, N'Shakespeare is the earliest recorded source for many English words (e.g., “eyeball,” “lonely,” “swagger”).', GETDATE(), 0, 1),
(@Cat_General, N'Roman numerals have no symbol for zero.', GETDATE(), 0, 1),
(@Cat_General, N'Earth’s atmosphere is roughly 78% nitrogen and 21% oxygen by volume.', GETDATE(), 0, 1),
(@Cat_General, N'Horseshoe crabs have blue blood due to copper‑based hemocyanin.', GETDATE(), 0, 1),
(@Cat_General, N'Pineapples typically take 18–24 months from planting to harvest.', GETDATE(), 0, 1),
(@Cat_General, N'It takes roughly 40 liters of maple sap to produce 1 liter of maple syrup.', GETDATE(), 0, 1),
(@Cat_General, N'Nickel‑titanium (Nitinol) alloys can “remember” shapes and return after deformation when heated.', GETDATE(), 0, 1),
(@Cat_General, N'The “French” croissant descends from the Austrian kipferl and became popularized in France.', GETDATE(), 0, 1),
(@Cat_General, N'Kangaroo joeys are born tiny—about the size of a jellybean—and continue developing in the pouch.', GETDATE(), 0, 1),
(@Cat_General, N'The term “astronaut” is Greek‑derived (“star sailor”); the Russian “cosmonaut” means “universe sailor.”', GETDATE(), 0, 1),
(@Cat_General, N'The Empire State Building has its own ZIP code (10118) due to mail volume.', GETDATE(), 0, 1),
(@Cat_General, N'On maps, Greenland often looks huge due to Mercator projection distortion; it is much smaller than Africa in area.', GETDATE(), 0, 1),
(@Cat_General, N'The Great Emu War (1932) in Australia was a real military operation—emus proved surprisingly hard to control.', GETDATE(), 0, 1),
(@Cat_General, N'The heaviest naturally occurring element by atomic number is uranium (Z=92).', GETDATE(), 0, 1),
(@Cat_General, N'The word “quiz” spread in the 18th–19th centuries; its origin is uncertain and much‑debated.', GETDATE(), 0, 1),
(@Cat_DIY, N'Remove red wine stains: blot (don''t rub), cover with salt to draw out moisture, rinse with cold water. For whites, a 1:1 mix of hydrogen peroxide and dish soap can help; avoid heat until the stain is gone.', GETDATE(), 0, 1),
(@Cat_DIY, N'Unclog a slow drain: pour ½ cup baking soda, then 1 cup warm vinegar; let foam 10–15 minutes, flush with hot water. Never mix with chemical drain cleaner.', GETDATE(), 0, 1),
(@Cat_DIY, N'Clean a microwave fast: heat a bowl of water with a splash of vinegar and lemon slices for 3–5 minutes; let steam sit, then wipe.', GETDATE(), 0, 1),
(@Cat_DIY, N'Pick up tiny broken glass shards with a slice of bread or duct tape after sweeping; double-bag the waste and label it.', GETDATE(), 0, 1),
(@Cat_DIY, N'Neutralize fridge odours with an open pot of coffee grounds or baking soda on a shelf; replace monthly.', GETDATE(), 0, 1),
(@Cat_DIY, N'Clean blender safely: half-fill with warm water and a drop of dish soap, blend 20–30 seconds, rinse well.', GETDATE(), 0, 1),
(@Cat_DIY, N'Remove sticky labels/adhesive by warming with a hairdryer or rubbing a few drops of cooking oil; peel and wash the residue.', GETDATE(), 0, 1),
(@Cat_DIY, N'Organise scarves/belts using shower-curtain rings on a hanger for a compact, visible rack.', GETDATE(), 0, 1),
(@Cat_DIY, N'Use two pillow inserts in one cover for extra fullness on sofas or beds.', GETDATE(), 0, 1),
(@Cat_DIY, N'De-fog bathroom mirrors: rub a small amount of shaving foam across the surface, then buff clean.', GETDATE(), 0, 1),
(@Cat_DIY, N'Shine taps and remove water spots with a vinegar-damp cloth, then rinse and dry. Don''t use on natural stone.', GETDATE(), 0, 1),
(@Cat_DIY, N'Descale a kettle: fill with a 1:1 vinegar-water mix, bring to a simmer/soak 20 minutes, rinse thoroughly. Check your manufacturer''s guidance first.', GETDATE(), 0, 1),
(@Cat_DIY, N'Remove hard-water haze from shower glass with a paste of baking soda and a little water; rinse and squeegee after showers to prevent buildup.', GETDATE(), 0, 1),
(@Cat_DIY, N'Clean showerheads: tie on a bag of vinegar so the head is submerged; soak a few hours or overnight, then rinse.', GETDATE(), 0, 1),
(@Cat_DIY, N'Deodorise shoes by sprinkling a little baking soda inside overnight or tuck dry tea bags in each shoe; avoid prolonged contact with delicate leather.', GETDATE(), 0, 1),
(@Cat_DIY, N'Freshen a mattress: sprinkle baking soda, let sit 30–60 minutes, then vacuum with an upholstery tool.', GETDATE(), 0, 1),
(@Cat_DIY, N'Stop squeaky door hinges with a tiny dab of silicone spray or petroleum jelly; wipe away excess to avoid drips.', GETDATE(), 0, 1),
(@Cat_DIY, N'Free a sticky zipper by rubbing the teeth with a graphite pencil or a sliver of candle wax.', GETDATE(), 0, 1),
(@Cat_DIY, N'Lift deodorant marks from clothing with a dry microfibre sponge or a tumble-dryer sheet.', GETDATE(), 0, 1),
(@Cat_DIY, N'Erase coffee/tea stains in mugs with a baking-soda paste; gentle scrub and rinse.', GETDATE(), 0, 1),
(@Cat_DIY, N'Remove chewing gum from fabric: harden with an ice pack, scrape off, then pre-treat residue with a little oil or stain remover before washing.', GETDATE(), 0, 1),
(@Cat_DIY, N'Pre-treat oil/grease stains on clothes with dishwashing liquid; gently work in and launder warm per care label.', GETDATE(), 0, 1),
(@Cat_DIY, N'Lift candle wax from fabric or carpet: let harden, pick off pieces, then use paper towel and a warm iron to absorb the rest.', GETDATE(), 0, 1),
(@Cat_DIY, N'Quick wrinkle release: hang clothes in a steamy bathroom or spritz with water and smooth by hand.', GETDATE(), 0, 1),
(@Cat_DIY, N'Stop a cutting board sliding by placing a damp paper towel or silicone mat underneath.', GETDATE(), 0, 1),
(@Cat_DIY, N'Reheat food evenly in the microwave by arranging it in a ring with a hole in the centre and covering; stir halfway.', GETDATE(), 0, 1),
(@Cat_DIY, N'Keep a paintbrush fresh between coats by wrapping it in cling film or foil and refrigerating for a few hours.', GETDATE(), 0, 1),
(@Cat_DIY, N'Catch drilling dust: fold a sticky note into a little shelf under the hole or hold a cup/vacuum nozzle beneath.', GETDATE(), 0, 1),
(@Cat_DIY, N'Find tiny dropped items (earrings, screws) with a vacuum hose covered by a stocking—objects get caught at the mesh.', GETDATE(), 0, 1),
(@Cat_DIY, N'Drive a stubborn screw by seating the correct bit and using a wide rubber band between bit and screw head for extra grip.', GETDATE(), 0, 1),
(@Cat_DIY, N'Loosen a stuck jar lid with extra grip from a rubber glove, a jar-opener, or by running the lid under hot water to expand it.', GETDATE(), 0, 1),
(@Cat_DIY, N'Revive day-old bread: lightly sprinkle with water and warm in the oven for a few minutes to re-gelatinise the starches.', GETDATE(), 0, 1),
(@Cat_DIY, N'Prevent mirror fogging temporarily with a tiny drop of dish soap wiped thin and buffed until clear.', GETDATE(), 0, 1),
(@Cat_DIY, N'Remove crayon from painted walls by gently warming with a hairdryer and wiping, or use a baking-soda paste; test paint first.', GETDATE(), 0, 1),
(@Cat_DIY, N'Remove white water rings on finished wood by warming gently with a hairdryer and then rubbing a little olive oil or furniture wax; test first.', GETDATE(), 0, 1),
(@Cat_DIY, N'Pet hair on carpets lifts well with a window squeegee; pull towards you and vacuum the clumps.', GETDATE(), 0, 1),
(@Cat_Science, N'Shannon estimated chess''s game-tree complexity around 10^120, vastly exceeding estimates of atoms in the observable universe.', GETDATE(), 0, 1),
(@Cat_Math, N'In standard real analysis, 0.999… equals 1 exactly — not just approximately.', GETDATE(), 0, 1),
(@Cat_Science, N'Boiling and freezing points depend on pressure: water can boil at room temperature in a vacuum (A space with absolutely zero matter. This basically doesn''t exist).)', GETDATE(), 0, 1),
(@Cat_Math, N'The Monty Hall problem: switching doors doubles your chance of winning from 1/3 to 2/3.', GETDATE(), 0, 1),
(@Cat_Space, N'Your head ages slightly faster than your feet because gravity slows time — a measurable general-relativity effect.', GETDATE(), 0, 1),
(@Cat_Space, N'Astronauts can grow up to 5 cm taller in orbit as spinal discs decompress; they shrink back on Earth.', GETDATE(), 0, 1),
(@Cat_Space, N'If you could fold a paper 42 times (ignoring physics), it would be thick enough to reach the Moon.', GETDATE(), 0, 1),
(@Cat_Space, N'All the planets could fit side-by-side in the average Earth–Moon distance with room to spare.', GETDATE(), 0, 1),
(@Cat_Space, N'On Neptune and Uranus, extreme pressures likely form "diamond rain" deep within the planets.', GETDATE(), 0, 1),
(@Cat_Space, N'Black holes have temperatures: stellar-mass black holes are incredibly cold via Hawking radiation.', GETDATE(), 0, 1),
(@Cat_Space, N'Neutron-star crust, nicknamed "nuclear pasta," may be the strongest known material in the universe.', GETDATE(), 0, 1),
(@Cat_History, N'Cleopatra lived closer in time to today than to the building of the Great Pyramid of Giza.', GETDATE(), 0, 1),
(@Cat_History, N'Oxford University had first teachings in 1096, making it the oldest university in the UK. ', GETDATE(), 0, 1),
(@Cat_History, N'In 1977, the "Wow!" signal a strong narrowband radio burst briefly hinted at a possible extraterrestrial source.', GETDATE(), 0, 1),
(@Cat_History, N'Roman concrete structures survived millennia partly thanks to volcanic ash that fosters self-healing minerals.', GETDATE(), 0, 1),
(@Cat_Animals, N'The "immortal jellyfish" Turritopsis dohrnii can revert its adult cells back to a juvenile state.', GETDATE(), 0, 1),
(@Cat_Animals, N'Pistol shrimp snap so fast they create a cavitation bubble that briefly reaches temperatures like the Sun’s surface.', GETDATE(), 0, 1),
(@Cat_Animals, N'Lyrebirds can mimic chainsaws, car alarms, and camera shutters with startling accuracy.', GETDATE(), 0, 1),
(@Cat_Animals, N'Greenland sharks may live for over 400 years, making them among the longest-lived vertebrates.', GETDATE(), 0, 1),
(@Cat_Animals, N'Bombardier beetles eject a hot, noxious spray from a chemical reaction chamber to deter predators.', GETDATE(), 0, 1),
(@Cat_Animals, N'Octopus arms have distributed neural control; an arm can execute complex motions semi-independently.', GETDATE(), 0, 1),
                (@Cat_EarthScience, N'The Earth hums: microseisms from ocean waves make the planet continuously vibrate at low amplitudes.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Continents drift at about the rate fingernails grow — centimeters per year.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Catatumbo, Venezuela, has storms with lightning hundreds of nights per year at the same spot.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Dead Sea''s shoreline is Earth’s lowest land elevation, more than 400 meters below sea level.', GETDATE(), 0, 1),
(@Cat_Geography, N'Lake Hillier in Australia is naturally pink due to microorganisms and high salinity.', GETDATE(), 0, 1),
(@Cat_Geography, N'There is a "boiling river" (Shanay-Timpishka) in the Peruvian Amazon that can reach ~90°C.', GETDATE(), 0, 1),
(@Cat_Geography, N'At the equator, Earth’s rotation makes you weigh slightly less than at the poles.', GETDATE(), 0, 1),
(@Cat_Tech, N'The Apollo Guidance Computer used rope memory literally woven by hand, with wires through or around cores to encode bits.', GETDATE(), 0, 1),
(@Cat_Tech, N'A single modern smartphone contains materials sourced from dozens of elements across the periodic table.', GETDATE(), 0, 1),
(@Cat_Health, N'You shed around 30,000–40,000 skin cells every minute; most household dust includes human skin and fabric fibers.', GETDATE(), 0, 1),
(@Cat_Health, N'Your stomach replaces its mucus layer about every few hours to safely contain hydrochloric acid.', GETDATE(), 0, 1),
(@Cat_Health, N'Goosebumps are a vestigial reflex once useful for fluffing fur to trap heat and look larger to threats.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Stonehenge predates the Great Pyramid; both align with celestial events.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'The golden ratio appears in some art and design, though its prevalence is often overstated.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Ancient Greek statues were once brightly painted; the pristine white look is a modern misconception.', GETDATE(), 0, 1),
(@Cat_Language, N'Emoji are encoded in Unicode as characters; their artwork varies by platform.', GETDATE(), 0, 1),
(@Cat_Language, N'Whistled languages like Silbo Gomero transpose speech into whistles to carry over long distances.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Saffron can cost thousands per kilogram because each flower yields just three stigmas.', GETDATE(), 0, 1),
(@Cat_General, N'The "new book smell" partly comes from lignin breakdown products similar to vanilla.', GETDATE(), 0, 1),
(@Cat_General, N'Bamboo scaffolding can outperform steel in flexibility and weight for certain construction uses.', GETDATE(), 0, 1),
(@Cat_General, N'Underwater, a duck''s quack echoes — it''s just hard to notice in open spaces.', GETDATE(), 0, 1),
(@Cat_General, N'A teaspoon of honey is the lifetime work of about 12 bees.', GETDATE(), 0, 1),
(@Cat_Science, N'Thixotropic fluids like ketchup get less viscous when shaken or squeezed.', GETDATE(), 0, 1),
(@Cat_Science, N'Sodium and potassium can explode on contact with water due to rapid hydrogen generation and heat.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Magnetite crystals in some animals may aid navigation by sensing Earth’s magnetic field.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Large volcanic eruptions can cool global climate temporarily by injecting aerosols into the stratosphere.', GETDATE(), 0, 1),
(@Cat_Tech, N'LiDAR measures distance by timing the return of laser pulses — useful for mapping and autonomy.', GETDATE(), 0, 1),
(@Cat_History, N'The Antikythera mechanism (c. 100 BCE) is an ancient Greek analog computer for predicting celestial events.', GETDATE(), 0, 1),
(@Cat_History, N'In WWII, "ghost armies" used inflatable tanks and sound deception to mislead enemy reconnaissance.', GETDATE(), 0, 1),
(@Cat_History, N'Voyager''s Golden Records include directions to Earth encoded with pulsar timings and a hydrogen transition.', GETDATE(), 0, 1),
(@Cat_History, N'Ancient Romans used urine (ammonia) as a cleaning agent and in textile processing.', GETDATE(), 0, 1),
(@Cat_History, N'Emperor penguins were once called "strange geese" by early Antarctic explorers unfamiliar with them.', GETDATE(), 0, 1),
(@Cat_Space, N'Neutron stars can spin hundreds of times per second; the fastest known pulsars rotate over 700 times per second.', GETDATE(), 0, 1),
(@Cat_Space, N'The Sun''s photosphere has a surface temperature of roughly 5,500°C.', GETDATE(), 0, 1),
(@Cat_Space, N'Earth is the densest planet in the solar system.', GETDATE(), 0, 1),
(@Cat_Space, N'Meteorites are rocks from space that survive their fiery passage through Earth’s atmosphere to reach the ground.', GETDATE(), 0, 1),
(@Cat_Space, N'The term "albedo" describes how much sunlight a surface reflects; fresh snow has a very high albedo.', GETDATE(), 0, 1),
(@Cat_Science, N'Graphene is a single layer of carbon atoms arranged in a hexagonal lattice with remarkable strength and conductivity.', GETDATE(), 0, 1),
(@Cat_Science, N'Superconductors conduct electricity with zero resistance below a critical temperature.', GETDATE(), 0, 1),
(@Cat_Science, N'An alloy is a mixture of metals (or metal with another element) that often has improved properties.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Permafrost is ground that remains frozen for two or more consecutive years.', GETDATE(), 0, 1),
(@Cat_Geography, N'The deepest lake by maximum depth is Lake Baikal, reaching about 1,642 meters.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Strait of Malacca is one of the world’s busiest shipping lanes, linking the Indian and Pacific Oceans.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Himalayas help create the South Asian monsoon by blocking and lifting moist air masses.', GETDATE(), 0, 1),
(@Cat_Math, N'The prime number 2 is the only even prime.', GETDATE(), 0, 1),
(@Cat_Math, N'In base-2 (binary), counting goes 1, 10, 11, 100, 101, and so on.', GETDATE(), 0, 1),
(@Cat_Math, N'A palindrome number reads the same forwards and backwards, such as 12321.', GETDATE(), 0, 1),
(@Cat_Health, N'White blood cells (leukocytes) are key players in immune defense against pathogens.', GETDATE(), 0, 1),
(@Cat_Health, N'Ligaments connect bone to bone, while tendons connect muscle to bone.', GETDATE(), 0, 1),
(@Cat_Health, N'Your sense of balance is governed largely by the vestibular system in the inner ear.', GETDATE(), 0, 1),
(@Cat_Health, N'Circadian rhythms are roughly 24-hour biological cycles influencing sleep and hormone release.', GETDATE(), 0, 1),
(@Cat_Animals, N'Mechanical sound production in crickets comes from rubbing specialized wings together (stridulation).', GETDATE(), 0, 1),
(@Cat_Animals, N'Male lions typically have manes, which may signal health and help in protection during fights.', GETDATE(), 0, 1),
(@Cat_Animals, N'Barn owls can hunt in near total darkness using highly sensitive hearing and facial discs that funnel sound.', GETDATE(), 0, 1),
(@Cat_Plants, N'Stomata are microscopic pores on leaves that regulate gas exchange and water loss.', GETDATE(), 0, 1),
(@Cat_Plants, N'Xylem transports water and minerals upward; phloem distributes sugars throughout the plant.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Brown rice retains its bran and germ, providing more fiber than white rice.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Umeboshi are Japanese salted, pickled plums known for their sour, salty flavor.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Ghee is clarified butter commonly used in South Asian cooking.', GETDATE(), 0, 1),
(@Cat_Tech, N'A hash function maps data to a fixed-size value; cryptographic hashes are designed to be collision-resistant.', GETDATE(), 0, 1),
(@Cat_Tech, N'An operating system manages hardware resources and provides common services for programs.', GETDATE(), 0, 1),
(@Cat_Tech, N'Optical fiber transmits light through total internal reflection for high-bandwidth communication.', GETDATE(), 0, 1),
(@Cat_Tech, N'Public-key cryptography uses mathematically linked key pairs for encryption and digital signatures.', GETDATE(), 0, 1),
(@Cat_Tech, N'Error-correcting codes like Hamming codes detect and correct data transmission errors.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Calligraphy is the art of beautiful handwriting with stylized, expressive lettering.', GETDATE(), 0, 1),
(@Cat_Language, N'An onomatopoeia is a word that imitates a sound, like "buzz" or "clang."', GETDATE(), 0, 1),
(@Cat_Language, N'In linguistics, morphology studies word formation and structure.', GETDATE(), 0, 1),
(@Cat_Language, N'An autonym is a community''s own name for itself or its language.', GETDATE(), 0, 1),
(@Cat_Language, N'Code-switching is the practice of alternating between languages or dialects in conversation.', GETDATE(), 0, 1),
(@Cat_General, N'Paper cuts hurt because they often occur in areas rich in nerve endings but poor in clotting tissue.', GETDATE(), 0, 1),
(@Cat_General, N'Zip codes in the U.S. were introduced in 1963 to improve mail sorting efficiency.', GETDATE(), 0, 1),
(@Cat_General, N'The "new car smell" comes from volatile organic compounds released by interior materials.', GETDATE(), 0, 1),
(@Cat_General, N'Quartz watches keep time using a vibrating quartz crystal driven by an electronic circuit.', GETDATE(), 0, 1),
(@Cat_Animals, N'An albatross can sleep while gliding, using dynamic soaring to travel long distances with minimal effort.', GETDATE(), 0, 1),
(@Cat_Animals, N'Bowerbirds build and decorate elaborate structures to attract mates.', GETDATE(), 0, 1),
(@Cat_Animals, N'Wolves communicate using howls that can carry for kilometers and coordinate pack activity.', GETDATE(), 0, 1),
(@Cat_Animals, N'Platypus males have venomous spurs on their hind legs, used primarily in competition.', GETDATE(), 0, 1),
(@Cat_Science, N'Diffraction is the bending and spreading of waves around obstacles or through narrow openings.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'An oxbow lake forms when a meandering river cuts off a loop, creating a standalone water body.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Calderas are large volcanic depressions formed after major eruptions empty a magma chamber.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Isostasy describes the gravitational equilibrium of Earth’s crust "floating" on the mantle.', GETDATE(), 0, 1),
(@Cat_Tech, N'Raster images store pixel grids; vector graphics store shapes defined by mathematics.', GETDATE(), 0, 1),
(@Cat_Tech, N'Lossless compression (e.g., PNG) preserves all data; lossy compression (e.g., JPEG) discards some to save space.', GETDATE(), 0, 1),
(@Cat_Tech, N'A checksum is a value used to verify data integrity after storage or transmission.', GETDATE(), 0, 1),
(@Cat_Tech, N'Firmware is software embedded in hardware devices, providing low-level control.', GETDATE(), 0, 1),
(@Cat_Tech, N'Latency is the delay before a transfer of data begins following an instruction; bandwidth is the rate of transfer.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'The sonnet is a 14-line poem form with various rhyme schemes such as Shakespearean and Petrarchan.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Ballet originated in Italian Renaissance courts and later developed in France and Russia.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Color temperature describes the hue of light sources; higher Kelvin values appear "cooler" and bluer.', GETDATE(), 0, 1),
(@Cat_Language, N'A homograph is a word that is spelled the same as another but may differ in pronunciation and meaning.', GETDATE(), 0, 1),
(@Cat_Language, N'Phonetics studies the physical sounds of human speech; phonology examines their abstract patterns.', GETDATE(), 0, 1),
(@Cat_Language, N'Etymology investigates the origins and historical development of words.', GETDATE(), 0, 1),
(@Cat_Language, N'A rhetorical question is asked to make a point rather than to elicit an answer.', GETDATE(), 0, 1),
(@Cat_Language, N'A portmanteau blends parts of two words, like "smog" from smoke and fog.', GETDATE(), 0, 1),
(@Cat_Health, N'The human brain uses about 20% of the body''s total energy despite being only 2% of body weight.', GETDATE(), 0, 1),
(@Cat_Science, N'Water expands by about 9% when it freezes, which is why ice floats on water.', GETDATE(), 0, 1),
(@Cat_General, N'The Great Wall of China is not visible from space without aid, contrary to popular belief.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first computer bug was an actual moth found in a Harvard Mark II computer in 1947.', GETDATE(), 0, 1),
(@Cat_Animals, N'Octopuses have three hearts and blue blood.', GETDATE(), 0, 1),
(@Cat_Space, N'A day on Venus is longer than its year because Venus rotates very slowly in the opposite direction.', GETDATE(), 0, 1),
(@Cat_Plants, N'Bananas are berries in botanical terms, while strawberries are not.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Honey found in ancient tombs can still be edible because it is naturally low in water and acidic.', GETDATE(), 0, 1),
(@Cat_Science, N'The Eiffel Tower gets slightly taller in summer due to thermal expansion of its metal, about 12–15 centimetres.', GETDATE(), 0, 1),
(@Cat_Animals, N'Wombats produce cube-shaped droppings that help keep them from rolling away.', GETDATE(), 0, 1),
(@Cat_Space, N'The Moon is slowly drifting away from Earth by a few centimeters each year.', GETDATE(), 0, 1),
(@Cat_Animals, N'Butterflies can taste using sensors on their feet.', GETDATE(), 0, 1),
(@Cat_Space, N'The International Space Station orbits Earth about sixteen times each day.', GETDATE(), 0, 1),
(@Cat_Space, N'Saturn is less dense than water, so a hypothetical planet-sized bathtub could make it float.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Rainbows are actually full circles; from the ground we usually see only an arc.', GETDATE(), 0, 1),
(@Cat_Language, N'The word "robot" comes from the Czech "robota," meaning forced labor.', GETDATE(), 0, 1),
(@Cat_Plants, N'Peanuts are legumes, not true nuts.', GETDATE(), 0, 1),
(@Cat_Science, N'Copper surfaces naturally kill many microbes through a process called contact killing.', GETDATE(), 0, 1),
(@Cat_General, N'The only letter not found in the name of any U.S. state is Q.', GETDATE(), 0, 1),
(@Cat_Animals, N'In seahorses, the males carry the pregnancy and give birth.', GETDATE(), 0, 1),
(@Cat_Space, N'Mars has two small moons named Phobos and Deimos.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Great Barrier Reef is the largest living structure on Earth.', GETDATE(), 0, 1),
(@Cat_Animals, N'Tardigrades, or water bears, can survive extreme conditions by entering a tun state.', GETDATE(), 0, 1),
(@Cat_Animals, N'Hummingbirds can hover and even fly backward.', GETDATE(), 0, 1),
(@Cat_Math, N'Sunflower seed patterns often follow Fibonacci spirals.', GETDATE(), 0, 1),
(@Cat_Animals, N'Polar bears have black skin beneath their white fur.', GETDATE(), 0, 1),
(@Cat_Space, N'A Martian day, called a sol, is about 24 hours and 39 minutes long.', GETDATE(), 0, 1),
(@Cat_Space, N'Jupiter''s Great Red Spot is a giant storm larger than Earth.', GETDATE(), 0, 1),
(@Cat_Science, N'Sound cannot travel through the vacuum of space because there is no medium.', GETDATE(), 0, 1),
(@Cat_Plants, N'Pineapples are multiple fruits formed when many flowers fuse together.', GETDATE(), 0, 1),
(@Cat_Animals, N'Some freshwater turtles can absorb oxygen through their cloaca (Opening) when underwater.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Lightning can strike the same place more than once.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Dead Sea is so salty that people float easily on its surface.', GETDATE(), 0, 1),
(@Cat_Animals, N'Cheetahs cannot roar like lions and tigers; they purr instead.', GETDATE(), 0, 1),
(@Cat_Space, N'A comet''s tail always points away from the Sun due to solar wind and radiation pressure.', GETDATE(), 0, 1),
(@Cat_Geography, N'Antarctica is the largest desert on Earth by area.', GETDATE(), 0, 1),
(@Cat_Animals, N'Bats are the only mammals capable of sustained flight.', GETDATE(), 0, 1),
(@Cat_Animals, N'Frogs absorb water through their skin rather than drinking with their mouths.', GETDATE(), 0, 1),
(@Cat_Science, N'By weight, spider silk can be stronger than steel.', GETDATE(), 0, 1),
(@Cat_Animals, N'Tigers have striped skin as well as striped fur.', GETDATE(), 0, 1),
(@Cat_Animals, N'Orcas, or killer whales, are the largest members of the dolphin family.', GETDATE(), 0, 1),
(@Cat_Space, N'Sunlight takes about eight minutes to reach Earth.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Earth''s rotation is gradually slowing down, making days slightly longer over long timescales, about 1.7 to 1.8 milliseconds per century.', GETDATE(), 0, 1),
(@Cat_Animals, N'Crows can recognize human faces and remember how people treat them.', GETDATE(), 0, 1),
(@Cat_Animals, N'Dolphins use unique signature whistles that function like names.', GETDATE(), 0, 1),
(@Cat_History, N'Potatoes were first domesticated in the Andes of South America.', GETDATE(), 0, 1),
(@Cat_History, N'Carrots were originally purple, white, or yellow. The modern orange variety was created in the 17th century by Dutch farmers through selective breeding.', GETDATE(), 0, 1),
(@Cat_Plants, N'Coast redwoods are among the tallest trees on Earth.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'The Sahara Desert was once greener, with lakes and grasslands in the distant past.', GETDATE(), 0, 1),
(@Cat_Space, N'Olympus Mons on Mars is the tallest known volcano in the solar system.', GETDATE(), 0, 1),
(@Cat_Space, N'Venus has thick clouds of sulfuric acid and a runaway greenhouse effect.', GETDATE(), 0, 1),
(@Cat_Health, N'An adult human skeleton typically has 206 bones.', GETDATE(), 0, 1),
(@Cat_Health, N'Cracking your knuckles has not been shown to cause arthritis.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Dust from the Sahara helps fertilize the Amazon rainforest across the Atlantic.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Coffee beans are the seeds of a fruit commonly called a coffee cherry.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Cinnamon is made from the inner bark of trees in the genus Cinnamomum.', GETDATE(), 0, 1),
(@Cat_Language, N'The word "alphabet" comes from the first two Greek letters: alpha and beta.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first retail product scanned with a barcode in 1974 was a pack of chewing gum.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first 3D printer was developed in the 1980s using a process called stereolithography.', GETDATE(), 0, 1),
(@Cat_Language, N'The word "emoji" comes from Japanese and is unrelated to the English word "emotion."', GETDATE(), 0, 1),
(@Cat_Tech, N'LEGO bricks made in 1958 still interlock with modern bricks because the design has stayed consistent.', GETDATE(), 0, 1),
(@Cat_Tech, N'Bubble wrap was originally invented as a textured wallpaper before becoming packing material.', GETDATE(), 0, 1),
(@Cat_Tech, N'Percy Spencer discovered microwave heating when a candy bar melted near a magnetron, leading to the microwave oven.', GETDATE(), 0, 1),
(@Cat_Animals, N'Honeybees communicate the location of flowers using a waggle dance.', GETDATE(), 0, 1),
(@Cat_Animals, N'Fireflies produce light through a chemical reaction called bioluminescence.', GETDATE(), 0, 1),
(@Cat_Animals, N'The platypus is one of the few mammals that lays eggs.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Amazon River carries more water than any other river in the world.', GETDATE(), 0, 1),
(@Cat_Animals, N'The Andean condor has one of the largest wingspans of any land bird.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Andes is the longest continental mountain range on Earth.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'The Himalayas are still rising due to the collision of tectonic plates, about 4 millimeters per year.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Hawaii moves northwest a few centimeters each year because it sits on a moving tectonic plate.', GETDATE(), 0, 1),
(@Cat_Space, N'A "Blue Moon" commonly refers to the second full moon in a single calendar month.', GETDATE(), 0, 1),
(@Cat_Language, N'The dot above the letters i and j is called a tittle.', GETDATE(), 0, 1),
(@Cat_Language, N'The # symbol is also called an octothorpe.', GETDATE(), 0, 1),
(@Cat_Language, N'A palindrome reads the same forward and backward, like "racecar."', GETDATE(), 0, 1),
(@Cat_General, N'U.S. paper currency is primarily a blend of cotton and linen rather than wood pulp.', GETDATE(), 0, 1),
(@Cat_Space, N'The International Space Station is the largest human-made object in low Earth orbit.', GETDATE(), 0, 1),
(@Cat_Animals, N'Termites are more closely related to cockroaches than to ants.', GETDATE(), 0, 1),
(@Cat_Animals, N'Koalas have fingerprints so similar to humans that they can confuse forensic analysis.', GETDATE(), 0, 1),
(@Cat_Animals, N'Giraffes and humans both have seven neck vertebrae despite their different neck lengths.', GETDATE(), 0, 1),
(@Cat_Animals, N'A group of flamingos is called a flamboyance.', GETDATE(), 0, 1),
(@Cat_Animals, N'Male pufferfish create intricate sand circles on the seafloor to attract mates.', GETDATE(), 0, 1),
(@Cat_Animals, N'Monarch butterflies migrate thousands of kilometers between North America and Mexico.', GETDATE(), 0, 1),
(@Cat_Math, N'A leap year helps keep the calendar aligned with Earth''s orbit around the Sun.', GETDATE(), 0, 1),
(@Cat_Science, N'Mercury is the only metal that is liquid at standard room temperature and pressure.', GETDATE(), 0, 1),
(@Cat_Animals, N'Glass frogs have transparent skin on their bellies that reveals their internal organs.', GETDATE(), 0, 1),
(@Cat_Animals, N'Sharks appear in the fossil record before trees existed.', GETDATE(), 0, 1),
(@Cat_Geography, N'The deepest part of the ocean is the Challenger Deep in the Mariana Trench.', GETDATE(), 0, 1),
(@Cat_Space, N'Polaris will not always be the North Star because Earth''s axis slowly wobbles over time.', GETDATE(), 0, 1),
(@Cat_Animals, N'Many lizards can shed their tails to escape predators and later regenerate them.', GETDATE(), 0, 1),
(@Cat_Health, N'The brain itself has no pain receptors; headaches arise from surrounding tissues and blood vessels.', GETDATE(), 0, 1),
(@Cat_Animals, N'The ostrich is the tallest living bird and lays the largest eggs of any bird.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'A piano is considered both a string instrument and a percussion instrument.', GETDATE(), 0, 1),
(@Cat_Tech, N'The modern internet traces its roots to ARPANET, a project started in the late 1960s.', GETDATE(), 0, 1),
(@Cat_Space, N'GPS satellites must account for relativity because time runs slightly differently in orbit.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'A cloud can weigh many tons because it contains vast numbers of tiny water droplets.', GETDATE(), 0, 1),
(@Cat_Plants, N'Mango trees are in the same plant family as cashews and pistachios.', GETDATE(), 0, 1),
(@Cat_Plants, N'Tomatoes are fruits botanically but are often treated as vegetables in cooking.', GETDATE(), 0, 1),
(@Cat_Animals, N'Seahorses have prehensile tails that help them anchor to seagrass and corals.', GETDATE(), 0, 1),
(@Cat_Space, N'A teaspoon of neutron star material would weigh billions of tons on Earth.', GETDATE(), 0, 1),
(@Cat_Space, N'The Milky Way and Andromeda galaxies are on a collision course expected in about 4-5 billion years.', GETDATE(), 0, 1),
(@Cat_Space, N'Pluto has a heart-shaped region called Tombaugh Regio.', GETDATE(), 0, 1),
(@Cat_Space, N'A year on Mercury lasts about 88 Earth days.', GETDATE(), 0, 1),
(@Cat_Space, N'The Sun contains about 99.8% of the total mass of the solar system.', GETDATE(), 0, 1),
(@Cat_Space, N'The Kuiper Belt beyond Neptune is filled with icy bodies including Pluto and Eris.', GETDATE(), 0, 1),
(@Cat_Space, N'Space is not completely empty; it contains a sparse interstellar medium of gas and dust.', GETDATE(), 0, 1),
(@Cat_Space, N'On Mars, sunsets can appear blue because dust scatters red light more than blue.', GETDATE(), 0, 1),
(@Cat_Space, N'Voyager 1 is the most distant human-made object from Earth.', GETDATE(), 0, 1),
(@Cat_Space, N'The ''dark side'' of the Moon is a misnomer; the far side receives sunlight too.', GETDATE(), 0, 1),
(@Cat_Space, N'Light in a vacuum travels about 299,792 kilometers per second.', GETDATE(), 0, 1),
(@Cat_Science, N'Absolute zero is 0 kelvin, equivalent to -273.15 degrees Celsius.', GETDATE(), 0, 1),
(@Cat_Science, N'Water is densest at about 4°C, which helps lakes freeze from the top down.', GETDATE(), 0, 1),
(@Cat_Science, N'Under some conditions, hot water can freeze faster than cold water (the Mpemba effect).', GETDATE(), 0, 1),
(@Cat_Science, N'The periodic table is ordered by atomic number, not atomic mass.', GETDATE(), 0, 1),
(@Cat_Science, N'A bolt of lightning can be several times hotter than the surface of the Sun.', GETDATE(), 0, 1),
(@Cat_Science, N'Penicillin was discovered by Alexander Fleming in 1928.', GETDATE(), 0, 1),
(@Cat_Science, N'The Doppler effect explains the change in pitch of a passing siren and redshift of distant galaxies.', GETDATE(), 0, 1),
(@Cat_Science, N'Some RNA molecules can catalyze reactions; these are called ribozymes.', GETDATE(), 0, 1),
(@Cat_Science, N'Mitochondria and chloroplasts contain their own DNA.', GETDATE(), 0, 1),
(@Cat_Health, N'The human liver can regenerate portions of itself after injury.', GETDATE(), 0, 1),
(@Cat_Health, N'Humans typically have 46 chromosomes in their somatic cells.', GETDATE(), 0, 1),
(@Cat_Health, N'An average adult has roughly five liters of blood.', GETDATE(), 0, 1),
(@Cat_Health, N'All regions of the tongue can detect basic tastes; the old ''tongue map'' is a myth.', GETDATE(), 0, 1),
(@Cat_Health, N'The skin is the largest organ of the human body by area.', GETDATE(), 0, 1),
(@Cat_Health, N'Earwax helps protect and lubricate the ear canal and is influenced by genetics.', GETDATE(), 0, 1),
(@Cat_Animals, N'Ravens are excellent mimics and can imitate human speech.', GETDATE(), 0, 1),
(@Cat_Animals, N'Most cats cannot taste sweetness due to a mutated taste receptor.', GETDATE(), 0, 1),
(@Cat_Animals, N'Blue whales are the largest animals known to have ever lived.', GETDATE(), 0, 1),
(@Cat_Animals, N'Camels have a transparent third eyelid that helps protect their eyes from blowing sand.', GETDATE(), 0, 1),
(@Cat_Animals, N'Penguins ''fly'' underwater using their flippers but cannot fly in the air.', GETDATE(), 0, 1),
(@Cat_Animals, N'Male emperor penguins incubate eggs on their feet under a brood pouch.', GETDATE(), 0, 1),
(@Cat_Animals, N'Pistol shrimp create a cavitation bubble with a snap that can stun prey.', GETDATE(), 0, 1),
(@Cat_Animals, N'Mantis shrimp have up to sixteen types of photoreceptors for color vision.', GETDATE(), 0, 1),
(@Cat_Animals, N'Owls can rotate their heads about 270 degrees in either direction.', GETDATE(), 0, 1),
(@Cat_Animals, N'A group of crows is called a murder.', GETDATE(), 0, 1),
(@Cat_Animals, N'Chocolate can be toxic to dogs because it contains theobromine.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'The heat of chili peppers is measured in Scoville Heat Units.', GETDATE(), 0, 1),
(@Cat_Plants, N'Almonds are the seeds of a drupe, not true nuts.', GETDATE(), 0, 1),
(@Cat_Plants, N'Cashews grow as seeds on the outside of the cashew apple.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Quinoa is a pseudocereal; it is a seed used like a grain.', GETDATE(), 0, 1),
(@Cat_History, N'Wheat and barley were among the first domesticated crops in the Fertile Crescent.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Tea is the most consumed beverage in the world after water.', GETDATE(), 0, 1),
(@Cat_Geography, N'Africa is the only continent that straddles all four hemispheres.', GETDATE(), 0, 1),
(@Cat_Geography, N'Canada has the longest coastline of any country.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Amazon River is the largest by discharge of water into the ocean.', GETDATE(), 0, 1),
(@Cat_Geography, N'Lake Baikal in Russia holds about one-fifth of the world''s unfrozen fresh surface water by volume.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Atacama Desert in Chile has areas that receive virtually no rainfall.', GETDATE(), 0, 1),
(@Cat_Geography, N'Angel Falls in Venezuela is the world''s tallest uninterrupted waterfall.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Sahara is the largest hot desert on Earth.', GETDATE(), 0, 1),
(@Cat_Geography, N'Iceland is known as the land of fire and ice for its volcanoes and glaciers.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Most of the world''s earthquakes and volcanoes occur along the Pacific Ring of Fire.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Tsunamis are most often caused by undersea earthquakes that displace large volumes of water.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Earth''s inner core is solid, while the outer core is liquid metal that helps generate the magnetic field.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Earth''s magnetic north pole wanders over time due to changes in the core.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Coral reefs are built by tiny animals called coral polyps that secrete calcium carbonate skeletons.', GETDATE(), 0, 1),
(@Cat_Language, N'The word ''quarantine'' comes from Italian ''quaranta giorni,'' meaning forty days.', GETDATE(), 0, 1),
(@Cat_Language, N'The English pangram ''The quick brown fox jumps over the lazy dog'' uses every letter of the alphabet.', GETDATE(), 0, 1),
(@Cat_Language, N'English is genetically a Germanic language (specifically West Germanic), but it has absorbed such a massive amount of vocabulary from French and Latin (Romance languages).', GETDATE(), 0, 1),
(@Cat_Math, N'Zero as a number and placeholder was developed in ancient India and spread via Arabic scholarship.', GETDATE(), 0, 1),
(@Cat_Math, N'A googol is the number 10 to the power of 100.', GETDATE(), 0, 1),
(@Cat_Math, N'There are infinitely many prime numbers, a fact proved by Euclid.', GETDATE(), 0, 1),
(@Cat_Math, N'Pi (π) is an irrational and transcendental number.', GETDATE(), 0, 1),
(@Cat_Math, N'The golden ratio, about 1.618, appears in some growth patterns and geometric constructions.', GETDATE(), 0, 1),
(@Cat_Tech, N'The QWERTY keyboard layout was designed to reduce jamming in early typewriters.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first website was created by Tim Berners-Lee and went online in 1991.', GETDATE(), 0, 1),
(@Cat_Tech, N'Moore''s Law observed that the number of transistors on a chip roughly doubled every two years.', GETDATE(), 0, 1),
(@Cat_Tech, N'Unicode assigns code points to characters to support writing systems worldwide.', GETDATE(), 0, 1),
(@Cat_Tech, N'Email existed before the World Wide Web.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Sushi refers to vinegared rice; raw fish is not required for sushi.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Bread rises because yeast ferments sugars, producing carbon dioxide.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Cheese is made by coagulating milk proteins, often using enzymes like rennet.', GETDATE(), 0, 1),
(@Cat_Animals, N'Sea otters use rocks as tools to crack open shellfish.', GETDATE(), 0, 1),
(@Cat_Animals, N'Elephants communicate using low-frequency rumbles that can travel long distances.', GETDATE(), 0, 1),
(@Cat_Animals, N'Geckos can walk on smooth walls thanks to microscopic hairs on their toes that exploit van der Waals forces.', GETDATE(), 0, 1),
(@Cat_Animals, N'Kangaroos cannot move their hind legs independently when moving slowly; they use their tail as a fifth limb.', GETDATE(), 0, 1),
(@Cat_Animals, N'The archerfish can shoot jets of water to knock insects off leaves into the water.', GETDATE(), 0, 1),
(@Cat_Plants, N'Bamboo can grow astonishingly fast, with some species growing over 30 centimeters in a day under ideal conditions.', GETDATE(), 0, 1),
(@Cat_History, N'Paper was invented in ancient China during the Han dynasty.', GETDATE(), 0, 1),
(@Cat_History, N'The printing press popularized by Johannes Gutenberg in the 15th century revolutionized information sharing.', GETDATE(), 0, 1),
(@Cat_History, N'The Silk Road was a network of trade routes connecting East and West for centuries.', GETDATE(), 0, 1),
(@Cat_History, N'The Rosetta Stone helped scholars decipher Egyptian hieroglyphs.', GETDATE(), 0, 1),
(@Cat_Geography, N'Mauna Kea in Hawaii is taller than Mount Everest when measured from its base on the ocean floor.', GETDATE(), 0, 1),
(@Cat_Space, N'Most comets originate from the Oort Cloud and Kuiper Belt, distant reservoirs of icy bodies.', GETDATE(), 0, 1),
(@Cat_Space, N'Neptune has some of the fastest winds in the solar system, reaching over 2,000 kilometers or 1,243 miles per hour.', GETDATE(), 0, 1),
(@Cat_Space, N'Uranus rotates on its side with an axial tilt of about 98 degrees.', GETDATE(), 0, 1),
(@Cat_Space, N'A light-year is the distance light travels in one year, about 9.46 trillion kilometers or 5.88 trillion miles', GETDATE(), 0, 1),
(@Cat_Space, N'Mars has a canyon system called Valles Marineris that stretches over 4,000 kilometers or 2,485 miles,', GETDATE(), 0, 1),
(@Cat_Space, N'Earth’s seasons are caused by its axial tilt of roughly 23.5 degrees, not by distance from the Sun.', GETDATE(), 0, 1),
(@Cat_Space, N'Auroras are produced when charged particles from the Sun interact with Earth’s magnetic field and atmosphere.', GETDATE(), 0, 1),
(@Cat_Space, N'Many exoplanets have been discovered using the transit method, which detects tiny dips in a star’s brightness.', GETDATE(), 0, 1),
(@Cat_Space, N'Halley’s Comet has an orbital period of about 76 years.', GETDATE(), 0, 1),
(@Cat_Space, N'The Moon is tidally locked to Earth, always showing the same face.', GETDATE(), 0, 1),
(@Cat_Science, N'DNA molecules typically form a double-helix structure.', GETDATE(), 0, 1),
(@Cat_Science, N'Enzymes are biological catalysts that speed up chemical reactions in cells.', GETDATE(), 0, 1),
(@Cat_Science, N'The pH scale ranges from 0 to 14, with 7 being neutral.', GETDATE(), 0, 1),
(@Cat_Science, N'Most of Earth’s freshwater is stored in glaciers and ice sheets.', GETDATE(), 0, 1),
(@Cat_Science, N'The speed of sound in air at about 20°C is roughly 343 meters per second.', GETDATE(), 0, 1),
(@Cat_Science, N'Plasma is an ionized state of matter distinct from solid, liquid, and gas.', GETDATE(), 0, 1),
(@Cat_Science, N'Viruses require host cells to replicate and are not considered living by many definitions.', GETDATE(), 0, 1),
(@Cat_Science, N'Catalysts lower the activation energy of reactions without being consumed.', GETDATE(), 0, 1),
(@Cat_Science, N'Visible light spans wavelengths of about 400 to 700 nanometers.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'The ozone layer absorbs most of the Sun’s harmful ultraviolet-B radiation.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'El Niño is a periodic warming of the central and eastern tropical Pacific that alters global weather.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'The water cycle circulates water through evaporation, condensation, and precipitation.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Earth is about 4.54 billion years old based on radiometric dating.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Fossils are most commonly preserved in sedimentary rocks.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'The moment magnitude scale is widely used to measure earthquake size.', GETDATE(), 0, 1),
(@Cat_EarthScience, N'Hurricanes, typhoons, and cyclones are the same kind of storm in different ocean basins.', GETDATE(), 0, 1),
(@Cat_Geography, N'Russia spans eleven time zones across its territory.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Nile River flows northward and empties into the Mediterranean Sea.', GETDATE(), 0, 1),
(@Cat_Geography, N'Mount Everest’s summit is about 8,849 meters above sea level.', GETDATE(), 0, 1),
(@Cat_Geography, N'Greenland is the world’s largest island that is not a continent.', GETDATE(), 0, 1),
(@Cat_Geography, N'Australia is both a country and a continent.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Danube River flows through more countries than any other river in Europe.', GETDATE(), 0, 1),
(@Cat_Geography, N'Lake Superior is the largest freshwater lake by surface area.', GETDATE(), 0, 1),
(@Cat_Geography, N'The Himalayas form where the Indian Plate collides with the Eurasian Plate.', GETDATE(), 0, 1),
(@Cat_History, N'The Wright brothers achieved the first sustained, powered flight in 1903 at Kitty Hawk.', GETDATE(), 0, 1),
(@Cat_History, N'The Roman Empire used volcanic ash in concrete, contributing to its durability.', GETDATE(), 0, 1),
(@Cat_History, N'The first modern Olympic Games were held in Athens in 1896.', GETDATE(), 0, 1),
(@Cat_History, N'The Black Death in the 14th century drastically reduced Europe’s population.', GETDATE(), 0, 1),
(@Cat_History, N'The Berlin Wall fell in 1989, symbolizing the end of the Cold War era.', GETDATE(), 0, 1),
(@Cat_History, N'Yuri Gagarin became the first human in space in 1961.', GETDATE(), 0, 1),
(@Cat_History, N'Apollo 11 astronauts first landed on the Moon in 1969.', GETDATE(), 0, 1),
(@Cat_History, N'Ancient Egyptians built pyramids as monumental royal tombs.', GETDATE(), 0, 1),
(@Cat_Tech, N'Transistors replaced vacuum tubes and enabled modern microelectronics.', GETDATE(), 0, 1),
(@Cat_Tech, N'HTTP is the protocol that web browsers use to request and fetch web pages.', GETDATE(), 0, 1),
(@Cat_Tech, N'Open-source software allows anyone to inspect and modify the source code.', GETDATE(), 0, 1),
(@Cat_Tech, N'Machine learning systems learn patterns from data rather than explicit rules.', GETDATE(), 0, 1),
(@Cat_Tech, N'Binary numbers use only two digits: 0 and 1.', GETDATE(), 0, 1),
(@Cat_Tech, N'A byte is a group of eight bits.', GETDATE(), 0, 1),
(@Cat_Tech, N'QR codes store data in a two-dimensional matrix of modules.', GETDATE(), 0, 1),
(@Cat_Tech, N'Cloud computing provides on-demand computing resources over the internet.', GETDATE(), 0, 1),
(@Cat_Tech, N'A compiler translates source code into machine code, while an interpreter executes it directly.', GETDATE(), 0, 1),
(@Cat_Health, N'Red blood cells carry oxygen using the protein hemoglobin.', GETDATE(), 0, 1),
(@Cat_Health, N'Vaccines train the immune system to recognize specific pathogens.', GETDATE(), 0, 1),
(@Cat_Health, N'Insulin is a hormone that helps regulate blood glucose levels.', GETDATE(), 0, 1),
(@Cat_Health, N'Antibiotics target bacteria and do not work against viruses.', GETDATE(), 0, 1),
(@Cat_Animals, N'Bees can see ultraviolet patterns on flowers that guide them to nectar.', GETDATE(), 0, 1),
(@Cat_Animals, N'Cats have a righting reflex that helps them land on their feet.', GETDATE(), 0, 1),
(@Cat_Animals, N'Peregrine falcons can exceed 300 km/h in a hunting dive.', GETDATE(), 0, 1),
(@Cat_Animals, N'Chameleons change color for communication and thermoregulation as well as camouflage.', GETDATE(), 0, 1),
(@Cat_Animals, N'Dolphins and bats use echolocation to navigate and hunt.', GETDATE(), 0, 1),
(@Cat_Animals, N'Giant pandas have a modified wrist bone that functions like a thumb.', GETDATE(), 0, 1),
(@Cat_Animals, N'Elephants have the largest brains of any land animal.', GETDATE(), 0, 1),
(@Cat_Animals, N'Octopuses are highly intelligent and can solve simple problems and puzzles.', GETDATE(), 0, 1),
(@Cat_Animals, N'Arctic foxes have seasonal coats that change from brown to white.', GETDATE(), 0, 1),
(@Cat_Animals, N'Sea stars can regenerate lost arms in many species.', GETDATE(), 0, 1),
(@Cat_Plants, N'Chlorophyll absorbs red and blue light and reflects green, giving plants their color.', GETDATE(), 0, 1),
(@Cat_Plants, N'Apples can float in water because a significant portion of their volume is air.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Lactose is the natural sugar in milk; many adults have reduced lactase enzyme levels.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Fermentation can preserve foods by producing acids or alcohol that inhibit microbes.', GETDATE(), 0, 1),
(@Cat_Language, N'The ampersand symbol (&) originated as a ligature of the Latin word ''et''.', GETDATE(), 0, 1),
(@Cat_Language, N'Writing systems include alphabets, abjads, abugidas, and logographies.', GETDATE(), 0, 1),
(@Cat_Math, N'In Euclidean geometry, the interior angles of a triangle sum to 180 degrees.', GETDATE(), 0, 1),
(@Cat_Math, N'Factorials, denoted n!, grow very rapidly with n.', GETDATE(), 0, 1),
(@Cat_Math, N'The Fibonacci sequence begins 0, 1, 1, 2, 3, and so on.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'The Mona Lisa is displayed at the Louvre Museum in Paris.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'A standard modern piano has 88 keys.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Primary colors for additive light mixing are red, green, and blue.', GETDATE(), 0, 1),
(@Cat_Science, N'If you could compress the Earth to the size of a marble, it would become a black hole due to its immense density.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'Only about 10% of the world''s population is left-handed, a statistic that has remained relatively stable for thousands of years.', GETDATE(), 0, 1),
(@Cat_General, N'The LEGO Group is technically the world''s largest tire manufacturer by volume, producing over 300 million tiny rubber tires annually.', GETDATE(), 0, 1),
(@Cat_Geography, N'Canada has more lakes than the rest of the world''s countries combined, with approximately 879,000 lakes.', GETDATE(), 0, 1),
(@Cat_Health, N'The human body contains approximately 60,000 miles (96,500 km) of blood vessels, enough to circle the Earth more than twice.', GETDATE(), 0, 1),
(@Cat_Science, N'A single teaspoon of soil can contain more microorganisms (bacteria, fungi, etc.) than there are people on Earth (8 billion).', GETDATE(), 0, 1),
(@Cat_Nature, N'There are estimated to be over 3 trillion trees on Earth, which is roughly 7.5 times the number of stars in the Milky Way galaxy (estimated at 100–400 billion).', GETDATE(), 0, 1),
(@Cat_History, N'The University of Al Quaraouiyine in Fez, Morocco, was founded in 859 AD by Fatima al-Fihri and is recognized by UNESCO as the oldest existing, continually operating educational institution in the world.', GETDATE(), 0, 1),
(@Cat_History, N'Garrett Morgan, an African American inventor, patented the three-position traffic signal in 1923, adding the warning amber light to the existing stop-and-go system.', GETDATE(), 0, 1),
(@Cat_History, N'Matthew Henson, an African American explorer, is widely credited by historians as being the first person to actually reach the geographic North Pole in 1909, ahead of Robert Peary.', GETDATE(), 0, 1),
(@Cat_ArtsCulture, N'The tempo of music can subconsciously influence your heart rate; fast beats can increase pulse and blood pressure, while slow beats can lower them.', GETDATE(), 0, 1),
(@Cat_Science, N'Synesthesia is a neurological condition where stimulation of one sensory pathway (like hearing) leads to involuntary experiences in another (like seeing colors); it affects roughly 2–4% of the population.', GETDATE(), 0, 1),
(@Cat_Health, N'The cornea is the only part of the human body with no blood supply; it gets oxygen directly from the air.', GETDATE(), 0, 1),
(@Cat_Health, N'Human babies are born with approximately 300 bones, but by adulthood, this number decreases to 206 as bones fuse together.', GETDATE(), 0, 1),
(@Cat_Health, N'The masseter (jaw muscle) is the strongest muscle in the human body based on its weight, capable of closing teeth with a force of over 200 pounds.', GETDATE(), 0, 1),
(@Cat_Health, N'When you blush, the lining of your stomach also turns red due to the rush of adrenaline dilating blood vessels.', GETDATE(), 0, 1),
(@Cat_Health, N'Human teeth are as strong as shark teeth; the enamel that covers them is the hardest substance in the human body.', GETDATE(), 0, 1),
(@Cat_Health, N'An average human produces enough saliva in a lifetime to fill two swimming pools (roughly 25,000 liters).', GETDATE(), 0, 1),
(@Cat_Health, N'Your nose can detect roughly one trillion distinct scents, far exceeding the old estimate of just 10,000.', GETDATE(), 0, 1),
(@Cat_Health, N'Emotional tears have a different chemical composition (containing more stress hormones) than reflex tears caused by cutting onions.', GETDATE(), 0, 1),
(@Cat_Health, N'The hyoid bone, located in the throat, is the only bone in the human body not connected to any other bone.', GETDATE(), 0, 1),
(@Cat_Health, N'Your heart creates enough pressure when it pumps to squirt blood roughly 30 feet (9 meters) across a room.', GETDATE(), 0, 1),
(@Cat_Health, N'Humans are bioluminescent; we emit a tiny amount of visible light, but it is 1,000 times weaker than the human eye can pick up.', GETDATE(), 0, 1),
(@Cat_Health, N'The acid in your stomach (hydrochloric acid) is strong enough to dissolve zinc metal, yet the stomach lining renews itself quickly enough to avoid being digested.', GETDATE(), 0, 1),
(@Cat_Health, N'If you laid out all the blood vessels in an average adult end-to-end, they would circle the Earth''s equator more than twice.', GETDATE(), 0, 1),
(@Cat_Health, N'Unlike most other cells, red blood cells do not contain a nucleus, allowing more space to carry oxygen.', GETDATE(), 0, 1),
(@Cat_Health, N'Adermatoglyphia is a rare genetic condition where people are born without fingerprints.', GETDATE(), 0, 1),
(@Cat_Health, N'The liver is the only internal organ capable of naturally regenerating lost tissue; as little as 25% of a liver can grow back into a full organ.', GETDATE(), 0, 1),
(@Cat_Health, N'Synesthesia is a condition where stimulation of one sense (like hearing) leads to involuntary experiences in another (like seeing colors).', GETDATE(), 0, 1),
(@Cat_Health, N'Nerve impulses to and from the brain travel at speeds of up to 270 miles per hour (434 km/h).', GETDATE(), 0, 1),
(@Cat_Health, N'Your ears and nose never stop growing due to the effects of gravity on cartilage, though bone growth stops after puberty.', GETDATE(), 0, 1),
(@Cat_Health, N'The placebo effect can still work even when the patient knows they are taking a placebo (open-label placebo).', GETDATE(), 0, 1),
(@Cat_Health, N'Prosopagnosia, or "face blindness," is a neurological disorder where people cannot recognize faces, sometimes even their own reflection.', GETDATE(), 0, 1),
(@Cat_Health, N'Humans are the only animals known to produce emotional tears; other animals produce tears only for lubrication and cleaning.', GETDATE(), 0, 1),
(@Cat_Health, N'Phantom limb syndrome occurs when amputees feel sensations, including pain, in a limb that is no longer there.', GETDATE(), 0, 1),
(@Cat_Health, N'The vagus nerve is the longest cranial nerve, connecting the brain to the heart, lungs, and digestive tract, influencing "gut feelings."', GETDATE(), 0, 1),
(@Cat_Health, N'Fingernails grow about four times faster than toenails.', GETDATE(), 0, 1),
(@Cat_Health, N'Your brain stops growing in size around age 18, but it continues to develop and mature into your mid-20s (especially the prefrontal cortex).', GETDATE(), 0, 1),
(@Cat_Health, N'Foreign Accent Syndrome is a rare condition usually resulting from a stroke, where a patient speaks their native language with what sounds like a foreign accent.', GETDATE(), 0, 1),
(@Cat_Health, N'Humans have a "diving reflex" that slows the heart rate and constricts blood flow to extremities when the face is submerged in cold water.', GETDATE(), 0, 1),
(@Cat_Health, N'Approximately 25% of the body''s bones are located in the feet and ankles.', GETDATE(), 0, 1),
(@Cat_Health, N'The femur (thigh bone) is stronger than concrete and can support 30 times the weight of an average person.', GETDATE(), 0, 1),
(@Cat_Health, N'Anosmia is the inability to perceive odor; it can be congenital or caused by injury/illness.', GETDATE(), 0, 1),
(@Cat_Health, N'The "funny bone" is not a bone but the ulnar nerve, which runs exposed near the elbow joint.', GETDATE(), 0, 1),
(@Cat_Health, N'Heterochromia is a condition where a person has two different colored eyes due to variations in melanin distribution.', GETDATE(), 0, 1),
(@Cat_Health, N'Alice in Wonderland Syndrome (AIWS) is a neurological condition where body parts or objects appear much smaller or larger than they actually are.', GETDATE(), 0, 1),
(@Cat_Health, N'The stapes bone in the middle ear is the smallest bone in the human body, measuring roughly 3 millimeters (0.1 inch).', GETDATE(), 0, 1),
(@Cat_Health, N'Humans shed about 600,000 particles of skin every hour.', GETDATE(), 0, 1),
(@Cat_Health, N'O type blood is often called the "universal donor" for red blood cells, while AB+ is the "universal recipient."', GETDATE(), 0, 1),
(@Cat_Health, N'Sleep paralysis is a phenomenon where a person wakes up unable to move or speak, often accompanied by hallucinations.', GETDATE(), 0, 1),
(@Cat_Health, N'Ignaz Semmelweis, a 19th-century doctor, was ridiculed for suggesting doctors should wash their hands between patients to prevent infection.', GETDATE(), 0, 1),
(@Cat_General, N'One million seconds is about 11 days, but one billion seconds is about 31 years.', GETDATE(), 0, 1),
(@Cat_General, N'The mechanical cigarette lighter was invented in 1823 (Dobereiner''s Lamp), three years before the friction match was invented in 1826.', GETDATE(), 0, 1),
(@Cat_General, N'Cotton candy (fairy floss) was co-invented by a dentist named William Morrison in 1897.', GETDATE(), 0, 1),
(@Cat_General, N'High heels were originally designed for Persian men in the 10th century to help secure their feet in stirrups while riding horses.', GETDATE(), 0, 1),
(@Cat_General, N'The red liquid in a rare steak is not blood; it is myoglobin, a protein found in muscle tissue that delivers oxygen.', GETDATE(), 0, 1),
(@Cat_General, N'Saudi Arabia imports camels and sand from Australia for meat production and construction respectively.', GETDATE(), 0, 1),
(@Cat_General, N'Fredric Baur, the inventor of the Pringles can, was buried with some of his ashes inside a Pringles can per his request.', GETDATE(), 0, 1),
(@Cat_General, N'The sum of all the numbers on a standard roulette wheel (0 through 36) equals 666.', GETDATE(), 0, 1),
(@Cat_General, N'Humans share approximately 60% of their DNA with bananas, simply because all cellular life shares common housekeeping genes.', GETDATE(), 0, 1),
(@Cat_General, N'Barbie''s full fictional name is Barbara Millicent Roberts.', GETDATE(), 0, 1),
(@Cat_General, N'A "jiffy" is an actual unit of time in physics, often defined as the time it takes for light to travel one centimeter (approx 33.3 picoseconds) or in electronics as 1/60th of a second.', GETDATE(), 0, 1),
(@Cat_General, N'In 1386, a pig in France was formally tried in court and executed by public hanging for the murder of a child.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'McDonald''s Coca-Cola tastes different because it is stored in stainless steel tanks rather than plastic bags, and the syrup is pre-chilled.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Ripe peppers actually contain more Vitamin C by weight than oranges.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Red bell peppers, green bell peppers, and yellow bell peppers are often the same fruit at different stages of ripeness (though some varieties stay green).', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Historically, ketchup was a fermented fish sauce from China; tomatoes weren''t added to the recipe until the early 1800s.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Pineapples contain bromelain, an enzyme that digests protein; when you eat pineapple, it is technically eating you back (which causes the tingling sensation).', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Tonic water glows bright blue under ultraviolet light because of the presence of quinine.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'White chocolate contains no cocoa solids; it is essentially a mixture of cocoa butter, sugar, and milk.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Worcestershire sauce is made from dissolved fermented fish (anchovies), which are left to mature in barrels for 18 months.', GETDATE(), 0, 1),
(@Cat_FoodDrink, N'Pure honey is the only food that essentially lasts forever; it creates an environment too low in moisture for bacteria to survive.', GETDATE(), 0, 1),
(@Cat_Nature, N'Only about 5% of the world’s oceans have been explored, meaning we have better maps of Mars than we do of our own ocean floor.', GETDATE(), 0, 1),
(@Cat_Nature, N'The Amazon Rainforest produces roughly 20% of the world''s oxygen, but most of it is consumed by the decomposing organic matter within the forest itself.', GETDATE(), 0, 1),
(@Cat_Nature, N'There is an underwater river called the Hamza River that flows roughly 4,000 meters below the Amazon River, moving in the same direction but much slower.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first computer mouse was invented in 1964 by Doug Engelbart and was made of wood.', GETDATE(), 0, 1),
(@Cat_Tech, N'A single Google search today uses more computing power than the entire Apollo program used to send astronauts to the Moon.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first webcam was created at the University of Cambridge in 1991 solely to monitor a coffee pot so researchers wouldn''t make a wasted trip.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first hard drive, the IBM 305 RAMAC (1956), weighed over a ton and could store only 5 megabytes of data.', GETDATE(), 0, 1),
(@Cat_Tech, N'CAPTCHA is an acronym for "Completely Automated Public Turing test to tell Computers and Humans Apart."', GETDATE(), 0, 1),
(@Cat_Tech, N'The Firefox logo is not actually a fox; it depicts a red panda, an animal native to the Himalayas.', GETDATE(), 0, 1),
(@Cat_Tech, N'Samsung started as a grocery store in 1938, selling noodles and dried seafood, long before entering the electronics market.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first mobile phone call was made in 1973 by Martin Cooper of Motorola; he called his rival at Bell Labs to brag.', GETDATE(), 0, 1),
(@Cat_Tech, N'Carrier pigeons have successfully transmitted internet data (IP over Avian Carriers) but with very high latency and packet loss.', GETDATE(), 0, 1),
(@Cat_Tech, N'The programming language "Python" is named after the comedy troupe Monty Python, not the snake.', GETDATE(), 0, 1),
(@Cat_Tech, N'Apple''s first logo didn''t look like an apple; it was an intricate drawing of Isaac Newton reading under a tree.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first ever banner ad on the web appeared in 1994 with the text: "Have you ever clicked your mouse right here? You will."', GETDATE(), 0, 1),
(@Cat_Tech, N'Nokia was originally a paper mill founded in 1865 and later manufactured rubber boots and car tires.', GETDATE(), 0, 1),
(@Cat_Tech, N'Google rents a herd of roughly 200 goats to mow the lawns at their headquarters in Mountain View, California.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first computer virus, "Creeper" (1971), was harmless and simply displayed the message: "I''M THE CREEPER: CATCH ME IF YOU CAN."', GETDATE(), 0, 1),
(@Cat_Tech, N'Amazon was originally going to be named "Cadabra" (as in abracadabra), but Jeff Bezos changed it because it sounded too much like "cadaver."', GETDATE(), 0, 1),
(@Cat_Tech, N'Technologically, the core invention that enabled Wi-Fi was developed by Australian astronomers trying to detect exploding black holes.', GETDATE(), 0, 1),
(@Cat_Tech, N'Approximately 300 to 500 hours of video are uploaded to YouTube every single minute.', GETDATE(), 0, 1),
(@Cat_Tech, N'The original case of the Macintosh computer had the signatures of the entire design team molded into the inside of the plastic.', GETDATE(), 0, 1),
(@Cat_Tech, N'Phantom Vibration Syndrome is a psychological phenomenon where you feel your phone vibrate when it hasn''t.', GETDATE(), 0, 1),
(@Cat_Tech, N'NASA''s shadow network (ESnet) is capable of transfer speeds up to 91 gigabits per second, vastly faster than consumer broadband.', GETDATE(), 0, 1),
(@Cat_Tech, N'More people in the world have access to a mobile phone than have access to a flushing toilet.', GETDATE(), 0, 1),
(@Cat_Tech, N'A single Wikipedia bot, "ClueBot NG," is responsible for reverting roughly 50% of all vandalism on the site automatically.', GETDATE(), 0, 1),
(@Cat_Tech, N'The "404 Not Found" error was not named after a room number at CERN; it was simply the next logical error code after 403 (Forbidden).', GETDATE(), 0, 1),
(@Cat_Tech, N'The first text message (SMS) was sent in December 1992 and simply said "Merry Christmas."', GETDATE(), 0, 1),
(@Cat_Tech, N'Nintendo''s Game Boy was the first video game console to be played in space (by a Russian cosmonaut in 1993).', GETDATE(), 0, 1),
(@Cat_Tech, N'Digital data is growing so fast that roughly 90% of the world''s data has been generated in the last two years alone.', GETDATE(), 0, 1),
(@Cat_Tech, N'The Apollo Guidance Computer had a clock speed of roughly 0.043 MHz; a modern toaster has a more powerful processor.', GETDATE(), 0, 1),
(@Cat_Tech, N'Before settling on "Twitter," the platform was almost named "Twitch," "Jitter," or "Friendstalker."', GETDATE(), 0, 1),
(@Cat_Tech, N'Most of the money in the world exists only as digital entries on bank servers; physical cash makes up less than 10% of global currency.', GETDATE(), 0, 1),
(@Cat_Tech, N'The password for the computer controls of U.S. nuclear missiles for roughly 20 years was simply "00000000".', GETDATE(), 0, 1),
(@Cat_Tech, N'A "logic bomb" is a piece of code intentionally inserted into a software system that will execute a malicious function only when specific conditions are met.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first alarm clock could only ring at 4 a.m., designed by Levi Hutchins in 1787 solely to wake himself up for work.', GETDATE(), 0, 1),
(@Cat_Tech, N'In 1956, 5 megabytes of data weighed a ton (IBM 305 RAMAC); today, a 1 terabyte microSD card weighs less than half a gram.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first product Sony ever made was an electric rice cooker, which failed commercially because it consistently undercooked or burnt the rice.', GETDATE(), 0, 1),
(@Cat_Tech, N'Ethernet cables are twisted in pairs to cancel out electromagnetic interference from external sources and other pairs (crosstalk).', GETDATE(), 0, 1),
(@Cat_Tech, N'There is an esoteric programming language called "Whitespace" that consists entirely of spaces, tabs, and linefeeds, ignoring all non-whitespace characters.', GETDATE(), 0, 1),
(@Cat_Tech, N'The standard CD was designed to hold 74 minutes of audio to accommodate Beethoven''s Ninth Symphony, per a request by Sony''s vice president.', GETDATE(), 0, 1),
(@Cat_Tech, N'Only about 8% of the world''s currency exists as physical cash; the vast majority exists only as electronic data.', GETDATE(), 0, 1),
(@Cat_Tech, N'The universal "save" icon remains a floppy disk, despite the fact that most modern users have never physically used one.', GETDATE(), 0, 1),
(@Cat_Tech, N'GPS relies on extremely precise atomic clocks; without relativity corrections, GPS accuracy would drift by about 10 kilometers per day.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first VCR, the Ampex VRX-1000 (1956), was the size of a piano and cost $50,000.', GETDATE(), 0, 1),
(@Cat_Tech, N'Transistors in modern processors are now so small (nanometer scale) that quantum tunneling becomes a serious issue causing electron leakage.', GETDATE(), 0, 1),
(@Cat_Tech, N'Linux powers 100% of the world''s top 500 supercomputers.', GETDATE(), 0, 1),
(@Cat_Tech, N'The "@" symbol was used in accounting centuries before email to mean "at the rate of" (e.g., 10 widgets @ $2).', GETDATE(), 0, 1),
(@Cat_Tech, N'Fibre optic cables transmit data using total internal reflection, bouncing light signals down a glass core thinner than a human hair.', GETDATE(), 0, 1),
(@Cat_Tech, N'A single Bitcoin transaction currently consumes about the same amount of energy as an average US household uses in over 20 days.', GETDATE(), 0, 1),
(@Cat_Tech, N'The first known "robot" was a steam-powered pigeon created by Archytas of Tarentum in ancient Greece around 400 BC.', GETDATE(), 0, 1),
(@Cat_Tech, N'Technically, you cannot "delete" data from a hard drive; standard deletion just marks the space as available. True erasure requires overwriting.', GETDATE(), 0, 1),
(@Cat_Tech, N'Deep Blue, the IBM computer that beat chess champion Garry Kasparov in 1997, could calculate 200 million positions per second.', GETDATE(), 0, 1),
(@Cat_Tech, N'The QR code (Quick Response) was originally invented in 1994 by Denso Wave to track automotive parts during manufacturing.', GETDATE(), 0, 1),
(@Cat_Tech, N'Bluetooth was specifically designed to replace the RS-232 data cables that were cluttering up desks in the 1990s.', GETDATE(), 0, 1),
(@Cat_Tech, N'The Voyager 1 spacecraft, launched in 1977, runs on less computing memory than a modern car key fob.', GETDATE(), 0, 1),
(@Cat_Tech, N'Domain names were free to register until 1995.', GETDATE(), 0, 1),
(@Cat_Tech, N'A "hacker" originally meant someone who was good at making furniture with an axe; later, at MIT, it meant someone who found clever solutions to problems.', GETDATE(), 0, 1),
(@Cat_Tech, N'The most expensive domain name ever sold was Voice.com for $30 million in 2019.', GETDATE(), 0, 1),
(@Cat_Tech, N'Steve Jobs originally wanted the iPhone to have a permanent "Back" button, but the interface designers convinced him software navigation was better.', GETDATE(), 0, 1),
(@Cat_Tech, N'Early computer memory was made of magnetic cores threaded by hand onto wires, resembling tiny woven metal donuts.', GETDATE(), 0, 1),
(@Cat_Tech, N'The very first digital camera was invented by Kodak in 1975; it weighed 8 pounds (3.6 kg) and took 23 seconds to record a single black-and-white image to a cassette tape.', GETDATE(), 0, 1),
(@Cat_Tech, N'A single gram of DNA has the theoretical capacity to store 215 petabytes (215 million gigabytes) of data.', GETDATE(), 0, 1),
(@Cat_Tech, N'The "Apple I" computer sold for $666.66, not for any occult reason, but because Steve Wozniak liked typing repeating digits.', GETDATE(), 0, 1),
(@Cat_Tech, N'In the 1990s, 50% of all CDs produced worldwide were for AOL (America Online) free trial disks.', GETDATE(), 0, 1),
(@Cat_Tech, N'Mark Zuckerberg chose blue for Facebook’s interface because he has red-green color blindness; blue is the color he sees most clearly.', GETDATE(), 0, 1),
(@Cat_Tech, N'The "Nokia Tune" ringtone is actually a snippet from a classical guitar waltz composed in 1902 called "Gran Vals" by Francisco Tárrega.', GETDATE(), 0, 1),
(@Cat_Tech, N'eBay''s first sold item was a broken laser pointer for $14.83. When the founder contacted the buyer to explain it was broken, the buyer replied, "I''m a collector of broken laser pointers."', GETDATE(), 0, 1),
(@Cat_Tech, N'Nintendo was founded in 1889—over 100 years before the Game Boy—originally to manufacture Hanafuda playing cards.', GETDATE(), 0, 1),
(@Cat_Tech, N'YouTube was originally founded in 2005 as a video-dating site called "Tune In Hook Up" before pivoting to general video sharing.', GETDATE(), 0, 1),
(@Cat_Tech, N'In 2012, a software glitch at Knight Capital Group caused the company to lose $440 million in just 45 minutes.', GETDATE(), 0, 1),
(@Cat_Tech, N'The USB symbol on connectors is modeled after Poseidon’s trident, representing the power to connect to multiple different devices.', GETDATE(), 0, 1),
(@Cat_Tech, N'If you opened a hard drive and scaled up the read/write head mechanisms, it would be comparable to a Boeing 747 flying 6 inches above the ground at 7,500 mph.', GETDATE(), 0, 1),
(@Cat_Tech, N'The term "Spam" for junk email is named after the Monty Python sketch where the word "Spam" is repeated incessantly, drowning out all other conversation.', GETDATE(), 0, 1),
(@Cat_Tech, N'Computer code was often distributed in magazines in the 1980s; users had to manually type thousands of lines of code into their PC to play a game.', GETDATE(), 0, 1),
(@Cat_Tech, N'Silicon Valley was historically known as "The Valley of Heart’s Delight" due to its high concentration of fruit orchards before the tech boom.', GETDATE(), 0, 1),
(@Cat_Tech, N'The term "glitch" entered technical jargon via radio broadcasters; it comes from the German "glitschen" (to slip) and Yiddish "gletshn" (to slide or skid).', GETDATE(), 0, 1),
(@Cat_Tech, N'The Apollo 11 source code includes a file named "BURN_BABY_BURN" which handled the master ignition routine.', GETDATE(), 0, 1),
(@Cat_Tech, N'IBM’s AI "Watson" is named after the company’s first CEO, Thomas J. Watson, not Sherlock Holmes’s assistant.', GETDATE(), 0, 1),
(@Cat_Tech, N'There is an esoteric programming language called "Shakespeare" where the source code reads exactly like a play, with characters entering the stage to manipulate variables.', GETDATE(), 0, 1),
(@Cat_Tech, N'When the first iPod was shown to Steve Jobs, he dropped it in an aquarium to prove there was air space inside (bubbles floated up), meaning it could be made smaller.', GETDATE(), 0, 1),
(@Cat_Tech, N'The "Scroll Lock" key on keyboards is a relic from the DOS era; it was originally used to scroll the page of text without moving the cursor, but is rarely used today.', GETDATE(), 0, 1),
(@Cat_Tech, N'The word "Phishing" is spelled with a "ph" as a tribute to "phone phreaking," an early hacker culture of exploring and exploiting telecommunication systems.', GETDATE(), 0, 1),
(@Cat_Tech, N'The domain name "cars.com" was valued at $872 million in the company''s SEC filing, making it one of the most valuable domains in history.', GETDATE(), 0, 1),
(@Cat_Tech, N'A "Heisenbug" is a computer bug that disappears or alters its behavior when an attempt is made to study it (a play on the Heisenberg Uncertainty Principle).', GETDATE(), 0, 1),
(@Cat_Tech, N'Google’s original search engine name was "BackRub" because it analyzed "backlinks" to understand the importance of a website.', GETDATE(), 0, 1);
GO
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
INSERT INTO Achievements (Code, Name, Category, Threshold, RewardXP, CreatedDate)
SELECT s.Code, s.Name, s.Category, s.Threshold, s.RewardXP, GETDATE()
FROM Seeds s
LEFT JOIN Achievements a ON a.Code = s.Code
WHERE a.AchievementID IS NULL;
GO

-- Step 17: Verify the setup
SELECT 'Categories' AS TableName, COUNT(*) AS RecordCount FROM Categories
UNION ALL SELECT 'Facts', COUNT(*) FROM Facts
UNION ALL SELECT 'ProfileFacts', COUNT(*) FROM ProfileFacts
UNION ALL SELECT 'ReviewLogs', COUNT(*) FROM ReviewLogs
UNION ALL SELECT 'ReviewSessions', COUNT(*) FROM ReviewSessions
UNION ALL SELECT 'AIUsageLogs', COUNT(*) FROM AIUsageLogs
UNION ALL SELECT 'GamificationProfile', COUNT(*) FROM GamificationProfile
UNION ALL SELECT 'Achievements', COUNT(*) FROM Achievements
UNION ALL SELECT 'AchievementUnlocks', COUNT(*) FROM AchievementUnlocks;