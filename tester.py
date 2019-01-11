from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import file, client, tools
from httplib2 import Http
import datetime
import time

driveScopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
sheetsScopes = 'https://www.googleapis.com/auth/spreadsheets'

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
    # Load in API Key
    key_file = open("creds/api_key.txt", "r")
    api_key = key_file.readline()

    # Load old permissions if possible (Drive)
    driveStore = file.Storage('creds/token_drive.json')
    driveCreds = driveStore.get()

    # Get api client creds (Drive)
    if not driveCreds or driveCreds.invalid:
        flow = client.flow_from_clientsecrets('creds/client_id.json', driveScopes)
        creds = tools.run_flow(flow, driveStore)
        driveCreds = driveStore.get()

    # Build service object used to create drive api calls (Drive)
    driveService = build('drive', 'v3', http=driveCreds.authorize(Http()))

    # Make a list call (Drive)
    results = driveService.files().list(
        fields="nextPageToken, files(id, name)", q="name contains \"WRSU_SP\"").execute()
    items = results.get('files', [])

    # Delays auth long enough to process
    time.sleep(2)

    # Load old permissions if possible (Sheets)
    sheetsStore = file.Storage('creds/token_sheets.json')
    sheetsCreds = sheetsStore.get()

    # Get api client creds (Sheets)
    if not sheetsCreds or sheetsCreds.invalid:
        flow = client.flow_from_clientsecrets('creds/client_id.json', sheetsScopes)
        sheetsCreds = tools.run_flow(flow, sheetsStore)
        sheetsCreds = sheetsStore.get()

    # Build service object used to create sheets api calls (Sheets)
    sheetService = build('sheets', 'v4', http=sheetsCreds.authorize(Http()))
    sheet = sheetService.spreadsheets()

    # Get Date Dictionary
    dates, original_date = date_dict_generator(datetime.datetime(2019, 1, 1))

    # Create Chart
    chart = {}

    print('Errors:')
    if len(items) == 0:
        print("**NO FILES FOUND**")

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
            err = "sheet title not found - This doesnt make logical sense..."

        if errVal != 0:
            print(item['name'] + ": \"" + err + "\"")

    chart_to_array(chart)

    # Make a list call (Drive)
    results = driveService.files().list(
        fields="nextPageToken, files(id, name)", q="name contains \"WRSU_CHART\"").execute()
    items = results.get('files', [])

    if len(items) == 0:
        print("**NO OUTPUT FILE FOUND**")

    else:
        # Check if the sheet exists, if not, create it
        try:
            result = sheet.values().get(spreadsheetId=items[0]['id'], range=original_date + "!A1:B2").execute()

        except HttpError as e:
            # Create the sheet
            batch = {"requests": [{"addSheet": {"properties": {"title": original_date, "gridProperties": {"rowCount": 100, "columnCount": 20}}}}]}

            request = sheet.batchUpdate(spreadsheetId=items[0]['id'], body=batch).execute()

        values = chart_to_array(chart)
        body = {'values': values}

        result = sheet.values().update(spreadsheetId=items[0]['id'], range=original_date + "!A1:B200", valueInputOption="USER_ENTERED", body=body).execute()
        print('{0} cells updated on the Weekly Charts.'.format(result.get('updatedCells')))
