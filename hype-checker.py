import sys, datetime, time, requests, random, operator
from lxml import html

reload(sys)
sys.setdefaultencoding('utf-8')

check_for_drop_first = False  # if true: will check for drop first

delayed_start_option = False  # if true: will start at time given in delayed_start_time
delayed_start_time = '01/11/1111 10:58:30AM'  # date entered is irrelevant

simulate_buying = False  # simulates real time buying
simulation_seconds_range = 3  # max real time buying wait in seconds if simulate_buying is true

time_of_drop = datetime.datetime.strptime('03:34:00AM', '%I:%M:%S%p').time()
refresh_rate = 2  # in seconds
check_duration = 0.3  # in minutes

primary_site_to_check = 'http://www.supremenewyork.com/shop/new'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}

base_url = 'http://www.supremenewyork.com'


def main():

    print("PROGRAM DETAILS:\nREFRESH RATE: {} seconds\nDURATION: {} minutes\n".format(refresh_rate, check_duration))

    if delayed_start_option:
        delayed_start()

    if check_for_drop_first:
        check_for_drop()

    actual_time_of_drop = datetime.datetime.now()  # record time immediately after items drop

    r = requests.get(url=primary_site_to_check, headers=headers)

    print(r.status_code)

    print(r.content)
    time.sleep(1000)

    all_article_links = initial_items_make()
    all_article_links = watch_for_sell_out_times(all_article_links, refresh_rate_seconds=refresh_rate,
                                                 check_duration_minutes=check_duration)  # loops for check_duration

    # finished looping. now just set all in_stock_time to current time for all in_stock items.

    print("FINISHED LOOPING. SETTING ALL IN STOCK ITEMS TO CURRENT TIME AND GENERATING REPORT...")

    in_stock_time_raw = datetime.datetime.now()
    in_stock_time = in_stock_time_raw.strftime("%I:%M:%S%p")

    for item in all_article_links:
        if all_article_links[item]['sold_out_tag'] == 'in stock':
            all_article_links[item]['in_stock_time'] = in_stock_time
            all_article_links[item]['in_stock_time_raw'] = in_stock_time_raw

    all_article_links = get_additional_information(all_article_links)  # scrapes each link for prices, names, etc.
    generate_report(all_article_links, in_stock_time, actual_time_of_drop)


    print("REPORT COMPLETE. EMAILING TO SELF.")
    # email_to_self()

    return


def delayed_start():
    drop_time = datetime.datetime.strptime(delayed_start_time, '%m/%d/%Y %I:%M:%S%p')
    current_time = datetime.datetime.strptime(datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S%p'),
                                              '%m/%d/%Y %I:%M:%S%p')
    difference = (drop_time - current_time).seconds

    print("Time until program start: {} seconds.".format(difference))

    while (difference > 0 and difference < 80000):
        time.sleep(difference * 0.5)
        current_time = datetime.datetime.strptime(datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S%p'),
                                                  '%m/%d/%Y %I:%M:%S%p')
        difference = (drop_time - current_time).seconds

        print("Time until program start: {} seconds.".format(difference))


    print("Time reached. Starting program!")
    return


def check_for_drop():
    page = requests.get(primary_site_to_check)
    tree = html.fromstring(page.content)
    old_sold_out_items_count = new_sold_out_items_count = len(tree.xpath('//div[@class="sold_out_tag"]'))

    while new_sold_out_items_count >= old_sold_out_items_count:
        current_time = datetime.datetime.now().time()
        time_difference = (datetime.datetime.combine(datetime.date.today(), time_of_drop) - datetime.datetime.combine(
            datetime.date.today(), current_time)).seconds

        if time_difference < 5 or time_difference > 3600:
            time.sleep(0.5)

            print("Waiting {} seconds for drop.".format(0.5))
        else:
            time.sleep(time_difference * 0.25)

            print("Waiting {} seconds for drop.".format(time_difference * 0.25))

        page = requests.get(primary_site_to_check)
        tree = html.fromstring(page.content)
        new_sold_out_items_count = len(tree.xpath('//div[@class="sold_out_tag"]'))


    print("New items dropped!")
    return


def initial_items_make():
    site = requests.get(primary_site_to_check)
    site_tree = html.fromstring(site.content)
    all_articles = site_tree.xpath('//div[@class="inner-article"]/a')
    all_article_links = {}

    ct = 0
    for article in all_articles:
        if simulate_buying:
            time.sleep(random.randrange(0, simulation_seconds_range))

        link = base_url + article.attrib['href']

        print(link)

        sold_out_tag_element_list = article.xpath('.//div[@class="sold_out_tag"]')
        if len(sold_out_tag_element_list) > 0:  # means this item has the sold_out_tag class, i.e. is sold out
            sold_out_tag = 'sold out'
            sold_out_time_raw = datetime.datetime.now()
            sold_out_time = sold_out_time_raw.strftime("%I:%M:%S%p")
        else:  # else not sold out
            sold_out_tag = 'in stock'
            sold_out_time_raw = None
            sold_out_time = None


        print('\t', sold_out_tag)

        item_name = None
        item_color = None
        item_desc = None
        item_price = None
        in_stock_time_raw = None
        in_stock_time = None
        item_picture_links = []

        all_article_links[link] = {
            'sold_out_tag': sold_out_tag,
            'item_name': item_name,
            'item_color': item_color,
            'item_desc': item_desc,
            'item_price': item_price,
            'sold_out_time_raw': sold_out_time_raw,
            'sold_out_time': sold_out_time,
            'index': ct,
            'grid_position': ct + 1,
            'in_stock_time_raw': in_stock_time_raw,
            'in_stock_time': in_stock_time,
            'item_picture_links': item_picture_links
        }
        ct += 1

    return all_article_links


def watch_for_sell_out_times(old_dict, refresh_rate_seconds, check_duration_minutes):
    new_dict = old_dict
    finish_time = datetime.datetime.now() + datetime.timedelta(minutes=check_duration_minutes)

    while datetime.datetime.now() < finish_time:

        print("time now: {} \t time until finish: {} seconds".format(datetime.datetime.now(),
                                                               (finish_time - datetime.datetime.now()).seconds))
        site = requests.get(primary_site_to_check)
        site_tree = html.fromstring(site.content)
        all_articles = site_tree.xpath('//div[@class="inner-article"]/a')
        for article in all_articles:
            link = base_url + article.attrib['href']

            if new_dict[link][
                'sold_out_tag'] == 'in stock':  # if item was in stock since last check, re-check for stock
                sold_out_tag_element_list = article.xpath('.//div[@class="sold_out_tag"]')

                if len(sold_out_tag_element_list) > 0:  # means this item has the sold_out_tag class, i.e. is sold out
                    sold_out_tag = 'sold out'
                    sold_out_time_raw = datetime.datetime.now()
                    sold_out_time = sold_out_time_raw.strftime("%I:%M:%S%p")
                    new_dict[link]['sold_out_tag'] = sold_out_tag
                    new_dict[link]['sold_out_time_raw'] = sold_out_time_raw
                    new_dict[link]['sold_out_time'] = sold_out_time

                else:
                    sold_out_tag = 'in stock'

            else:  # if not in stock, we already checked. pass that shit.
                pass
        time.sleep(refresh_rate_seconds)

    return new_dict


def get_additional_information(old_dict):
    new_dict = old_dict

    for item in new_dict:

        site = requests.get(item)
        site_tree = html.fromstring(site.content)

        item_name = site_tree.xpath('//h1[contains(@itemprop, "name")]')[0].text
        item_name = ' '.join(item_name.split())

        item_color = site_tree.xpath('//p[contains(@class, "style") and contains(@itemprop, "model")]')[0].text
        item_color = ' '.join(item_color.split())

        item_desc = site_tree.xpath('//p[contains(@class, "description") and contains(@itemprop, "description")]')[0].text
        item_desc = ' '.join(item_desc.split())

        item_price = site_tree.xpath('//p[contains(@class, "price")]/span[contains(@itemprop, "price")]')[0].text

        item_picture_links = []
        item_pictures_elements = site_tree.xpath('//a[contains(@data-style-name, "' + item_color + '")]/img[1]')
        for pic in item_pictures_elements:
            pic_link = str(pic.attrib['src']).replace('/sw/', '/zo/')
            item_picture_links.append(pic_link)

        new_dict[item]['item_name'] = item_name
        new_dict[item]['item_color'] = item_color
        new_dict[item]['item_desc'] = item_desc
        new_dict[item]['item_price'] = item_price
        new_dict[item]['item_picture_links'] = item_picture_links

    return new_dict


def generate_report(dict, bot_finish_time, actual_time_of_drop):
    datestr = time.strftime("%Y%m%d")
    f = open('Hype Stats - ' + datestr + '.txt', 'w')
    f.write("Hype Stats: {}\n========================\n\n".format(time.strftime("%B %d, %Y")))
    f.write("Product sell-out times are tracked up to about {} minutes after drop. Restocks are not tracked. "
            "These stats might give everyone an idea of how hyped an item was and how it might do in the market if you plan on buying/selling. "
            "The refresh rate (time between checking for stock) is {} seconds. All times are in EST.\n\n&nbsp;\n\n".format(
        check_duration, refresh_rate))

    main_products = {}
    max_name_length = 0

    for item in dict:
        main_link = item.rsplit('/', 1)[0]
        main_name = dict[item]['item_name']
        main_price = dict[item]['item_price']
        main_description = dict[item]['item_desc']
        main_products[main_link] = {
            'main_name': main_name,
            'main_price': main_price,
            'main_description': main_description
        }
        max_name_length = max(len(dict[item]['item_color']), max_name_length)

    sell_out_times_dict = {}

    for product in main_products:
        f.write('\n\n**{}** | {} | [Link]({})\n\n'.format(main_products[product]['main_name'],
                                                          main_products[product]['main_price'], product))
        f.write('^(*{}*)\n\n'.format(main_products[product]['main_description']))
        for item in dict:
            if product in item:
                if dict[item]['sold_out_tag'] == 'sold out':
                    time_difference = (dict[item]['sold_out_time_raw'] - actual_time_of_drop).seconds
                    sell_out_times_dict[item] = time_difference  # time difference in seconds
                    f.write("* {} | **{}** at {} (~{} after drop)".format(dict[item]['item_color'],
                                                                          dict[item]['sold_out_tag'],
                                                                          dict[item]['sold_out_time'],
                                                                          seconds_to_seconds_minutes(time_difference)))
                else:
                    f.write("* {} | **{}** as of {}".format(dict[item]['item_color'], dict[item]['sold_out_tag'],
                                                            dict[item]['in_stock_time']))

                x = 1
                if len(dict[item]['item_picture_links']) > 0:
                    for pic_link in dict[item]['item_picture_links']:
                        f.write(" [[image {}]({})]".format(x, pic_link))
                        x += 1
                f.write('\n')
        f.write('\n\n&nbsp;\n\n')
    sorted_sell_out_times = sorted(sell_out_times_dict.items(), key=operator.itemgetter(1))

    f.write("\n\nSell Out Times In Order:\n==================\n")

    count = 1
    for itm in sorted_sell_out_times:
        f.write(
            "{}. **{} [{}]** *(~{} after drop)*\n".format(count, dict[itm[0]]['item_name'], dict[itm[0]]['item_color'],
                                                          seconds_to_seconds_minutes(itm[1])))
        count += 1

    total_items_count = len(dict)
    total_items_sold_count = len(sorted_sell_out_times)

    one_fourth_of_all_items_count = int(round(0.25 * total_items_count))
    one_half_of_all_items_count = int(round(0.5 * total_items_count))
    three_fourths_of_all_items_count = int(round(0.75 * total_items_count))

    f.write("\n\nMiscellaneous:\n==================\n")

    if total_items_sold_count >= one_fourth_of_all_items_count:
        f.write("* 25% of all items ({} items) sold out within {}.\n".format(one_fourth_of_all_items_count,
                                                                             seconds_to_seconds_minutes(
                                                                                 sorted_sell_out_times[
                                                                                     one_fourth_of_all_items_count - 1][
                                                                                     1])))
    if total_items_sold_count >= one_half_of_all_items_count:
        f.write("* 50% of all items ({} items) sold out within {}.\n".format(one_half_of_all_items_count,
                                                                             seconds_to_seconds_minutes(
                                                                                 sorted_sell_out_times[
                                                                                     one_half_of_all_items_count - 1][
                                                                                     1])))
    if total_items_sold_count >= three_fourths_of_all_items_count:
        f.write("* 75% of all items ({} items) sold out within {}.\n".format(three_fourths_of_all_items_count,
                                                                             seconds_to_seconds_minutes(
                                                                                 sorted_sell_out_times[
                                                                                     three_fourths_of_all_items_count - 1][
                                                                                     1])))
    if total_items_sold_count == total_items_count:
        f.write("* All {} items sold out within {}.\n".format(total_items_count,
                                                              seconds_to_seconds_minutes(
                                                                  sorted_sell_out_times[total_items_count - 1][1])))

    f.write(
        '\n\nEverything else is in stock as of {} (when tracking stopped).\n\nSuggestions/questions are welcome. **Stay swift, boys.**\n'.format(
            bot_finish_time))
    f.write('\n\n&nbsp;\n\n`- dahchen`')
    f.close()
    return


def seconds_to_seconds_minutes(s):
    s = s
    seconds = s % 60
    minutes = (s - seconds) / 60
    statement = ''

    if minutes == 0:
        if seconds == 1:
            statement += '1 second'
        else:
            statement += '{} seconds'.format(seconds)
        return statement

    if minutes == 1:
        statement += '1 minute'
    else:
        statement += '{} minutes'.format(minutes)

    if seconds == 0:
        statement += ''
    elif seconds == 1:
        statement += ' 1 second'
    else:
        statement += ' {} seconds'.format(seconds)

    return statement


if __name__ == '__main__':
    main()
