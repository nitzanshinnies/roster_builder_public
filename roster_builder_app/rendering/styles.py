"""Shared CSS for generated HTML reports."""

BASE_TABLE_STYLE = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            direction: rtl;
        }
        h1 {
            text-align: center;
            color: #333;
            font-size: 1.5em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        th, td {
            border: 1px solid #e0e0e0;
            text-align: center;
            font-size: 14px;
        }
        th {
            background: #4a5568;
            color: white;
            font-weight: 600;
        }
        @media print {
            body { padding: 0; background: white; }
            table { box-shadow: none; }
        }
"""

JUSTICE_STYLE = BASE_TABLE_STYLE + """
        h1 {
            margin-bottom: 8px;
        }
        h2 {
            text-align: center;
            margin-bottom: 20px;
            color: #666;
            font-size: 1.1em;
            font-weight: 400;
        }
        table {
            margin-bottom: 30px;
        }
        th, td {
            padding: 10px 8px;
        }
        td.guard-name {
            background: #edf2f7;
            font-weight: 600;
            color: #2d3748;
            text-align: right;
            padding-right: 12px;
        }
        td.total {
            font-weight: 700;
            background: #ebf4ff;
        }
        td.min-rest {
            font-weight: 600;
        }
        td.rest-ok {
            color: #276749;
            background: #f0fff4;
        }
        td.rest-warn {
            color: #c53030;
            background: #fff5f5;
        }
        .highlight-max {
            color: #c53030;
            font-weight: 700;
        }
        .highlight-min {
            color: #276749;
            font-weight: 700;
        }
"""

ROSTER_STYLE = BASE_TABLE_STYLE + """
        h1 {
            margin-bottom: 20px;
        }
        h1 + table {
            margin-bottom: 36px;
        }
        th, td {
            padding: 12px 8px;
        }
        th .date {
            display: block;
            font-size: 12px;
            font-weight: 400;
            opacity: 0.85;
        }
        td.shift-label {
            background: #edf2f7;
            font-weight: 600;
            color: #2d3748;
            white-space: nowrap;
            min-width: 90px;
        }
        tr:nth-child(even) td:not(.shift-label) {
            background: #f7fafc;
        }
        tr:hover td:not(.shift-label) {
            background: #ebf4ff;
        }
"""
