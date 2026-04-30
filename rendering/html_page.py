"""Small HTML page assembly helpers."""


def html_document(title: str, style: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{style}
    </style>
</head>
<body>
{body}</body>
</html>
"""
