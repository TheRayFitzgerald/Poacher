import requests, json, time, sys
from grubhub_scrape import scrape_menu

DATA_API_ENDPOINT='https://example.com/api/1.1/obj/%s'
DATA_API_ENDPOINT_BULK='https://example.com/api/1.1/obj/%s/bulk'

GH_URL = 'https://www.grubhub.com/restaurant/example_restaurant'
RESTAURANT_ID = '1604088652939x955424457933102600'


menuItem_ID_list=list()
recorded_modifier_sets=dict()
recorded_option_menuItems=dict()
data = json.load(open('data.json'))
offset=0

def create_menu(restaurant_id):
    print('creating menu')
    r_menu = requests.post(DATA_API_ENDPOINT % 'menu', data={'restaurant_custom_restaurantes': '1586078023745x937039188582989800'})
    print('adding menu to restaurant')
    r_restaurant = requests.patch(DATA_API_ENDPOINT % ('restaurants/' + RESTAURANT_ID), \
        data={'menu_custom_menu': json.loads(r_menu.text)['id']})
    print(r_restaurant.text)
    return json.loads(r_menu.text)['id']



def freeze(d):
    if isinstance(d, dict):
        return frozenset((key, freeze(value)) for key, value in d.items())
    elif isinstance(d, list):
        return tuple(freeze(value) for value in d)
    return d

def upload_to_bubble(menu_id, scraped_menu):
    #data = scraped_menu
    data= json.load(open(scraped_menu))
    menu_categories_ids = list()
    for category, item_list in data.items():
        print('------------------ %s --------------------' % category)
        #create the menuCategory and store the ID
        r = requests.post(DATA_API_ENDPOINT % 'menucategories', data={'name_text': category})
        print(r.text)
        categoryID = json.loads(r.text)['id']
        menu_categories_ids.append(categoryID)

        for item in item_list:
            #item['menu_custom_menu']="1600882687618x714029763212864500"
            item['itemcategories_custom_subcategories'] = categoryID
            for i in range(len(item['menuitemmodifiers_list_custom_menuitemmodifiers'])):
                offset=0
                modifier_original_copy = item['menuitemmodifiers_list_custom_menuitemmodifiers'][i]
                modifier = item['menuitemmodifiers_list_custom_menuitemmodifiers'][i]

                if freeze(item['menuitemmodifiers_list_custom_menuitemmodifiers'][i]) in recorded_modifier_sets:
                    print('### DUPLICATE MODIFIER SET ###')
                    # assign the unique id of the modifier set
                    try:

                        item['menuitemmodifiers_list_custom_menuitemmodifiers'][i] = recorded_modifier_sets[freeze(item['menuitemmodifiers_list_custom_menuitemmodifiers'][i])]

                    except Exception as e:
                        print('did not assign ID')
                        print(e)
                        sys.exit(1)

                else:
                    # enter it into the records. the value of the modifier ID will be added after the POST Request
                    #recorded_modifier_sets[freeze(item['menuitemmodifiers_list_custom_menuitemmodifiers'][i])] = ''
                    # list to keep a copy of the original MenuItems before they are reassigned to their Bubble IDs
                    original_modifier_menuItem_objects=list()
                    # NEW MODIFIER SET
                    print('!!! NEW MODIFIER SET !!!')
                    # ITERATE THROUGH MENU ITEMS(just name & price)
                    for j in range(len(modifier['modifiermenuitems_list_custom_menuitem'])):
                        original_modifier_menuItem_objects.append(modifier['modifiermenuitems_list_custom_menuitem'][j])
                        #item has already been recorded - avoid duplicate upload
                        if freeze(modifier['modifiermenuitems_list_custom_menuitem'][j]) in recorded_option_menuItems:
                            print('### DUPLICATE MENUITEM ###')
                            #replace with menuItem ID
                            modifier['modifiermenuitems_list_custom_menuitem'][j] = recorded_option_menuItems[freeze(modifier['modifiermenuitems_list_custom_menuitem'][j])]
                        else:
                            print('!!! NEW MENUITEM !!!')
                            try:
                                r = requests.post(DATA_API_ENDPOINT % 'menuitem', data = {'name_text':modifier['modifiermenuitems_list_custom_menuitem'][j]['name_text'],
                                                                                            'price_number':modifier['modifiermenuitems_list_custom_menuitem'][j]['price_number']})
                                #record and then add ID to modifier's list of menuItems
                                recorded_option_menuItems[freeze(modifier['modifiermenuitems_list_custom_menuitem'][j])] = json.loads(r.text)['id']
                                modifier['modifiermenuitems_list_custom_menuitem'][j] = json.loads(r.text)['id']
                            except:
                                print('new menu item post failed')
                                sys.exit(1)
                        # bubble does not accept single item lists. Need to append an empty item to make it length of 2
                    if len(modifier['modifiermenuitems_list_custom_menuitem']) == 1:
                        modifier['modifiermenuitems_list_custom_menuitem'].append("")
                        offset=1

                    # create the modifier set & record it
                    try:
                        r = requests.post(DATA_API_ENDPOINT % 'menuitemmodifier', data=modifier)
                        # record the original modifier
                        # reinstate the original modifier by changing the menuItems back to their original form
                        for t in range(len(modifier['modifiermenuitems_list_custom_menuitem']) - offset):
                            modifier['modifiermenuitems_list_custom_menuitem'][t] = original_modifier_menuItem_objects[t]
                        if offset == 1:
                            modifier['modifiermenuitems_list_custom_menuitem'].pop()

                        print(r.text)
                        recorded_modifier_sets[freeze(modifier)] = json.loads(r.text)['id']

                        # assign the unique id of the modifier set
                        item['menuitemmodifiers_list_custom_menuitemmodifiers'][i] = json.loads(r.text)['id']

                    except requests.exceptions.HTTPError as e:
                        # Whoops it wasn't a 200
                        print("Error: " + str(e))
                        print(modifier)
                        print('modifier group post failed')
                        sys.exit(1)

            #bubble does not accept single item lists. Need to append an empty item to make it length of 2
            if len(item['menuitemmodifiers_list_custom_menuitemmodifiers']) == 1:
                item['menuitemmodifiers_list_custom_menuitemmodifiers'].append("")
            #finally create the menuItem
            try:
                print('!!! NEW TOP-LEVEL MENUITEM !!!')
                r = requests.post(DATA_API_ENDPOINT % 'menuitem', data=item)

                menuItem_ID_list.append(json.loads(r.text)['id'])
            except requests.exceptions.RequestException as e:  # This is the correct syntax
                print(e)
                raise SystemExit(e)

            except requests.exceptions.HTTPError as e:
                # Whoops it wasn't a 200
                print("Error: " + str(e))



    '''
    #modify restaurant entry with new menucategories
    r = requests.patch(DATA_API_ENDPOINT % ('restaurants/' + RESTAURANT_ID), \
        data={'menucategories_list_custom_subcategories': menu_categories_ids})
    print(r.text)
    '''

    with open('menuItem_ID_list.txt', 'w') as filehandle:
        for menuItem_ID in menuItem_ID_list:
            filehandle.write('%s\n' % menuItem_ID)

    #modify menu entry with new menuitems
    r = requests.patch(DATA_API_ENDPOINT % ('menu/' + menu_id), \
        data={'menuitem_list_custom_menuitem': menuItem_ID_list})
    print(r.text)




if __name__ == '__main__':
    #start = time.time()
    #menu_id = create_menu(RESTAURANT_ID)
    #scraped_menu = scrape_menu(GH_URL, '3')
    upload_to_bubble('1604748221356x430943347884501500', 'data/data_cd_dinner2.json')
    #end = time.time()
    #print(end - start)


