import csv
from datetime import datetime

QA_LOG_PATH = "qa_logs.csv"

def log_qa(question, answer, score):
    with open(QA_LOG_PATH, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([datetime.now().isoformat(), question, answer, score])