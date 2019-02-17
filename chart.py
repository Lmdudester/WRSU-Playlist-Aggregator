from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import file, client, tools
from httplib2 import Http
import datetime
import time
import sys

driveScopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
sheetsScopes = 'https://www.googleapis.com/auth/spreadsheets'
clientIdPath = 'creds/client_id.json'

weekdays = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR', 5: 'SA', 6: 'SU'}

''' 
___date_dict_generator___
Takes a datetime date object and generates MM/DD/YY strings for a week long period beginning on that day.
Returns these strings in a dictionary where the key is the first two letters of the associated weekday.
'''
def date_dict_generator(date):
    date_dict = {}
    first_date = "%02d/%02d/%02d" % (date.month, date.day, date.year % 100)

    for i in range(0, 7):
        date_dict[weekdays[date.weekday()]] = "%02d/%02d/%02d" % (date.month, date.day, date.year % 100)

        date = date + datetime.timedelta(days=1)

    return date_dict, first_date


'''
___insert_values_into_chart___
Takes the current chart dictionary and a set of values for a given playlist sheet and adds those values to the chart.
Returns the chart after the values have been accounted for.
'''
def insert_values_into_chart(temp_chart, values):
    for i in values:
        try:
            val = int(i[0])

            if temp_chart.get(val, "") != "":
                temp_chart[val] += 1
            else:
                temp_chart[val] = 1

        except ValueError:
            continue

    return temp_chart


'''
___show_execute___
Performs all operations needed to gather data for a given show.
Returns the updated chart.
'''
def show_execute(show_id, s, temp_chart, date):
    try:
        result = s.values().get(spreadsheetId=show_id, range=date + "!A4:B200").execute()

        try:
            wrsu_nums = result.get('values', [])
            temp_chart = insert_values_into_chart(temp_chart, wrsu_nums)

        except:
            return temp_chart, -2, date + ": Playlist was misread. The \'values\' field missing from response"

    except HttpError as e:
        # No such sheet
        if e.resp.status == 400:
            return temp_chart, -1, "No playlist with date \"" + date + "\" (as a sheet title) was found."

        # API call error
        else:
            return temp_chart, e.resp.status, e.resp.reason

    return temp_chart, 0, ""


'''
___get_drive_service___
Gets the drive service object given the client_id path.
'''
def get_drive_service(dpath):
    # Load old permissions if possible (Drive)
    driveStore = file.Storage(dpath)
    driveCreds = driveStore.get()

    # Display errors (Drive)
    if not driveCreds:
        print("Drive token could not be loaded. Please run updatecreds.py and try again.")
        exit(1)

    if driveCreds.invalid:
        print("Drive token has expired. Please run updatecreds.py and try again.")
        exit(1)

    # Build service object used to create drive api calls (Drive)
    return build('drive', 'v3', http=driveCreds.authorize(Http()))


'''
___get_sheet_service___
Gets the sheets service object given the client_id path. 
'''
def get_sheet_service(spath):
    # Load old permissions if possible (Sheets)
    sheetsStore = file.Storage(spath)
    sheetsCreds = sheetsStore.get()

    if not sheetsCreds:
        print("Sheets token could not be loaded. Please run updatecreds.py and try again.")
        exit(1)

    if sheetsCreds.invalid:
        print("Sheets token has expired. Please run updatecreds.py and try again.")
        exit(1)

    # Build service object used to create sheets api calls (Sheets)
    return build('sheets', 'v4', http=sheetsCreds.authorize(Http()))

'''
___chart_to_array___
Takes the chart and generates an ordered array to be written to the chart output.
Returns the ordered array.
'''
def chart_to_array(chart_dict):
    resp = []
    for k in chart_dict:
        resp.append([chart_dict[k], k])

    return sorted(resp, reverse=True)


if __name__ == '__main__':
    # If -h is used
    if "-h" in sys.argv:
        print("Please enter a date in \"mm dd yyyy\" format.")
        exit(0)

    # Read command line date
    input_date = datetime.datetime.now()

    try:
        input_date = datetime.datetime(int(sys.argv[3]), int(sys.argv[1]), int(sys.argv[2]))

        # Validation check
        if input_date > datetime.datetime.now() or input_date < datetime.datetime(2019, 1, 1):
            print("Please enter a date in \"mm dd yyyy\" format: Date was outside of the acceptable range. (01/01/19 < INPUT < Tomorrow)")
            exit(-1)

    except Exception as e:
        print("Please enter a date in \"mm dd yyyy\" format: " + str(e))
        exit(-1)

    # Build service object used to create drive api calls (Drive)
    driveService = get_drive_service('creds/token_drive.json')

    # Make a list call (Drive)
    results = driveService.files().list(
        fields="nextPageToken, files(id, name)", q="name contains \"WRSU_SP\"").execute()
    items = results.get('files', [])

    # Delays auth long enough to process
    time.sleep(2)

    # Build service object used to create sheets api calls (Sheets)
    sheetService = get_sheet_service('creds/token_sheets.json')
    sheet = sheetService.spreadsheets()

    # Get Date Dictionary
    dates, original_date = date_dict_generator(input_date)

    # Create Chart
    chart = {}

    if len(items) == 0:
        print("**NO PLAYLIST FILES FOUND**")
        exit(-1)

    # Iterate over all Playlist sheets to collect data
    for item in items:
        sheet_name = item.get('name', "")
        if len(sheet_name) >= 2:
            d = dates.get(sheet_name[-2:], "")
            if d != "":
                chart, errVal, err = show_execute(item['id'], sheet, chart, d)
            else:
                errVal = -3
                err = "weekday not properly included in sheet title"
        else:
            errVal = -4
            err = "sheet title not found - This doesn't make sense..."

        if errVal != 0:
            print(item['name'] + ": \"" + err + "\"")

    chart_to_array(chart)

    # Find the charts sheet
    results = driveService.files().list(
        fields="nextPageToken, files(id, name)", q="name contains \"WRSU_CHART\"").execute()
    items = results.get('files', [])

    if len(items) == 0:
        print("**NO OUTPUT FILE FOUND**")
        exit(-1)

    # Place values into the charts sheet
    else:
        # Check if the sheet exists, if not, create it
        try:
            result = sheet.values().get(spreadsheetId=items[0]['id'], range=original_date + "!A1:B2").execute()

        except HttpError as e:
            batch = {"requests": [{"addSheet": {"properties": {"title": original_date, "gridProperties": {"rowCount": 100, "columnCount": 20}}}}]}
            request = sheet.batchUpdate(spreadsheetId=items[0]['id'], body=batch).execute()

        values = chart_to_array(chart)
        body = {'values': values}

        result = sheet.values().update(spreadsheetId=items[0]['id'], range=original_date + "!A2:B200", valueInputOption="USER_ENTERED", body=body).execute()
        print('{0} cells updated on the Weekly Charts.'.format(result.get('updatedCells')))
