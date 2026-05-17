import os
import sys
import email
from email.policy import default
import pandas as pd
import glob

def parse_eml(file_path):
    try:
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=default)
            
        subject = msg.get('Subject', '')
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
                
        return subject, body
    except Exception as e:
        return "", ""

def process_apache_corpus(base_dir):
    print("Processing Apache SpamAssassin Corpus...")
    data = []
    
    ham_dirs = ['easy_ham', 'easy_ham_2', 'hard_ham']
    spam_dirs = ['spam', 'spam_2']
    
    for h_dir in ham_dirs:
        path = os.path.join(base_dir, h_dir)
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            for f in files:
                subj, body = parse_eml(os.path.join(path, f))
                data.append({"subject": subj, "body": body, "label": 0, "source": f"apache_{h_dir}"})
                
    for s_dir in spam_dirs:
        path = os.path.join(base_dir, s_dir)
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            for f in files:
                subj, body = parse_eml(os.path.join(path, f))
                data.append({"subject": subj, "body": body, "label": 1, "source": f"apache_{s_dir}"})
                
    return pd.DataFrame(data)

def main():
    # 1. Process Apache Dataset
    apache_dir = os.path.join("ml_training", "data", "raw", "spamassassin", "apache_extracted")
    apache_df = process_apache_corpus(apache_dir)
    print(f"Loaded {len(apache_df)} emails from Apache corpus.")
    
    # 2. Process Zenodo Dataset
    zenodo_path = os.path.join("ml_training", "data", "raw", "spamassassin", "zenodo", "SpamAssasin.csv")
    print(f"Loading Zenodo dataset from {zenodo_path}...")
    try:
        zenodo_df = pd.read_csv(zenodo_path)
        # Zenodo label: 0 for ham, 1 for spam. Let's ensure it's integer
        zenodo_df['label'] = pd.to_numeric(zenodo_df['label'], errors='coerce')
        zenodo_df = zenodo_df.dropna(subset=['label', 'body'])
        zenodo_df['label'] = zenodo_df['label'].astype(int)
        
        # Select relevant columns
        zenodo_df = zenodo_df[['subject', 'body', 'label']]
        zenodo_df['source'] = 'zenodo'
        
        print(f"Loaded {len(zenodo_df)} valid emails from Zenodo dataset.")
    except Exception as e:
        print(f"Failed to load Zenodo dataset: {e}")
        zenodo_df = pd.DataFrame(columns=["subject", "body", "label", "source"])
        
    # 3. Combine Datasets
    unified_df = pd.concat([apache_df, zenodo_df], ignore_index=True)
    
    # 4. Clean Data
    unified_df['subject'] = unified_df['subject'].fillna("")
    unified_df['body'] = unified_df['body'].fillna("")
    unified_df = unified_df[unified_df['body'].str.strip() != ""]
    
    # Remove duplicates
    unified_df = unified_df.drop_duplicates(subset=['body'])
    
    print(f"\nFinal Unified Dataset Size: {len(unified_df)} unique emails.")
    print("Label Distribution:")
    print(unified_df['label'].value_counts())
    
    # 5. Save Processed Dataset
    out_dir = os.path.join("ml_training", "data", "processed")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "unified_emails.csv")
    unified_df.to_csv(out_path, index=False)
    print(f"\nDataset saved to: {out_path}")

if __name__ == "__main__":
    main()
