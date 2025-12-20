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
| **`TotalQuestionTokens`** / **`TotalQuestionCost`** | `INT/DECIMAL` | **Question Generation Tracking.** Aggregates cost from `QuestionLogs` for LLM-generated questions. |
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
| **`CreatedBy`** | `INT (FK)` | **Owner.** Points to `GamificationProfile.ProfileID`. All analytics and counts are scoped to the active profile’s categories only. |

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
| **`QuestionsRefreshCountdown`** | `INT` | **Question Refresh Countdown.** Starts at 50, decrements by 1 each review. When it reaches 0, delete old questions, regenerate fresh ones, and reset to 50. |
| **`CreatedBy`** | `INT (FK)` | **Owner.** Points to `GamificationProfile.ProfileID`. Used to scope analytics so each profile only sees its own facts. |

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
| **`TimedOut`** | `BIT` | **Idle Flag.** Set to `1` if the view ended because the session timed out (`handle_idle_timeout`). Drives the timeout chart. |
| **`Action`** | `NVARCHAR` | **Type.** 'view', 'add', 'edit', 'delete'. Allows filtering logs by type. |
| **`FactEdited`** | `BIT` | **Edit Marker.** `1` when the log was created from an edit action. Used to distinguish edits from plain views. |
| **`FactDeleted`** | `BIT` | **State Flag.** `1` if this log represents a deletion event. |
| **`FactContentSnapshot`** | `NVARCHAR` | **History.** Copies the text of the fact *at the moment of deletion*. Ensures "Deleted" entries in analytics still show what was deleted even after the `Facts` table row is gone. |
| **`CategoryIDSnapshot`** | `INT` | **Category History.** Captures the category at the time of the log so analytics can still bucket deleted/edited facts correctly. |

---

### 7. Table: `AIUsageLogs`
**Definition:** Audit trail for API calls to LLMs (Together AI / DeepSeek).
**Primary Use:** Cost estimation and debugging AI latency.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`AIUsageID`** | `INT (PK)` | **Identity.** |
| **`FactID`** | `INT (FK, NULL)` | **Target (optional).** Links the AI call to a fact. NULL if not tied to a fact. |
| **`SessionID`** | `INT (FK, NULL)` | **Session (optional).** Associates the AI call with an active review session if present. |
| **`ProfileID`** | `INT (FK)` | **User.** Defaults to 1; used for per-profile cost/stats. |
| **`OperationType`** | `NVARCHAR` | **Context.** Usually 'EXPLANATION'. |
| **`Status`** | `NVARCHAR` | **Outcome.** 'SUCCESS' or 'FAILED'. Drives success/failure counts. |
| **`ModelName`** | `NVARCHAR` | **Model Used.** Stored for debugging/analytics (shown in recent AI table). |
| **`Provider`** | `NVARCHAR` | **Provider Tag.** Used to group cost/latency by provider. |
| **`InputTokens`** | `INT` | **Cost Basis.** Number of tokens sent to AI. |
| **`OutputTokens`** | `INT` | **Cost Basis.** Number of tokens received from AI. |
| **`TotalTokens`** | `COMPUTED` | **Sum.** `InputTokens + OutputTokens`; used directly in analytics cost charts. |
| **`Cost`** | `DECIMAL` | **Financial.** Calculated in Python based on `config.AI_PRICING` and stored here. |
| **`CurrencyCode`** | `CHAR(3)` | **Currency.** Defaults to 'USD'. |
| **`ReadingDurationSec`** | `INT` | **Engagement.** How long the user kept the AI explanation popup open. |
| **`LatencyMs`** | `INT` | **Performance.** Time taken for the API to respond. |
| **`CreatedAt`** | `DATETIME` | **Timestamp.** When the AI call was logged. Used for daily cost/timeline charts. |

---

### 8. Table: `Questions`
**Definition:** Cache of pre-generated LLM questions for each fact (up to 3 per fact).
**Primary Use:** Storing reusable questions to avoid repeated LLM calls. When a fact needs a question, check this table first — only call the LLM if fewer than 3 questions exist.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`QuestionID`** | `INT (PK)` | **Identity.** |
| **`FactID`** | `INT (FK)` | **Target.** Links the cached question to the source fact/answer. **ON DELETE CASCADE**: If fact is deleted, its cached questions are removed. |
| **`QuestionText`** | `NVARCHAR(MAX)` | **Content.** The actual LLM-generated question text. |
| **`ModelName`** | `NVARCHAR` | **Model Used.** Stored for debugging/analytics. |
| **`Provider`** | `NVARCHAR` | **Provider Tag.** Used to group cost/latency by provider. |
| **`InputTokens`** | `INT` | **Cost Basis.** Number of tokens sent to AI (fact content + prompt). |
| **`OutputTokens`** | `INT` | **Cost Basis.** Number of tokens in the generated question. |
| **`TotalTokens`** | `COMPUTED` | **Sum.** `InputTokens + OutputTokens`; used in cost analytics. |
| **`Cost`** | `DECIMAL` | **Financial.** Calculated in Python based on `config.AI_PRICING` and stored here. |
| **`CurrencyCode`** | `CHAR(3)` | **Currency.** Defaults to 'USD'. |
| **`LatencyMs`** | `INT` | **Performance.** Time taken for the API to generate the question. |
| **`Status`** | `NVARCHAR` | **Outcome.** 'SUCCESS' or 'FAILED'. Drives success/failure counts. |
| **`TimesShown`** | `INT` | **Usage Counter.** How many times this cached question has been shown to users. |
| **`LastShownAt`** | `DATETIME` | **Usage Timestamp.** When this question was last displayed. |
| **`GeneratedAt`** | `DATETIME` | **Timestamp.** When the question was generated by the LLM. |

---

### 9. Table: `QuestionLogs`
**Definition:** Usage log tracking when cached questions are shown to users.
**Primary Use:** Measuring reading time analytics and engagement metrics for the "question-first" learning mode. Links to `Questions` (not directly to `Facts`).

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`QuestionLogID`** | `INT (PK)` | **Identity.** |
| **`QuestionID`** | `INT (FK)` | **Target.** Links to the cached question that was shown. **ON DELETE CASCADE**: If question is deleted, the log is removed. |
| **`SessionID`** | `INT (FK, NULL)` | **Session (optional).** Associates the question view with an active review session. |
| **`ProfileID`** | `INT (FK)` | **User.** Defaults to 1; used for per-profile stats. |
| **`QuestionShownAt`** | `DATETIME` | **Start Timer.** When the question was displayed to the user. |
| **`AnswerRevealedAt`** | `DATETIME` | **End Timer.** When the user clicked to reveal the answer/fact. |
| **`QuestionReadingDurationSec`** | `INT` | **Engagement.** Calculated time spent reading the question before revealing the answer. |
| **`CreatedAt`** | `DATETIME` | **Timestamp.** When the log entry was created. |

---

### 10. Table: `Achievements`
**Definition:** The "Rulebook" for gamification.
**Primary Use:** Static lookup table. The app queries this to see "What is the requirement for the next 'Known' achievement?"

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`AchievementID`** | `INT (PK)` | **Identity.** |
| **`Code`** | `NVARCHAR` | **Unique Key.** e.g., `KNOWN_10`. Used in code to check specific unlocks. |
| **`Name`** | `NVARCHAR` | **Display.** The human-readable achievement title shown in popups and tables. |
| **`Category`** | `NVARCHAR` | **Type.** 'streak', 'reviews', 'known', etc. Used to filter which achievements to check after a specific user action. |
| **`Threshold`** | `INT` | **Logic.** The number required to unlock (e.g., 50 reviews). |
| **`RewardXP`** | `INT` | **Incentive.** Amount of XP added to `GamificationProfile.XP` upon unlock. |
| **`CreatedDate`** | `DATETIME` | **Audit.** When the achievement definition was created/seeded. |

---

### 11. Table: `AchievementUnlocks`
**Definition:** The "Trophy Case" for the user.
**Primary Use:** Preventing duplicate rewards.

| Column | Data Type | Definition & Application Use Case |
| :--- | :--- | :--- |
| **`UnlockID`** | `INT (PK)` | **Identity.** |
| **`AchievementID`** | `INT (FK)` | **Trophy.** Link to the definition. |
| **`ProfileID`** | `INT (FK)` | **User.** Link to the winner. |
| **`UnlockDate`** | `DATETIME` | **History.** When it was earned. |
| **`Notified`** | `BIT` | **UI State.** `0` = User hasn't seen the popup yet. `1` = User saw it. Used to queue achievement toasts in the UI. |
