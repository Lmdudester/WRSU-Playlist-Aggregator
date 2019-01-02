from googleapiclient.discovery import build
from oauth2client import file, client, tools
from httplib2 import Http

driveScopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
sheetsScopes = 'https://www.googleapis.com/auth/spreadsheets.readonly'


if __name__ == '__main__':
    # Load in API Key
    keyfile = open("creds/api_key.txt", "r")
    api_key = keyfile.readline()

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

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

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

    # Get data from a sheet
    results = sheet.values().get(spreadsheetId=items[0]['id'],
                                 range="01/03/18!A4:A100").execute()
    print(results)
