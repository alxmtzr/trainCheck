import http.client
from datetime import datetime as dt
import datetime
import xml.etree.ElementTree as ET
import xml
import sys


def convert_date(date):
    return f"{date[4:6]}.{date[2:4]}.20{date[0:2]}"


def convert_time(time):
    return f"{time[0:2]}:{time[2:4]} Uhr"


def get_current_datetime():
    now = str(datetime.datetime.now())
    now = now.replace("-", "").replace(":", "").replace(" ", "")
    return now[2:12]


class TrainCheck:
    # db api
    conn = http.client.HTTPSConnection("apis.deutschebahn.com")
    headers = None

    def get_journey_data(self, destination, evaNo, date, hour):
        # send request
        global trip_id, trip_category, dictionary
        self.conn.request("GET", f"/db-api-marketplace/apis/timetables/v1/plan/{evaNo}/{date}/{hour}",
                          headers=self.headers)
        # get response
        res = self.conn.getresponse()
        data = res.read()

        # no output writing necessary -> formstring
        # get root name
        root = xml.etree.ElementTree.fromstring(data)

        timetable_dictionary = {}
        # iterate through all departures
        for timetable in root.iter('dp'):
            # if dp attribute ppth (stops) includes destination
            if str(timetable.get("ppth")).__contains__(destination):
                # get "pt"attribute which delivers date and time in form of YYMMddHHmm
                date_and_time = timetable.get("pt")
                # if journey time is >= now
                if date_and_time >= get_current_datetime():
                    # stopovers
                    stops = str(timetable.get("ppth"))
                    stops = stops.replace("|", " | ").replace(destination, f"DESTINATION: {destination}")
                    # how many min left to departure -> converting date_and_time and current_datetime to Date-Format
                    mins_left_until_depart = \
                        dt.strptime(date_and_time, '%y%m%d%H%M') - dt.strptime(get_current_datetime(), '%y%m%d%H%M')
                    # pick date
                    departure_date = date_and_time[0:6]
                    # pick time
                    departure_time = date_and_time[6:]
                    # convert into human-readable String
                    departure_date = convert_date(departure_date)
                    departure_time = convert_time(departure_time)

                    # planned platform
                    planned_platform = timetable.get("pp")

                    # retrieving other xml.tag
                    for train_info in root.iter("tl"):
                        train_number = train_info.get("n")

                    # dictionary with all necessary information
                    dictionary = {
                        "departure in": str(mins_left_until_depart) + "min",
                        "departure date": departure_date,
                        "departure time": departure_time,
                        "platform": planned_platform,
                        "stops": stops,
                        "train number": train_number
                    }
                    # cancellation time
                    cancellation_time = timetable.get("clt")
                    if cancellation_time:
                        dictionary["cancellation time"] = cancellation_time

                    # ---- train details ----
                    # retrieving other xml.tag
                    for train_info in root.iter("tl"):
                        trip_category = train_info.get("c")
                    if trip_category:
                        dictionary["trip category"] = trip_category
                    # line indicator e.g. IRE ->3<-
                    line_indicator = timetable.get("l")
                    if line_indicator:
                        dictionary["line indicator"] = line_indicator
                    # changed distant endpoint
                    changed_endpoint = timetable.get("cde")
                    if changed_endpoint:
                        dictionary["changed distand endpoint"] = changed_endpoint
                    # changed path
                    changed_path = timetable.get("cpth")
                    if changed_path:
                        dictionary["changed path"] = changed_path
                    # event status -> 0 = p - PLANNED, 1 = a - ADDED, 2 = c - CANCELED
                    event_status1 = timetable.get("cs")
                    event_status2 = timetable.get("ps")
                    if event_status1:
                        dictionary["event status (2=canceled)"] = event_status1
                    if event_status2:
                        dictionary["event status (2=canceled)"] = event_status2
                    # changed time
                    changed_time = timetable.get("ct")
                    if changed_time:
                        dictionary["changed time"] = changed_time
                    # message
                    message = timetable.get("m")
                    if message:
                        dictionary["message"] = message
                    # add dictionary to main dictionary with all available journeys
                    # date_and_time key because of sorting the different options in the output
                    timetable_dictionary[date_and_time] = dictionary
        # sorted dictionary by date_and_time ascending
        return dict(sorted(timetable_dictionary.items()))

    def connect_to_api(self):
        # ---- import ID_key and store to variable ----
        file = open('api_keys/client_id_key.txt')
        id_key = str(file.read())
        # remove blanks
        id_key = id_key.strip()

        # ---- import ApiKey and store to variable ----
        file = open('api_keys/client_secret_key_APIkey.txt')
        api_key = str(file.read())
        # remove blanks
        api_key = api_key.strip()

        # ---- header details ----
        self.headers = {
            'DB-Client-Id': f"{id_key}",
            'DB-Api-Key': f"{api_key}",
            'accept': "application/xml"
        }

    # Returns information about stations matching the given pattern
    def get_station_evaNo(self, station_name):
        # send request
        self.conn.request("GET", f"/db-api-marketplace/apis/timetables/v1/station/{station_name}", headers=self.headers)
        # get response
        res = self.conn.getresponse()
        # read content
        data = res.read()

        # get root name
        root = xml.etree.ElementTree.fromstring(data)
        # get evaNo
        for station in root.iter('station'):
            evaNo = station.get('eva')
            return str(evaNo)

    def main(self):
        self.connect_to_api()

        # ---- Journey information ----
        departure = sys.argv[1]
        destination = sys.argv[2]
        # today's date
        date = datetime.date.today()
        # remove dash and 20 from 2022
        date = str(date).replace('-', '')[2:]
        # time hour
        hour_now = str(datetime.datetime.now().hour)
        hour_now = 13
        # evaNo
        departure_evaNo = self.get_station_evaNo(departure)

        # ---- get train data ----
        count = 1

        timetable = self.get_journey_data(destination, departure_evaNo, date, hour_now)
        for key in timetable:
            dictionary = timetable[key]
            print(f"---- Option No. {count} ----")
            count += 1
            for key2 in dictionary:
                print(key2, ": ", dictionary[key2])
            print()

        # if amount of travel options is <2 show travel options for the following hour
        if count <= 2:
            timetable = self.get_journey_data(destination, departure_evaNo, date, str(datetime.datetime.now().hour + 1))
            for key in timetable:
                dictionary = timetable[key]
                print(f"---- Option No. {count} ----")
                count += 1
                for key2 in dictionary:
                    print(key2, ": ", dictionary[key2])
                print()
        # if count is still 1, no options are available
        if count == 1:
            print("No travel options available.")



TrainCheck().main()
