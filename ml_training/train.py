import os
import sys
import pandas as pd
import numpy as np
import joblib
import kagglehub
import time
from concurrent.futures import ProcessPoolExecutor
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# Feature ordering to maintain consistency with backend/agents/ml_agent.py
FEATURE_KEYS = [
    "domain_age_days", "keyword_count", "entropy", "subdomain_depth", "is_https",
    "url_length", "hyphen_count", "tld_risk_score", "special_char_count", "numeric_substitution",
    "percent_encoding_count", "double_slash_redirect", "is_ip_address",
    "v_c_ratio", "consecutive_chars", "is_shortened", "has_non_standard_port",
    "path_depth", "has_suspicious_extension", "suspicious_subdomain"
]

def _extract_worker(url_label_tuple):
    """Worker function for parallel feature extraction."""
    # Move imports inside to avoid Windows pickling/import issues
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
    from tools.url_tools import extract_features
    
    url, label = url_label_tuple
    try:
        f = extract_features(url, skip_whois=True)
        if f:
            row = [f.get(k, 0) for k in FEATURE_KEYS]
            return row, label
    except Exception:
        pass
    return None

def main():
    print("--- GaudOn ML Trainer v3 (Multi-Class) ---", flush=True)
    
    # 1. Download Kaggle Dataset
    print("Downloading sid321axn/malicious-urls-dataset...", flush=True)
    path = kagglehub.dataset_download("sid321axn/malicious-urls-dataset")
    csv_file = next((os.path.join(path, f) for f in os.listdir(path) if f.endswith('.csv')), None)
    
    if not csv_file:
        print("Error: No CSV file found in dataset.", flush=True)
        return

    # 2. Load Data
    print("Loading dataset...", flush=True)
    df = pd.read_csv(csv_file)
    
    # Map labels to integers
    label_map = {"benign": 0, "phishing": 1, "malware": 2, "defacement": 3}
    df['label'] = df['type'].map(label_map)
    print(f"Dataset loaded: {len(df)} records.", flush=True)

    urls_to_process = list(zip(df['url'], df['label']))
    total = len(urls_to_process)

    # 3. Parallel Feature Extraction with Progress
    print(f"Extracting features from {total} URLs using multiprocessing...", flush=True)
    data, labels = [], []
    start_time = time.time()
    
    # Process in chunks to maintain memory and show progress
    chunk_size = 50000
    with ProcessPoolExecutor() as executor:
        for i in range(0, total, chunk_size):
            chunk = urls_to_process[i:i+chunk_size]
            results = list(executor.map(_extract_worker, chunk))
            
            for res in results:
                if res:
                    data.append(res[0])
                    labels.append(res[1])
            
            processed = min(i + chunk_size, total)
            print(f"Progress: {processed}/{total} ({(processed/total)*100:.1f}%)", flush=True)

    elapsed = time.time() - start_time
    print(f"Extraction complete in {elapsed:.2f}s ({len(data)} valid samples).", flush=True)

    # 4. Train/Test Split
    print("Splitting dataset (80% train, 20% test)...", flush=True)
    X, y = np.array(data), np.array(labels)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. Training
    print("Training Multi-Class Random Forest (200 trees)...", flush=True)
    # Using n_jobs=-1 for training too
    clf = RandomForestClassifier(n_estimators=200, max_depth=15, min_samples_leaf=2, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    # 6. Evaluation
    print("\n--- CLASSIFICATION REPORT ---", flush=True)
    target_names = ["benign", "phishing", "malware", "defacement"]
    print(classification_report(y_test, clf.predict(X_test), target_names=target_names), flush=True)

    # 7. Save Model
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'model.joblib'))
    joblib.dump(clf, output_path)
    print(f"\nModel saved successfully to: {output_path}", flush=True)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
