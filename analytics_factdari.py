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

@app.route('/')
def index():
    """Render the main analytics page"""
    return render_template('analytics_factdari.html')

# No static resource route is needed; template uses CDN-only assets

@app.route('/favicon.ico')
def favicon():
    """Serve a small SVG favicon to avoid 404s"""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'>"
        "<rect width='64' height='64' fill='#2563eb'/>"
        "<text x='50%' y='54%' dominant-baseline='middle' text-anchor='middle'"
        " font-size='42' fill='white'>F</text>"
        "</svg>"
    )
    return Response(svg, mimetype='image/svg+xml')

@app.route('/api/chart-data')
def chart_data():
    """Get all chart data for FactDari analytics"""
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Check if we need to return all facts
    return_all = request.args.get('all', 'false').lower() == 'true'
    
    data = {
        # Category distribution
        'categoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(f.FactID) as FactCount
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID
            GROUP BY c.CategoryName
            ORDER BY COUNT(f.FactID) DESC
        """),
        
        # Facts viewed per day (last 30 days)
        'factsViewedPerDay': fetch_query("""
            SELECT 
                CONVERT(varchar, ReviewDate, 23) as Date,
                COUNT(DISTINCT FactID) as FactsReviewed,
                COUNT(*) as TotalReviews
            FROM ReviewLogs
            WHERE ReviewDate >= ?
            GROUP BY CONVERT(varchar, ReviewDate, 23)
            ORDER BY CONVERT(varchar, ReviewDate, 23)
        """, (thirty_days_ago,)),
        
        # Most reviewed facts (top 10 for display)
        'mostReviewedFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                f.IsFavorite,
                f.IsEasy
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.ReviewCount > 0
            ORDER BY f.ReviewCount DESC
        """),
        
        # Least reviewed facts (include 0 reviews; show zeros first, then oldest last viewed)
        'leastReviewedFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                CASE 
                    WHEN f.LastViewedDate IS NULL THEN NULL
                    ELSE DATEDIFF(day, f.LastViewedDate, GETDATE())
                END as DaysSinceReview,
                f.IsFavorite,
                f.IsEasy
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            ORDER BY 
                f.ReviewCount ASC,
                CASE WHEN f.LastViewedDate IS NULL THEN 0 ELSE 1 END ASC,
                f.LastViewedDate ASC
        """),
        
        # Facts added over time
        'factsAddedOverTime': fetch_query("""
            SELECT 
                CONVERT(varchar, DateAdded, 23) as Date,
                COUNT(FactID) as FactsAdded
            FROM Facts
            GROUP BY CONVERT(varchar, DateAdded, 23)
            ORDER BY CONVERT(varchar, DateAdded, 23)
        """),
        
        # Review frequency heatmap data (last 7 days, by hour)
        'reviewHeatmap': fetch_query("""
            SELECT 
                DATEPART(hour, ReviewDate) as Hour,
                DATEPART(weekday, ReviewDate) as DayOfWeek,
                COUNT(*) as ReviewCount
            FROM ReviewLogs
            WHERE ReviewDate >= ?
            GROUP BY DATEPART(hour, ReviewDate), DATEPART(weekday, ReviewDate)
            ORDER BY DATEPART(weekday, ReviewDate), DATEPART(hour, ReviewDate)
        """, (seven_days_ago,)),
        
        # Category distribution for favorite cards
        'favoriteCategoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(f.FactID) as FavoriteCount
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.IsFavorite = 1
            GROUP BY c.CategoryName
            HAVING COUNT(f.FactID) > 0
            ORDER BY COUNT(f.FactID) DESC
        """),
        
        # Category distribution for known/easy cards
        'knownCategoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(f.FactID) as KnownCount
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID AND f.IsEasy = 1
            GROUP BY c.CategoryName
            HAVING COUNT(f.FactID) > 0
            ORDER BY COUNT(f.FactID) DESC
        """),
        
        # All favorite facts
        'allFavoriteFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                f.IsFavorite,
                f.IsEasy,
                CASE 
                    WHEN f.LastViewedDate IS NULL THEN NULL
                    ELSE DATEDIFF(day, f.LastViewedDate, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.IsFavorite = 1
            ORDER BY NEWID()
        """ if not return_all else """
            SELECT
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                f.IsFavorite,
                f.IsEasy,
                CASE 
                    WHEN f.LastViewedDate IS NULL THEN NULL
                    ELSE DATEDIFF(day, f.LastViewedDate, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.IsFavorite = 1
            ORDER BY f.ReviewCount DESC
        """),
        
        # All known facts
        'allKnownFacts': fetch_query("""
            SELECT TOP 10
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                f.IsFavorite,
                f.IsEasy,
                CASE 
                    WHEN f.LastViewedDate IS NULL THEN NULL
                    ELSE DATEDIFF(day, f.LastViewedDate, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.IsEasy = 1
            ORDER BY NEWID()
        """ if not return_all else """
            SELECT
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                f.IsFavorite,
                f.IsEasy,
                CASE 
                    WHEN f.LastViewedDate IS NULL THEN NULL
                    ELSE DATEDIFF(day, f.LastViewedDate, GETDATE())
                END as DaysSinceReview
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.IsEasy = 1
            ORDER BY f.ReviewCount DESC
        """),
        
        # Categories viewed today
        'categoriesViewedToday': fetch_query("""
            SELECT c.CategoryName, COUNT(DISTINCT rl.FactID) as ViewedCount
            FROM Categories c
            INNER JOIN Facts f ON c.CategoryID = f.CategoryID
            INNER JOIN ReviewLogs rl ON f.FactID = rl.FactID
            WHERE CONVERT(date, rl.ReviewDate) = CONVERT(date, GETDATE())
            GROUP BY c.CategoryName
            ORDER BY COUNT(DISTINCT rl.FactID) DESC
        """),
        
        # Review streak data
        'reviewStreak': calculate_review_streak(),
        
        # Category review distribution
        'categoryReviews': fetch_query("""
            SELECT 
                c.CategoryName,
                SUM(f.ReviewCount) as TotalReviews,
                AVG(f.ReviewCount) as AvgReviewsPerFact
            FROM Categories c
            LEFT JOIN Facts f ON c.CategoryID = f.CategoryID
            GROUP BY c.CategoryName
            ORDER BY SUM(f.ReviewCount) DESC
        """),
        
        # Count of favorite facts
        'favoritesCount': fetch_query("""
            SELECT COUNT(*) as FavoriteCount
            FROM Facts
            WHERE IsFavorite = 1
        """),
        
        # Count of known facts (marked as easy)
        'knownFactsCount': fetch_query("""
            SELECT COUNT(*) as KnownCount
            FROM Facts
            WHERE IsEasy = 1
        """)
    }
    
    # Format data for frontend
    formatted_data = {
        'category_distribution': format_pie_chart(data['categoryDistribution'], 'CategoryName', 'FactCount'),
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
        # Include favorite/known fact tables for the frontend
        'allFavoriteFacts': format_table_data(data['allFavoriteFacts']),
        'allKnownFacts': format_table_data(data['allKnownFacts'])
    }

    # If all=true, also include ALL facts (including those with 0 reviews)
    if return_all:
        # Get ALL facts sorted by review count (including 0 reviews)
        formatted_data['all_most_reviewed_facts'] = format_table_data(fetch_query("""
            SELECT 
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                f.IsFavorite,
                f.IsEasy
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            ORDER BY f.ReviewCount DESC, f.Content
        """))
        
        # Get ALL facts sorted by least reviewed (including 0 reviews)
        formatted_data['all_least_reviewed_facts'] = format_table_data(fetch_query("""
            SELECT 
                f.Content,
                f.ReviewCount,
                c.CategoryName,
                CASE 
                    WHEN f.LastViewedDate IS NULL THEN NULL
                    ELSE DATEDIFF(day, f.LastViewedDate, GETDATE())
                END as DaysSinceReview,
                f.IsFavorite,
                f.IsEasy
            FROM Facts f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            ORDER BY 
                f.ReviewCount ASC,
                CASE WHEN f.LastViewedDate IS NULL THEN 0 ELSE 1 END ASC,
                f.LastViewedDate ASC
        """))

    # Add average per-view duration by day for last 30 days
    avg_view_duration = fetch_query("""
        SELECT 
            CONVERT(varchar, ReviewDate, 23) as Date,
            AVG(CASE WHEN SessionDuration IS NULL THEN NULL ELSE CAST(SessionDuration AS FLOAT) END) as AvgSeconds
        FROM ReviewLogs
        WHERE ReviewDate >= ?
        GROUP BY CONVERT(varchar, ReviewDate, 23)
        ORDER BY CONVERT(varchar, ReviewDate, 23)
    """, (thirty_days_ago,))

    formatted_data['avg_view_duration_per_day'] = format_single_line_chart(
        avg_view_duration,
        label='Avg View Duration (s)',
        value_field='AvgSeconds'
    )

    # Add recent session summaries (last 20 sessions)
    recent_sessions = fetch_query("""
        SELECT TOP 20
            s.SessionID,
            s.StartTime,
            s.EndTime,
            s.DurationSeconds,
            COUNT(rl.ReviewLogID) AS Views,
            COUNT(DISTINCT rl.FactID) AS DistinctFacts
        FROM ReviewSessions s
        LEFT JOIN ReviewLogs rl ON rl.SessionID = s.SessionID
        GROUP BY s.SessionID, s.StartTime, s.EndTime, s.DurationSeconds
        ORDER BY s.SessionID DESC
    """)
    formatted_data['recent_sessions'] = recent_sessions

    return jsonify(formatted_data)

def calculate_review_streak():
    """Calculate the current review streak"""
    query = """
    SELECT DISTINCT CONVERT(date, ReviewDate) as ReviewDate
    FROM ReviewLogs
    ORDER BY CONVERT(date, ReviewDate) DESC
    """
    
    review_dates = fetch_query(query)
    
    if not review_dates:
        return {'current_streak': 0, 'longest_streak': 0, 'last_review': None}
    
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
        return {'current_streak': 0, 'longest_streak': 0, 'last_review': start.isoformat()}

    # Count consecutive days backward from the start day
    current_streak = 1
    base = start
    for next_date in ordered_dates[1:]:
        if next_date == base - timedelta(days=current_streak):
            current_streak += 1
        else:
            break
    
    # Calculate longest streak (simplified)
    longest_streak = current_streak  # For now, just use current
    
    last_review = ordered_dates[0].isoformat() if ordered_dates else None
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
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

def format_bar_chart(data, label_field, value_field):
    """Format data for bar charts"""
    return {
        'labels': [row[label_field] for row in data],
        'datasets': [{
            'label': 'Total Reviews',
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

if __name__ == '__main__':
    app.run(debug=True)
