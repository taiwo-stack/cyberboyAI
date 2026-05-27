import os
import subprocess
import sys
from pathlib import Path

def load_env(env_path):
    env_vars = {}
    if not env_path.exists():
        print(f"Error: env file not found at {env_path}")
        sys.exit(1)
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                env_vars[key.strip()] = val.strip()
    return env_vars

def main():
    backend_dir = Path(__file__).resolve().parent.parent
    env_path = backend_dir / ".env"
    root_dir = backend_dir.parent
    template_path = root_dir / "aws-backend-ec2.yaml"
    
    print(f"Loading environment variables from {env_path}...")
    env_vars = load_env(env_path)
    
    # Map backend/.env variables to CloudFormation Parameters
    param_mapping = {
        "OpenAiApiKey": "OPENAI_API_KEY",
        "SupabaseUrl": "SUPABASE_URL",
        "SupabaseServiceKey": "SUPABASE_SERVICE_KEY",
        "AbuseIpDbApiKey": "ABUSEIPDB_API_KEY",
        "OtxApiKey": "OTX_API_KEY",
        "GoogleSafeBrowsingApiKey": "GOOGLE_SAFE_BROWSING_API_KEY",
        "AdminSecretKey": "ADMIN_SECRET_KEY",
        "HfToken": "HF_TOKEN",
        "HfRepoId": "HF_REPO_ID",
        "ProxyEnabled": "PROXY_ENABLED"
    }
    
    params = []
    for cf_param, env_key in param_mapping.items():
        val = env_vars.get(env_key)
        if val is None:
            if cf_param == "ProxyEnabled":
                val = "false"
            else:
                print(f"Error: Required environment variable {env_key} is missing in backend/.env")
                sys.exit(1)
        params.append(f"ParameterKey={cf_param},ParameterValue={val}")
    
    # Build AWS CLI Command
    cmd = [
        "aws", "cloudformation", "update-stack",
        "--stack-name", "cyberboyai-backend",
        "--template-body", f"file://{template_path}",
        "--capabilities", "CAPABILITY_IAM", "CAPABILITY_NAMED_IAM",
        "--parameters"
    ] + params
    
    print("Executing CloudFormation stack update...")
    # Hide parameters from printed command for security
    safe_cmd = [
        "aws", "cloudformation", "update-stack",
        "--stack-name", "cyberboyai-backend",
        "--template-body", f"file://{template_path}",
        "--capabilities", "CAPABILITY_IAM", "CAPABILITY_NAMED_IAM",
        "--parameters", "[SECRETS_HIDDEN]"
    ]
    print(f"Running command: {' '.join(safe_cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("\nStack update initiated successfully!")
        print(result.stdout)
    else:
        print("\nError initiating stack update:")
        print(result.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
