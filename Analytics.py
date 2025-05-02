from flask import Flask, render_template, jsonify
import pyodbc
from datetime import datetime, timedelta
import json
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
    # Pass chart configuration to the template
    return render_template('index.html', chart_config=config.get_chart_config_js())

@app.route('/api/category-distribution')
def category_distribution():
    """Get data for category distribution pie chart"""
    query = """
    SELECT c.CategoryName, COUNT(f.FactCardID) as CardCount
    FROM Categories c
    LEFT JOIN FactCards f ON c.CategoryID = f.CategoryID
    GROUP BY c.CategoryName
    ORDER BY COUNT(f.FactCardID) DESC
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/cards-per-category')
def cards_per_category():
    """Get data for cards per category bar chart"""
    query = """
    SELECT c.CategoryName, COUNT(f.FactCardID) as CardCount
    FROM Categories c
    LEFT JOIN FactCards f ON c.CategoryID = f.CategoryID
    GROUP BY c.CategoryName
    ORDER BY COUNT(f.FactCardID) DESC
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/view-mastery-correlation')
def view_mastery_correlation():
    """Get data for view count vs mastery scatter plot"""
    query = """
    SELECT ViewCount, Mastery * 100 as MasteryPercentage, Question
    FROM FactCards
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/interval-growth')
def interval_growth():
    """Get data for interval growth line chart"""
    query = """
    SELECT 
        CurrentInterval,
        COUNT(FactCardID) as CardCount
    FROM 
        FactCards
    GROUP BY 
        CurrentInterval
    ORDER BY 
        CurrentInterval
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/review-schedule')
def review_schedule():
    """Get data for review schedule timeline"""
    # Get cards due in the next 30 days
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    query = """
    SELECT 
        CONVERT(varchar, NextReviewDate, 23) as ReviewDate,
        COUNT(FactCardID) as CardCount
    FROM 
        FactCards
    WHERE 
        NextReviewDate BETWEEN ? AND ?
    GROUP BY 
        CONVERT(varchar, NextReviewDate, 23)
    ORDER BY 
        CONVERT(varchar, NextReviewDate, 23)
    """
    data = fetch_query(query, (today, end_date))
    return jsonify(data)

@app.route('/api/cards-added-over-time')
def cards_added_over_time():
    """Get data for cards added over time timeline"""
    query = """
    SELECT 
        CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, DateAdded), 0), 23) as Date,
        COUNT(FactCardID) as CardsAdded
    FROM 
        FactCards
    GROUP BY 
        CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, DateAdded), 0), 23)
    ORDER BY 
        CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, DateAdded), 0), 23)
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/learning-efficiency')
def learning_efficiency():
    """Get data for learning efficiency chart"""
    query = """
    SELECT 
        ViewCount,
        (Mastery * 100 / NULLIF(ViewCount, 0)) as EfficiencyScore,
        Question
    FROM 
        FactCards
    WHERE 
        ViewCount > 0
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/learning-curve')
def learning_curve():
    """Get data for learning curve line chart - using LastReviewDate"""
    query = """
    SELECT 
        CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, LastReviewDate), 0), 23) as Date,
        AVG(Mastery * 100) as AverageMastery
    FROM 
        FactCards
    WHERE
        LastReviewDate IS NOT NULL
    GROUP BY 
        CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, LastReviewDate), 0), 23)
    ORDER BY 
        CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, LastReviewDate), 0), 23)
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/stability-distribution')
def stability_distribution():
    """Get distribution of card stability values"""
    query = """
    SELECT 
        CASE
            WHEN Stability <= 1 THEN '0-1'
            WHEN Stability <= 5 THEN '1-5'
            WHEN Stability <= 10 THEN '5-10'
            WHEN Stability <= 20 THEN '10-20'
            WHEN Stability <= 50 THEN '20-50'
            WHEN Stability <= 100 THEN '50-100'
            ELSE '100+'
        END as StabilityRange,
        COUNT(FactCardID) as CardCount,
        MIN(Stability) as MinStability
    FROM FactCards
    GROUP BY CASE
            WHEN Stability <= 1 THEN '0-1'
            WHEN Stability <= 5 THEN '1-5'
            WHEN Stability <= 10 THEN '5-10'
            WHEN Stability <= 20 THEN '10-20'
            WHEN Stability <= 50 THEN '20-50'
            WHEN Stability <= 100 THEN '50-100'
            ELSE '100+'
        END
    ORDER BY MinStability
    """
    data = fetch_query(query)
    return jsonify(data)

@app.route('/api/chart-data')
def chart_data():
    """Get all chart data in a single request"""
    # Convert date objects to strings for SQL Server
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    data = {
        'categoryDistribution': fetch_query("""
            SELECT c.CategoryName, COUNT(f.FactCardID) as CardCount
            FROM Categories c
            LEFT JOIN FactCards f ON c.CategoryID = f.CategoryID
            GROUP BY c.CategoryName
            ORDER BY COUNT(f.FactCardID) DESC
        """),
        'viewMasteryCorrelation': fetch_query("""
            SELECT ViewCount, Mastery * 100 as MasteryPercentage, Question
            FROM FactCards
        """),
        'intervalGrowth': fetch_query("""
            SELECT 
                CurrentInterval,
                COUNT(FactCardID) as CardCount
            FROM 
                FactCards
            GROUP BY 
                CurrentInterval
            ORDER BY 
                CurrentInterval
        """),
        'reviewSchedule': fetch_query("""
            SELECT 
                CONVERT(varchar, NextReviewDate, 23) as ReviewDate,
                COUNT(FactCardID) as CardCount
            FROM 
                FactCards
            WHERE 
                NextReviewDate BETWEEN ? AND ?
            GROUP BY 
                CONVERT(varchar, NextReviewDate, 23)
            ORDER BY 
                CONVERT(varchar, NextReviewDate, 23)
        """, (today, end_date)),
        'cardsAddedOverTime': fetch_query("""
            SELECT 
                CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, DateAdded), 0), 23) as Date,
                COUNT(FactCardID) as CardsAdded
            FROM 
                FactCards
            GROUP BY 
                CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, DateAdded), 0), 23)
            ORDER BY 
                CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, DateAdded), 0), 23)
        """),
        'learningEfficiency': fetch_query("""
            SELECT 
                ViewCount,
                (Mastery * 100 / NULLIF(ViewCount, 0)) as EfficiencyScore,
                Question
            FROM 
                FactCards
            WHERE 
                ViewCount > 0
        """),
        'learningCurve': fetch_query("""
            SELECT 
                CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, LastReviewDate), 0), 23) as Date,
                AVG(Mastery * 100) as AverageMastery
            FROM 
                FactCards
            WHERE
                LastReviewDate IS NOT NULL
            GROUP BY 
                CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, LastReviewDate), 0), 23)
            ORDER BY 
                CONVERT(varchar, DATEADD(day, DATEDIFF(day, 0, LastReviewDate), 0), 23)
        """),
        'stabilityDistribution': fetch_query("""
            SELECT 
                CASE
                    WHEN Stability <= 1 THEN '0-1'
                    WHEN Stability <= 5 THEN '1-5'
                    WHEN Stability <= 10 THEN '5-10'
                    WHEN Stability <= 20 THEN '10-20'
                    WHEN Stability <= 50 THEN '20-50'
                    WHEN Stability <= 100 THEN '50-100'
                    ELSE '100+'
                END as StabilityRange,
                COUNT(FactCardID) as CardCount,
                MIN(Stability) as MinStability
            FROM FactCards
            GROUP BY CASE
                    WHEN Stability <= 1 THEN '0-1'
                    WHEN Stability <= 5 THEN '1-5'
                    WHEN Stability <= 10 THEN '5-10'
                    WHEN Stability <= 20 THEN '10-20'
                    WHEN Stability <= 50 THEN '20-50'
                    WHEN Stability <= 100 THEN '50-100'
                    ELSE '100+'
                END
            ORDER BY MIN(Stability)
        """)
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)