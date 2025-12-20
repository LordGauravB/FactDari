from flask import Flask, render_template, jsonify, Response, request
import pyodbc
from datetime import datetime, timedelta, date
import config  # Import the config module

app = Flask(__name__) 

# Get database connection string from config
CONN_STR = config.get_connection_string()

def fetch_query(query, params=None):
    """Execute a SELECT query and return the results"""
    with pyodbc.connect(CONN_STR) as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_default_profile_id():
    """Fetch the first profile id, defaulting to 1 if not found."""
    try:
        rows = fetch_query("SELECT TOP 1 ProfileID FROM GamificationProfile ORDER BY ProfileID")
        if rows:
            pid = rows[0].get('ProfileID') if isinstance(rows[0], dict) else rows[0][0]
            return int(pid) if pid is not None else 1
    except Exception:
        pass
    return 1

@app.route('/')
def index():
    """Render the main analytics page"""
    return render_template('analytics_factdari.html')

# No static resource route is needed; template uses CDN-only assets

# No favicon route; allow browser default or static hosting if desired

@app.route('/api/chart-data')
def chart_data():
    """Get all chart data for FactDari analytics"""
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    profile_id = get_default_profile_id()
    
    # Check if we need to return all facts
    return_all = request.args.get('all', 'false').lower() == 'true'
    
    data = {
        # Category distribution (active categories only)
        'categoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(f.FactID) as FactCount
            FROM Categories c
            LEFT JOIN Facts f 
              ON c.CategoryID = f.CategoryID
             AND f.CreatedBy = ?
            WHERE c.IsActive = 1
              AND c.CreatedBy = ?
            GROUP BY c.CategoryName
            ORDER BY COUNT(f.FactID) DESC
        """, (profile_id, profile_id)),

        # Count of active categories
        'activeCategoriesCount': fetch_query("""
            SELECT COUNT(*) as ActiveCount
            FROM Categories
            WHERE IsActive = 1 AND CreatedBy = ?
        """, (profile_id,)),
        
        # Facts viewed per day (last 30 days)
        'factsViewedPerDay': fetch_query("""
            SELECT 
                CONVERT(varchar, rl.ReviewDate, 23) as Date,
                COUNT(DISTINCT rl.FactID) as FactsReviewed,
                COUNT(*) as TotalReviews
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rl.ReviewDate >= ? AND (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND rs.ProfileID = ?
            GROUP BY CONVERT(varchar, rl.ReviewDate, 23)
            ORDER BY CONVERT(varchar, rl.ReviewDate, 23)
        """, (thirty_days_ago, profile_id)),
        
        # Most reviewed facts (top 10 for display)
        'mostReviewedFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) AS ReviewCount,
                c.CategoryName,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.CreatedBy = ?
              AND c.CreatedBy = ?
              AND (COALESCE(pf.PersonalReviewCount, 0) > 0 OR f.TotalViews > 0)
            ORDER BY COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) DESC, f.TotalViews DESC
        """, (profile_id, profile_id, profile_id)),
        
        # Least reviewed facts (include 0 reviews; show zeros first, then oldest last viewed)
        'leastReviewedFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) AS ReviewCount,
                c.CategoryName,
                CASE 
                    WHEN pf.LastViewedByUser IS NULL THEN NULL
                    ELSE DATEDIFF(day, pf.LastViewedByUser, GETDATE())
                END as DaysSinceReview,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY 
                COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) ASC,
                CASE WHEN pf.LastViewedByUser IS NULL THEN 0 ELSE 1 END ASC,
                pf.LastViewedByUser ASC
        """, (profile_id, profile_id, profile_id)),
        
        # Facts added over time
        'factsAddedOverTime': fetch_query("""
            SELECT Date, FactsAdded
            FROM (
                SELECT TOP 10 
                    CONVERT(varchar, DateAdded, 23) as Date,
                    COUNT(FactID) as FactsAdded
                FROM Facts
                WHERE CreatedBy = ?
                GROUP BY CONVERT(varchar, DateAdded, 23)
                ORDER BY CONVERT(varchar, DateAdded, 23) DESC
            ) as RecentDates
            ORDER BY Date ASC
        """, (profile_id,)),
        
        # Review frequency heatmap data (last 30 days, by hour)
        'reviewHeatmap': fetch_query("""
            SET DATEFIRST 7; -- Ensure Sunday=1 for consistent weekday mapping
            SELECT 
                DATEPART(hour, rl.ReviewDate) as Hour,
                DATEPART(weekday, rl.ReviewDate) as DayOfWeek,
                COUNT(*) as ReviewCount
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rl.ReviewDate >= ? AND (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND rs.ProfileID = ?
            GROUP BY DATEPART(hour, rl.ReviewDate), DATEPART(weekday, rl.ReviewDate)
            ORDER BY DATEPART(weekday, rl.ReviewDate), DATEPART(hour, rl.ReviewDate)
        """, (thirty_days_ago, profile_id)),
        
        # Category distribution for favorite cards
        'favoriteCategoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(pf.FactID) as FavoriteCount
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.CreatedBy = ?
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ? AND pf.IsFavorite = 1
            WHERE c.CreatedBy = ?
            GROUP BY c.CategoryName
            HAVING COUNT(pf.FactID) > 0
            ORDER BY COUNT(pf.FactID) DESC
        """, (profile_id, profile_id, profile_id)),
        
        # Category distribution for known/easy cards
        'knownCategoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(pf.FactID) as KnownCount
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.CreatedBy = ?
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ? AND pf.IsEasy = 1
            WHERE c.CreatedBy = ?
            GROUP BY c.CategoryName
            HAVING COUNT(pf.FactID) > 0
            ORDER BY COUNT(pf.FactID) DESC
        """, (profile_id, profile_id, profile_id)),
        
        # All favorite facts
        'allFavoriteFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                COALESCE(pf.PersonalReviewCount, 0) AS ReviewCount,
                c.CategoryName,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy,
                CASE 
                    WHEN pf.LastViewedByUser IS NULL THEN NULL
                    ELSE DATEDIFF(day, pf.LastViewedByUser, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE COALESCE(pf.IsFavorite, 0) = 1
              AND f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY NEWID()
        """ if not return_all else """
            SELECT
                f.Content,
                COALESCE(pf.PersonalReviewCount, 0) AS ReviewCount,
                c.CategoryName,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy,
                CASE 
                    WHEN pf.LastViewedByUser IS NULL THEN NULL
                    ELSE DATEDIFF(day, pf.LastViewedByUser, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE COALESCE(pf.IsFavorite, 0) = 1
              AND f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) DESC, f.TotalViews DESC
        """, (profile_id, profile_id, profile_id) if not return_all else (profile_id, profile_id, profile_id)),
        
        # All known facts
        'allKnownFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                COALESCE(pf.PersonalReviewCount, 0) AS ReviewCount,
                c.CategoryName,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy,
                CASE 
                    WHEN pf.LastViewedByUser IS NULL THEN NULL
                    ELSE DATEDIFF(day, pf.LastViewedByUser, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE COALESCE(pf.IsEasy, 0) = 1
              AND f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY NEWID()
        """ if not return_all else """
            SELECT
                f.Content,
                COALESCE(pf.PersonalReviewCount, 0) AS ReviewCount,
                c.CategoryName,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy,
                CASE 
                    WHEN pf.LastViewedByUser IS NULL THEN NULL
                    ELSE DATEDIFF(day, pf.LastViewedByUser, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE COALESCE(pf.IsEasy, 0) = 1
              AND f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) DESC, f.TotalViews DESC
        """, (profile_id, profile_id, profile_id) if not return_all else (profile_id, profile_id, profile_id)),
        
        # Categories viewed today
        'categoriesViewedToday': fetch_query("""
            SELECT c.CategoryName, COUNT(DISTINCT rl.FactID) as ViewedCount
            FROM Categories c
            INNER JOIN Facts f ON c.CategoryID = f.CategoryID
            INNER JOIN FactLogs rl ON f.FactID = rl.FactID
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE CONVERT(date, rl.ReviewDate) = CONVERT(date, GETDATE())
              AND (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND rs.ProfileID = ?
              AND c.CreatedBy = ?
              AND f.CreatedBy = ?
            GROUP BY c.CategoryName
            ORDER BY COUNT(DISTINCT rl.FactID) DESC
        """, (profile_id, profile_id, profile_id)),
        
        # Review streak data
        'reviewStreak': calculate_review_streak(profile_id),
        
        # Category review distribution
        'categoryReviews': fetch_query("""
            SELECT 
                c.CategoryName,
                SUM(COALESCE(pf.PersonalReviewCount, 0)) as TotalReviews,
                AVG(COALESCE(pf.PersonalReviewCount, 0)) as AvgReviewsPerFact
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.CreatedBy = ?
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            WHERE c.CreatedBy = ?
            GROUP BY c.CategoryName
            ORDER BY SUM(COALESCE(pf.PersonalReviewCount, 0)) DESC
        """, (profile_id, profile_id, profile_id)),
        
        # Count of favorite facts
        'favoritesCount': fetch_query("""
            SELECT COUNT(*) as FavoriteCount
            FROM ProfileFacts
            WHERE ProfileID = ? AND IsFavorite = 1
        """, (profile_id,)),
        
        # Count of known facts (marked as easy)
        'knownFactsCount': fetch_query("""
            SELECT COUNT(*) as KnownCount
            FROM ProfileFacts
            WHERE ProfileID = ? AND IsEasy = 1
        """, (profile_id,)),

        # Count of distinct facts viewed today
        'viewedTodayCount': fetch_query("""
            SELECT COUNT(DISTINCT rl.FactID) as ViewedTodayCount
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE CONVERT(date, rl.ReviewDate) = CONVERT(date, GETDATE())
              AND (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND rs.ProfileID = ?
        """, (profile_id,)),

        # Duration-based analytics
        'sessionDurationStats': fetch_query("""
            SELECT 
                AVG(DurationSeconds) as AvgDuration,
                MIN(DurationSeconds) as MinDuration,
                MAX(DurationSeconds) as MaxDuration,
                SUM(DurationSeconds) as TotalDuration,
                COUNT(*) as SessionCount
            FROM ReviewSessions
            WHERE DurationSeconds IS NOT NULL AND DurationSeconds > 0
              AND ProfileID = ?
        """, (profile_id,)),
        
        # Additional session metrics
        'avgFactsPerSession': fetch_query("""
            SELECT 
                AVG(CAST(FactCount as FLOAT)) as AvgFactsPerSession
            FROM (
                SELECT 
                    s.SessionID,
                    COUNT(DISTINCT rl.FactID) as FactCount
                FROM ReviewSessions s
                LEFT JOIN FactLogs rl ON s.SessionID = rl.SessionID AND (rl.Action IS NULL OR rl.Action = 'view') AND COALESCE(rl.TimedOut, 0) = 0
                WHERE s.DurationSeconds IS NOT NULL AND s.DurationSeconds > 0
                  AND s.ProfileID = ?
                GROUP BY s.SessionID
            ) as SessionFacts
        """, (profile_id,)),
        
        'bestEfficiency': fetch_query("""
            SELECT TOP 1
                CASE 
                    WHEN s.DurationSeconds > 0 
                    THEN CAST(COUNT(DISTINCT rl.FactID) * 60.0 / s.DurationSeconds as DECIMAL(10,2))
                    ELSE 0 
                END as BestFactsPerMinute
            FROM ReviewSessions s
            LEFT JOIN FactLogs rl ON s.SessionID = rl.SessionID AND (rl.Action IS NULL OR rl.Action = 'view') AND COALESCE(rl.TimedOut, 0) = 0
            WHERE s.DurationSeconds IS NOT NULL AND s.DurationSeconds > 0
              AND s.ProfileID = ?
            GROUP BY s.SessionID, s.DurationSeconds
            ORDER BY BestFactsPerMinute DESC
        """, (profile_id,)),
        
        'sessionDurationDistribution': fetch_query("""
            SELECT 
                CASE 
                    WHEN DurationSeconds < 60 THEN '< 1 min'
                    WHEN DurationSeconds < 300 THEN '1-5 min'
                    WHEN DurationSeconds < 600 THEN '5-10 min'
                    WHEN DurationSeconds < 1800 THEN '10-30 min'
                    WHEN DurationSeconds < 3600 THEN '30-60 min'
                    ELSE '> 1 hour'
                END as DurationRange,
                COUNT(*) as SessionCount
            FROM ReviewSessions
            WHERE DurationSeconds IS NOT NULL AND DurationSeconds > 0
              AND ProfileID = ?
            GROUP BY 
                CASE 
                    WHEN DurationSeconds < 60 THEN '< 1 min'
                    WHEN DurationSeconds < 300 THEN '1-5 min'
                    WHEN DurationSeconds < 600 THEN '5-10 min'
                    WHEN DurationSeconds < 1800 THEN '10-30 min'
                    WHEN DurationSeconds < 3600 THEN '30-60 min'
                    ELSE '> 1 hour'
                END
            ORDER BY 
                MIN(DurationSeconds)
        """, (profile_id,)),
        
        'avgReviewTimePerFact': fetch_query("""
            SELECT
                AVG(SessionDuration) as AvgTimePerReview,
                MIN(SessionDuration) as MinTimePerReview,
                MAX(SessionDuration) as MaxTimePerReview,
                COUNT(*) as TotalReviews
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rl.SessionDuration IS NOT NULL AND rl.SessionDuration > 0
              AND (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND rs.ProfileID = ?
        """, (profile_id,)),
        
        'categoryReviewTime': fetch_query("""
            SELECT
                c.CategoryName,
                AVG(rl.SessionDuration) as AvgReviewTime,
                SUM(rl.SessionDuration) as TotalReviewTime,
                COUNT(rl.FactLogID) as ReviewCount
            FROM Categories c
            JOIN Facts f ON c.CategoryID = f.CategoryID AND f.CreatedBy = ?
            JOIN FactLogs rl ON f.FactID = rl.FactID
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rl.SessionDuration IS NOT NULL AND rl.SessionDuration > 0
              AND (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND rs.ProfileID = ?
              AND c.CreatedBy = ?
            GROUP BY c.CategoryName
            ORDER BY AVG(rl.SessionDuration) DESC
        """, (profile_id, profile_id, profile_id)),
        
        'dailySessionDuration': fetch_query("""
            SELECT 
                CONVERT(varchar, StartTime, 23) as Date,
                AVG(DurationSeconds) as AvgDuration,
                SUM(DurationSeconds) as TotalDuration,
                COUNT(*) as SessionCount
            FROM ReviewSessions
            WHERE DurationSeconds IS NOT NULL AND DurationSeconds > 0
                AND StartTime >= ?
                AND ProfileID = ?
            GROUP BY CONVERT(varchar, StartTime, 23)
            ORDER BY CONVERT(varchar, StartTime, 23)
        """, (thirty_days_ago, profile_id)),
        
        'sessionEfficiency': fetch_query("""
            SELECT TOP 100
                s.SessionID,
                s.StartTime,
                s.DurationSeconds,
                COUNT(DISTINCT rl.FactID) as UniqueFactsReviewed,
                COUNT(rl.FactLogID) as TotalReviews,
                CASE 
                    WHEN s.DurationSeconds > 0 
                    THEN CAST(COUNT(DISTINCT rl.FactID) * 60.0 / s.DurationSeconds as DECIMAL(10,2))
                    ELSE 0 
                END as FactsPerMinute,
                CASE 
                    WHEN s.DurationSeconds > 0 
                    THEN CAST(COUNT(rl.FactLogID) * 60.0 / s.DurationSeconds as DECIMAL(10,2))
                    ELSE 0 
                END as ReviewsPerMinute
            FROM ReviewSessions s
            LEFT JOIN FactLogs rl ON s.SessionID = rl.SessionID AND (rl.Action IS NULL OR rl.Action = 'view') AND COALESCE(rl.TimedOut, 0) = 0
            WHERE s.DurationSeconds IS NOT NULL AND s.DurationSeconds > 0
              AND s.ProfileID = ?
            GROUP BY s.SessionID, s.StartTime, s.DurationSeconds
            ORDER BY s.SessionID DESC
        """, (profile_id,)),
        
        # Session Timeout Analysis (last 30 days)
        'timeoutAnalysis': fetch_query("""
            SELECT 
                CONVERT(varchar, rl.ReviewDate, 23) as Date,
                COUNT(CASE WHEN rl.TimedOut = 1 THEN 1 END) as TimeoutCount,
                COUNT(*) as TotalReviews,
                CAST(COUNT(CASE WHEN rl.TimedOut = 1 THEN 1 END) * 100.0 / COUNT(*) as DECIMAL(5,2)) as TimeoutPercentage
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rl.ReviewDate >= ? AND (rl.Action IS NULL OR rl.Action = 'view')
              AND rs.ProfileID = ?
            GROUP BY CONVERT(varchar, rl.ReviewDate, 23)
            ORDER BY CONVERT(varchar, rl.ReviewDate, 23)
        """, (thirty_days_ago, profile_id)),
        
        # New analytics for Overview tab
        'knownVsUnknownRatio': fetch_query("""
            SELECT
                SUM(CASE WHEN pf.IsEasy = 1 THEN 1 ELSE 0 END) AS KnownFacts,
                SUM(CASE WHEN pf.IsEasy <> 1 OR pf.IsEasy IS NULL THEN 1 ELSE 0 END) AS UnknownFacts,
                COUNT(*) AS TotalFacts
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            WHERE f.CreatedBy = ?
        """, (profile_id, profile_id)),
        
        'weeklyReviewPattern': fetch_query("""
            SET DATEFIRST 7;
            SELECT 
                CASE DATEPART(weekday, ReviewDate)
                    WHEN 1 THEN 'Sunday'
                    WHEN 2 THEN 'Monday'
                    WHEN 3 THEN 'Tuesday'
                    WHEN 4 THEN 'Wednesday'
                    WHEN 5 THEN 'Thursday'
                    WHEN 6 THEN 'Friday'
                    WHEN 7 THEN 'Saturday'
                END as DayName,
                COUNT(*) as ReviewCount,
                COUNT(DISTINCT FactID) as UniqueFactsCount
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE (rl.Action IS NULL OR rl.Action = 'view') AND rs.ProfileID = ?
              AND COALESCE(rl.TimedOut, 0) = 0
            GROUP BY DATEPART(weekday, ReviewDate)
            ORDER BY DATEPART(weekday, ReviewDate)
        """, (profile_id,)),
        
        'topReviewHours': fetch_query("""
            SELECT TOP 5
                DATEPART(hour, ReviewDate) as Hour,
                COUNT(*) as ReviewCount
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE (rl.Action IS NULL OR rl.Action = 'view') AND rs.ProfileID = ?
              AND COALESCE(rl.TimedOut, 0) = 0
            GROUP BY DATEPART(hour, ReviewDate)
            ORDER BY COUNT(*) DESC
        """, (profile_id,)),
        
        'categoryGrowthTrend': fetch_query("""
            SELECT
                c.CategoryName,
                COUNT(f.FactID) as AllTime
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.CreatedBy = ?
            WHERE c.CreatedBy = ?
            GROUP BY c.CategoryName
            HAVING COUNT(f.FactID) > 0
            ORDER BY COUNT(f.FactID) DESC
        """, (profile_id, profile_id)),
        
        # New chart for Progress tab
        'monthlyProgress': fetch_query("""
            SELECT
                YEAR(ReviewDate) as Year,
                MONTH(ReviewDate) as Month,
                COUNT(*) as TotalReviews,
                COUNT(DISTINCT FactID) as UniqueFactsReviewed,
                COUNT(DISTINCT CONVERT(date, ReviewDate)) as ActiveDays
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rl.ReviewDate >= DATEADD(month, -6, GETDATE())
              AND (rl.Action IS NULL OR rl.Action = 'view') AND rs.ProfileID = ?
              AND COALESCE(rl.TimedOut, 0) = 0
            GROUP BY YEAR(ReviewDate), MONTH(ReviewDate)
            ORDER BY YEAR(ReviewDate), MONTH(ReviewDate)
        """, (profile_id,)),

        # AI Usage Analytics
        'aiUsageSummary': fetch_query("""
            SELECT
                COUNT(*) as TotalCalls,
                COALESCE(SUM(InputTokens), 0) as TotalInputTokens,
                COALESCE(SUM(OutputTokens), 0) as TotalOutputTokens,
                COALESCE(SUM(TotalTokens), 0) as TotalTokens,
                COALESCE(SUM(Cost), 0) as TotalCost,
                COALESCE(AVG(Cost), 0) as AvgCost,
                COALESCE(AVG(LatencyMs), 0) as AvgLatency,
                SUM(CASE WHEN Status = 'SUCCESS' THEN 1 ELSE 0 END) as SuccessCount,
                SUM(CASE WHEN Status = 'FAILED' THEN 1 ELSE 0 END) as FailedCount,
                COALESCE(AVG(ReadingDurationSec), 0) as AvgReadingTime,
                COALESCE(MIN(ReadingDurationSec), 0) as MinReadingTime,
                COALESCE(MAX(ReadingDurationSec), 0) as MaxReadingTime
            FROM AIUsageLogs
            WHERE ProfileID = ?
        """, (profile_id,)),

        'aiCostTimeline': fetch_query("""
            SELECT
                CONVERT(varchar, CreatedAt, 23) as Date,
                COUNT(*) as Calls,
                COALESCE(SUM(Cost), 0) as DailyCost,
                COALESCE(SUM(TotalTokens), 0) as DailyTokens
            FROM AIUsageLogs
            WHERE ProfileID = ? AND CreatedAt >= ?
            GROUP BY CONVERT(varchar, CreatedAt, 23)
            ORDER BY CONVERT(varchar, CreatedAt, 23)
        """, (profile_id, thirty_days_ago)),

        'aiTokenDistribution': fetch_query("""
            SELECT
                COALESCE(SUM(InputTokens), 0) as InputTokens,
                COALESCE(SUM(OutputTokens), 0) as OutputTokens
            FROM AIUsageLogs
            WHERE ProfileID = ?
        """, (profile_id,)),

        'aiUsageByCategory': fetch_query("""
            SELECT
                COALESCE(c.CategoryName, 'Unknown') as CategoryName,
                COUNT(*) as CallCount,
                COALESCE(SUM(ai.Cost), 0) as TotalCost
            FROM AIUsageLogs ai
            LEFT JOIN Facts f ON ai.FactID = f.FactID
            LEFT JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE ai.ProfileID = ?
            GROUP BY c.CategoryName
            ORDER BY COUNT(*) DESC
        """, (profile_id,)),

        'aiLatencyDistribution': fetch_query("""
            SELECT
                CASE
                    WHEN LatencyMs < 500 THEN '< 0.5s'
                    WHEN LatencyMs < 1000 THEN '0.5-1s'
                    WHEN LatencyMs < 2000 THEN '1-2s'
                    WHEN LatencyMs < 5000 THEN '2-5s'
                    ELSE '> 5s'
                END as LatencyRange,
                COUNT(*) as CallCount
            FROM AIUsageLogs
            WHERE ProfileID = ? AND LatencyMs IS NOT NULL
            GROUP BY
                CASE
                    WHEN LatencyMs < 500 THEN '< 0.5s'
                    WHEN LatencyMs < 1000 THEN '0.5-1s'
                    WHEN LatencyMs < 2000 THEN '1-2s'
                    WHEN LatencyMs < 5000 THEN '2-5s'
                    ELSE '> 5s'
                END
            ORDER BY MIN(LatencyMs)
        """, (profile_id,)),

        'aiMostExplainedFacts': fetch_query("""
            SELECT TOP 10
                COALESCE(f.Content, 'Deleted Fact') as Content,
                COALESCE(c.CategoryName, 'Unknown') as CategoryName,
                COUNT(*) as CallCount,
                COALESCE(SUM(ai.Cost), 0) as TotalCost
            FROM AIUsageLogs ai
            LEFT JOIN Facts f ON ai.FactID = f.FactID
            LEFT JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE ai.ProfileID = ?
            GROUP BY f.Content, c.CategoryName
            ORDER BY COUNT(*) DESC
        """, (profile_id,)),

        'aiRecentUsage': fetch_query("""
            SELECT TOP 50
                ai.CreatedAt,
                COALESCE(LEFT(f.Content, 100), 'Deleted Fact') as FactContent,
                ai.TotalTokens,
                ai.Cost,
                ai.LatencyMs,
                ai.Status,
                ai.ModelName as Model
            FROM AIUsageLogs ai
            LEFT JOIN Facts f ON ai.FactID = f.FactID
            WHERE ai.ProfileID = ?
            ORDER BY ai.CreatedAt DESC
        """, (profile_id,)),

        # Category Completion Rate - % of facts marked as "known" per category
        'categoryCompletionRate': fetch_query("""
            SELECT
                c.CategoryName,
                COUNT(f.FactID) as TotalFacts,
                SUM(CASE WHEN pf.IsEasy = 1 THEN 1 ELSE 0 END) as KnownFacts,
                CASE
                    WHEN COUNT(f.FactID) > 0
                    THEN CAST(SUM(CASE WHEN pf.IsEasy = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(f.FactID) as DECIMAL(5,2))
                    ELSE 0
                END as CompletionRate
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.CreatedBy = ?
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            WHERE c.CreatedBy = ?
            GROUP BY c.CategoryName
            HAVING COUNT(f.FactID) > 0
            ORDER BY CompletionRate DESC
        """, (profile_id, profile_id, profile_id)),

        # Learning Velocity - Time from fact creation to first marked as known
        'learningVelocity': fetch_query("""
            SELECT
                c.CategoryName,
                AVG(DATEDIFF(day, f.DateAdded, pf.KnownSince)) AS AvgDaysToKnow,
                MIN(DATEDIFF(day, f.DateAdded, pf.KnownSince)) AS MinDaysToKnow,
                MAX(DATEDIFF(day, f.DateAdded, pf.KnownSince)) AS MaxDaysToKnow,
                COUNT(*) AS KnownFactsCount
            FROM ProfileFacts pf
            JOIN Facts f ON pf.FactID = f.FactID
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE pf.ProfileID = ? AND pf.IsEasy = 1 AND pf.KnownSince IS NOT NULL
              AND f.CreatedBy = ?
              AND c.CreatedBy = ?
            GROUP BY c.CategoryName
            HAVING COUNT(*) > 0
            ORDER BY AVG(DATEDIFF(day, f.DateAdded, pf.KnownSince)) ASC
        """, (profile_id, profile_id, profile_id)),

        # Peak Productivity Times - Session efficiency by hour of day
        'peakProductivityTimes': fetch_query("""
            SELECT
                DATEPART(hour, s.StartTime) as Hour,
                COUNT(*) as SessionCount,
                AVG(s.DurationSeconds) as AvgDuration,
                AVG(CAST(sub.UniqueFactsReviewed as FLOAT)) as AvgFactsReviewed,
                CASE
                    WHEN AVG(s.DurationSeconds) > 0
                    THEN CAST(AVG(CAST(sub.UniqueFactsReviewed as FLOAT)) * 60.0 / AVG(s.DurationSeconds) as DECIMAL(10,2))
                    ELSE 0
                END as AvgEfficiency
            FROM ReviewSessions s
            INNER JOIN (
                SELECT
                    rl.SessionID,
                    COUNT(DISTINCT rl.FactID) as UniqueFactsReviewed
                FROM FactLogs rl
                WHERE (rl.Action IS NULL OR rl.Action = 'view')
                  AND COALESCE(rl.TimedOut, 0) = 0
                GROUP BY rl.SessionID
            ) sub ON s.SessionID = sub.SessionID
            WHERE s.DurationSeconds IS NOT NULL AND s.DurationSeconds > 0
              AND s.ProfileID = ?
            GROUP BY DATEPART(hour, s.StartTime)
            ORDER BY DATEPART(hour, s.StartTime)
        """, (profile_id,)),

        # Action Breakdown - Distribution of action types
        'actionBreakdown': fetch_query("""
            SELECT
                COALESCE(rl.Action, 'view') as ActionType,
                COUNT(*) as ActionCount
            FROM FactLogs rl
            JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
            WHERE rs.ProfileID = ?
            GROUP BY COALESCE(rl.Action, 'view')
            ORDER BY COUNT(*) DESC
        """, (profile_id,)),

        # AI Provider Comparison - Compare costs/latency by provider
        'aiProviderComparison': fetch_query("""
            SELECT
                COALESCE(Provider, 'Unknown') as Provider,
                COUNT(*) as CallCount,
                COALESCE(SUM(Cost), 0) as TotalCost,
                COALESCE(AVG(Cost), 0) as AvgCost,
                COALESCE(AVG(LatencyMs), 0) as AvgLatency,
                COALESCE(SUM(TotalTokens), 0) as TotalTokens,
                SUM(CASE WHEN Status = 'SUCCESS' THEN 1 ELSE 0 END) as SuccessCount,
                SUM(CASE WHEN Status = 'FAILED' THEN 1 ELSE 0 END) as FailedCount
            FROM AIUsageLogs
            WHERE ProfileID = ?
            GROUP BY Provider
            ORDER BY COUNT(*) DESC
        """, (profile_id,))
    }

    # Gamification: level/xp and achievements
    def safe_fetch_one(q, params=None, default=None):
        try:
            rows = fetch_query(q, params)
            return rows[0] if rows else (default or {})
        except Exception:
            return default or {}

    # Profile snapshot
    profile = safe_fetch_one("""
        SELECT TOP 1 XP, Level, CurrentStreak, LongestStreak, LastCheckinDate,
               TotalReviews, TotalAdds, TotalEdits, TotalDeletes
        FROM GamificationProfile
        WHERE ProfileID = ?
        ORDER BY ProfileID
    """, (profile_id,))

    # Compute level progression aligned with stored Level (gated at 99 unless all achievements unlocked)
    def level_progress(xp_val: int, stored_level: int):
        try:
            xp_val = int(xp_val or 0)
        except Exception:
            xp_val = 0
        try:
            stored_level = int(stored_level or 1)
        except Exception:
            stored_level = 1

        cfg = getattr(config, 'LEVELING_CONFIG', {})
        b1_end = int(cfg.get('band1_end', 4))
        b1_step = int(cfg.get('band1_step', 100))
        b2_end = int(cfg.get('band2_end', 9))
        b2_step = int(cfg.get('band2_step', 500))
        b3_end = int(cfg.get('band3_end', 14))
        b3_step = int(cfg.get('band3_step', 1000))
        b4_end = int(cfg.get('band4_end', 19))
        b4_step = int(cfg.get('band4_step', 5000))
        const_end = int(cfg.get('const_end', 98))
        total_target = int(cfg.get('total_xp_l100', 1_000_000))

        def early_band_step(lvl: int) -> int:
            if lvl <= b1_end:
                return b1_step
            if lvl <= b2_end:
                return b2_step
            if lvl <= b3_end:
                return b3_step
            if lvl <= b4_end:
                return b4_step
            return 0

        EARLY_SUM = sum(early_band_step(l) for l in range(1, b4_end + 1))
        const_start = b4_end + 1
        const_levels = max(0, const_end - const_start + 1)
        MID_CONST = (total_target - EARLY_SUM) // (const_levels + 1) if (const_levels + 1) > 0 else 0

        def step_for_level(lvl: int) -> int:
            if lvl >= 100:
                return 0
            if lvl <= b4_end:
                return early_band_step(lvl)
            if lvl <= const_end:
                return int(MID_CONST)
            # lvl == 99
            sum_const = MID_CONST * const_levels
            final_needed = total_target - (EARLY_SUM + sum_const)
            return int(final_needed)

        # Total XP required to reach stored_level
        total_required = 0
        cur = 1
        while cur < stored_level:
            total_required += step_for_level(cur)
            cur += 1

        need_next = step_for_level(stored_level)
        xp_into = max(0, xp_val - total_required)
        if stored_level < 100:
            xp_into = min(xp_into, need_next)
        xp_to_next = 0 if stored_level >= 100 else max(0, need_next - xp_into)
        return {
            'level': stored_level,
            'xp': xp_val,
            'xp_into_level': int(xp_into),
            'xp_to_next': int(xp_to_next),
            'next_level_requirement': 0 if stored_level >= 100 else int(need_next)
        }

    gamify = level_progress(profile.get('XP') if profile else 0, profile.get('Level', 1) if profile else 1)

    # Achievements summary
    totals = safe_fetch_one("SELECT COUNT(*) AS Total FROM Achievements")
    unlocked = safe_fetch_one("SELECT COUNT(*) AS Unlocked FROM AchievementUnlocks WHERE ProfileID = ?", (profile_id,))
    achievements_summary = {
        'total': totals.get('Total', 0) if totals else 0,
        'unlocked': unlocked.get('Unlocked', 0) if unlocked else 0
    }

    # Recent unlocked achievements
    try:
        recent_achievements = fetch_query("""
            SELECT TOP 10 a.Code, a.Name, a.RewardXP, u.UnlockDate
            FROM AchievementUnlocks u
            JOIN Achievements a ON a.AchievementID = u.AchievementID
            WHERE u.ProfileID = ?
            ORDER BY u.UnlockDate DESC, u.UnlockID DESC
        """, (profile_id,))
    except Exception:
        recent_achievements = []

    # Full achievements with status and progress
    # Build counters: known/favorites from Facts, others from profile
    try:
        known_count_row = fetch_query("SELECT COUNT(*) AS C FROM ProfileFacts WHERE ProfileID = ? AND IsEasy = 1", (profile_id,))
        known_count = int(known_count_row[0]['C']) if known_count_row else 0
    except Exception:
        known_count = 0
    try:
        fav_count_row = fetch_query("SELECT COUNT(*) AS C FROM ProfileFacts WHERE ProfileID = ? AND IsFavorite = 1", (profile_id,))
        favorites_count_val = int(fav_count_row[0]['C']) if fav_count_row else 0
    except Exception:
        favorites_count_val = 0

    counters = {
        'known': known_count,
        'favorites': favorites_count_val,
        'reviews': int((profile or {}).get('TotalReviews', 0) or 0),
        'adds': int((profile or {}).get('TotalAdds', 0) or 0),
        'edits': int((profile or {}).get('TotalEdits', 0) or 0),
        'deletes': int((profile or {}).get('TotalDeletes', 0) or 0),
        'streak': int((profile or {}).get('CurrentStreak', 0) or 0),
    }

    try:
        ach_rows = fetch_query(
            """
            SELECT a.AchievementID, a.Code, a.Name, a.Category, a.Threshold, a.RewardXP,
                   u.UnlockID, u.UnlockDate, u.Notified
            FROM Achievements a
            LEFT JOIN AchievementUnlocks u ON u.AchievementID = a.AchievementID AND u.ProfileID = ?
            ORDER BY a.Category, a.Threshold
            """
        , (profile_id,))
    except Exception:
        ach_rows = []
    achievements_full = []
    for r in ach_rows:
        progress = counters.get(str(r.get('Category')), 0)
        achievements_full.append({
            'Code': r.get('Code'),
            'Name': r.get('Name'),
            'Category': r.get('Category'),
            'Threshold': int(r.get('Threshold') or 0),
            'RewardXP': int(r.get('RewardXP') or 0),
            'Unlocked': r.get('UnlockID') is not None,
            'UnlockDate': r.get('UnlockDate'),
            'Notified': bool(r.get('Notified')) if r.get('UnlockID') is not None else False,
            'ProgressCurrent': int(progress),
        })
    
    # Format data for frontend
    formatted_data = {
        'category_distribution': format_pie_chart(data['categoryDistribution'], 'CategoryName', 'FactCount'),
        'active_categories_count': data['activeCategoriesCount'][0]['ActiveCount'] if data['activeCategoriesCount'] else 0,
        'reviews_per_day': format_line_chart(data['factsViewedPerDay']),
        'most_reviewed_facts': format_table_data(data['mostReviewedFacts']),
        'least_reviewed_facts': format_table_data(data['leastReviewedFacts']),
        'facts_added_timeline': format_timeline(data['factsAddedOverTime']),
        'review_heatmap': format_heatmap(data['reviewHeatmap']),
        'favorite_category_distribution': format_pie_chart(data['favoriteCategoryDistribution'], 'CategoryName', 'FavoriteCount'),
        'known_category_distribution': format_pie_chart(data['knownCategoryDistribution'], 'CategoryName', 'KnownCount'),
        'categories_viewed_today': format_pie_chart(data['categoriesViewedToday'], 'CategoryName', 'ViewedCount'),
        'review_streak': data['reviewStreak'],
        'category_reviews': format_bar_chart(data['categoryReviews'], 'CategoryName', 'TotalReviews'),
        'favorites_count': data['favoritesCount'][0]['FavoriteCount'] if data['favoritesCount'] else 0,
        'known_facts_count': data['knownFactsCount'][0]['KnownCount'] if data['knownFactsCount'] else 0,
        'viewed_today_count': data['viewedTodayCount'][0]['ViewedTodayCount'] if data['viewedTodayCount'] else 0,
        # Include favorite/known fact tables for the frontend
        'allFavoriteFacts': format_table_data(data['allFavoriteFacts']),
        'allKnownFacts': format_table_data(data['allKnownFacts']),
        # Duration analytics
        'session_duration_stats': data['sessionDurationStats'][0] if data['sessionDurationStats'] else {},
        'avg_facts_per_session': data['avgFactsPerSession'][0] if data['avgFactsPerSession'] else {},
        'best_efficiency': data['bestEfficiency'][0] if data['bestEfficiency'] else {},
        'session_duration_distribution': format_pie_chart(data['sessionDurationDistribution'], 'DurationRange', 'SessionCount'),
        'avg_review_time_per_fact': data['avgReviewTimePerFact'][0] if data['avgReviewTimePerFact'] else {},
        'category_review_time': format_bar_chart(data['categoryReviewTime'], 'CategoryName', 'AvgReviewTime', 'Avg Review Time (s)'),
        'daily_session_duration': format_duration_line_chart(data['dailySessionDuration']),
        'session_efficiency': format_table_data(data['sessionEfficiency']),
        'timeout_analysis': format_timeout_chart(data['timeoutAnalysis']),
        # New Overview charts
        'known_vs_unknown': format_known_unknown_chart(data['knownVsUnknownRatio']),
        'weekly_review_pattern': format_weekly_pattern(data['weeklyReviewPattern']),
        'top_review_hours': format_top_hours(data['topReviewHours']),
        'category_growth_trend': format_growth_trend(data['categoryGrowthTrend']),
        # New Progress chart
        'monthly_progress': format_monthly_progress(data['monthlyProgress']),
        # Gamification exports
        'gamification': gamify,
        'achievements_summary': achievements_summary,
        'recent_achievements': recent_achievements,
        'achievements': achievements_full,
        # AI Usage Analytics
        'ai_usage_summary': data['aiUsageSummary'][0] if data['aiUsageSummary'] else {},
        'ai_cost_timeline': format_ai_cost_timeline(data['aiCostTimeline']),
        'ai_token_distribution': format_ai_token_distribution(data['aiTokenDistribution']),
        'ai_usage_by_category': format_pie_chart(data['aiUsageByCategory'], 'CategoryName', 'CallCount'),
        'ai_latency_distribution': format_pie_chart(data['aiLatencyDistribution'], 'LatencyRange', 'CallCount'),
        'ai_most_explained_facts': format_table_data(data['aiMostExplainedFacts']),
        'ai_recent_usage': format_table_data(data['aiRecentUsage']),
        'ai_provider_comparison': format_table_data(data['aiProviderComparison']),
        # New analytics
        'category_completion_rate': format_table_data(data['categoryCompletionRate']),
        'learning_velocity': format_table_data(data['learningVelocity']),
        'peak_productivity_times': format_table_data(data['peakProductivityTimes']),
        'action_breakdown': format_pie_chart(data['actionBreakdown'], 'ActionType', 'ActionCount'),
        # Lifetime stats from profile
        'lifetime_stats': {
            'total_adds': int((profile or {}).get('TotalAdds', 0) or 0),
            'total_edits': int((profile or {}).get('TotalEdits', 0) or 0),
            'total_deletes': int((profile or {}).get('TotalDeletes', 0) or 0),
            'total_reviews': int((profile or {}).get('TotalReviews', 0) or 0),
            'current_streak': int((profile or {}).get('CurrentStreak', 0) or 0),
            'longest_streak': int((profile or {}).get('LongestStreak', 0) or 0),
        }
    }

    # If all=true, also include ALL facts (including those with 0 reviews)
    if return_all:
        # Get ALL facts sorted by review count (including 0 reviews)
        formatted_data['all_most_reviewed_facts'] = format_table_data(fetch_query("""
            SELECT
                f.Content,
                COALESCE(pf.PersonalReviewCount, 0) AS ReviewCount,
                c.CategoryName,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY COALESCE(pf.PersonalReviewCount, f.TotalViews, 0) DESC, f.TotalViews DESC, f.Content
        """, (profile_id, profile_id, profile_id)))
        
        # Get ALL facts sorted by least reviewed (including 0 reviews)
        formatted_data['all_least_reviewed_facts'] = format_table_data(fetch_query("""
            SELECT
                f.Content,
                COALESCE(pf.PersonalReviewCount, 0) AS ReviewCount,
                c.CategoryName,
                CASE 
                    WHEN pf.LastViewedByUser IS NULL THEN NULL
                    ELSE DATEDIFF(day, pf.LastViewedByUser, GETDATE())
                END as DaysSinceReview,
                COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                COALESCE(pf.IsEasy, 0) AS IsEasy
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.CreatedBy = ?
              AND c.CreatedBy = ?
            ORDER BY 
                COALESCE(pf.PersonalReviewCount, 0) ASC,
                CASE WHEN pf.LastViewedByUser IS NULL THEN 0 ELSE 1 END ASC,
                pf.LastViewedByUser ASC
        """, (profile_id, profile_id, profile_id)))

    # removed avg per-view duration series

    # Add recent session summaries (last 100 sessions)
    recent_sessions = fetch_query("""
        SELECT TOP 100
            s.SessionID,
            s.StartTime,
            s.EndTime,
            s.DurationSeconds,
            COUNT(rl.FactLogID) AS Views,
            COUNT(DISTINCT rl.FactID) AS DistinctFacts
        FROM ReviewSessions s
        LEFT JOIN FactLogs rl ON rl.SessionID = s.SessionID AND (rl.Action IS NULL OR rl.Action = 'view') AND COALESCE(rl.TimedOut, 0) = 0
        WHERE s.ProfileID = ?
        GROUP BY s.SessionID, s.StartTime, s.EndTime, s.DurationSeconds
        ORDER BY s.SessionID DESC
    """, (profile_id,))
    formatted_data['recent_sessions'] = recent_sessions

    # Last card reviews (top 50 by latest session start time, then review time)
    recent_card_reviews = fetch_query("""
        SELECT TOP 50
            rl.FactLogID,
            s.StartTime,
            rl.ReviewDate,
            COALESCE(c.CategoryName, c2.CategoryName) AS CategoryName,
            COALESCE(f.Content, rl.FactContentSnapshot) AS Content
        FROM FactLogs rl
        JOIN ReviewSessions s ON s.SessionID = rl.SessionID
        LEFT JOIN Facts f ON f.FactID = rl.FactID
        LEFT JOIN Categories c ON f.CategoryID = c.CategoryID
        LEFT JOIN Categories c2 ON rl.CategoryIDSnapshot = c2.CategoryID
        WHERE (rl.Action IS NULL OR rl.Action = 'view')
          AND COALESCE(rl.TimedOut, 0) = 0
          AND s.ProfileID = ?
        ORDER BY ISNULL(s.StartTime, rl.ReviewDate) DESC, rl.ReviewDate DESC, rl.FactLogID DESC
    """, (profile_id,))
    formatted_data['recent_card_reviews'] = format_table_data(recent_card_reviews)

    # If all=true also provide the last 500 reviews for modal expansion
    if return_all:
        all_recent_card_reviews = fetch_query("""
            SELECT TOP 500
                rl.FactLogID,
                s.StartTime,
                rl.ReviewDate,
                COALESCE(c.CategoryName, c2.CategoryName) AS CategoryName,
                COALESCE(f.Content, rl.FactContentSnapshot) AS Content
            FROM FactLogs rl
            JOIN ReviewSessions s ON s.SessionID = rl.SessionID
            LEFT JOIN Facts f ON f.FactID = rl.FactID
            LEFT JOIN Categories c ON f.CategoryID = c.CategoryID
            LEFT JOIN Categories c2 ON rl.CategoryIDSnapshot = c2.CategoryID
            WHERE (rl.Action IS NULL OR rl.Action = 'view')
              AND COALESCE(rl.TimedOut, 0) = 0
              AND s.ProfileID = ?
            ORDER BY ISNULL(s.StartTime, rl.ReviewDate) DESC, rl.ReviewDate DESC, rl.FactLogID DESC
        """, (profile_id,))
        formatted_data['all_recent_card_reviews'] = format_table_data(all_recent_card_reviews)

    # Session actions (Add/Edit/Delete) per recent sessions
    session_actions_rows = fetch_query("""
        SELECT TOP 100
            s.SessionID,
            s.StartTime,
            ISNULL(s.FactsAdded, 0) AS FactsAdded,
            ISNULL(s.FactsEdited, 0) AS FactsEdited,
            ISNULL(s.FactsDeleted, 0) AS FactsDeleted
        FROM ReviewSessions s
        WHERE s.StartTime IS NOT NULL AND s.ProfileID = ?
        ORDER BY s.SessionID DESC
    """, (profile_id,))

    # Build grouped bar payload (oldest first for readability)
    labels = []
    added = []
    edited = []
    deleted = []
    for r in reversed(session_actions_rows):
        # Label with short datetime or session id fallback
        st = r.get('StartTime')
        try:
            lbl = st.strftime('%m-%d %H:%M') if isinstance(st, datetime) else str(st)
        except Exception:
            lbl = f"#{r.get('SessionID')}"
        labels.append(lbl)
        added.append(int(r.get('FactsAdded') or 0))
        edited.append(int(r.get('FactsEdited') or 0))
        deleted.append(int(r.get('FactsDeleted') or 0))

    formatted_data['session_actions_chart'] = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Added',
                'data': added,
                'backgroundColor': '#10b981'
            },
            {
                'label': 'Edited',
                'data': edited,
                'backgroundColor': '#3b82f6'
            },
            {
                'label': 'Deleted',
                'data': deleted,
                'backgroundColor': '#ef4444'
            }
        ]
    }
    formatted_data['session_actions_table'] = session_actions_rows

    return jsonify(formatted_data)

def calculate_review_streak(profile_id: int):
    """Calculate the current review streak for a profile"""
    # Fetch longest streak from GamificationProfile
    profile_longest = 0
    try:
        profile_row = fetch_query(
            "SELECT LongestStreak FROM GamificationProfile WHERE ProfileID = ?",
            (profile_id,)
        )
        if profile_row:
            profile_longest = int(profile_row[0].get('LongestStreak', 0) or 0)
    except Exception:
        pass

    query = """
    SELECT DISTINCT CONVERT(date, rl.ReviewDate) as ReviewDate
    FROM FactLogs rl
    JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
    WHERE (rl.Action IS NULL OR rl.Action = 'view')
      AND COALESCE(rl.TimedOut, 0) = 0
      AND rs.ProfileID = ?
    ORDER BY CONVERT(date, rl.ReviewDate) DESC
    """

    review_dates = fetch_query(query, (profile_id,))

    if not review_dates:
        return {'current_streak': 0, 'longest_streak': profile_longest, 'last_review': None}

    # Coerce DB values to date objects
    def to_date(val):
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        # Fallback: assume ISO-like string
        return datetime.strptime(str(val), '%Y-%m-%d').date()

    ordered_dates = [to_date(row['ReviewDate']) for row in review_dates]

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Determine starting day for streak (today or yesterday)
    start = ordered_dates[0]
    if start not in (today, yesterday):
        return {'current_streak': 0, 'longest_streak': profile_longest, 'last_review': start.isoformat()}

    # Count consecutive days backward from the start day
    current_streak = 1
    base = start
    for next_date in ordered_dates[1:]:
        if next_date == base - timedelta(days=current_streak):
            current_streak += 1
        else:
            break

    last_review = ordered_dates[0].isoformat() if ordered_dates else None

    return {
        'current_streak': current_streak,
        'longest_streak': profile_longest,
        'last_review': last_review
    }

def format_pie_chart(data, label_field, value_field):
    """Format data for pie charts"""
    return {
        'labels': [row[label_field] for row in data],
        'data': [row[value_field] for row in data]
    }

def format_line_chart(data):
    """Format data for line charts showing reviews per day"""
    labels = []
    facts_reviewed = []
    total_reviews = []
    
    for row in data:
        labels.append(row['Date'])
        facts_reviewed.append(row['FactsReviewed'])
        total_reviews.append(row['TotalReviews'])
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Unique Facts Reviewed',
                'data': facts_reviewed,
                'borderColor': '#4CAF50',
                'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                'fill': True
            },
            {
                'label': 'Total Reviews',
                'data': total_reviews,
                'borderColor': '#2196F3',
                'backgroundColor': 'rgba(33, 150, 243, 0.1)',
                'fill': True
            }
        ]
    }

def format_table_data(data):
    """Format data for table display"""
    return data

def format_timeline(data):
    """Format data for timeline chart"""
    labels = [row['Date'] for row in data]
    values = [row['FactsAdded'] for row in data]
    
    # Calculate cumulative
    cumulative = []
    total = 0
    for value in values:
        total += value
        cumulative.append(total)
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Facts Added',
                'data': values,
                'type': 'bar',
                'backgroundColor': '#FFC107'
            },
            {
                'label': 'Cumulative Total',
                'data': cumulative,
                'type': 'line',
                'borderColor': '#4CAF50',
                'backgroundColor': 'transparent',
                'borderWidth': 2
            }
        ]
    }

def format_heatmap(data):
    """Format data for heatmap visualization"""
    # Create a 7x24 matrix for week days x hours
    heatmap_matrix = [[0 for _ in range(24)] for _ in range(7)]
    
    for row in data:
        day = row['DayOfWeek'] - 1  # Convert to 0-based index
        hour = row['Hour']
        count = row['ReviewCount']
        if 0 <= day < 7 and 0 <= hour < 24:
            heatmap_matrix[day][hour] = count
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    return {
        'data': heatmap_matrix,
        'days': days,
        'hours': list(range(24))
    }

def format_bar_chart(data, label_field, value_field, legend_label='Total Reviews'):
    """Format data for bar charts"""
    return {
        'labels': [row[label_field] for row in data],
        'datasets': [{
            'label': legend_label,
            'data': [row[value_field] for row in data],
            'backgroundColor': '#9C27B0'
        }]
    }

def format_single_line_chart(data, label='Series', value_field='Value'):
    """Format data with Date + single numeric field for a simple line chart."""
    labels = [str(row.get('Date')) for row in data]
    series = []
    for row in data:
        val = row.get(value_field)
        try:
            series.append(0 if val is None else float(val))
        except Exception:
            series.append(0)
    return {
        'labels': labels,
        'datasets': [{
            'label': label,
            'data': series,
            'borderColor': '#f97316',
            'backgroundColor': 'rgba(249, 115, 22, 0.1)',
            'fill': True
        }]
    }

def format_duration_line_chart(data):
    """Format duration data for line chart with multiple metrics"""
    labels = []
    avg_duration = []
    total_duration = []
    session_count = []
    
    for row in data:
        labels.append(row['Date'])
        avg_duration.append(round(row['AvgDuration'] / 60, 2) if row['AvgDuration'] else 0)  # Convert to minutes
        total_duration.append(round(row['TotalDuration'] / 60, 2) if row['TotalDuration'] else 0)  # Convert to minutes
        session_count.append(row['SessionCount'])
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Avg Duration (min)',
                'data': avg_duration,
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'yAxisID': 'y',
                'fill': True
            },
            {
                'label': 'Total Duration (min)',
                'data': total_duration,
                'borderColor': '#3b82f6',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'yAxisID': 'y',
                'fill': True
            },
            {
                'label': 'Sessions',
                'data': session_count,
                'borderColor': '#f59e0b',
                'backgroundColor': 'rgba(245, 158, 11, 0.1)',
                'yAxisID': 'y1',
                'type': 'bar'
            }
        ]
    }

def format_timeout_chart(data):
    """Format timeout analysis data for chart"""
    labels = []
    timeout_count = []
    timeout_percentage = []
    
    for row in data:
        labels.append(row['Date'])
        timeout_count.append(row['TimeoutCount'])
        timeout_percentage.append(float(row['TimeoutPercentage']) if row['TimeoutPercentage'] else 0)
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Timeout Count',
                'data': timeout_count,
                'type': 'bar',
                'backgroundColor': '#ef4444',
                'yAxisID': 'y'
            },
            {
                'label': 'Timeout %',
                'data': timeout_percentage,
                'type': 'line',
                'borderColor': '#dc2626',
                'backgroundColor': 'transparent',
                'borderWidth': 2,
                'yAxisID': 'y1'
            }
        ]
    }

def format_known_unknown_chart(data):
    """Format known vs unknown facts for doughnut chart"""
    if not data or not data[0]:
        return {'labels': [], 'data': []}
    row = data[0]
    return {
        'labels': ['Known Facts', 'Unknown Facts'],
        'data': [row.get('KnownFacts', 0), row.get('UnknownFacts', 0)]
    }

def format_weekly_pattern(data):
    """Format weekly review pattern as radar chart data"""
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    day_data = {row['DayName']: row['ReviewCount'] for row in data if row.get('DayName')}
    
    return {
        'labels': days_order,
        'datasets': [{
            'label': 'Reviews',
            'data': [day_data.get(day, 0) for day in days_order],
            'backgroundColor': 'rgba(59, 130, 246, 0.2)',
            'borderColor': '#3b82f6',
            'pointBackgroundColor': '#3b82f6',
            'pointBorderColor': '#fff',
            'pointHoverBackgroundColor': '#fff',
            'pointHoverBorderColor': '#3b82f6'
        }]
    }

def format_top_hours(data):
    """Format top review hours as horizontal bar chart"""
    hours = []
    counts = []
    for row in data:
        hour = row.get('Hour', 0)
        hour_str = f"{hour:02d}:00-{(hour+1)%24:02d}:00"
        hours.append(hour_str)
        counts.append(row.get('ReviewCount', 0))
    
    return {
        'labels': hours,
        'datasets': [{
            'label': 'Reviews',
            'data': counts,
            'backgroundColor': '#10b981',
            'borderColor': '#059669',
            'borderWidth': 1
        }]
    }

def format_growth_trend(data):
    """Format category growth trend"""
    categories = []
    all_time = []
    
    for row in data[:8]:  # Top 8 categories
        categories.append(row.get('CategoryName', ''))
        all_time.append(row.get('AllTime', 0))
    
    return {
        'labels': categories,
        'datasets': [
            {
                'label': 'Total Facts (Lifetime)',
                'data': all_time,
                'backgroundColor': '#3b82f6',
                'borderColor': '#2563eb',
                'borderWidth': 1
            }
        ]
    }

def format_monthly_progress(data):
    """Format monthly progress data"""
    labels = []
    reviews = []
    unique_facts = []
    active_days = []

    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    for row in data:
        year = row.get('Year', 2024)
        month = row.get('Month', 1)
        labels.append(f"{month_names[month]} {year}")
        reviews.append(row.get('TotalReviews', 0))
        unique_facts.append(row.get('UniqueFactsReviewed', 0))
        active_days.append(row.get('ActiveDays', 0))

    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Total Reviews',
                'data': reviews,
                'type': 'line',
                'borderColor': '#3b82f6',
                'backgroundColor': 'transparent',
                'borderWidth': 2,
                'tension': 0.4,
                'yAxisID': 'y'
            },
            {
                'label': 'Unique Facts',
                'data': unique_facts,
                'type': 'bar',
                'backgroundColor': '#10b981',
                'yAxisID': 'y'
            },
            {
                'label': 'Active Days',
                'data': active_days,
                'type': 'line',
                'borderColor': '#f59e0b',
                'backgroundColor': 'transparent',
                'borderWidth': 2,
                'borderDash': [5, 5],
                'yAxisID': 'y1'
            }
        ]
    }

def format_ai_cost_timeline(data):
    """Format AI cost timeline data for chart"""
    labels = []
    costs = []
    tokens = []
    calls = []
    cumulative_cost = []
    running_total = 0

    for row in data:
        labels.append(row.get('Date', ''))
        cost = float(row.get('DailyCost', 0) or 0)
        costs.append(round(cost, 4))
        tokens.append(row.get('DailyTokens', 0))
        calls.append(row.get('Calls', 0))
        running_total += cost
        cumulative_cost.append(round(running_total, 4))

    return {
        'labels': labels,
        'costs': costs,
        'cumulative_cost': cumulative_cost,
        'tokens': tokens,
        'calls': calls,
        'datasets': [
            {
                'label': 'Daily Cost ($)',
                'data': costs,
                'type': 'bar',
                'backgroundColor': '#10b981',
                'yAxisID': 'y'
            },
            {
                'label': 'Cumulative Cost ($)',
                'data': cumulative_cost,
                'type': 'line',
                'borderColor': '#3b82f6',
                'backgroundColor': 'transparent',
                'borderWidth': 2,
                'tension': 0.4,
                'yAxisID': 'y'
            }
        ]
    }

def format_ai_token_distribution(data):
    """Format AI token distribution for doughnut chart"""
    if not data or not data[0]:
        return {'labels': [], 'data': []}
    row = data[0]
    return {
        'labels': ['Input Tokens', 'Output Tokens'],
        'data': [row.get('InputTokens', 0), row.get('OutputTokens', 0)]
    }

if __name__ == '__main__':
    # Use environment variable for debug mode (default: False for production safety)
    import os
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode)
