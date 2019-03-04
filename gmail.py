import random, re, asyncio

class GmailJig(object):
    emails = ''
    
    ''' Kickstarts the Gmail Jigging Process.
        
        @param email: Email to be jigged
        @param ctx: Discord information '''
    def run(self, email):
        if email.replace(' ', '') == "":
            return("FAILED")
            #await client.send_message(ctx.message.author,"Empty input given. Please try again")
        else:
            return self.email_check(email)
            
            
    ''' Checks for a correct email (google email address only).
    
        @param email: Email to be checked
        @param ctx: Discord information '''
    def email_check(self, email):
        # Make sure gmail address was passed
        verified = re.search('(@gmail.+)', email)
        if verified == None:
            return("FAILED")
            #await client.send_message(ctx.message.author,"Invalid email address. Please use a @gmail address")
        else:
            # Store email provider/second part of email address -> @gmail...
            email_suffix = verified.group()
            # Store first part of email
            prefix = email.replace(email_suffix, '')
            # Make sure first part of email is of a reasonable length for jigging
            if len(prefix) > 2:
                return self.jig_email(prefix, email_suffix)
            else:
                return("FAILED")
                #await client.send_message(ctx.message.author,"Your email is not long enough. Please try another email")
    
    ''' Jigs a given gmail address.
    
        @param email_prefix: Everything before the @ sign
        @param email_suffix: Everything after the @ sign, @ sign included
        @param ctx: Discord information '''   
    def jig_email(self, email_prefix, email_suffix):
        # Keeps track of indices where period was applied
        used_indeces = []
        # Keeps track of indices neighboring an existing period + periods location
        email_dot_indeces = []
        # length of email prefix
        last_index = len(email_prefix) - 1
        limit = 6    
        stop = 0
        
        # Go through the prefix
        for index, character in enumerate(email_prefix):
            # If there is a dot anywhere in the prefix already
            if character == '.':
                # Keep track of its location and adjacent indexes
                email_dot_indeces.append(index)
                if index-1 not in email_dot_indeces:
                    email_dot_indeces.append(index-1)
                
                if (index + 1) < last_index and (index + 1) not in email_dot_indeces:
                    email_dot_indeces.append(index+1)
        # Limit the number of items to be displayed to the user           
        if limit < last_index - len(email_dot_indeces):
            stop = limit
        else:
            stop = (last_index - len(email_dot_indeces)) + 1
        # Randomly get an integer to serve as index to insert a dot    
        for i in range(1,stop):
            r = random.randint(1, last_index)
            # Make sure index is not already used
            if r not in used_indeces and r not in email_dot_indeces:
                used_indeces.append(r)
            else:
                while r in used_indeces or r in email_dot_indeces:
                    r = random.randint(1, last_index)
                    
                used_indeces.append(r)
            
        count = 0
        # Go through all the indeces to be used
        for i in used_indeces:
            # Add only 1 dot to email
            email_var = email_prefix[:i] + '.' + email_prefix[i:]
            self.emails += email_var + email_suffix + '\n'

            # Add 2 dots for variety
            if i == used_indeces[-1]:
                smaller = i if i < used_indeces[0] else used_indeces[0]
                larger = i if i > used_indeces[0] else used_indeces[0]
                
                email_var = email_prefix[:smaller] + '.' + email_prefix[smaller:larger] + '.' + email_prefix[larger:]
            else:
                smaller = i if i < used_indeces[count+1] else used_indeces[count+1]
                larger = i if i > used_indeces[count+1] else used_indeces[count+1]
                
                email_var = email_prefix[:smaller] + '.' + email_prefix[smaller:larger] + '.' + email_prefix[larger:]
            
            self.emails += email_var + email_suffix + '\n'
            count += 1
            
        #embed = Embed(title="", color=0xff2600)
        #embed.add_field(name='Jigged Gmail', value=self.emails, inline=True)
        emails = self.emails
        return(emails)