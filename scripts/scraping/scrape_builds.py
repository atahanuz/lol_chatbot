from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
import glob
import json

# Get project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # ssw_chatbot/
GAME_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'game_data')
COUNTER_DATA_DIR = os.path.join(GAME_DATA_DIR, 'counter_data')
BUILD_DATA_DIR = os.path.join(GAME_DATA_DIR, 'build_data')

def get_champion_list():
    """Extract champion names from counter_data files"""
    counter_files = glob.glob(os.path.join(COUNTER_DATA_DIR, '*_counters.json'))
    champions = []
    for f in counter_files:
        basename = os.path.basename(f)
        champ_name = basename.replace('_counters.json', '')
        champions.append(champ_name)
    return sorted(champions)

def get_items_from_section(driver, actions, section, selector='.image-wrapper'):
    """Extract item names by hovering over items in a section"""
    items = []
    wrappers = section.find_elements(By.CSS_SELECTOR, selector)
    for wrapper in wrappers:
        try:
            actions.move_to_element(wrapper).perform()
            time.sleep(0.25)
            tooltips = driver.find_elements(By.CSS_SELECTOR, '[class*="tooltip"]')
            for tip in tooltips:
                if tip.text:
                    item_name = tip.text.split('\n')[0].strip()
                    if item_name and item_name not in items:
                        items.append(item_name)
                    break
        except:
            continue
    return items

def scrape_champion_build(driver, champion_name):
    """Scrape build data for a single champion"""
    url = f"https://u.gg/lol/champions/{champion_name}/build"
    driver.get(url)

    build_data = {
        'champion': champion_name,
        'starting_items': [],
        'core_items': [],
        'fourth_item_options': [],
        'fifth_item_options': [],
        'sixth_item_options': [],
        'full_build': [],
        'summoner_spells': [],
        'keystone': None,
        'primary_runes': [],
        'secondary_runes': []
    }

    try:
        time.sleep(3)
        driver.execute_script('window.scrollTo(0, 1500);')
        time.sleep(1.5)

        actions = ActionChains(driver)

        # Find all content sections
        sections = driver.find_elements(By.CSS_SELECTOR, '[class*="content-section_content"]')

        for section in sections:
            header = section.find_elements(By.CSS_SELECTOR, '[class*="header"]')
            header_text = header[0].text if header else ''

            if 'Starting Items' in header_text:
                build_data['starting_items'] = get_items_from_section(driver, actions, section, '.image-wrapper')

            elif 'Core Items' in header_text:
                build_data['core_items'] = get_items_from_section(driver, actions, section, '.image-wrapper')

            elif 'Fourth Item' in header_text:
                build_data['fourth_item_options'] = get_items_from_section(driver, actions, section, '.item-img')[:3]

            elif 'Fifth Item' in header_text:
                build_data['fifth_item_options'] = get_items_from_section(driver, actions, section, '.item-img')[:3]

            elif 'Sixth Item' in header_text:
                build_data['sixth_item_options'] = get_items_from_section(driver, actions, section, '.item-img')[:3]

        # Build full 6-item build
        full_build = list(build_data['core_items'])
        if build_data['fourth_item_options']:
            full_build.append(build_data['fourth_item_options'][0])
        if build_data['fifth_item_options']:
            full_build.append(build_data['fifth_item_options'][0])
        if build_data['sixth_item_options']:
            full_build.append(build_data['sixth_item_options'][0])
        build_data['full_build'] = full_build[:6]

        # Summoner spells
        try:
            spell_imgs = driver.find_elements(By.CSS_SELECTOR, 'img[alt*="Summoner Spell"]')
            for img in spell_imgs[:2]:
                alt = img.get_attribute('alt') or ''
                spell_name = alt.replace('Summoner Spell ', '')
                if spell_name and spell_name not in build_data['summoner_spells']:
                    build_data['summoner_spells'].append(spell_name)
        except:
            pass

        # Runes
        try:
            keystone_imgs = driver.find_elements(By.CSS_SELECTOR, 'img[alt*="Keystone"]')
            if keystone_imgs:
                alt = keystone_imgs[0].get_attribute('alt') or ''
                build_data['keystone'] = alt.replace('The Keystone ', '')

            rune_imgs = driver.find_elements(By.CSS_SELECTOR, 'img[alt*="The Rune "]')
            for img in rune_imgs[:8]:
                alt = img.get_attribute('alt') or ''
                rune_name = alt.replace('The Rune ', '').replace('Tree ', '')
                if rune_name and 'Tree' not in rune_name:
                    if len(build_data['primary_runes']) < 3:
                        build_data['primary_runes'].append(rune_name)
                    elif len(build_data['secondary_runes']) < 2:
                        build_data['secondary_runes'].append(rune_name)
        except:
            pass

    except Exception as e:
        print(f"  Error: {e}")

    return build_data

def main():
    os.makedirs(BUILD_DATA_DIR, exist_ok=True)

    champions = get_champion_list()
    print(f"Found {len(champions)} champions to scrape")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,4000")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        for i, champion in enumerate(champions):
            output_file = os.path.join(BUILD_DATA_DIR, f'{champion}_build.json')

            if os.path.exists(output_file):
                print(f"[{i+1}/{len(champions)}] {champion} - already scraped, skipping")
                continue

            print(f"[{i+1}/{len(champions)}] Scraping {champion}...", end=' ')

            build_data = scrape_champion_build(driver, champion)

            with open(output_file, 'w') as f:
                json.dump(build_data, f, indent=2)

            full_build = build_data.get('full_build', [])
            print(f"OK - {len(full_build)} items in full build")

            time.sleep(0.5)

    finally:
        driver.quit()

    print(f"\nDone! All build data saved to {BUILD_DATA_DIR}/")

if __name__ == "__main__":
    main()
