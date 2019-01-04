from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import file, client, tools
from httplib2 import Http
# import datetime

driveScopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
sheetsScopes = 'https://www.googleapis.com/auth/spreadsheets.readonly'


def insert_values(temp_chart, values):
    for i in values:
        if i[0] != "":
            if temp_chart.get(i[0], "") != "":
                temp_chart[i[0]] += 1
            else:
                temp_chart[i[0]] = 1

    return temp_chart


def show_execute(show_id, temp_chart, dates, s):
    playlists_found = 0
    misreads = 0
    misread_errors = ""

    for date in dates:
        try:
            result = s.values().get(spreadsheetId=show_id, range=date + "!A4:B200").execute()

            try:
                wrsu_nums = result.get('values', [])
                temp_chart = insert_values(temp_chart, wrsu_nums)

                playlists_found += 1

            except:
                misreads += 1
                misread_errors += date + " | "

        except HttpError as e:
            # No such sheet, this is fine
            if e.resp.status == 400:
                continue

            # API call error
            else:
                return temp_chart, e.resp.status, e.resp.reason

    if misreads > 0:
        return temp_chart, -2, str(misreads) + " misreads occurred on the following sheets: " + misread_errors + str(playlists_found) + " playlists were properly read for the given date range"

    elif playlists_found < 1:
        return temp_chart, -1, "Zero playlists were found for the given date range"

    else:
        return temp_chart, 0, ""


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

    # Build service object used to create drive api calls (Drive)
    driveService = build('drive', 'v3', http=driveCreds.authorize(Http()))

    # Make a list call (Drive)
    results = driveService.files().list(
        fields="nextPageToken, files(id, name)", q="name contains \"- Show Playlist\"").execute()
    items = results.get('files', [])

    # Load old permissions if possible (Sheets)
    sheetsStore = file.Storage('creds/token_sheets.json')
    sheetsCreds = sheetsStore.get()

    # Get api client creds (Sheets)
    if not sheetsCreds or sheetsCreds.invalid:
        flow = client.flow_from_clientsecrets('creds/client_id.json', sheetsScopes)
        sheetsCreds = tools.run_flow(flow, sheetsStore)

    # Build service object used to create sheets api calls (Sheets)
    sheetService = build('sheets', 'v4', http=sheetsCreds.authorize(Http()))
    sheet = sheetService.spreadsheets()

    # Create Chart
    chart = {}

    print('Errors:')
    if len(items) == 0:
        print("**NO FILES FOUND**")

    for item in items:
        chart, errVal, err = show_execute(item['id'], chart, {"01/03/18", "01/04/18", "01/05/18"}, sheet)

        if errVal != 0:
            print(item['name'] + ": \"" + err + "\"")

    print(chart)
