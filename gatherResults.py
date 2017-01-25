import requests
import re
import mysqlManager
import datetime
from pytz import timezone

CONTEST_MAIN_URL = 'https://www.draftkings.com/lobby/getcontests?sport=NHL'

def get_pst_from_timestamp(timestamp_str):
    timestamp = float(re.findall('[^\d]*(\d+)[^\d]*', timestamp_str)[0])
    return datetime.datetime.fromtimestamp(
        timestamp / 1000, timezone('America/Denver')
    )


def getTodaysContests():
    #if(mysqlHelper.haveGatheredTodaysContests() != True):
    #session = loginManager.getSession()
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
                mysqlManager.insertContest(contest_id, name, "NHL", "NOTSTARTED", date, total_prizes, max_entries, entries, entry_fee, is_guaranteed)

        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            return False
            print 'Got a unicode error for the contest %s', contest['id']
    
 
if __name__ == "__main__":
    getTodaysContests()
