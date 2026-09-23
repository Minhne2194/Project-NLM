GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Container cards */
.stCard {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}

/* Citation chip badge */
.citation-chip {
    display: inline-block;
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    margin-right: 6px;
    margin-bottom: 4px;
}

/* Flashcard container */
.flashcard-box {
    background: #1e1e2f;
    border-radius: 12px;
    border: 1px solid #3b3b54;
    padding: 24px;
    margin-bottom: 18px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.flashcard-box:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.2);
}

.flashcard-front {
    font-size: 17px;
    font-weight: 600;
    color: #e0e7ff;
    margin-bottom: 12px;
}

.flashcard-back {
    font-size: 15px;
    color: #cbd5e1;
    border-top: 1px dashed #4b5563;
    padding-top: 12px;
}

/* Quiz Box */
.quiz-card {
    background: #181825;
    border-radius: 12px;
    border: 1px solid #313244;
    padding: 20px;
    margin-bottom: 20px;
}

.quiz-question {
    font-size: 16px;
    font-weight: 600;
    color: #f5c2e7;
    margin-bottom: 14px;
}

.quiz-option {
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 8px;
    background: #1e1e2e;
    border: 1px solid #45475a;
    font-size: 14px;
}
</style>
"""
