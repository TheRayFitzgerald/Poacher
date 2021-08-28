from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time, os, platform, json, sys

GH_URL = 'https://www.grubhub.com/restaurant/example_restaurant'
MENU = '1599675614973x652726785232916400'


dirpath = os.getcwd()
chromepath = dirpath + '/assets/chromedriver_%s' % (platform.system()).lower()


def get_item(browser, id, item_price):
    """ given an id, scrape a menu item and all of its options """
    button = browser.find_element_by_id(id)
    browser.execute_script("arguments[0].click();", button)
    time.sleep(1)

    innerHTML = browser.page_source
    html = BeautifulSoup(innerHTML, 'html.parser')

    _options = []

    options = html.find_all('div', class_='menuItemModal-options') # menuItemModal-choice-option-description
    for option in options:
        single_option=dict()
        single_option['modifiername_text'] = name = option.find(class_='menuItemModal-choice-name').text

        instruction_text = option.find(class_='menuItemModal-choice-instructions').text.replace('.','').split(' - ')

        if instruction_text[0] == 'Required':
            single_option['required_boolean']=True
            single_option['numberallowedselections_number']= [int(s) for s in instruction_text[1].split() if s.isdigit()][0]
        else:
            single_option['required_boolean']=False
            if instruction_text[1] == "Choose as many as you like":
                single_option['numberallowedselections_number']=0
            else:
                single_option['numberallowedselections_number']= [int(s) for s in instruction_text[1].split() if s.isdigit()][0]

        _choices=[]
        choices = option.find_all('span', class_='menuItemModal-choice-option-description')
        for choice in choices:
            #print(choice.text.split(' + ')[0] + choice.text.split(' + ')[1])
            if ' + ' in choice.text:
                _choices.append({'name_text':choice.text.split(' + ')[0], 'price_number':float(choice.text.split(' + ')[1].replace('$', ''))})
                # infering that if mod first item price is the same as top-level item price, then it must be a size-based modifier
                if choices.index(choice) == 0 and float(choice.text.split(' + ')[1].replace('$', '')) == item_price:
                    single_option['modifiersize_boolean'] = True
            else:
                _choices.append({'name_text':choice.text, 'price_number':0})

        single_option['modifiermenuitems_list_custom_menuitem'] = _choices
        #append the dictionary
        _options.append(single_option)
    return _options

def scrape_menu(url, menu_id):
    """ given a valid grubhub url, scrape the menu of a restaurant """
    print('Running...')
    chrome_options = Options()
    # To disable headless mode (for debugging or troubleshooting), comment out the following line:
    chrome_options.add_argument("--headless")

    browser = webdriver.Chrome(options=chrome_options, executable_path = chromepath)
    browser.get(url)
    time.sleep(7)
    innerHTML = browser.page_source

    html = BeautifulSoup(innerHTML, 'html.parser')
    menu = html.find_all("div",{"class":"menuSectionsContainer"})[0]
    #menu = html.find_element(By.XPATH, '//*[@id="ghs-restaurant-menu"]/div/div/ghs-impression-tracker/div')
    if menu is None:
        print('menu fail')
        scrape_menu(url)
        return

    # Categories
    cats = menu.find_all('ghs-restaurant-menu-section')
    if not cats:
        print('cats fail')
        #scrape_menu(url)
        return
    #print(len(cats))
    #cats = cats[1:2]

    cat_titles = [cat.find('h3', class_='menuSection-title').text for cat in cats]
    print(cat_titles)
    cat_items = [[itm.text for itm in cat.find_all('a', class_='menuItem-name')] for cat in cats]
    prices = [[p.text for p in cat.find_all('span', class_='menuItem-displayPrice')] for cat in cats]
    descriptions = [[itm.text for itm in cat.find_all('p', class_='menuItemNew-description--truncate')] for cat in cats]
    images = [[itm['src'] for itm in cat.find_all('img', class_='u-width-full u-height-full menuItemNew-imageMagazine-img')] for cat in cats]
    print(images)

    ids = []
    for cat in cats:
        cat_ids = []
        items = cat.find_all('div', class_='menuItem-inner')
        for item in items:
            cat_ids.append(item.get('id'))
        ids.append(cat_ids)

    full_menu = {}
    for ind, title in enumerate(cat_titles):
        if title == 'Dinner Entrees':

            all_items = []
            for ind2, itm_name in enumerate(cat_items[ind]):
                item = {}
                item['name_text'] = itm_name
                item['price_number'] = float(prices[ind][ind2].replace('$', ''))
                item['description_text']= descriptions[ind][ind2]
                item['menu_custom_menu'] = menu_id
                try:
                    item['image_image'] = images[ind][ind2]
                except:
                    pass
                item['menuitemmodifiers_list_custom_menuitemmodifiers'] = get_item(browser, ids[ind][ind2], item['price_number'])
                all_items.append(item)
            full_menu[title] = all_items
    path = '/'.join(os.path.realpath(__file__).split('/')[:-1])
    with open('data/data_cd_dinner2.json', 'w') as f:
        json.dump(full_menu, f, indent=4)
    print('[Finished]')
    return full_menu
#print(sys.argv[1])
scrape_menu(GH_URL, 3)
#example link: 'https://www.grubhub.com/restaurant/insomnia-cookies-76-pearl-st-new-york/295836'
