import datetime
import json
import requests
import argparse #parsing arguments so that we get flags like --help, etc. 
import logging #For beautifying the error and warning handling
from bs4 import BeautifulSoup #for scraping website from government website 
from tabulate import tabulate
from prettytable import PrettyTable #for tabular display of data from the government website 
from slack_client import slacker 

FORMAT = '[%(asctime)-15s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG, filename='bot.log', filemode='a') #Determining log entry format

URL = 'https://www.mohfw.gov.in'
SHORT_HEADERS = ['SNo', 'State/UT','Indian','Foreigner','Cured','Dead']
FILE = '/home/arghyadeep99/Desktop/Go-Karuna-Go/corona_india_data.json'

contents = lambda row: [x.text.replace('\n', '') for x in row]

def save(x):
    with open(FILE, 'w') as f:
        json.dump(x, f)

def load():
    res = {}
    with open(FILE, 'r') as f:
        res = json.load(f)
    return res
#print(load())
if __name__ == '__main__':
    #print(load())
    parser  = argparse.ArgumentParser()
    parser.add_argument('--states', default=',')
    args = parser.parse_args()
    req_states = args.states.split(',')

    current_time = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    info = []

    try:
        response = requests.get(URL).content
        bs = BeautifulSoup(response, 'html.parser')
        table = bs.findAll(lambda tag: tag.name=='table' and tag.has_attr('class') and tag['class']=="table table-striped table-dark") 
        #rows = table.findAll(lambda tag: tag.name=='tr')
        #header = (bs.findChildren('table'))
        #print(table)
        stats = []
        all_rows = bs.find_all('tr')
        for row in all_rows:
            stat = contents(row.find_all('td'))
            if stat:
                if len(stat) < 5:
                    try:
                        stats.remove(stat)
                    except:
                        continue
                if len(stat) == 5:
                    # last row
                    stat[0] = 'Total confirmed cases'
                    stat = ['', *stat]
                    stats.append(stat)
                elif len(stat) == 6 and any([s.lower() in stat[1].lower() for s in req_states]):
                    stats.append(stat)

        prev_data = load()
        cur_data = {x[1]: {current_time: x[2:]} for x in stats}

        flag = False #flag to indicate if data has been changed

        for state in cur_data:
            if state not in prev_data and state != 'Total confirmed cases':
                info.append(f'New State {state} is hit by Corona Virus: {cur_data[state][current_time]}')
                prev_data[state] = {}
                flag = True
            else:
                past = prev_data[state]['latest']
                cur = cur_data[state][current_time]
                if past != cur:
                    flag = True
                    info.append(f'There is a change for {state}: {past}->{cur}')
            
        events_info = ''
        for event in info:
            logging.warning(event)
            events_info += '\n - ' + event.replace("'", "")
            
        if flag:
            # override the latest one now
            for state in cur_data:
                prev_data[state]['latest'] = cur_data[state][current_time]
                prev_data[state][current_time] = cur_data[state][current_time]
            save(prev_data)

            table = tabulate(stats, headers=SHORT_HEADERS, tablefmt='psql')
            slack_text = f'Current Corona Virus Pandemic Status in India: \n(Format is [Indian, Foreigner, Cured, Dead]):\n{events_info}\n```{table}```'
            slacker()(slack_text)
        print(cur_data)
        print("Success!")
    except Exception as e:
        logging.exception('Damn, The Corona Tracker script has failed!')
        slacker()(f'Exception occured: [{e}]')
