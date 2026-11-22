import simplematrixbotlib as botlib
import asyncio


# Default system state
position = 0
instruction_sms = "**balance** - to verify your balance\n**buy** - to buy a temporary number"
input_buy_number = []
ids =[[], None]
domen = ""
credentials = [None, None, None]

# Callback
async def get_call(room, message, match: botlib.MessageMatch, bot: botlib.Bot, methods):
    global position, input_buy_number, ids, domen, credentials
    if position == 0:
            # 'new' command
            if match.is_not_from_this_bot() and match.prefix() and match.command("new"):
                await bot.api.send_markdown_message(room.room_id, "### Choose your provider:\n * 1) Catchmail ( publicly available - less private)\n * 2) mail.tm (Create a new instance with credentials - more private )" +
                    "\n* 3) Outlook (buy a new outlook account) ")
                position = 1

             # 'all' command to get the list of accounts
            elif match.is_not_from_this_bot() and match.prefix() and match.command("all"):
                try:
                    file = methods['read_files']()
                    response = "There are no emails" if file[0] == 0 else "Emails:\n"+"\n".join(file[1])
                    await bot.api.send_text_message(room.room_id, response)
                except:
                    await bot.api.send_text_message(room.room_id, "No emails")

            # 'receive' to set an address into listening mode
            elif match.is_not_from_this_bot() and match.prefix() and match.command("receive"):
                await bot.api.send_text_message(room.room_id, "Send an address of the email")
                position = 2


            elif match.is_not_from_this_bot() and match.prefix() and match.command("inbox"):
                await bot.api.send_text_message(room.room_id, "Specify the email for which you would like to see the inbox")
                position = 3
            elif match.is_not_from_this_bot() and match.prefix() and match.command("read"):
                await bot.api.send_text_message(room.room_id, "Specify the email for which you would like to read email")
                position = 4
            elif match.is_not_from_this_bot() and match.prefix() and match.command("send"):
                await bot.api.send_text_message(room.room_id, "Specify the text content")
                position = 6
            elif match.is_not_from_this_bot() and match.prefix() and match.command("sms"):
                await bot.api.send_markdown_message(room.room_id, instruction_sms)
                position = 10
            elif match.is_not_from_this_bot() and match.prefix() and match.command("delete"):
                await bot.api.send_text_message(room.room_id, "Enter an account")
                position = 9
            elif match.is_not_from_this_bot():
                    await bot.api.send_markdown_message(room.room_id, "new email - to create one-time temporary email and receive email\n" +
                        "all - to see existing emails\nreceive - to receive new messages from existing emails\ninbox -  to check the entire inbox\n"+
                        "read - to read a specific email\n **send** - to send email \n **delete** - to delete existing email address" +
                        "\n **sms** - to manage temporary numbers ")

    # Create a new disposable email
    elif position == 1:
        if match.is_not_from_this_bot():
           match int(message.body):
              case 1:
                  await bot.api.send_text_message(room.room_id, "Send a desirable address (without domain)")
                  position = 14
              case 2:
                  domen = methods['spawn_email']()
                  await bot.api.send_text_message(room.room_id, "Available domains:\n"+ domen)
                  await bot.api.send_text_message(room.room_id, "Send a desirable address (without domain)")
                  position = 13
              case 3:
                      await bot.api.send_markdown_message(room.room_id, f"Do you agree to buy an account for {await methods['buy_outlook'](False, bot, room.room_id)} rubles?\nYes/No")
                      position = 15
              case _:
                   await bot.api.send_text_message(room.room_id, "Error: invalid input")
                   position =0
    # Verify the cost
    elif position == 15:
        if match.is_not_from_this_bot() and message.body == "yes":
            result = await methods['buy_outlook'](True, bot, room.room_id)
            position = 0

        elif match.is_not_from_this_bot():
            await bot.api.send_text_message(room.room_id, "Error: Purchase process has been interrupted")
            position = 0

    elif position == 14:
        if match.is_not_from_this_bot():
            match methods['register_email'](f"{message.body}@catchmail.io"):
                case 0:
                    await bot.api.send_text_message(room.room_id, "Error: this address already recorded")
                case 1:
                    await bot.api.send_text_message(room.room_id, f"Success!\n {message.body}@catchmail.io was successfully created")


            position = 0



    # Mail.tml was chosen as the provider
    elif position == 13:
            if match.is_not_from_this_bot():
                resp = methods["spawn_account"](f"{message.body}@{domen}", "12345")
                match resp[0]:
                    case 200:
                        await bot.api.send_text_message(room.room_id, "Successfully created address, listener is starting...")
                        asyncio.create_task(methods["listen_mail"](resp, room.room_id))
                        position = 0
                    case _:
                        await bot.api.send_text_message(room.room_id, "Error: "+str(resp[0])+"\nmessage: "+resp[1])
                        position = 0 # Switch to main loop


    elif position == 2:
            if match.is_not_from_this_bot():
                try:
                    resp = methods['find_token'](message.body)
                    print("Found: ", resp)
                    asyncio.create_task(methods["listen_mail"](resp, room.room_id))
                    position = 0
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                    position = 0

    # Inbox
    elif position == 3:
            if match.is_not_from_this_bot():
                try:
                    token = methods['find_token'](message.body)[1]
                    result = methods['fetch'](token, message.body)
                    await bot.api.send_markdown_message(room.room_id, f"### Yout have total: {result[0]} messages")
                    items = "\n".join(f"* {item}" for item in result[1])
                    await bot.api.send_markdown_message(room.room_id,f"### The mesages:\n{items}")
                    position = 0
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                    position = 0

    # Read message
    elif position == 4:
            if match.is_not_from_this_bot():
                try:
                    token = methods['find_token'](message.body)[1]
                    result = methods['fetch'](token, message.body)
                    ids[0] = result[2]
                    ids[1] = result[3]
                    await bot.api.send_markdown_message(room.room_id, f"### Yout have total: {result[0]} messages")
                    items = "\n".join(f"* {item}" for item in result[1])
                    await bot.api.send_markdown_message(room.room_id,f"### The mesages:\n{items}")
                    await bot.api.send_text_message(room.room_id, "Print the number of the email to read or 'exit' to return")
                    position = 5
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                    position = 0
    # Get content
    elif position == 5:
            if match.is_not_from_this_bot():
                try:
                    if message.body == "exit":
                        await bot.api.send_text_message(room.room_id, "Your're back")
                        position = 0
                    else:
                        content =  methods['get_content'](ids[0][int(message.body)-1], ids[1], int(message.body))
                        await bot.api.send_markdown_message(room.room_id, "### Content: \n" + f"> {content[0]}")
                        await bot.api.send_markdown_message(room.room_id, "### HTML VERSION: \n" + f"> {content[1]}")
                        position = 0
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                    position = 0
    # Send email
    elif position == 6:
            if match.is_not_from_this_bot():
                    credentials[0] = message.body
                    await bot.api.send_text_message(room.room_id, "Enter the receiver")
                    position = 7
    elif position == 7:
            if match.is_not_from_this_bot():
                    credentials[1] = message.body
                    await bot.api.send_text_message(room.room_id, "Enter the subject")
                    position = 8
    elif position == 8:
            if match.is_not_from_this_bot():
                try:
                    credentials[2] = message.body
                    methods["send_mail"](credentials[0],credentials[1],credentials[2])
                    await bot.api.send_text_message(room.room_id, "Successfully sent")
                    position = 0
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                    position = 0
    elif position == 9:
            if match.is_not_from_this_bot():
                try:
                    delete_account(find_token(message.body)[2],find_token(message.body)[1])
                    await bot.api.send_text_message(room.room_id, f"{message.body} was deleted")
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                position = 0
    elif position == 10:
            # Look for a balance
            if match.is_not_from_this_bot() and match.prefix() and match.command("balance"):
                try:
                    balance = methods['get_balance']()
                    await bot.api.send_text_message(room.room_id, f"Your current balance: {balance}")
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")

            # Buy a new number
            if match.is_not_from_this_bot() and match.prefix() and match.command("buy"):
                try:
                    result = methods['buy_number'](match.args()[0], match.args()[1])
                    if result['result'] == "failed":
                         await bot.api.send_text_message(room.room_id, f"Unfortunately, the purchase failed.\nError: {result['message']}")
                         position = 10 # Return back
                    print("output: ", result)
                except:
                    await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")

    # Obtain service name
    elif position == 11:
        if match.is_not_from_this_bot():
                # Write the input as service name
                input_buy_number.append(message.body)
                await bot.api.send_text_message(room.room_id, "Ok, enter price range")
                position = 12
                # Obtain service name

    # Obtain price range and perform the purchase
    elif position == 12:
        if match.is_not_from_this_bot():
            try:
                input_buy_number.append(message.body)
                result = methods['buy_number'](input_buy_number[0], message.body)
                if result['result'] == "failed":
                     await bot.api.send_text_message(room.room_id, f"Unfortunately, the purchase failed.\nError: {result['message']}")
                     position = 10 # Return back
                print("output: ", result)

            except:
                # If failed
                await bot.api.send_text_message(room.room_id, "Unknown error: check your spelling ")
                position = 10 # Return to main menu for sms management
