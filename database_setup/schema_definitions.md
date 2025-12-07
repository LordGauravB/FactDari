This is a comprehensive reference guide defining every table and column in your schema, mapped directly to how your Python application logic (`FactDari.py`, `gamification.py`, `analytics_factdari.py`) utilizes them.

---

### 1. Table: `GamificationProfile`
**Definition:** Stores the "save state" for a user. Currently, your app defaults to using `ProfileID=1`, but the design supports multiple users.
**Primary Use:** Displaying the top-left stats (Level/XP) and tracking lifetime progress for achievements.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`ProfileID`** | `INT (PK)` | **Identity.** The app calls `get_active_profile_id()` to fetch this. Defaults to 1. All user actions are linked to this ID. |
| **`XP`** | `INT` | **Experience Points.** Updated by `gamification.award_xp()` whenever a user reviews a fact, adds a card, or unlocks an achievement. |
| **`Level`** | `INT` | **Current Level.** Calculated in Python based on `XP` curves defined in `config.py` and stored here to avoid recalculating it on every render. |
| **`TotalReviews`** | `INT` | **Lifetime Counter.** Incremented in `track_fact_view`. Used to unlock "Review Master" style achievements. |
| **`TotalKnown`** | `INT` | **Lifetime Counter.** Incremented when user clicks the "Known" (Easy) button. Triggers "Knowledge" achievements. |
| **`TotalFavorites`** | `INT` | **Lifetime Counter.** Incremented when user clicks the "Star" button. |
| **`TotalAdds`** / **`Edits`** / **`Deletes`** | `INT` | **Activity Counters.** Incremented during CRUD operations to reward content curation. |
| **`TotalAITokens`** / **`TotalAICost`** | `INT/DECIMAL` | **Usage Tracking.** Aggregates cost from `AIUsageLogs`. Used to display total spend or potentially limit usage. |
| **`CurrentStreak`** | `INT` | **Streak Counter.** Updated by `daily_checkin()`. Resets to 0 if `LastCheckinDate` is older than yesterday. |
| **`LongestStreak`** | `INT` | **High Score.** Stores the highest value `CurrentStreak` has ever reached. |
| **`LastCheckinDate`** | `DATE` | **State Marker.** The last date the user opened the app or reviewed a card. Used to calculate if a streak continues or breaks. |

---

### 2. Table: `Categories`
**Definition:** Organizational buckets for facts.
**Primary Use:** Populating the dropdown filter in the main window and Add/Edit popups.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`CategoryID`** | `INT (PK)` | **Reference.** Linked by `Facts` table. |
| **`CategoryName`** | `NVARCHAR` | **Display Label.** Shown in the `Combobox` dropdown in the UI. Must be unique. |
| **`Description`** | `NVARCHAR` | **Metadata.** Optional text describing the category (currently unused in UI). |
| **`IsActive`** | `BIT` | **Soft Delete.** If set to 0, the category won't appear in the dropdown, but historical data remains. |
| **`CreatedDate`** | `DATETIME` | **Audit.** When the category was created. |

---

### 3. Table: `Facts`
**Definition:** The central repository of flashcard content.
**Primary Use:** Stores the actual text displayed on the card.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`FactID`** | `INT (PK)` | **Reference.** The core ID used throughout the app to link logs, user states, and AI usage. |
| **`CategoryID`** | `INT (FK)` | **Grouping.** Links the fact to a Category. |
| **`Content`** | `NVARCHAR` | **Payload.** The actual text string displayed on the `fact_label` in the GUI. |
| **`ContentKey`** | `COMPUTED` | **Deduplication.** A persisted column that lowercases text and removes whitespace. A unique index on this prevents users from adding duplicate facts via `add_new_fact()`. |
| **`DateAdded`** | `DATE` | **Timeline.** Used in analytics to show "Facts Added Over Time". |
| **`TotalViews`** | `INT` | **Global Stat.** A counter of how many times this fact has been seen by *anyone* (global popularity). |

---

### 4. Table: `ProfileFacts`
**Definition:** Stores **user-specific** relationships to facts.
**Primary Use:** Deciding if the "Star" (Favorite) or "Easy" icons should be gold or white when a card loads.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`ProfileFactID`** | `INT (PK)` | **Identity.** Internal ID. |
| **`ProfileID`** | `INT (FK)` | **User Link.** Links this state to the active profile. |
| **`FactID`** | `INT (FK)` | **Fact Link.** Links to the specific fact. **ON DELETE CASCADE**: If a Fact is deleted, this user state is automatically removed. |
| **`PersonalReviewCount`** | `INT` | **Personal Stat.** How many times *this specific user* has viewed this fact. Used for "Spaced Repetition" logic (future proofing). |
| **`IsFavorite`** | `BIT` | **UI State.** `1` = Gold Star icon, `0` = White Star icon. Filter used when "Favorites" is selected in dropdown. |
| **`IsEasy`** | `BIT` | **UI State.** `1` = Gold checkmark (Known), `0` = Gray checkmark. Filter used when "Known" is selected in dropdown. |
| **`LastViewedByUser`** | `DATETIME` | **Sorting.** Used by analytics to determine "Least Reviewed" or "Neglected" cards. |
| **`KnownSince`** | `DATETIME` | **Learning Velocity.** Timestamp of when the fact was first marked as "Known". Set only once via `COALESCE(KnownSince, GETDATE())` when toggling to known. Used in analytics to calculate "days to know" for the Learning Velocity chart. |

---

### 5. Table: `ReviewSessions`
**Definition:** Represents a "block" of time the user spent using the app.
**Primary Use:** Calculating "Efficiency" (Facts per Minute) and generating the "Time Spent" charts in analytics.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`SessionID`** | `INT (PK)` | **Grouping.** Created when `start_reviewing()` is called. Links multiple `ReviewLogs`. |
| **`ProfileID`** | `INT (FK)` | **User Link.** Who owns this session. |
| **`StartTime`** | `DATETIME` | **Start Timer.** Set when the user enters the review screen. |
| **`EndTime`** | `DATETIME` | **End Timer.** Set when user clicks "Home" or closes the app. |
| **`DurationSeconds`** | `INT` | **Analysis.** Calculated as `DATEDIFF(second, Start, End)`. Used for "Average Session Length" charts. |
| **`TimedOut`** | `BIT` | **Logic Flag.** Set to `1` if the session was auto-closed due to inactivity (`IDLE_TIMEOUT_SECONDS`). Excludes these sessions from efficiency stats. |
| **`FactsAdded/Edited/Deleted`** | `INT` | **Summary Stats.** Counters for actions performed specifically during this session. |

---

### 6. Table: `ReviewLogs`
**Definition:** A granular log of every single interaction (view, add, edit, delete).
**Primary Use:** The raw data source for the Heatmap, Activity Timeline, and "Cards Reviewed Today" counters.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`ReviewLogID`** | `INT (PK)` | **Identity.** |
| **`FactID`** | `INT (FK)` | **Target.** The fact being interacted with. **ON DELETE SET NULL**: If fact is deleted, the log remains for stats but `FactID` becomes NULL. |
| **`ReviewDate`** | `DATETIME` | **Timestamp.** Exact moment the card was shown. Used for Heatmap (Hour of Day). |
| **`SessionDuration`** | `INT` | **Reading Time.** How long the user stared at *this specific card*. The app pauses this timer if a popup opens. |
| **`SessionID`** | `INT (FK)` | **Parent Link.** Groups this view into a `ReviewSession`. |
| **`Action`** | `NVARCHAR` | **Type.** 'view', 'add', 'edit', 'delete'. Allows filtering logs by type. |
| **`FactDeleted`** | `BIT` | **State Flag.** `1` if this log represents a deletion event. |
| **`FactContentSnapshot`** | `NVARCHAR` | **History.** Copies the text of the fact *at the moment of deletion*. Ensures "Deleted" entries in analytics still show what was deleted even after the `Facts` table row is gone. |

---

### 7. Table: `AIUsageLogs`
**Definition:** Audit trail for API calls to LLMs (Together AI / DeepSeek).
**Primary Use:** Cost estimation and debugging AI latency.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`AIUsageID`** | `INT (PK)` | **Identity.** |
| **`OperationType`** | `NVARCHAR` | **Context.** Usually 'EXPLANATION'. |
| **`InputTokens`** | `INT` | **Cost Basis.** Number of tokens sent to AI. |
| **`OutputTokens`** | `INT` | **Cost Basis.** Number of tokens received from AI. |
| **`Cost`** | `DECIMAL` | **Financial.** Calculated in Python based on `config.AI_PRICING` and stored here. |
| **`ReadingDurationSec`** | `INT` | **Engagement.** How long the user kept the AI explanation popup open. |
| **`LatencyMs`** | `INT` | **Performance.** Time taken for the API to respond. |

---

### 8. Table: `Achievements`
**Definition:** The "Rulebook" for gamification.
**Primary Use:** Static lookup table. The app queries this to see "What is the requirement for the next 'Known' achievement?"

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`Code`** | `NVARCHAR` | **Unique Key.** e.g., `KNOWN_10`. Used in code to check specific unlocks. |
| **`Category`** | `NVARCHAR` | **Type.** 'streak', 'reviews', 'known', etc. Used to filter which achievements to check after a specific user action. |
| **`Threshold`** | `INT` | **Logic.** The number required to unlock (e.g., 50 reviews). |
| **`RewardXP`** | `INT` | **Incentive.** Amount of XP added to `GamificationProfile.XP` upon unlock. |

---

### 9. Table: `AchievementUnlocks`
**Definition:** The "Trophy Case" for the user.
**Primary Use:** Preventing duplicate rewards.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`UnlockID`** | `INT (PK)` | **Identity.** |
| **`AchievementID`** | `INT (FK)` | **Trophy.** Link to the definition. |
| **`ProfileID`** | `INT (FK)` | **User.** Link to the winner. |
| **`UnlockDate`** | `DATETIME` | **History.** When it was earned. |
| **`Notified`** | `BIT` | **UI State.** `0` = User hasn't seen the popup yet. `1` = User saw it. Used to queue achievement toasts in the UI. |