from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
import os
import glob

# Get project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # ssw_chatbot/
GAME_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'game_data')
COUNTER_DATA_DIR = os.path.join(GAME_DATA_DIR, 'counter_data')
SYNERGY_DATA_DIR = os.path.join(GAME_DATA_DIR, 'synergy_data')

def get_champion_list():
    """Extract champion names from counter_data files"""
    counter_files = glob.glob(os.path.join(COUNTER_DATA_DIR, '*_counters.json'))
    champions = []
    for f in counter_files:
        # Extract champion name from filename
        basename = os.path.basename(f)
        champ_name = basename.replace('_counters.json', '')
        champions.append(champ_name)
    return sorted(champions)

def scrape_champion_duos(driver, champion_name):
    """Scrape duo data for a single champion"""
    url = f"https://u.gg/lol/champions/{champion_name}/duos"
    driver.get(url)

    try:
        # Wait for the table to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr, .rt-tr-group"))
        )
        time.sleep(2)  # Extra time for dynamic content
    except:
        print(f"  Timeout waiting for page to load")
        return []

    duos_data = []

    # Find table rows
    rows = driver.find_elements(By.CSS_SELECTOR, "tr, .rt-tr-group, [class*='TableRow']")

    for row in rows:
        try:
            text = row.text.strip()
            if not text or 'Rank' in text or 'Role' in text:
                continue

            parts = text.split('\n')
            if len(parts) >= 3:
                for i, part in enumerate(parts):
                    if '%' in part:
                        champion_name = None
                        win_rate = part.strip()

                        # Find champion name (usually before the %)
                        for j in range(i-1, -1, -1):
                            if parts[j].strip() and not parts[j].strip().isdigit():
                                champion_name = parts[j].strip()
                                break

                        if champion_name:
                            # Find matches count (usually last number)
                            matches = None
                            for p in reversed(parts):
                                p = p.replace(',', '')
                                if p.isdigit():
                                    matches = int(p)
                                    break

                            duos_data.append({
                                'champion': champion_name,
                                'duo_win_rate': win_rate,
                                'matches': matches
                            })
                        break
        except Exception as e:
            continue

    return duos_data

def main():
    # Create output directory
    os.makedirs(SYNERGY_DATA_DIR, exist_ok=True)

    # Get champion list
    champions = get_champion_list()
    print(f"Found {len(champions)} champions to scrape")

    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        for i, champion in enumerate(champions):
            output_file = os.path.join(SYNERGY_DATA_DIR, f'{champion}_duos.json')

            # Skip if already scraped
            if os.path.exists(output_file):
                print(f"[{i+1}/{len(champions)}] {champion} - already scraped, skipping")
                continue

            print(f"[{i+1}/{len(champions)}] Scraping {champion}...", end=' ')

            duos_data = scrape_champion_duos(driver, champion)

            if duos_data:
                with open(output_file, 'w') as f:
                    json.dump(duos_data, f, indent=2)
                print(f"OK - {len(duos_data)} duos")
            else:
                print("No data found")

            # Small delay to be respectful to the server
            time.sleep(0.5)

    finally:
        driver.quit()

    print(f"\nDone! All duo data saved to {SYNERGY_DATA_DIR}/")

if __name__ == "__main__":
    main()
