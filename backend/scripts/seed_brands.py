import os
import sys

# Add the parent directory to sys.path to allow importing tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.supabase_client import supabase

BRANDS = [
    # BANKS
    {"name": "GTBank", "domain": "gtbank.com", "category": "bank", "aliases": ["gtb", "guaranty trust"]},
    {"name": "Access Bank", "domain": "accessbank.com", "category": "bank", "aliases": ["access"]},
    {"name": "Zenith Bank", "domain": "zenithbank.com", "category": "bank", "aliases": ["zenith"]},
    {"name": "First Bank", "domain": "firstbank.ng", "category": "bank", "aliases": ["firstbank", "fbn"]},
    {"name": "UBA", "domain": "ubagroup.com", "category": "bank", "aliases": ["united bank for africa"]},
    {"name": "Fidelity", "domain": "fidelitybank.ng", "category": "bank", "aliases": ["fidelity bank"]},
    {"name": "Sterling", "domain": "sterlingbank.ng", "category": "bank", "aliases": ["sterling bank"]},
    {"name": "Wema", "domain": "wemabank.com", "category": "bank", "aliases": ["wema bank"]},
    {"name": "Polaris", "domain": "polarisbank.com", "category": "bank", "aliases": ["polaris bank"]},
    {"name": "Union Bank", "domain": "unionbankng.com", "category": "bank", "aliases": ["union bank"]},
    {"name": "Stanbic", "domain": "stanbicibtc.com", "category": "bank", "aliases": ["stanbic ibtc"]},
    {"name": "FCMB", "domain": "fcmb.com", "category": "bank", "aliases": []},

    # FINTECHS
    {"name": "OPay", "domain": "opay.com", "category": "fintech", "aliases": ["opay"]},
    {"name": "PalmPay", "domain": "palmpay.com", "category": "fintech", "aliases": ["palmpay"]},
    {"name": "Kuda", "domain": "kuda.com", "category": "fintech", "aliases": ["kuda bank"]},
    {"name": "Moniepoint", "domain": "moniepoint.com", "category": "fintech", "aliases": ["moniepoint"]},
    {"name": "Flutterwave", "domain": "flutterwave.com", "category": "fintech", "aliases": ["flutterwave"]},
    {"name": "Paystack", "domain": "paystack.com", "category": "fintech", "aliases": ["paystack"]},
    {"name": "Cowrywise", "domain": "cowrywise.com", "category": "fintech", "aliases": ["cowrywise"]},
    {"name": "PiggyVest", "domain": "piggyvest.com", "category": "fintech", "aliases": ["piggyvest"]},
    {"name": "Chipper", "domain": "chippercash.com", "category": "fintech", "aliases": ["chipper cash"]},

    # TELCOS
    {"name": "MTN", "domain": "mtn.com.ng", "category": "telco", "aliases": ["mtn nigeria"]},
    {"name": "Airtel", "domain": "ng.airtel.com", "category": "telco", "aliases": ["airtel nigeria"]},
    {"name": "Glo", "domain": "glo.com", "category": "telco", "aliases": ["globacom"]},
    {"name": "9mobile", "domain": "9mobile.com.ng", "category": "telco", "aliases": ["9mobile"]},

    # GOVERNMENT
    {"name": "CBN", "domain": "cbn.gov.ng", "category": "govt", "aliases": ["central bank of nigeria"]},
    {"name": "EFCC", "domain": "efccnigeria.org", "category": "govt", "aliases": ["efcc nigeria"]},
    {"name": "FIRS", "domain": "firs.gov.ng", "category": "govt", "aliases": ["federal inland revenue"]},
    {"name": "JAMB", "domain": "jamb.gov.ng", "category": "govt", "aliases": ["jamb nigeria"]},
    {"name": "INEC", "domain": "inec.gov.ng", "category": "govt", "aliases": ["inec nigeria"]},
    {"name": "NIN/NIMC", "domain": "nimc.gov.ng", "category": "govt", "aliases": ["nimc", "national identity management"]},

    # ECOMMERCE
    {"name": "Jumia", "domain": "jumia.com.ng", "category": "ecommerce", "aliases": ["jumia nigeria"]},
    {"name": "Konga", "domain": "konga.com", "category": "ecommerce", "aliases": ["konga nigeria"]},
    
    # GLOBAL BRANDS (New requested expansion)
    {"name": "PayPal", "domain": "paypal.com", "category": "fintech", "aliases": ["paypal"]},
    {"name": "Binance", "domain": "binance.com", "category": "fintech", "aliases": ["binance", "bnc"]},
    {"name": "Coinbase", "domain": "coinbase.com", "category": "fintech", "aliases": ["coinbase"]},
    {"name": "Google", "domain": "google.com", "category": "tech", "aliases": ["gmail", "google account"]},
    {"name": "Microsoft", "domain": "microsoft.com", "category": "tech", "aliases": ["outlook", "office 365", "msn"]},
    {"name": "Meta", "domain": "facebook.com", "category": "social", "aliases": ["facebook", "instagram", "whatsapp"]},
    {"name": "Amazon", "domain": "amazon.com", "category": "ecommerce", "aliases": ["amazon prime"]},
    {"name": "Apple", "domain": "apple.com", "category": "tech", "aliases": ["icloud", "apple id"]},
    {"name": "Netflix", "domain": "netflix.com", "category": "streaming", "aliases": []}
]

def seed_brands():
    print(f"[*] Seeding {len(BRANDS)} Nigerian brands...")
    
    try:
        # Batch upsert to nigerian_brands table on conflict domain
        # Using .upsert() with on_conflict='domain'
        response = supabase.table("nigerian_brands").upsert(
            BRANDS, 
            on_conflict="domain"
        ).execute()
        
        print(f"[+] Successfully seeded {len(BRANDS)} brands.")
        
    except Exception as e:
        print(f"[!] Error seeding brands: {e}")

if __name__ == "__main__":
    seed_brands()
