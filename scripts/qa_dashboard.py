import streamlit as st
import pandas as pd

QA_LOG_PATH = "logs/qa_logs.csv"

st.title("Code Wiz QA Dashboard")

df = pd.read_csv(QA_LOG_PATH, names=["timestamp", "user_type", "question", "answer"])

# Most common questions by user type
st.subheader("Most common questions by Franchisee")
st.write(df[df["user_type"].str.lower() == "franchisee"]["question"].value_counts().head(10))

st.subheader("Most common questions by Support/Technical Team")
st.write(df[df["user_type"].str.lower().isin(["support/technical team", "support", "technical"])]["question"].value_counts().head(10))

st.subheader("Most common questions by Management/Leadership")
st.write(df[df["user_type"].str.lower().isin(["management/leadership", "leadership", "management"])]["question"].value_counts().head(10))

# Unanswered questions (custom logic)
unanswered_mask = df["answer"].str.strip().str.lower() == "I couldn’t find a clear answer based on current documentation.".lower()
st.subheader("Unanswered questions")
st.write(df[unanswered_mask][["user_type", "question"]])

# Most relevant chunks (if you have a score column)
if "score" in df.columns:
    st.subheader("Most relevant chunks")
    st.write(df.sort_values("score", ascending=False).head(10)[["question", "score"]])