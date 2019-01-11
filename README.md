# WRSU-Playlist-Aggregator
Uses Google APIs to aggregate data for WRSU's weekly charts.

## Current Usage
Run *tester.py*. It will search your entire google drive for any files with the characters *"WRSU_SP"* in the title.
It then determines on which weekday each of these shows occurs by the last two characters in the title. *(MO, TU, WE, etc.)*
Cross-referencing this data with the weekday data of the week starting on a hard coded date *(01/01/19)* 
It then attempts to pull and aggregate playlist data for the specific days each show would have run on in that week.
After that it will write the chart data out to a sheet titled *(01/01/19)* in the document with *"WRSU_CHART"* in the title.