import requests
import time
import re
import mysqlManager
import datetime
from pytz import timezone
import loginManager
from bs4 import BeautifulSoup
import decimal
import zipfile
import os.path
import csv


CONTEST_MAIN_URL = 'https://www.draftkings.com/lobby/getcontests?sport=NHL'
INDIVIDUAL_CONTEST_URL = 'https://www.draftkings.com/contest/gamecenter/%s'

def get_pst_from_timestamp(timestamp_str):
    timestamp = float(re.findall('[^\d]*(\d+)[^\d]*', timestamp_str)[0])
    return datetime.datetime.fromtimestamp(
        timestamp / 1000, timezone('America/Denver')
    )


# the payout table is a combination of ranges to prize. For example, if a contest paid $10 to places 1-5, it would have 'start' : 1, 'end' : 5, 'prize' : 10
def get_prize_for_place(place, payoutTable):
    for payoutRange in payoutTable['payouts']:
       # check if the place is between the range of places paid out for this prize value 
        if( int(payoutRange['start']) <= int(place) and int(place) <= int(payoutRange['end'])):
            return payoutRange['prize']
   # we couldn't find a payout for this place
    return 0


def find_draft_group_id(contest_id):
    session = loginManager.getSession()
    
    url= INDIVIDUAL_CONTEST_URL % contest_id
    response = session.get(url)
    try:
        result = response.text.find('contestDraftGroupId:')

        trimmedResponse = response.text[result+20:result+35]
        return int(trimmedResponse)
    except IndexError:
        print 'Couldn\'t find the draft group for the contest %s' % contest_id
        print 'the url we used was %s' %url

# take a string that may have dollar signs and commas in it, and format it to a decimal
def dollars_to_decimal(dollarstr):
    dollarstr = dollarstr.replace('$', '').replace(',', '')
    return decimal.Decimal()


def get_todays_contests():
    if(mysqlManager.have_gathered_todays_contests() != True):
        r = requests.get(CONTEST_MAIN_URL).json()
        for contest in r['Contests']:
            try:
                date_time = get_pst_from_timestamp(contest['sd'])
                date = date_time.date()
                name = contest['n'].encode('ascii', 'ignore')
                contest_id = contest['id']
                if('IsGuaranteed' in contest['attr']):
                    is_guaranteed = contest['attr']['IsGuaranteed']
                else:
                    is_guaranteed = False
                total_prizes = contest['po']
                max_entries = contest['mec']
                entries = contest['m']
                entry_fee = contest['a']

                if(total_prizes != 0): # no sense recording non-prize contests
                    mysqlManager.insert_contest(contest_id, name, "NHL", "NOTSTARTED", date, total_prizes, max_entries, entries, entry_fee, is_guaranteed)
    
            except (UnicodeDecodeError, UnicodeEncodeError) as e:
                return False
                print 'Got a unicode error for the contest %s', contest['id']


# get the prize data for the given contest id.  
def get_contest_prize_data(contest_id):
    def place_to_number(s):
        return int(re.findall(r'\d+', s)[0])

    URL = 'https://www.draftkings.com/contest/detailspop'
    session = loginManager.getSession()
    PARAMS = {
        'contestId': contest_id,
        'showDraftButton': False,
        'defaultToDetails': True,
        'layoutType': 'legacy'
    }
    response = session.get(URL, params=PARAMS)

    #soup = BeautifulSoup(response.text, 'html5lib')
    soup = BeautifulSoup(response.text, 'lxml')

    try:
        payouts = soup.find_all(id='payouts-table')[0].find_all('tr')
        entry_fee = soup.find_all('h2')[0].text.split('|')[2].strip()
        
        if(entry_fee != 'Free'):
            entry_fee_formatted = dollars_to_decimal(entry_fee)
        else:
            entry_fee_formatted = 0
        results = { 
                    'entry_fee' : entry_fee_formatted,
                    'payouts' : []
        }
        for payout in payouts:

            places, payout = [x.string for x in payout.find_all('td')]
            places = [place_to_number(x.strip()) for x in places.split('-')]
            top, bot = ((places[0], places[0]) if len(places) == 1
                        else places)
            #if "Ticket" in payout or "Experience" in payout: # I'm not going to include tickets here.
            #    print 'FOUND A TICKET/EXPERIENCE IN CONTEST: ', contest_id, ' so I\'m removing it.'
            #    mysqlHelper.cancelContest(contest_id)
            #    return False
            #    payout = dollars_to_decimal(payout)
            results['payouts'].append({'start' : top, 'end' : bot, 'prize' : payout})

        return results
    except IndexError:
        # See comment in get_contest_data()
        print 'Couldn\'t find prize data for contest %s' % contest_id


def get_contest_results(contest_id, date, payoutTable):
    url = 'https://www.draftkings.com/contest/gamecenter/%s' % contest_id
    CSVPATH = 'contestResults/'
    OUTFILE = 'contest-standings-%s.csv' % contest_id
    file_name = CSVPATH + OUTFILE

    def download_results(response):
        try:
            with open(file_name, 'wb') as f:
                decoded_content = response.content.decode('utf-8')
                cr = csv.reader(decoded_content.splitlines(), delimiter=',')
                my_list = list(cr)
    
                for row in my_list:
                    f.write(str(row))
                    f.write('\n') 

        # Draftkings appears to put the results for large contests into zip files, so if this is one of those contest, we'll need to go about downloading it slightly differently
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            try:
                with open('out.zip', 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                with open('out.zip', 'rb') as f:
                        z = zipfile.ZipFile(f)
                        for name in z.namelist():
                            z.extract(name, CSVPATH)
    
            except zipfile.BadZipfile:
                print 'Couldn\'t download/extract CSV zip for %s' % contest_id

                    
    #Format the lineup into only player names, as it comes in as a position + name combo
    def format_lineup(lineupString):
        POSITIONS=["W", "D", "C", "G", "UTIL"]
        lineup = lineupString.split()
        for i, word in enumerate(lineup[:]):
            if word in POSITIONS:
                lineup[i] = '\t'
        names = ' '.join(lineup).split('\t')
        resultLineup = []
        for word in names:
            if word.strip():
                resultLineup.append(word.strip())
        return resultLineup

    def read_csv():
        print 'Trying to read the CSV results from the file'
        results=[]
        try:
            with open(file_name, 'r') as f:
                csvreader = csv.reader(f, delimiter=',', quotechar='"')
                for i, row in enumerate(csvreader):
                    row = [item.replace("'", '') for item in row]
                    row[0] = row[0].replace('[', '')

                    if(i != 0): #first row is just the column names
                        if(row[0]):
                            lineup = format_lineup(row[5])
                            individual_result = {
                                'place' : row[0],
                                'payout': get_prize_for_place(row[0], payoutTable),
                                'name' : row[2],
                                'points' : row[4],
                                'lineup' : lineup
                            }
                            results.append(individual_result)

            return results
        except IOError:
            print 'Couldn\'t find the CSV results file for ', contest_id

    session = loginManager.getSession()
    
    response = session.get(url)
    #soup = BeautifulSoup(response.text, 'html5lib')
    soup = BeautifulSoup(response.text, 'lxml')

    try:
        header = soup.find_all(class_='top')[0].find_all('h4')
        info_header = (soup.find_all(class_='top')[0]
                           .find_all(class_='info-header')[0]
                           .find_all('span'))
        completed = info_header[3].string

        if completed.strip().upper() == 'COMPLETED':
            export_url = url.replace('gamecenter', 'exportfullstandingscsv')
            if not os.path.isfile(file_name): # if the file already exists, we don't need to re-download it
                download_results(session.get(export_url))
            results = read_csv()

            name = header[0].string,
            positions_paid = int(info_header[4].string)
            money_line = results[positions_paid-1]['points']
            mysqlManager.update_contest_results(contest_id, completed, find_draft_group_id(contest_id), positions_paid, money_line, results)
        elif completed.strip().upper() == 'CANCELLED':
            mysqlManager.cancel_contest(contest_id)
        else:
            print 'Contest %s has status: %s' % (contest_id, completed)
    except IndexError:
        # This error occurs for old contests whose pages no longer are
        # being served.
        # Traceback:
        # header = soup.find_all(class_='top')[0].find_all('h4')
        # IndexError: list index out of range
        print 'index error: Couldn\'t find DK contest with id %s' % contest_id
        #get current dateTime
        currentDate = datetime.datetime.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d")
        convertedDate = datetime.datetime.strptime(date, "%Y-%m-%d")
        if (currentDate-convertedDate).days > 8:
            print "This contest is too old because it's from date %s" % date
            mysqlManager.date_too_old(date)
            tooOld.append(date)
       
 
if __name__ == "__main__":
    get_todays_contests()
    contests = mysqlManager.get_contests_that_need_results()

    # keep track of contests we've seen that are deemed too old (i.e. we've tried to gather the results from draftkings.com, but the results no longer exist)
    tooOld = []
    for contest in contests:
        contest_id = contest[0]
        date = contest[1]
        if(date in tooOld):
            print 'contest %s was on date %s, but weve already determined this is too old to gather results for it.' % (contest_id, date)
        else:
            payoutTable= get_contest_prize_data( contest_id )
            if payoutTable:
                get_contest_results(contest_id, date, payoutTable)

