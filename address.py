import random, string, asyncio

class AddressJig(object):
    addresses = ''
    
    ''' Generates the 4 character code to be added to beginning of address. 
    
        @return: 4 Character code to be added to beginning of address '''
    def generate_code(self):
        code = ''
        for i in range(0,4):
            code += random.choice(string.ascii_uppercase)
            
        return code
        
    ''' Generates the 2nd part of the address
    
        @param address: The address passed by the user
        @param ctx: Discord information '''  
    async def generate_address_two(self, address, ctx):
        if address.replace(' ', '') == '':
            return("INVALID")
            #await client.send_message(ctx.message.author,"Please enter a valid address.")
        else:
            address_options = ['Apt', 'Apartment', 'Building', 'Bldg', 'Suite', 'Room', 'Condo', 'Unit']
            
            for i in range(1,16):
                index = random.randint(0, len(address_options)-1)
                address_2 = address_options[index]
                
                code = self.generate_code()
                num = 0
                if address_2 == 'Unit':
                    num = random.randint(5, 100)
                else:
                    num = random.randint(15, 500)
                
                self.addresses += code + ' ' + address + ' ' + address_2 + ' ' + str(num) + '\n'
            
            #embed = Embed(title="", color=0xff9300)
            #embed.add_field(name='Jigged Addresses', value=self.addresses, inline=True)
            return(self.addresses)
            #await client.send_message(ctx.message.author, embed=embed)