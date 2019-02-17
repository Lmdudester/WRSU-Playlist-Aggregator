from googleapiclient.discovery import build
from oauth2client import file, client, tools
from httplib2 import Http
import time

driveScopes = 'https://www.googleapis.com/auth/drive.metadata.readonly'
sheetsScopes = 'https://www.googleapis.com/auth/spreadsheets'
clientIdPath = 'creds/client_id.json'

'''
___get_drive_service___
Gets the drive service object given the client_id path.
'''
def get_drive_service(dpath):
    # Load old permissions if possible (Drive)
    driveStore = file.Storage(dpath)
    driveCreds = driveStore.get()

    # Get api client creds (Drive)
    if not driveCreds or driveCreds.invalid:
        flow = client.flow_from_clientsecrets(clientIdPath, driveScopes)
        tools.run_flow(flow, driveStore)
        driveCreds = driveStore.get()

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

    # Get api client creds (Sheets)
    if not sheetsCreds or sheetsCreds.invalid:
        flow = client.flow_from_clientsecrets(clientIdPath, sheetsScopes)
        tools.run_flow(flow, sheetsStore)
        sheetsCreds = sheetsStore.get()

    # Build service object used to create sheets api calls (Sheets)
    return build('sheets', 'v4', http=sheetsCreds.authorize(Http()))


if __name__ == '__main__':
    # Build service object used to create drive api calls (Drive)
    driveService = get_drive_service('creds/token_drive.json')

    # Make a list call (Drive)
    results = driveService.files().list(
        fields="nextPageToken, files(id, name)", q="name contains \"WRSU_SP\"").execute()
    items = results.get('files', [])

    print("Drive token obtained.")

    # Delays auth long enough to process
    time.sleep(2)

    # Build service object used to create sheets api calls (Sheets)
    sheetService = get_sheet_service('creds/token_sheets.json')
    sheet = sheetService.spreadsheets()

    print("Sheets token obtained.")

    print("Credentials Updated. If failure continues, delete token_* from /creds folder and try again.")
