import time, random, os, sys, requests, hashlib, struct
from colorama import Fore, init
init(autoreset=True)

BTC_PRICE_USD = 65000  # geschaetzter BTC Preis
MIN_USD = 50           # Mindestbalance in USD

# Zieladressen aus OwnBTCAdress.txt
def load_targets():
    try:
        with open("OwnBTCAdress.txt", "r") as f:
            addrs = []
            for line in f:
                parts = line.strip().split()
                if parts and (parts[0].startswith("1") or parts[0].startswith("3") or parts[0].startswith("bc1")):
                    addrs.append(parts[0])
            return addrs
    except:
        return []

def generate_btc_keypair():
    """Generate random BTC private key and address (P2PKH)"""
    try:
        import ecdsa, base58, hashlib
        private_key = os.urandom(32)
        signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        verifying_key = signing_key.get_verifying_key()
        public_key = b'\x04' + verifying_key.to_string()
        sha256 = hashlib.sha256(public_key).digest()
        ripemd160 = hashlib.new('ripemd160', sha256).digest()
        network_byte = b'\x00' + ripemd160
        checksum = hashlib.sha256(hashlib.sha256(network_byte).digest()).digest()[:4]
        address = base58.b58encode(network_byte + checksum).decode()
        return private_key.hex(), address
    except Exception as e:
        return None, None

def get_btc_balance(address):
    """Check BTC balance via blockchain.info with fallback"""
    endpoints = [
        f"https://blockchain.info/q/addressbalance/{address}",
        f"https://blockstream.info/api/address/{address}",
    ]
    # Try blockchain.info first (returns satoshis directly)
    try:
        resp = requests.get(endpoints[0], timeout=10)
        if resp.status_code == 200:
            return int(resp.text) / 1e8
    except:
        pass
    # Fallback: blockstream
    try:
        resp = requests.get(endpoints[1], timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            funded = data["chain_stats"]["funded_txo_sum"]
            spent = data["chain_stats"]["spent_txo_sum"]
            return (funded - spent) / 1e8
    except:
        pass
    return None

# ── STARTUP ───────────────────────────────────────────────────────────────────
try:
    import ecdsa, base58
except ImportError:
    print(Fore.RED + "[!] Fehlende Pakete — installiere: pip install ecdsa base58")
    sys.exit(1)

target_wallets = load_targets()

print(Fore.MAGENTA + "="*60)
print(Fore.CYAN    + "  Yantes BTC API Checker — by Yante Yamamoto")
print(Fore.MAGENTA + "="*60)
print(Fore.YELLOW  + f"  Mindestbalance : ${MIN_USD} USD")
if target_wallets:
    print(Fore.GREEN + f"  Zieladressen   : {len(target_wallets)} geladen")
    for i, w in enumerate(target_wallets, 1):
        print(Fore.CYAN + f"    {i}. {w}")
else:
    print(Fore.YELLOW + "  [~] Keine Zieladressen — checkt alle generierten")
print(Fore.MAGENTA + "="*60 + "\n")

target_set = set(target_wallets)
checked = 0
t0 = time.time()

def crack_wallet(wallet_idx, wallet, total):
    """Infinite loop against one BTC address until private key matches"""
    print(Fore.CYAN + f"\n  Wallet {wallet_idx}/{total}: {wallet}")
    print(Fore.MAGENTA + "="*60)
    local_checked = 0
    t_start = time.time()
    while True:
        private_key_hex, address = generate_btc_keypair()
        if not address:
            continue
        if address == wallet:
            balance_btc = get_btc_balance(address) or 0
            balance_usd = balance_btc * BTC_PRICE_USD
            print(Fore.GREEN + f"\n[***] MATCH — Wallet {wallet_idx}/{total}")
            print(Fore.GREEN + f"  Address     : {address}")
            print(Fore.GREEN + f"  Private Key : {private_key_hex}")
            print(Fore.GREEN + f"  Balance     : {balance_btc:.8f} BTC (~${balance_usd:.2f})")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(script_dir, "BitcoinFoundIt.txt"), "a", encoding="utf-8") as f:
                f.write("="*60 + "\n")
                f.write(f"BTC MATCH — Wallet {wallet_idx}/{total}\n")
                f.write(f"Address     : {address}\n")
                f.write(f"Private Key : {private_key_hex}\n")
                f.write(f"Balance BTC : {balance_btc:.8f}\n")
                f.write(f"Balance USD : ~${balance_usd:.2f}\n")
                f.write(f"Time        : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n")
            print(Fore.GREEN + f"[OK] Gespeichert in BitcoinFoundIt.txt — weiter mit Wallet {wallet_idx+1}/{total}\n")
            time.sleep(2)
            return
        local_checked += 1
        elapsed = time.time() - t_start
        speed = local_checked / elapsed if elapsed > 0 else 0
        print(f"\r  {Fore.MAGENTA}[{local_checked:,} | {speed:.0f}/s | Wallet {wallet_idx}/{total}]  "
              f"{Fore.GREEN}Key: {Fore.WHITE}{private_key_hex[:16]}...  "
              f"{Fore.CYAN}Addr: {Fore.WHITE}{address}{Fore.RESET}   ", end="", flush=True)
        time.sleep(0.05)

# ── INFINITE LOOP — wallet by wallet ─────────────────────────────────────────
total = len(target_wallets)
for idx, wallet in enumerate(target_wallets, 1):
    crack_wallet(idx, wallet, total)

print(Fore.GREEN + f"\n  ALLE {total} WALLETS GECRACKT — Ergebnisse in founditBTC.txt\n")
