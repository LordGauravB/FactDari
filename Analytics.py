from flask import Flask, render_template, jsonify, send_from_directory
import pyodbc
from datetime import datetime, timedelta
import json
import os
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
    # Use the new analytics template
    return render_template('analytics.html')

@app.route('/resources/<path:filename>')
def serve_resources(filename):
    """Serve files from the Resources directory"""
    return send_from_directory(config.RESOURCES_DIR, filename)

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
    
    # Transform data for new frontend format
    formatted_data = {
        'category_distribution': {
            'labels': [row['CategoryName'] for row in data['categoryDistribution']],
            'data': [row['CardCount'] for row in data['categoryDistribution']]
        },
        'cards_per_category': format_cards_per_category(data['categoryDistribution']),
        'review_schedule_timeline': format_review_schedule(data['reviewSchedule']),
        'learning_curve': format_learning_curve(data['learningCurve']),
        'cards_added_over_time': format_cards_over_time(data['cardsAddedOverTime']),
        'view_mastery_correlation': format_scatter_data(data['viewMasteryCorrelation'], 'ViewCount', 'MasteryPercentage'),
        'interval_growth_distribution': format_bar_chart(data['intervalGrowth'], 'CurrentInterval', 'CardCount', 'Interval (days)'),
        'learning_efficiency': format_scatter_data(data['learningEfficiency'], 'ViewCount', 'EfficiencyScore'),
        'fsrs_stability_distribution': format_bar_chart(data['stabilityDistribution'], 'StabilityRange', 'CardCount', 'Stability Range')
    }
    
    return jsonify(formatted_data)

def format_cards_per_category(category_data):
    """Format data for stacked bar chart showing mastery levels"""
    categories = [row['CategoryName'] for row in category_data]
    
    # Compute mastered (Mastery >= 0.9) per category
    mastered_counts = []
    total_counts = []
    for cat in categories:
        total_row = fetch_query("""
            SELECT COUNT(*) AS cnt
            FROM FactCards f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE c.CategoryName = ?
        """, (cat,))
        total = total_row[0]['cnt'] if total_row else 0
        total_counts.append(total)
        
        mastered_row = fetch_query("""
            SELECT COUNT(*) AS cnt
            FROM FactCards f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE c.CategoryName = ? AND f.Mastery >= 0.9
        """, (cat,))
        mastered = mastered_row[0]['cnt'] if mastered_row else 0
        mastered_counts.append(mastered)
    
    learning_counts = [max(0, t - m) for t, m in zip(total_counts, mastered_counts)]
    
    return {
        'labels': categories,
        'datasets': [
            {
                'label': 'Mastered',
                'data': mastered_counts,
                'backgroundColor': '#4CAF50'
            },
            {
                'label': 'Learning',
                'data': learning_counts,
                'backgroundColor': '#FFC107'
            }
        ]
    }

def format_review_schedule(schedule_data):
    """Format review schedule for next 30 days"""
    # Create labels for next 30 days
    labels = []
    data_values = []
    schedule_dict = {row['ReviewDate']: row['CardCount'] for row in schedule_data}
    
    for i in range(30):
        date = datetime.now() + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        labels.append(f"Day {i+1}")
        data_values.append(schedule_dict.get(date_str, 0))
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Cards Due',
            'data': data_values,
            'backgroundColor': '#2196F3'
        }]
    }

def format_learning_curve(curve_data):
    """Format learning curve data"""
    return {
        'labels': [row['Date'] for row in curve_data],
        'datasets': [{
            'label': 'Average Retention',
            'data': [row['AverageMastery'] for row in curve_data],
            'borderColor': '#4CAF50',
            'backgroundColor': 'rgba(76, 175, 80, 0.1)',
            'fill': True
        }]
    }

def format_cards_over_time(time_data):
    """Format cards added over time with cumulative total"""
    labels = [row['Date'] for row in time_data]
    new_cards = [row['CardsAdded'] for row in time_data]
    
    # Calculate cumulative
    cumulative = []
    total = 0
    for count in new_cards:
        total += count
        cumulative.append(total)
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'New Cards',
                'data': new_cards,
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

def format_scatter_data(data, x_field, y_field):
    """Format data for scatter plots"""
    return {
        'datasets': [{
            'label': 'Data Points',
            'data': [{'x': row[x_field], 'y': row[y_field]} for row in data]
        }]
    }

def format_bar_chart(data, label_field, value_field, label_name):
    """Format data for simple bar charts"""
    return {
        'labels': [str(row[label_field]) for row in data],
        'datasets': [{
            'label': label_name,
            'data': [row[value_field] for row in data],
            'backgroundColor': '#9C27B0'
        }]
    }

if __name__ == '__main__':
    app.run(debug=True)
