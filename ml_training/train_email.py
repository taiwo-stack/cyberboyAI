import os
import pandas as pd
import numpy as np
import joblib
import time
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

def main():
    print("--- GaudOn Email Phishing Model Trainer ---", flush=True)
    
    # 1. Load Data
    data_path = os.path.join("ml_training", "data", "processed", "unified_emails.csv")
    if not os.path.exists(data_path):
        print(f"Error: Processed data not found at {data_path}. Run preprocess.py first.", flush=True)
        return
        
    print(f"Loading dataset from {data_path}...", flush=True)
    df = pd.read_csv(data_path)
    df['subject'] = df['subject'].fillna("")
    df['body'] = df['body'].fillna("")
    
    # Combine subject and body
    df['text'] = df['subject'] + " " + df['body']
    
    X = df['text'].values
    y = df['label'].values
    
    print(f"Dataset loaded: {len(df)} records.", flush=True)
    print(f"Class distribution: 0 (Ham) = {sum(y==0)}, 1 (Spam/Phishing) = {sum(y==1)}", flush=True)
    
    # 2. Train/Test Split
    print("\nSplitting dataset (80% train, 20% test)...", flush=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 3. TF-IDF Vectorization
    print("Vectorizing text using TF-IDF (max 5000 features)...", flush=True)
    start_time = time.time()
    vectorizer = TfidfVectorizer(max_features=5000, stop_words='english', max_df=0.8, min_df=5)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    print(f"Vectorization complete in {time.time() - start_time:.2f}s.", flush=True)
    
    # 4. Training
    print("Training Random Forest Classifier...", flush=True)
    start_time = time.time()
    clf = RandomForestClassifier(n_estimators=100, max_depth=20, min_samples_leaf=2, random_state=42, n_jobs=-1)
    clf.fit(X_train_vec, y_train)
    print(f"Training complete in {time.time() - start_time:.2f}s.", flush=True)
    
    # 5. Evaluation
    print("\n--- CLASSIFICATION REPORT ---", flush=True)
    y_pred = clf.predict(X_test_vec)
    target_names = ["Ham (Safe)", "Spam/Phishing"]
    print(classification_report(y_test, y_pred, target_names=target_names), flush=True)
    
    # 6. Save Model & Vectorizer
    model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models'))
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, 'email_model.joblib')
    vectorizer_path = os.path.join(model_dir, 'email_vectorizer.joblib')
    
    joblib.dump(clf, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    
    print(f"\nModel saved successfully to: {model_path}", flush=True)
    print(f"Vectorizer saved successfully to: {vectorizer_path}", flush=True)

if __name__ == "__main__":
    main()
