from datetime import time
from datetime import datetime

def channel_check(channel, keyword, sub_key, posted_channels):
    ''' Check if the channel already exists in the dictionary '''
    if channel in posted_channels:
        ch_values = posted_channels[channel]

        for index,item in enumerate(ch_values):
            if keyword == item[1] and sub_key == item[2]:
                ''' Retrieve stored time '''
                prev_time = item[0]
                ''' Retrieve current time '''
                curr_time = datetime.time(datetime.now().replace(microsecond=0))
                ''' Format the time and get the difference between the current and previous time '''
                fmt = "%H:%M:%S"
                diff = datetime.strptime(str(curr_time), fmt) - datetime.strptime(str(prev_time), fmt)
    
                ''' If its been longer than a minute '''
                if (str(diff) >= "0:01:00"):
                    ''' Means its okay to post again '''
                    del posted_channels[channel][index]
                    return False
                else:
                    ''' It hasnt been 1 minute and keyword and sub keyword were already pinged '''
                    return True
        ''' All dictionary entries were looked at and no duplicate value found '''
        return False
    else:
        posted_channels[channel] = []
        return False

    return True